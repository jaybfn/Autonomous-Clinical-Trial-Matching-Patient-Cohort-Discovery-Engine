variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "runtime_gsa_email" {
  description = "Workload Identity runtime GSA email (publisher/subscriber)"
  type        = string
}

variable "clinical_topic_name" {
  description = "Primary clinical-records topic name"
  type        = string
  default     = "clinical-records"
}

variable "lab_topic_name" {
  description = "Primary lab-updates topic name"
  type        = string
  default     = "lab-updates"
}

variable "clinical_subscription_name" {
  description = "Subscription for clinical-records"
  type        = string
  default     = "clinical-records-sub"
}

variable "lab_subscription_name" {
  description = "Subscription for lab-updates"
  type        = string
  default     = "lab-updates-sub"
}

variable "ack_deadline_seconds" {
  description = "Ack deadline for primary subscriptions"
  type        = number
  default     = 60
}

variable "message_retention_duration" {
  description = "Message retention (duration string)"
  type        = string
  default     = "604800s" # 7 days
}

variable "max_delivery_attempts" {
  description = "Attempts before dead-letter (must be >= 5)"
  type        = number
  default     = 5
}

variable "retry_minimum_backoff" {
  description = "Minimum retry backoff"
  type        = string
  default     = "10s"
}

variable "retry_maximum_backoff" {
  description = "Maximum retry backoff"
  type        = string
  default     = "600s"
}
