resource "google_compute_global_address" "ingress" {
  project = var.project_id
  name    = var.address_name

  ip_version = "IPV4"
}

# Optional managed cert when a public hostname is provided (Phase 11 wires the Ingress).
resource "google_compute_managed_ssl_certificate" "ingress" {
  count = var.domain != "" ? 1 : 0

  project = var.project_id
  name    = var.ssl_certificate_name

  managed {
    domains = [var.domain]
  }

  lifecycle {
    create_before_destroy = true
  }
}
