output "deployment_summary" {
  description = "Full deployment summary of all provisioned AWS resources"
  value       = <<-EOT

    ==========================================
      ShopMart Pipeline - Deployment Summary
    ==========================================

    [S3 Storage]
      Raw Bucket:        ${aws_s3_bucket.raw_data.id}
      Processed Bucket:  ${aws_s3_bucket.processed_data.id}
      Quarantine Bucket: ${aws_s3_bucket.quarantine_data.id}

    [DynamoDB]
      Metadata Table:    ${aws_dynamodb_table.metadata.name}
      Partition Key:     file_name (String)
      Billing Mode:      PAY_PER_REQUEST

    [Lambda]
      Function:          ${aws_lambda_function.processor.function_name}
      Runtime:           ${aws_lambda_function.processor.runtime}
      Memory:            ${aws_lambda_function.processor.memory_size} MB
      Timeout:           ${aws_lambda_function.processor.timeout}s
      Handler:           ${aws_lambda_function.processor.handler}
      Layer:             AWSSDKPandas-Python311

    [SNS Alerting]
      Topic:             ${aws_sns_topic.alerts.name}
      ARN:               ${aws_sns_topic.alerts.arn}
      Email Subscription: ${var.alert_email != "" ? "Yes (${var.alert_email})" : "None"}

    [IAM]
      Role:              ${aws_iam_role.lambda_exec.name}
      Policy:            ${aws_iam_policy.lambda_policy.name}

    [S3 Event Trigger]
      Source Bucket:     ${aws_s3_bucket.raw_data.id}
      Event:             s3:ObjectCreated:*
      Filter:            .csv
      Target:            ${aws_lambda_function.processor.function_name}

    [Event Flow]
      CSV Upload -> S3 Raw -> Lambda -> Clean Data -> S3 Processed (Parquet)
                                      -> Bad Data  -> S3 Quarantine (CSV)
                                      -> Metadata  -> DynamoDB
                                      -> Alerts    -> SNS

    ==========================================
  EOT
}

output "raw_bucket_name" {
  value       = aws_s3_bucket.raw_data.id
  description = "S3 bucket for raw CSV uploads from store POS terminals"
}

output "processed_bucket_name" {
  value       = aws_s3_bucket.processed_data.id
  description = "S3 bucket for cleaned Parquet files partitioned by date"
}

output "quarantine_bucket_name" {
  value       = aws_s3_bucket.quarantine_data.id
  description = "S3 bucket for rejected records and corrupt files"
}

output "dynamodb_metadata_table" {
  value       = aws_dynamodb_table.metadata.name
  description = "DynamoDB table tracking file processing status and idempotency"
}

output "sns_alerts_arn" {
  value       = aws_sns_topic.alerts.arn
  description = "SNS topic ARN for pipeline failure and quarantine alerts"
}

output "lambda_processor_arn" {
  value       = aws_lambda_function.processor.arn
  description = "Lambda function ARN that processes incoming CSV files"
}

output "lambda_role_arn" {
  value       = aws_iam_role.lambda_exec.arn
  description = "IAM execution role ARN attached to the Lambda function"
}

output "region" {
  value       = var.aws_region
  description = "AWS region where all resources are deployed"
}
