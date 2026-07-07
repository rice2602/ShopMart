variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS Target deployment region"
}

variable "unique_suffix" {
  type        = string
  default     = "devops-dev"
  description = "A suffix appended to resource names (buckets, roles) to ensure uniqueness"
}

variable "alert_email" {
  type        = string
  default     = ""
  description = "Optional email address to subscribe to SNS pipeline alerts"
}
