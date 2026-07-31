variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Region for the bastion subnet"
  type        = string
}

variable "zone" {
  description = "Zone for the bastion VM"
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

variable "name" {
  description = "Bastion instance name"
  type        = string
  default     = "trialmatch-bastion"
}

variable "machine_type" {
  description = "Bastion machine type (keep small)"
  type        = string
  default     = "e2-micro"
}

variable "disk_size_gb" {
  description = "Boot disk size GB"
  type        = number
  default     = 20
}

variable "disk_type" {
  description = "Boot disk type"
  type        = string
  default     = "pd-standard"
}

variable "tags" {
  description = "Network tags (must match IAP SSH firewall target)"
  type        = list(string)
  default     = ["trialmatch-bastion"]
}

variable "iap_members" {
  description = "Principals granted IAP tunnel + OS Login to the bastion (e.g. user:you@example.com)"
  type        = list(string)
  default     = []
}
