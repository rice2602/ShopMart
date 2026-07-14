import os
import json
import logging
from datetime import datetime
import pandas as pd

# Set up logging
logger = logging.getLogger("ShopMart-Pipeline")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(ch)

class ShopMartPipeline:
    def __init__(self, mode="local", storage_config=None):
        """
        Initialize the pipeline.
        mode: "local" for local disk-based simulation, "aws" for real S3/DynamoDB execution.
        """
        self.mode = mode
        self.storage_config = storage_config or {}
        
        if self.mode == "aws":
            import boto3
            self.s3_client = boto3.client("s3")
            self.dynamodb = boto3.resource("dynamodb")
            self.metadata_table = self.dynamodb.Table(self.storage_config.get("metadata_table", "shopmart-metadata"))
            self.sns_client = boto3.client("sns")
            self.sns_topic_arn = self.storage_config.get("sns_topic_arn")
        else:
            # Local Simulation configuration
            self.local_raw_dir = self.storage_config.get("local_raw", "data/raw")
            self.local_processed_dir = self.storage_config.get("local_processed", "data/processed")
            self.local_quarantine_dir = self.storage_config.get("local_quarantine", "data/quarantine")
            self.local_metadata_file = self.storage_config.get("local_metadata", "data/metadata.json")
            
            # Ensure local directories exist
            os.makedirs(self.local_raw_dir, exist_ok=True)
            os.makedirs(self.local_processed_dir, exist_ok=True)
            os.makedirs(self.local_quarantine_dir, exist_ok=True)
            self._init_local_metadata()

    def _init_local_metadata(self):
        """Initialize the local JSON file tracking metadata if running locally."""
        if not os.path.exists(self.local_metadata_file):
            with open(self.local_metadata_file, "w") as f:
                json.dump({}, f)

    def _check_idempotency(self, file_name):
        """
        Check if the file has been processed successfully.
        Returns:
            bool: True if already processed successfully (or is currently duplicate), False otherwise.
        """
        if self.mode == "aws":
            try:
                response = self.metadata_table.get_item(Key={"file_name": file_name})
                if "Item" in response:
                    status = response["Item"].get("processing_status")
                    if status == "SUCCESS":
                        return True
            except Exception as e:
                logger.error(f"Error querying DynamoDB for file {file_name}: {str(e)}")
            return False
        else:
            with open(self.local_metadata_file, "r") as f:
                metadata = json.load(f)
            if file_name in metadata:
                return metadata[file_name].get("processing_status") == "SUCCESS"
            return False

    def _log_metadata(self, file_name, status, record_count=0, error_reason=None, metrics=None):
        """Log execution metadata to S3/DynamoDB or local JSON."""
        timestamp = datetime.utcnow().isoformat()
        log_entry = {
            "file_name": file_name,
            "processing_status": status,
            "timestamp": timestamp,
            "record_count": int(record_count),
            "error_reason": error_reason or "N/A"
        }
        if metrics:
            log_entry["metrics"] = metrics

        if self.mode == "aws":
            try:
                self.metadata_table.put_item(Item=log_entry)
            except Exception as e:
                logger.error(f"Failed to log metadata to DynamoDB: {str(e)}")
        else:
            with open(self.local_metadata_file, "r") as f:
                metadata = json.load(f)
            metadata[file_name] = log_entry
            with open(self.local_metadata_file, "w") as f:
                json.dump(metadata, f, indent=4)

    def _send_alert(self, file_name, error_reason):
        """Send alerting email/notification via SNS or log message locally."""
        message = f"CRITICAL: ShopMart Data Pipeline processing failed for file: {file_name}. Reason: {error_reason}"
        logger.warning(f"ALERT DISPATCHED: {message}")
        if self.mode == "aws" and self.sns_topic_arn:
            try:
                self.sns_client.publish(
                    TopicArn=self.sns_topic_arn,
                    Subject=f"ShopMart Pipeline Alert: {file_name}",
                    Message=message
                )
            except Exception as e:
                logger.error(f"Failed to send SNS alert: {str(e)}")

    def process_data(self, file_name, file_content_bytes):
        """
        Main data processing routine.
        Validates headers, cleans data, computes metrics, partitions output, and logs metadata.
        """
        logger.info(f"Starting processing for file: {file_name}")

        # 1. Idempotency validation
        if self._check_idempotency(file_name):
            logger.info(f"File {file_name} was already processed successfully. Skipping.")
            self._log_metadata(file_name, "DUPLICATE", error_reason="Duplicate file upload ignored")
            return {"status": "SKIPPED_DUPLICATE", "file_name": file_name}

        try:
            # Import bytes into Pandas DataFrame
            from io import BytesIO
            df = pd.read_csv(BytesIO(file_content_bytes))
        except Exception as e:
            # File is corrupt or not a CSV
            err_msg = f"Failed to parse CSV file: {str(e)}"
            logger.error(err_msg)
            self._log_metadata(file_name, "FAILED", error_reason=err_msg)
            self._send_alert(file_name, err_msg)
            # Write raw content to quarantine
            self._write_quarantine_raw(file_name, file_content_bytes)
            return {"status": "FAILED", "file_name": file_name, "reason": err_msg}

        # 2. Schema Validation
        required_columns = ["order_id", "customer_id", "product_id", "order_date", "quantity", "unit_price", "payment_status"]
        missing_cols = [col for col in required_columns if col not in df.columns]
        
        if missing_cols:
            err_msg = f"Schema validation failed. Missing columns: {missing_cols}"
            logger.error(err_msg)
            self._log_metadata(file_name, "FAILED", error_reason=err_msg)
            self._send_alert(file_name, err_msg)
            self._write_quarantine_raw(file_name, file_content_bytes)
            return {"status": "FAILED", "file_name": file_name, "reason": err_msg}

        # Handle completely empty files
        if len(df) == 0:
            err_msg = "CSV file is empty"
            logger.warning(err_msg)
            self._log_metadata(file_name, "SUCCESS", record_count=0, error_reason="Empty file processed")
            return {"status": "SUCCESS_EMPTY", "file_name": file_name}

        # 3. Clean Data & Route to Quarantine/Processed
        # A row is quarantined if:
        # - order_id, customer_id, product_id, or order_date are null
        # - quantity is null, non-numeric, or <= 0
        # - unit_price is null, non-numeric, or <= 0
        
        # Make a copy of raw data for tracking original invalid entries
        df_clean = df.copy()

        # Fill missing payment status with UNKNOWN
        df_clean["payment_status"] = df_clean["payment_status"].fillna("UNKNOWN").astype(str).str.strip().str.lower()

        # Coerce numeric columns to float/integer to expose invalid inputs
        df_clean["quantity"] = pd.to_numeric(df_clean["quantity"], errors="coerce")
        df_clean["unit_price"] = pd.to_numeric(df_clean["unit_price"], errors="coerce")

        # Create validation mask
        valid_mask = (
            df_clean["order_id"].notna() & (df_clean["order_id"].astype(str).str.strip() != "") &
            df_clean["customer_id"].notna() & (df_clean["customer_id"].astype(str).str.strip() != "") &
            df_clean["product_id"].notna() & (df_clean["product_id"].astype(str).str.strip() != "") &
            df_clean["order_date"].notna() & (df_clean["order_date"].astype(str).str.strip() != "") &
            df_clean["quantity"].notna() & (df_clean["quantity"] > 0) &
            df_clean["unit_price"].notna() & (df_clean["unit_price"] > 0)
        )

        df_good = df_clean[valid_mask].copy()
        df_bad = df[~valid_mask].copy() # keep original formatting for quarantine

        # Deduplication based on order_id and product_id (on valid rows only)
        # Keeps first occurrence, moves duplicates to bad/quarantine
        if not df_good.empty:
            dup_mask = df_good.duplicated(subset=["order_id", "product_id"], keep="first")
            df_dups = df_good[dup_mask].copy()
            df_good = df_good[~dup_mask].copy()

            if not df_dups.empty:
                # Add duplicate rows back to bad dataframe using original indices
                dup_original = df[df.index.isin(df_dups.index)].copy().reset_index(drop=True)
                df_bad = pd.concat([df_bad.reset_index(drop=True), dup_original], ignore_index=True)

        # 4. Computation and Aggregation on valid, non-duplicate records
        metrics = None
        if not df_good.empty:
            # Compute line_revenue
            df_good["line_revenue"] = df_good["quantity"] * df_good["unit_price"]
            df_good["line_revenue"] = df_good["line_revenue"].round(2)

            # Compute aggregations for reporting summary
            # Filter paid transactions for daily revenue
            paid_txs = df_good[df_good["payment_status"] == "paid"]
            daily_revenue = float(paid_txs["line_revenue"].sum())

            # Top product by quantity
            if not paid_txs.empty:
                top_product_series = paid_txs.groupby("product_id")["quantity"].sum()
                top_product = str(top_product_series.idxmax()) if not top_product_series.empty else "N/A"
            else:
                top_product = "N/A"

            # Payment Success Rate
            total_orders = len(df_good)
            paid_orders = len(paid_txs)
            payment_success_rate = float(paid_orders / total_orders) if total_orders > 0 else 0.0

            metrics = {
                "daily_revenue": round(daily_revenue, 2),
                "top_product": top_product,
                "payment_success_rate": round(payment_success_rate, 4),
                "valid_records_count": len(df_good),
                "quarantined_records_count": len(df_bad)
            }
            logger.info(f"Metrics calculated: {metrics}")

        # 5. Output Storage Routing
        # Save processed Parquet data
        if not df_good.empty:
            self._write_processed_parquet(file_name, df_good)
            
            # Save a copy of aggregated metrics
            if metrics:
                self._write_metrics_summary(file_name, metrics)

        # Save quarantined CSV records
        if not df_bad.empty:
            self._write_quarantine_csv(file_name, df_bad)
            # Dispatch warning alert if quarantine files contain items
            # BR-5 Alert when data quality issues are detected
            self._send_alert(file_name, f"Quarantined {len(df_bad)} records containing schema, duplicate, or validation errors.")

        # 6. Log final success status in database/metadata log
        self._log_metadata(
            file_name=file_name,
            status="SUCCESS",
            record_count=len(df_good),
            error_reason=None if len(df_bad) == 0 else f"Quarantined {len(df_bad)} rows",
            metrics=metrics
        )

        return {
            "status": "SUCCESS",
            "file_name": file_name,
            "processed_records": len(df_good),
            "quarantined_records": len(df_bad),
            "metrics": metrics
        }

    def _write_processed_parquet(self, file_name, df):
        """Write processed Pandas DataFrame to parquet format on S3 or local disk."""
        if self.mode == "aws":
            # Buffer Parquet output to memory and upload to S3
            from io import BytesIO
            parquet_buffer = BytesIO()
            df.to_parquet(parquet_buffer, index=False)
            
            # Format partition path: yyyy/mm/dd/
            # Use order_date of the first record or current date as backup
            try:
                date_str = str(df["order_date"].iloc[0]).split(" ")[0] # extract YYYY-MM-DD
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                dt = datetime.utcnow()
                
            partition_path = dt.strftime("year=%Y/month=%m/day=%d")
            base_name = file_name.replace(".csv", ".parquet")
            s3_key = f"processed/{partition_path}/{base_name}"
            
            try:
                self.s3_client.put_object(
                    Bucket=self.storage_config["processed_bucket"],
                    Key=s3_key,
                    Body=parquet_buffer.getvalue()
                )
                logger.info(f"Uploaded processed parquet to s3://{self.storage_config['processed_bucket']}/{s3_key}")
            except Exception as e:
                logger.error(f"Failed to upload processed parquet to S3: {str(e)}")
                raise e
        else:
            # Local disk layout: data/processed/year=YYYY/month=MM/day=DD/filename.parquet
            try:
                date_str = str(df["order_date"].iloc[0]).split(" ")[0]
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                dt = datetime.utcnow()
            
            partition_dir = os.path.join(
                self.local_processed_dir,
                f"year={dt.strftime('%Y')}",
                f"month={dt.strftime('%m')}",
                f"day={dt.strftime('%d')}"
            )
            os.makedirs(partition_dir, exist_ok=True)
            
            base_name = file_name.replace(".csv", ".parquet")
            output_path = os.path.join(partition_dir, base_name)
            df.to_parquet(output_path, index=False)
            logger.info(f"Saved processed parquet to {output_path}")

    def _write_quarantine_csv(self, file_name, df):
        """Write quarantined data to CSV on S3 or local disk."""
        if self.mode == "aws":
            from io import StringIO
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            s3_key = f"quarantine/{file_name}"
            
            try:
                self.s3_client.put_object(
                    Bucket=self.storage_config["quarantine_bucket"],
                    Key=s3_key,
                    Body=csv_buffer.getvalue()
                )
                logger.info(f"Uploaded quarantined records to s3://{self.storage_config['quarantine_bucket']}/{s3_key}")
            except Exception as e:
                logger.error(f"Failed to upload quarantined CSV to S3: {str(e)}")
        else:
            output_path = os.path.join(self.local_quarantine_dir, file_name)
            df.to_csv(output_path, index=False)
            logger.info(f"Saved quarantined CSV to {output_path}")

    def _write_quarantine_raw(self, file_name, file_content_bytes):
        """Write raw invalid files directly to quarantine S3 or local disk."""
        if self.mode == "aws":
            s3_key = f"quarantine/raw_{file_name}"
            try:
                self.s3_client.put_object(
                    Bucket=self.storage_config["quarantine_bucket"],
                    Key=s3_key,
                    Body=file_content_bytes
                )
                logger.info(f"Uploaded quarantined raw file to s3://{self.storage_config['quarantine_bucket']}/{s3_key}")
            except Exception as e:
                logger.error(f"Failed to upload quarantined raw file to S3: {str(e)}")
        else:
            output_path = os.path.join(self.local_quarantine_dir, f"raw_{file_name}")
            with open(output_path, "wb") as f:
                f.write(file_content_bytes)
            logger.info(f"Saved quarantined raw file to {output_path}")

    def _write_metrics_summary(self, file_name, metrics):
        """Write daily aggregate metrics in JSON format to S3 processed bucket or local disk."""
        metrics_payload = json.dumps(metrics, indent=4)
        if self.mode == "aws":
            metrics_key = f"aggregates/{file_name.replace('.csv', '_metrics.json')}"
            try:
                self.s3_client.put_object(
                    Bucket=self.storage_config["processed_bucket"],
                    Key=metrics_key,
                    Body=metrics_payload
                )
                logger.info(f"Uploaded daily metrics summary to s3://{self.storage_config['processed_bucket']}/{metrics_key}")
            except Exception as e:
                logger.error(f"Failed to upload daily metrics summary to S3: {str(e)}")
        else:
            metrics_dir = os.path.join(self.local_processed_dir, "aggregates")
            os.makedirs(metrics_dir, exist_ok=True)
            output_path = os.path.join(metrics_dir, file_name.replace(".csv", "_metrics.json"))
            with open(output_path, "w") as f:
                f.write(metrics_payload)
            logger.info(f"Saved daily metrics summary to {output_path}")

