# ShopMart AWS Sales Data Pipeline Architecture

This document details the system design, architectural choices, decision records, and operational failure scenarios for the automated ShopMart sales data pipeline.

---

## 1. Architecture Diagram & Data Flow

Below is the end-to-end architecture diagram showing the data lifecycle from store upload to business intelligence consumption.

```mermaid
graph TD
    subgraph Ingestion ["1. Ingestion Layer"]
        A[50 Store POS Terminals] -->|Daily CSV Uploads| B["Amazon S3: shopmart-raw-data<br/>(Naming: store_id_YYYYMMDD.csv)"]
    end

    subgraph Processing ["2. Processing & Validation Layer"]
        B -->|S3 ObjectCreated Event| C["AWS Lambda: shopmart-data-processor<br/>(Python + Pandas + PyArrow)"]
        C -->|1. Check Idempotency| D[("Amazon DynamoDB:<br/>shopmart-metadata")]
    end

    subgraph Storage ["3. Storage Layer"]
        C -->|2. Valid Records (Parquet)| E["Amazon S3: shopmart-processed-data<br/>(Partitioned: yyyy/mm/dd/)"]
        C -->|3. Rejected Records (CSV)| F["Amazon S3: shopmart-quarantine-data<br/>(Error Logged)"]
        C -->|4. Update File Status| D
    end

    subgraph Monitoring ["4. Observability & Alerting"]
        C -->|Lambda Logs & Metrics| G[Amazon CloudWatch]
        G -->|Alarms: Errors/Timeouts| H[Amazon SNS Topic]
        H -->|Alerts| I[BI / DevOps Team]
    end

    subgraph Consumption ["5. Consumption & BI Layer"]
        E -->|Glue Schema Mapping| J[AWS Glue Data Catalog]
        J -->|External Table Metadata| K[Amazon Athena]
        K -->|SQL Query Results| L[Amazon QuickSight / BI Dashboard]
    end

    classDef aws fill:#FF9900,stroke:#333,stroke-width:1px,color:#fff;
    classDef storage fill:#1A73E8,stroke:#333,stroke-width:1px,color:#fff;
    classDef process fill:#34A853,stroke:#333,stroke-width:1px,color:#fff;
    
    class B,E,F storage;
    class C process;
    class D,J,K,L aws;
```

### Ingestion to Consumption Lifecycle

1. **Ingestion:** Store uploads a CSV file matching the format `store_{store_id}_{YYYYMMDD}.csv` to the S3 Raw Bucket.
2. **Trigger & Execution:** The upload triggers an AWS Lambda function asynchronously.
3. **Idempotency Check:** The Lambda queries DynamoDB to verify if the file has already been processed successfully. If yes, it skips processing.
4. **Data Cleaning & Schema Validation:** Lambda verifies headers and types, filters duplicates, cleans missing values, flags negative quantities/null values, and computes `line_revenue = quantity * unit_price`.
5. **Output Routing:**
   - **Good Data:** Clean records are written to the Processed S3 bucket in Parquet format, partitioned by date.
   - **Quarantined Data:** Invalid records are isolated in the Quarantine S3 bucket with raw CSV layout for troubleshooting.
   - **Metadata Logging:** DynamoDB is updated with processing stats (e.g. success/failed/duplicate status, record count, execution time, timestamp).
6. **Analytics Execution:** AWS Glue catalog tracks the schema of the partitioned Parquet files. Athena runs serverless SQL queries against this catalog, feeding Amazon QuickSight or internal reports.

---

## 2. Architecture Decision Records (ADRs)

### ADR-01: Serverless Compute with AWS Lambda

*   **Context:**
    The system processes files daily from 50 stores, with a concentrated upload window between 6:00 AM and 8:00 AM. Total daily rows range from 25,000 to 250,000 rows. Provisioning a dedicated server or Spark cluster would be highly idle outside this window.
*   **Decision:**
    Use **AWS Lambda** (Python 3.11 run-time) triggered directly via S3 `s3:ObjectCreated:*` notifications.
*   **Alternatives Considered:**
    *   *AWS Glue ETL:* Rejected due to higher start-up cost (minutes vs. milliseconds) and high baseline costs for small datasets.
    *   *Amazon EC2 / ECS:* Rejected due to the operational complexity of auto-scaling, OS patch management, and cost overhead.
