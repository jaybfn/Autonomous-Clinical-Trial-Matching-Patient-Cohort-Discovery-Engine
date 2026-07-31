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

variable "clinical_topic_name" {
  description = "Pub/Sub topic for clinical record events"
  type        = string
  default     = "clinical-records"
}

variable "lab_topic_name" {
  description = "Pub/Sub topic for lab update events"
  type        = string
  default     = "lab-updates"
}

variable "clinical_subscription_name" {
  description = "Subscription name for clinical-records"
  type        = string
  default     = "clinical-records-sub"
}

variable "lab_subscription_name" {
  description = "Subscription name for lab-updates"
  type        = string
  default     = "lab-updates-sub"
}

variable "secret_ids" {
  description = "Secret Manager secret IDs (shells only — values out-of-band)"
  type        = list(string)
  default = [
    "trialmatch-snowflake-private-key",
    "trialmatch-snowflake-passphrase",
  ]
}

variable "ingress_address_name" {
  description = "Global static IP name for Ingress"
  type        = string
  default     = "trialmatch-ingress-ip"
}

variable "ingress_domain" {
  description = "Optional public hostname for managed SSL (empty defers cert)"
  type        = string
  default     = ""
}

variable "qdrant_disk_name" {
  description = "Persistent disk for in-cluster Qdrant"
  type        = string
  default     = "trialmatch-qdrant-data"
}

variable "qdrant_disk_zone" {
  description = "Zone for Qdrant disk (pick a GKE node zone)"
  type        = string
  default     = "us-central1-a"
}

variable "qdrant_disk_size_gb" {
  description = "Qdrant disk size GB"
  type        = number
  default     = 20
}

variable "qdrant_disk_type" {
  description = "Qdrant disk type"
  type        = string
  default     = "pd-standard"
}

variable "bastion_name" {
  description = "Private IAP bastion VM name"
  type        = string
  default     = "trialmatch-bastion"
}

variable "bastion_zone" {
  description = "Zone for the bastion VM"
  type        = string
  default     = "us-central1-a"
}

variable "bastion_machine_type" {
  description = "Bastion machine type"
  type        = string
  default     = "e2-micro"
}

variable "bastion_iap_members" {
  description = "Principals allowed to IAP-SSH to the bastion (user:you@domain.com)"
  type        = list(string)
  default     = []
}