# Lambda Handler Entry Point
def lambda_handler(event, context):
    """
    AWS Lambda entry point triggered by S3 ObjectCreated events.
    """
    import boto3
    s3 = boto3.client("s3")
    
    # Extract buckets and DynamoDB table names from environment variables
    processed_bucket = os.environ["PROCESSED_BUCKET_NAME"]
    quarantine_bucket = os.environ["QUARANTINE_BUCKET_NAME"]
    metadata_table = os.environ["METADATA_TABLE_NAME"]
    sns_topic_arn = os.environ.get("SNS_TOPIC_ARN", "")
    
    pipeline = ShopMartPipeline(
        mode="aws",
        storage_config={
            "processed_bucket": processed_bucket,
            "quarantine_bucket": quarantine_bucket,
            "metadata_table": metadata_table,
            "sns_topic_arn": sns_topic_arn
        }
    )
    
    # Process all objects in the event trigger
    results = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        
        # Download raw file from S3 raw bucket
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            file_content = response["Body"].read()
            file_name = os.path.basename(key)
            
            result = pipeline.process_data(file_name, file_content)
            results.append(result)
        except Exception as e:
            logger.error(f"Lambda execution failed for object s3://{bucket}/{key}: {str(e)}")
            results.append({"status": "ERROR", "key": key, "error": str(e)})
            
    return {
        "statusCode": 200,
        "body": json.dumps(results)
    }

if __name__ == "__main__":
    # Local simulation test execution
    print("--- Running Local Simulation of ShopMart Pipeline ---")
    pipeline = ShopMartPipeline(
        mode="local",
        storage_config={
            "local_raw": "data/raw",
            "local_processed": "data/processed",
            "local_quarantine": "data/quarantine",
            "local_metadata": "data/metadata.json"
        }
    )
    
    # Read sample sales data
    sample_file_path = "sample_sales_data.csv"
    if os.path.exists(sample_file_path):
        with open(sample_file_path, "rb") as f:
            content = f.read()
        res = pipeline.process_data("store_101_20260707.csv", content)
        print("Pipeline Result:")
        print(json.dumps(res, indent=4))
    else:
        print(f"Sample sales data file not found at: {sample_file_path}")
