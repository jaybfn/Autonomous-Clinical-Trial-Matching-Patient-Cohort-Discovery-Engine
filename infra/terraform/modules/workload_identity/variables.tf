variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "gsa_name" {
  description = "Runtime GSA resource name (projects/.../serviceAccounts/...)"
  type        = string
}

variable "gsa_email" {
  description = "Runtime GSA email for KSA annotation"
  type        = string
}

variable "ksa_name" {
  description = "Kubernetes ServiceAccount name"
  type        = string
  default     = "trialmatch-ksa"
}

variable "ksa_namespace" {
  description = "Kubernetes namespace for the KSA"
  type        = string
  default     = "trialmatch"
}
