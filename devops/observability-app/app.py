import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import pandas as pd

app = Flask(__name__)

# Config logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Observability-App")

# Paths for local file system discovery
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOCAL_METADATA_FILE = os.path.join(WORKSPACE_ROOT, "data", "metadata.json")
LOCAL_RAW_DIR = os.path.join(WORKSPACE_ROOT, "data", "raw")
LOCAL_PROCESSED_DIR = os.path.join(WORKSPACE_ROOT, "data", "processed")

def get_metadata():
    """Reads processing metadata registry. Yields mock data if the pipeline registry is empty."""
    # Check if real metadata exists
    if os.path.exists(LOCAL_METADATA_FILE):
        try:
            with open(LOCAL_METADATA_FILE, "r") as f:
                data = json.load(f)
                if data:
                    return data
        except Exception as e:
            logger.error(f"Failed to read metadata file: {str(e)}")
            
    # Mock data to ensure the dashboard looks stunning on initial load
    return {
        "store_01_20260705.csv": {
            "file_name": "store_01_20260705.csv",
            "processing_status": "SUCCESS",
            "timestamp": "2026-07-05T08:15:32",
            "record_count": 1420,
            "error_reason": "N/A",
            "metrics": {
                "daily_revenue": 45120.50,
                "top_product": "PROD102",
                "payment_success_rate": 0.965,
                "valid_records_count": 1395,
                "quarantined_records_count": 25
            }
        },
        "store_12_20260705.csv": {
            "file_name": "store_12_20260705.csv",
            "processing_status": "SUCCESS",
            "timestamp": "2026-07-05T08:24:11",
            "record_count": 890,
            "error_reason": "N/A",
            "metrics": {
                "daily_revenue": 21300.00,
                "top_product": "PROD101",
                "payment_success_rate": 0.981,
                "valid_records_count": 882,
                "quarantined_records_count": 8
            }
        },
        "store_05_20260706.csv": {
            "file_name": "store_05_20260706.csv",
            "processing_status": "SUCCESS",
            "timestamp": "2026-07-06T08:10:02",
            "record_count": 3120,
            "error_reason": "Quarantined 45 rows",
            "metrics": {
                "daily_revenue": 89450.25,
                "top_product": "PROD104",
                "payment_success_rate": 0.945,
                "valid_records_count": 3075,
                "quarantined_records_count": 45
            }
        },
        "store_02_20260706_corrupt.csv": {
            "file_name": "store_02_20260706_corrupt.csv",
            "processing_status": "FAILED",
            "timestamp": "2026-07-06T08:44:19",
            "record_count": 0,
            "error_reason": "Schema validation failed. Missing columns: ['payment_status']",
            "metrics": None
        },
        "store_01_20260705_dup.csv": {
            "file_name": "store_01_20260705_dup.csv",
            "processing_status": "DUPLICATE",
            "timestamp": "2026-07-06T08:52:00",
            "record_count": 0,
            "error_reason": "Duplicate file upload ignored",
            "metrics": None
        }
    }

@app.route("/")
def index():
    metadata = get_metadata()
    
    # Calculate global metrics for the dashboard
    total_files = len(metadata)
    successful_files = sum(1 for f in metadata.values() if f["processing_status"] == "SUCCESS")
    failed_files = sum(1 for f in metadata.values() if f["processing_status"] == "FAILED")
    duplicate_files = sum(1 for f in metadata.values() if f["processing_status"] == "DUPLICATE")
    
    total_revenue = 0.0
    total_valid_records = 0
    total_quarantined_records = 0
    
    for item in metadata.values():
        if item["metrics"]:
            total_revenue += item["metrics"].get("daily_revenue", 0.0)
            total_valid_records += item["metrics"].get("valid_records_count", 0)
            total_quarantined_records += item["metrics"].get("quarantined_records_count", 0)
            
    # Success rate
    pipeline_success_rate = (successful_files / total_files * 100) if total_files > 0 else 0.0

    return render_template(
        "index.html",
        metadata=metadata,
        stats={
            "total_files": total_files,
            "successful_files": successful_files,
            "failed_files": failed_files,
            "duplicate_files": duplicate_files,
            "total_revenue": round(total_revenue, 2),
            "total_valid_records": total_valid_records,
            "total_quarantined_records": total_quarantined_records,
            "success_rate": round(pipeline_success_rate, 1)
        }
    )

@app.route("/api/metrics")
def api_metrics():
    """Returns metadata dashboard data as JSON."""
    return jsonify(get_metadata())

@app.route("/api/simulate", methods=["POST"])
def simulate_upload():
    """Simulates raw CSV upload and runs the local pipeline in real-time."""
    scenario = request.json.get("scenario", "happy")
    timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
    
    from src.pipeline import ShopMartPipeline
    pipeline = ShopMartPipeline(mode="local")
    
    if scenario == "happy":
        file_name = f"store_99_{timestamp_str}.csv"
        csv_content = (
            "order_id,customer_id,product_id,order_date,quantity,unit_price,payment_status\n"
            f"ORD901,CUST009,PROD102,2026-07-07,5,49.99,paid\n"
            f"ORD902,CUST010,PROD104,2026-07-07,2,120.00,paid\n"
            f"ORD903,CUST011,PROD101,2026-07-07,1,29.99,pending\n"
        )
    elif scenario == "corrupt":
        file_name = f"store_error_{timestamp_str}.csv"
        csv_content = (
            "order_id,customer_id,quantity,unit_price\n" # Missing key columns
            "ORD999,CUST999,10,15.00\n"
        )
    elif scenario == "quality_warning":
        file_name = f"store_warn_{timestamp_str}.csv"
        # Duplicate row, negative quantity, empty price, valid row
        csv_content = (
            "order_id,customer_id,product_id,order_date,quantity,unit_price,payment_status\n"
            "ORD501,CUST501,PROD101,2026-07-07,2,29.99,paid\n"  # Valid
            "ORD502,CUST502,PROD102,2026-07-07,-1,49.99,paid\n" # Bad Quantity
            "ORD503,CUST503,PROD103,2026-07-07,3,,pending\n"    # Bad Price
            "ORD501,CUST501,PROD101,2026-07-07,2,29.99,paid\n"  # Duplicate
        )
    else:
        return jsonify({"error": "Unknown scenario"}), 400

    try:
        # Run processing logic directly
        result = pipeline.process_data(file_name, csv_content.encode("utf-8"))
        return jsonify({
            "message": "Simulation executed successfully",
            "file_name": file_name,
            "pipeline_result": result
        })
    except Exception as e:
        return jsonify({"error": f"Failed to simulate pipeline execution: {str(e)}"}), 500

if __name__ == "__main__":
    # Standard local debug port 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
