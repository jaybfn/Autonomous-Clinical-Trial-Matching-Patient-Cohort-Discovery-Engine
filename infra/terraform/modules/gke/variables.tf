variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
}

variable "region" {
  description = "Regional cluster location"
  type        = string
}

variable "network_self_link" {
  description = "VPC network self link"
  type        = string
}

variable "subnet_self_link" {
  description = "Private subnet self link"
  type        = string
}

variable "pods_range_name" {
  description = "Secondary range name for pods (must match VPC module)"
  type        = string
  default     = "gke-pods"
}

variable "services_range_name" {
  description = "Secondary range name for services (must match VPC module)"
  type        = string
  default     = "gke-services"
}

variable "master_ipv4_cidr_block" {
  description = "Private master CIDR (/28)"
  type        = string
  default     = "172.16.0.0/28"
}

variable "release_channel" {
  description = "GKE release channel"
  type        = string
  default     = "REGULAR"
}

variable "node_pool_name" {
  description = "Primary node pool name"
  type        = string
  default     = "trialmatch-primary"
}

variable "node_count" {
  description = "Nodes per zone for a regional cluster (total ≈ node_count × zones)"
  type        = number
  default     = 1
}

variable "machine_type" {
  description = "Node machine type"
  type        = string
  default     = "e2-standard-2"
}

variable "disk_size_gb" {
  description = "Boot disk size per node (keep low for SSD_TOTAL_GB quota)"
  type        = number
  default     = 30
}

variable "disk_type" {
  description = "Boot disk type (pd-standard avoids SSD_TOTAL_GB quota)"
  type        = string
  default     = "pd-standard"
}

variable "node_service_account_email" {
  description = "GSA email used by GKE nodes (not the workload GSA)"
  type        = string
}

variable "deletion_protection" {
  description = "Prevent accidental cluster destroy"
  type        = bool
  default     = false
}

variable "master_authorized_cidrs" {
  description = "CIDRs allowed to reach the private control plane (e.g. bastion subnet)"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = []
}
