bucket         = "shopmart-terraform-state"
key            = "pipeline/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "shopmart-terraform-locks"
encrypt        = true
