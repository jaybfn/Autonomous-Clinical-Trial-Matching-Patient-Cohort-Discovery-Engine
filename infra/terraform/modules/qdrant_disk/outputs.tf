output "disk_name" {
  description = "Compute Engine disk name for Qdrant PVC / static PV binding"
  value       = google_compute_disk.qdrant.name
}

output "disk_self_link" {
  description = "Disk self link"
  value       = google_compute_disk.qdrant.self_link
}

output "zone" {
  description = "Disk zone"
  value       = google_compute_disk.qdrant.zone
}

output "size_gb" {
  description = "Disk size GB"
  value       = google_compute_disk.qdrant.size
}
