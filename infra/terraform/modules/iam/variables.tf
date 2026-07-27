variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "runtime_account_id" {
  description = "Workload Identity GSA account_id (pods)"
  type        = string
  default     = "trialmatch-runtime"
}

variable "node_account_id" {
  description = "Node-pool GSA account_id"
  type        = string
  default     = "trialmatch-nodes"
}

variable "runtime_roles" {
  description = "Least-privilege project roles for the runtime GSA"
  type        = list(string)
  default = [
    "roles/pubsub.subscriber",
    "roles/pubsub.publisher",
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ]
}

variable "node_roles" {
  description = "Least-privilege project roles for the node GSA"
  type        = list(string)
  default = [
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/artifactregistry.reader",
  ]
}
