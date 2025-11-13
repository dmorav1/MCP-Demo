# Terraform Variables for MCP Demo Infrastructure

# Backend Configuration Variables
# Note: These are used in backend.tf for the S3 backend configuration
# The backend resources (S3 bucket and DynamoDB table) must be created
# manually before running terraform init

variable "terraform_state_bucket" {
  description = "S3 bucket name for Terraform state storage (must exist before terraform init)"
  type        = string
  default     = "mcp-demo-terraform-state"
}

variable "terraform_state_dynamodb_table" {
  description = "DynamoDB table name for Terraform state locking (must exist before terraform init)"
  type        = string
  default     = "mcp-demo-terraform-locks"
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "eks_cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.28"
}

variable "node_groups" {
  description = "EKS node group configurations"
  type = map(object({
    instance_types = list(string)
    min_size       = number
    max_size       = number
    desired_size   = number
    disk_size      = number
    labels         = map(string)
    taints         = list(object({
      key    = string
      value  = string
      effect = string
    }))
  }))
  
  default = {
    application = {
      instance_types = ["m5.xlarge"]
      min_size       = 3
      max_size       = 10
      desired_size   = 3
      disk_size      = 50
      labels = {
        workload = "application"
      }
      taints = []
    }
    observability = {
      instance_types = ["r5.large"]
      min_size       = 2
      max_size       = 4
      desired_size   = 2
      disk_size      = 100
      labels = {
        workload = "observability"
      }
      taints = [{
        key    = "observability"
        value  = "true"
        effect = "NoSchedule"
      }]
    }
  }
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r5.large"
}

variable "rds_allocated_storage" {
  description = "Allocated storage for RDS in GB"
  type        = number
  default     = 100
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ for RDS"
  type        = bool
  default     = true
}

variable "rds_backup_retention" {
  description = "Backup retention period in days"
  type        = number
  default     = 30
}

variable "elasticache_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.r5.large"
}

variable "elasticache_num_nodes" {
  description = "Number of ElastiCache nodes"
  type        = number
  default     = 3
}

variable "enable_monitoring" {
  description = "Enable monitoring stack deployment"
  type        = bool
  default     = true
}

variable "enable_istio" {
  description = "Enable Istio service mesh"
  type        = bool
  default     = true
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "mcp-demo.example.com"
}

variable "certificate_arn" {
  description = "ARN of ACM certificate for HTTPS"
  type        = string
  default     = ""
}
