import os
import json
import pytest
import pandas as pd
from src.pipeline import ShopMartPipeline

@pytest.fixture
def test_setup(tmp_path):
    """Fixture to set up temporary simulation directories for each test run."""
    local_raw = tmp_path / "raw"
    local_processed = tmp_path / "processed"
    local_quarantine = tmp_path / "quarantine"
    local_metadata = tmp_path / "metadata.json"
    
    storage_config = {
        "local_raw": str(local_raw),
        "local_processed": str(local_processed),
        "local_quarantine": str(local_quarantine),
        "local_metadata": str(local_metadata)
    }
    
    pipeline = ShopMartPipeline(mode="local", storage_config=storage_config)
    return pipeline, storage_config

def test_case_1_happy_path(test_setup):
    """TC1: Happy Path - Process a clean valid CSV, checking output formats and metrics."""
    pipeline, config = test_setup
    
    # 1. Define clean sales data CSV content
    csv_content = (
        "order_id,customer_id,product_id,order_date,quantity,unit_price,payment_status\n"
        "ORD001,CUST001,PROD101,2024-01-15,2,29.99,paid\n"
        "ORD002,CUST002,PROD102,2024-01-15,1,49.99,paid\n"
        "ORD003,CUST003,PROD103,2024-01-15,3,10.00,pending\n"
    )
    
    file_name = "store_001_20260707.csv"
    result = pipeline.process_data(file_name, csv_content.encode("utf-8"))
    
    # 2. Assertions
    assert result["status"] == "SUCCESS"
    assert result["processed_records"] == 3
    assert result["quarantined_records"] == 0
    
    # Check computed metrics
    # Only "paid" status rows count for daily revenue (ORD001 & ORD002)
    # daily_revenue = (2 * 29.99) + (1 * 49.99) = 59.98 + 49.99 = 109.97
    assert result["metrics"]["daily_revenue"] == 109.97
    # 2 paid out of 3 total records = 0.6667 success rate
    assert result["metrics"]["payment_success_rate"] == 0.6667
    
    # Check processed Parquet file generation
    processed_files = []
    for root, dirs, files in os.walk(config["local_processed"]):
        for file in files:
            if file.endswith(".parquet"):
                processed_files.append(os.path.join(root, file))
                
    assert len(processed_files) == 1
    
    # Verify metadata entry in local file database
    with open(config["local_metadata"], "r") as f:
        meta = json.load(f)
    assert file_name in meta
    assert meta[file_name]["processing_status"] == "SUCCESS"
    assert meta[file_name]["record_count"] == 3

def test_case_2_missing_columns(test_setup):
    """TC2: Schema Validation - File missing columns is rejected and quarantined."""
    pipeline, config = test_setup
    
    # Header missing product_id and payment_status
    csv_content = (
        "order_id,customer_id,order_date,quantity,unit_price\n"
        "ORD001,CUST001,2024-01-15,2,29.99\n"
    )
    
    file_name = "store_002_20260707.csv"
    result = pipeline.process_data(file_name, csv_content.encode("utf-8"))
    
    # Assertions
    assert result["status"] == "FAILED"
    assert "Schema validation failed" in result["reason"]
    
    # Verify file was isolated in raw quarantine
    quarantined_raw_files = os.listdir(config["local_quarantine"])
    assert f"raw_{file_name}" in quarantined_raw_files
    
    # Check metadata status is FAILED
    with open(config["local_metadata"], "r") as f:
        meta = json.load(f)
    assert file_name in meta
    assert meta[file_name]["processing_status"] == "FAILED"

def test_case_3_data_cleaning_logic(test_setup):
    """TC3: Data Quality - Invalid or duplicate rows are quarantined, valid rows processed."""
    pipeline, config = test_setup
    
    csv_content = (
        "order_id,customer_id,product_id,order_date,quantity,unit_price,payment_status\n"
        "ORD001,CUST001,PROD101,2024-01-15,2,29.99,paid\n"            # Valid
        "ORD002,CUST002,PROD102,2024-01-15,-1,49.99,paid\n"          # Invalid quantity (-1)
        "ORD003,CUST003,PROD103,2024-01-15,3,,pending\n"             # Missing price
        "ORD004,CUST004,PROD104,,2,9.99,paid\n"                      # Missing date
        "ORD001,CUST001,PROD101,2024-01-15,2,29.99,paid\n"            # Duplicate (order_id, product_id)
        "ORD005,CUST005,PROD105,2024-01-15,1,10.00,paid\n"            # Valid
    )
    
    file_name = "store_003_20260707.csv"
    result = pipeline.process_data(file_name, csv_content.encode("utf-8"))
    
    assert result["status"] == "SUCCESS"
    assert result["processed_records"] == 2   # ORD001 and ORD005
    assert result["quarantined_records"] == 4 # ORD002, ORD003, ORD004, and duplicate ORD001
    
    # Validate quarantine file contains 4 records (+1 header row)
    quarantine_path = os.path.join(config["local_quarantine"], file_name)
    assert os.path.exists(quarantine_path)
    quarantine_df = pd.read_csv(quarantine_path)
    assert len(quarantine_df) == 4

def test_case_4_empty_file(test_setup):
    """TC4: Empty File Handling - Checks that empty files are handled without crashing."""
    pipeline, config = test_setup
    
    csv_content = ""
    file_name = "store_004_20260707.csv"
    
    result = pipeline.process_data(file_name, csv_content.encode("utf-8"))
    
    # Empty CSV fails on parsing step because pd.read_csv errors out on empty stream
    # So it should be logged as FAILED or handle gracefully
    assert result["status"] == "FAILED"
    assert "Failed to parse CSV" in result["reason"]
    assert os.path.exists(os.path.join(config["local_quarantine"], f"raw_{file_name}"))

def test_case_4_header_only_file(test_setup):
    """TC4 Extension: Header Only File - Checks that headers with 0 records is handled successfully."""
    pipeline, config = test_setup
    
    csv_content = "order_id,customer_id,product_id,order_date,quantity,unit_price,payment_status\n"
    file_name = "store_004_headers_20260707.csv"
    
    result = pipeline.process_data(file_name, csv_content.encode("utf-8"))
    
    assert result["status"] == "SUCCESS_EMPTY"

def test_case_5_duplicate_metadata_handling(test_setup):
    """TC5: Idempotency - Duplicate uploads are checked and skipped to avoid double processing."""
    pipeline, config = test_setup
    
    csv_content = (
        "order_id,customer_id,product_id,order_date,quantity,unit_price,payment_status\n"
        "ORD001,CUST001,PROD101,2024-01-15,2,29.99,paid\n"
    )
    
    file_name = "store_005_20260707.csv"
    
    # First Upload
    result_first = pipeline.process_data(file_name, csv_content.encode("utf-8"))
    assert result_first["status"] == "SUCCESS"
    
    # Second Upload (Duplicate filename)
    result_second = pipeline.process_data(file_name, csv_content.encode("utf-8"))
    assert result_second["status"] == "SKIPPED_DUPLICATE"
    
    # Double check database records only reflect the successful first execution
    with open(config["local_metadata"], "r") as f:
        meta = json.load(f)
    assert meta[file_name]["processing_status"] == "DUPLICATE"