*   **Consequences:**
    *   *Advantages:* Scaling is automated and instant. Costs are zero when no files are uploaded.
    *   *Trade-offs:* 15-minute runtime ceiling and 10 GB ephemeral storage limit. However, the largest daily file (~5,000 rows) takes less than 5 seconds to process, meaning limits are well respected.

### ADR-02: Columnar storage using Parquet

*   **Context:**
    ShopMart needs to query historical sales data efficiently for business intelligence reports. Querying raw CSV files in Athena requires scanning entire columns, which incurs higher query costs and slower execution as data grows over time.
*   **Decision:**
    Convert all cleaned data to **Apache Parquet format** prior to saving in the Processed S3 bucket.
*   **Alternatives Considered:**
    *   *Direct CSV storage:* Rejected because querying is slow and expensive for long-term aggregate analytical workloads.
    *   *Relational DB (Amazon RDS):* Rejected due to provisioning cost, storage management, and lack of serverless query scaling for analytical workloads.
*   **Consequences:**
    *   *Advantages:* Columnar compression yields up to 90% storage savings and significantly reduces data scanned by Athena, lowering query costs.
    *   *Trade-offs:* Requires bundling Pandas and PyArrow dependencies in the Lambda deployment package/layer, increasing deployment package size.

### ADR-03: DynamoDB for Metadata Tracking and Idempotency

*   **Context:**
    Network failures or manual retries may cause stores to upload the same file multiple times. We must prevent double-counting of daily sales revenue and track the operational state of the ingestion pipeline.
*   **Decision:**
    Maintain an **Amazon DynamoDB table** (`shopmart-metadata`) with `file_name` as the partition key.
*   **Alternatives Considered:**
    *   *RDS Metadata Table:* Rejected due to cost and connection management scaling issues in serverless architectures.
    *   *S3 File Inventory / Log Files:* Scanning S3 to check for past files is slow and expensive (O(N) operations).
*   **Consequences:**
    *   *Advantages:* Offers sub-millisecond lookup and write capabilities, simple key-value indexing, and automatically scales to handle simultaneous file checks.
    *   *Trade-offs:* Requires configuring DynamoDB write capacity units (WCU) and read capacity units (RCU), though it easily fits in the DynamoDB Free Tier (25 GB, 25 WCU/RCU).

---

## 3. Failure Scenarios and Recovery Strategies

### Scenario 1: Schema Mismatch & Data Quality Failures

*   **What happens:** A store uploads a CSV file containing missing columns, altered headers, or extensive quality anomalies (e.g. unit prices containing letters or completely blank rows).
*   **Detection:** Lambda validation logic catches schema discrepancies or types checks via exception handling and validation assertions.
*   **Recovery Strategy:**
    1. The entire input file or the specific broken rows are written to the Quarantine S3 bucket (`shopmart-quarantine-data`).
    2. The processing execution status is logged as `FAILED` in the DynamoDB metadata table with a detailed `error_reason`.
    3. The file is skipped from processed aggregates to maintain reporting integrity.
*   **Notification:** Lambda sends an alert to the SNS alerting topic, which dispatches a notification email/Slack ping to the Data Operations team.

### Scenario 2: Duplicate File Upload

*   **What happens:** A store POS terminal uploads `store_001_20260707.csv` twice due to a local network hiccup, which could double-count sales.
*   **Detection:** Prior to processing, the Lambda queries the DynamoDB metadata table for the incoming filename. If the record exists and status is `SUCCESS`, it triggers the duplicate event exception.
*   **Recovery Strategy:**
    1. The pipeline logs a warning and marks the file status as `DUPLICATE` in DynamoDB.
    2. Lambda returns successfully without performing transformations or writing records to the processed storage zone.
*   **Notification:** Recorded in CloudWatch and DynamoDB logs; no pager alert is dispatched since it is handled gracefully.

### Scenario 3: Lambda Timeout or Runtime Crash

*   **What happens:** The Lambda processing function runs out of memory or times out due to AWS resource constraints or an unhandled python dependency crash.
*   **Detection:** CloudWatch tracks the execution duration and execution failure rate. A CloudWatch Metric Alarm triggers if the failure rate exceeds 0.
*   **Recovery Strategy:**
    1. The S3 Event notification automatically retries execution up to 2 times (default S3-to-Lambda retry policy).
    2. If all retries fail, S3 events are sent to a Dead Letter Queue (DLQ) SQS Queue to preserve the event message.
    3. The metadata status in DynamoDB remains untracked or is caught by a dead-letter monitor.
*   **Notification:** SNS Alert sends high-priority notifications to the DevOps infrastructure team.
