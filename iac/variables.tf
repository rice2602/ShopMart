variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS Target deployment region"
}

variable "unique_suffix" {
  type        = string
  default     = "devops-dev"
  description = "A suffix appended to resource names (buckets, roles) to ensure uniqueness"

  validation {
    condition     = length(var.unique_suffix) > 0
    error_message = "unique_suffix must not be empty."
  }
}

variable "alert_email" {
  type        = string
  default     = ""
  description = "Optional email address to subscribe to SNS pipeline alerts"
}

variable "pandas_layer_version" {
  type        = number
  default     = 12
  description = "Version of the AWS SDK for Pandas Lambda Layer"

  validation {
    condition     = var.pandas_layer_version > 0
    error_message = "pandas_layer_version must be a positive integer."
  }
}
