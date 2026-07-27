output "repository_id" {
  description = "Artifact Registry repository ID"
  value       = google_artifact_registry_repository.docker.repository_id
}

output "repository_url" {
  description = "Docker push/pull URL prefix (host/project/repo)"
  value       = "${var.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

output "location" {
  description = "Registry location"
  value       = google_artifact_registry_repository.docker.location
}
