variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "disk_name" {
  description = "Persistent disk name for Qdrant storage"
  type        = string
  default     = "trialmatch-qdrant-data"
}

variable "zone" {
  description = "Zone for the regional attach (match a GKE node zone)"
  type        = string
  default     = "us-central1-a"
}

variable "disk_size_gb" {
  description = "Disk size in GB"
  type        = number
  default     = 20
}

variable "disk_type" {
  description = "pd-standard avoids SSD quota pressure"
  type        = string
  default     = "pd-standard"
}
