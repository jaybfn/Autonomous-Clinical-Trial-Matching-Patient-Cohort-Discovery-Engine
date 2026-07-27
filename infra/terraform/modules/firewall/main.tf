# Baseline firewall: allow internal + GCP health checks.
# Implicit deny for unmatched ingress remains GCP default.

resource "google_compute_firewall" "allow_internal" {
  project = var.project_id
  name    = var.allow_internal_name
  network = var.network_name

  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
  }

  allow {
    protocol = "udp"
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = var.internal_source_ranges
}

resource "google_compute_firewall" "allow_health_checks" {
  project = var.project_id
  name    = var.allow_health_checks_name
  network = var.network_name

  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
  }

  # Google Cloud health check / LB probe ranges
  source_ranges = [
    "35.191.0.0/16",
    "130.211.0.0/22",
  ]
}
