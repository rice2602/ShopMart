terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# --- S3 Buckets ---
resource "aws_s3_bucket" "raw_data" {
  bucket        = "shopmart-raw-data-${var.unique_suffix}"
  force_destroy = true
}

resource "aws_s3_bucket" "processed_data" {
  bucket        = "shopmart-processed-data-${var.unique_suffix}"
  force_destroy = true
}

resource "aws_s3_bucket" "quarantine_data" {
  bucket        = "shopmart-quarantine-data-${var.unique_suffix}"
  force_destroy = true
}

# --- DynamoDB Metadata Table ---
resource "aws_dynamodb_table" "metadata" {
  name         = "shopmart-metadata"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "file_name"

  attribute {
    name = "file_name"
    type = "S"
  }

  tags = {
    Project = "ShopMart-Data-Pipeline"
  }
}

# --- SNS Topic for Alerting ---
resource "aws_sns_topic" "alerts" {
  name = "shopmart-pipeline-alerts"
}

resource "aws_sns_topic_subscription" "email_sub" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# --- IAM Execution Role for Lambda ---
resource "aws_iam_role" "lambda_exec" {
  name = "ShopMartLambdaRole-${var.unique_suffix}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_policy" {
  name        = "ShopMartLambdaPolicy-${var.unique_suffix}"
  description = "Execution policy for ShopMart Lambda pipeline"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.raw_data.arn,
          "${aws_s3_bucket.raw_data.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.processed_data.arn}/*",
          "${aws_s3_bucket.quarantine_data.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.metadata.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.alerts.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# --- AWS Lambda Function ---

# Generate ZIP of src/ folder dynamically
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/pipeline.py"
  output_path = "${path.module}/dist/pipeline.zip"
}

resource "aws_lambda_function" "processor" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "shopmart-data-processor"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "pipeline.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 120
  memory_size      = 512

  # Pre-built AWS Data Wrangler layer containing Pandas and PyArrow (AWS SDK for Pandas)
  # Standard layer ARN pattern for Python 3.11 in us-east-1
  layers = [
    "arn:aws:lambda:${var.aws_region}:336392948345:layer:AWSSDKPandas-Python311:${var.pandas_layer_version}"
  ]

  environment {
    variables = {
      PROCESSED_BUCKET_NAME = aws_s3_bucket.processed_data.id
      QUARANTINE_BUCKET_NAME = aws_s3_bucket.quarantine_data.id
      METADATA_TABLE_NAME    = aws_dynamodb_table.metadata.name
      SNS_TOPIC_ARN          = aws_sns_topic.alerts.arn
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_attach
  ]
}

# --- S3 Trigger Configuration ---
resource "aws_lambda_permission" "allow_s3_trigger" {
  statement_id  = "AllowS3TriggerToCallLambda"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.raw_data.arn
}

resource "aws_s3_bucket_notification" "raw_upload_trigger" {
  bucket = aws_s3_bucket.raw_data.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  }

  depends_on = [
    aws_lambda_permission.allow_s3_trigger
  ]
}
