variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Region for Cloud Router / NAT"
  type        = string
}

variable "network_name" {
  description = "VPC network name"
  type        = string
}

variable "router_name" {
  description = "Cloud Router name"
  type        = string
  default     = "trialmatch-router"
}

variable "nat_name" {
  description = "Cloud NAT name"
  type        = string
  default     = "trialmatch-nat"
}

variable "nat_ip_count" {
  description = "Number of static external IPs for NAT (Snowflake allowlist)"
  type        = number
  default     = 2
}

variable "nat_ip_name_prefix" {
  description = "Prefix for reserved static NAT addresses"
  type        = string
  default     = "trialmatch-nat-ip"
}
