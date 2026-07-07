output "raw_bucket_name" {
  value       = aws_s3_bucket.raw_data.id
  description = "The S3 bucket name for uploading raw CSV files"
}

output "processed_bucket_name" {
  value       = aws_s3_bucket.processed_data.id
  description = "The S3 bucket name where cleaned Parquet files are stored"
}

output "quarantine_bucket_name" {
  value       = aws_s3_bucket.quarantine_data.id
  description = "The S3 bucket name containing rejected files and error logs"
}

output "dynamodb_metadata_table" {
  value       = aws_dynamodb_table.metadata.name
  description = "The DynamoDB table name tracking pipeline execution state"
}

output "sns_alerts_arn" {
  value       = aws_sns_topic.alerts.arn
  description = "The SNS Topic ARN for receiving pipeline failure reports"
}

output "lambda_processor_arn" {
  value       = aws_lambda_function.processor.arn
  description = "The AWS Lambda function processing data"
}
