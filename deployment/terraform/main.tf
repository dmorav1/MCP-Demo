# MCP Demo Production Infrastructure
# Terraform Configuration for AWS EKS Deployment

terraform {
  required_version = ">= 1.6.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
  
  # IMPORTANT: S3 Backend Prerequisites
  # ------------------------------------
  # Before running 'terraform init', you MUST manually create:
  #
  # 1. S3 Bucket for state storage:
  #    - Name: mcp-demo-terraform-state (or custom name via -backend-config)
  #    - Versioning: ENABLED (required for state recovery)
  #    - Encryption: ENABLED (AES256 or KMS)
  #    - Block Public Access: ENABLED
  #
  # 2. DynamoDB Table for state locking:
  #    - Name: mcp-demo-terraform-locks (or custom name via -backend-config)
  #    - Primary Key: LockID (String)
  #    - Billing Mode: PAY_PER_REQUEST (recommended)
  #
  # For multiple environments, use different values:
  #   terraform init \
  #     -backend-config="bucket=mcp-demo-terraform-state-staging" \
  #     -backend-config="dynamodb_table=mcp-demo-terraform-locks-staging" \
  #     -backend-config="key=staging/terraform.tfstate"
  #
  # See deployment/README.md for detailed setup instructions.

  # IMPORTANT: The S3 backend resources (bucket and DynamoDB table) must be created
  # before running 'terraform init'. These resources must exist or initialization will fail.
  # 
  # To create the backend resources manually:
  # 1. aws s3api create-bucket --bucket mcp-demo-terraform-state --region us-east-1
  # 2. aws s3api put-bucket-versioning --bucket mcp-demo-terraform-state --versioning-configuration Status=Enabled
  # 3. aws dynamodb create-table --table-name mcp-demo-terraform-locks \
  #      --attribute-definitions AttributeName=LockID,AttributeType=S \
  #      --key-schema AttributeName=LockID,KeyType=HASH \
  #      --billing-mode PAY_PER_REQUEST
  #
  # Consider using variables for bucket and table names to support multiple environments.
  backend "s3" {
    bucket         = "mcp-demo-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "mcp-demo-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "mcp-demo"
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = "platform-team"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# Local variables
locals {
  cluster_name = "mcp-demo-${var.environment}"
  azs          = slice(data.aws_availability_zones.available.names, 0, 3)
  
  tags = {
    Project     = "mcp-demo"
    Environment = var.environment
    Terraform   = "true"
  }
}

# Modules
module "vpc" {
  source = "./modules/vpc"
  
  environment  = var.environment
  cluster_name = local.cluster_name
  vpc_cidr     = var.vpc_cidr
  azs          = local.azs
  tags         = local.tags
}

module "eks" {
  source = "./modules/eks"
  
  environment        = var.environment
  cluster_name       = local.cluster_name
  cluster_version    = var.eks_cluster_version
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  node_groups        = var.node_groups
  tags               = local.tags
  
  depends_on = [module.vpc]
}

module "rds" {
  source = "./modules/rds"
  
  environment        = var.environment
  identifier         = "mcp-demo-${var.environment}"
  instance_class     = var.rds_instance_class
  allocated_storage  = var.rds_allocated_storage
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.database_subnet_ids
  multi_az           = var.rds_multi_az
  backup_retention   = var.rds_backup_retention
  tags               = local.tags
  
  depends_on = [module.vpc]
}

module "elasticache" {
  source = "./modules/elasticache"
  
  environment        = var.environment
  cluster_id         = "mcp-demo-${var.environment}"
  node_type          = var.elasticache_node_type
  num_cache_nodes    = var.elasticache_num_nodes
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.database_subnet_ids
  tags               = local.tags
  
  depends_on = [module.vpc]
}

module "s3" {
  source = "./modules/s3"
  
  environment     = var.environment
  backup_bucket   = "mcp-demo-${var.environment}-backups"
  logs_bucket     = "mcp-demo-${var.environment}-logs"
  tags            = local.tags
}

module "secrets" {
  source = "./modules/secrets"
  
  environment = var.environment
  tags        = local.tags
}

module "monitoring" {
  source = "./modules/monitoring"
  
  environment  = var.environment
  cluster_name = local.cluster_name
  tags         = local.tags
  
  depends_on = [module.eks]
}

# Outputs
output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "elasticache_endpoint" {
  description = "ElastiCache cluster endpoint"
  value       = module.elasticache.endpoint
  sensitive   = true
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}
