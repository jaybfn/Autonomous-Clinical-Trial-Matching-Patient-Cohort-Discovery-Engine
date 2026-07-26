variable "project_id" {
  description = "GCP project ID (locked: autonomous-agent-503517)"
  type        = string
}

variable "region" {
  description = "Primary region"
  type        = string
  default     = "us-central1"
}

variable "network_name" {
  description = "VPC name"
  type        = string
  default     = "trialmatch-vpc"
}

variable "subnet_name" {
  description = "Private subnet name"
  type        = string
  default     = "trialmatch-private"
}

variable "subnet_cidr" {
  description = "Private subnet CIDR"
  type        = string
  default     = "10.10.0.0/20"
}

variable "nat_ip_count" {
  description = "Static NAT IPs reserved for Snowflake allowlisting"
  type        = number
  default     = 2
}
