variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "network_name" {
  description = "VPC network name"
  type        = string
}

variable "subnet_name" {
  description = "Private subnet name"
  type        = string
}

variable "region" {
  description = "Subnet region"
  type        = string
}

variable "subnet_cidr" {
  description = "Primary CIDR for the private subnet"
  type        = string
}

variable "secondary_pods_cidr" {
  description = "Secondary CIDR range for GKE pods (Phase 3)"
  type        = string
  default     = "10.20.0.0/16"
}

variable "secondary_services_cidr" {
  description = "Secondary CIDR range for GKE services (Phase 3)"
  type        = string
  default     = "10.30.0.0/20"
}
