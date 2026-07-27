variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "network_name" {
  description = "VPC network name"
  type        = string
}

variable "allow_internal_name" {
  description = "Firewall rule name for internal VPC traffic"
  type        = string
  default     = "trialmatch-allow-internal"
}

variable "allow_health_checks_name" {
  description = "Firewall rule name for GCP health checks"
  type        = string
  default     = "trialmatch-allow-health-checks"
}

variable "internal_source_ranges" {
  description = "Source CIDRs treated as internal (VPC + secondary ranges)"
  type        = list(string)
  default     = ["10.0.0.0/8"]
}
