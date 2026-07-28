resource "google_compute_disk" "qdrant" {
  project = var.project_id
  name    = var.disk_name
  type    = var.disk_type
  zone    = var.zone
  size    = var.disk_size_gb

  labels = {
    app  = "trialmatch"
    role = "qdrant"
  }
}
