variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "address_name" {
  description = "Global static IP name for HTTPS Ingress / Gateway"
  type        = string
  default     = "trialmatch-ingress-ip"
}

variable "domain" {
  description = "Optional public hostname for a managed SSL cert (empty = skip cert)"
  type        = string
  default     = ""
}

variable "ssl_certificate_name" {
  description = "Managed SSL certificate resource name (used when domain is set)"
  type        = string
  default     = "trialmatch-ingress-cert"
}
