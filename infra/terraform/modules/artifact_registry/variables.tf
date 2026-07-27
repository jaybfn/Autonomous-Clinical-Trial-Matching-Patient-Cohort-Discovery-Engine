variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "location" {
  description = "Artifact Registry location"
  type        = string
  default     = "us-central1"
}

variable "repository_id" {
  description = "Docker repository ID"
  type        = string
  default     = "trialmatch-docker"
}

variable "description" {
  description = "Repository description"
  type        = string
  default     = "trialmatch FastAPI / agent container images"
}
