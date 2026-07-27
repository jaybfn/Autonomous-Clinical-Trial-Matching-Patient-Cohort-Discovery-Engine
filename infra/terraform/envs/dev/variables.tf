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

variable "cluster_name" {
  description = "Private GKE cluster name"
  type        = string
  default     = "trialmatch-gke"
}

variable "master_ipv4_cidr_block" {
  description = "GKE private master CIDR (/28)"
  type        = string
  default     = "172.16.0.0/28"
}

variable "gke_node_count" {
  description = "Nodes per zone (regional total ≈ count × 3). Keep low for quota."
  type        = number
  default     = 1
}

variable "gke_machine_type" {
  description = "Primary node pool machine type"
  type        = string
  default     = "e2-standard-2"
}

variable "gke_disk_size_gb" {
  description = "Boot disk GB per node (SSD quota is tight on new projects)"
  type        = number
  default     = 30
}

variable "gke_disk_type" {
  description = "Boot disk type — pd-standard avoids SSD_TOTAL_GB quota"
  type        = string
  default     = "pd-standard"
}

variable "gke_deletion_protection" {
  description = "Protect GKE cluster from destroy"
  type        = bool
  default     = false
}

variable "artifact_repository_id" {
  description = "Artifact Registry Docker repository ID"
  type        = string
  default     = "trialmatch-docker"
}

variable "ksa_name" {
  description = "Kubernetes ServiceAccount name (must match k8s/serviceaccounts)"
  type        = string
  default     = "trialmatch-ksa"
}

variable "ksa_namespace" {
  description = "Kubernetes namespace for the KSA"
  type        = string
  default     = "trialmatch"
}
