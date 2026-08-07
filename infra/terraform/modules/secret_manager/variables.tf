variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "accessor_gsa_email" {
  description = "GSA email granted secretAccessor (runtime Workload Identity GSA)"
  type        = string
}

variable "secret_ids" {
  description = "Secret Manager secret IDs to create (empty shells; no values in TF)"
  type        = list(string)
  default = [
    "trialmatch-snowflake-private-key",
    "trialmatch-snowflake-passphrase",
    "trialmatch-api-key",
  ]
}
