# Private bastion for kubectl / deploy access to private GKE via IAP SSH.
# No public IP. SSH only from Google IAP ranges (35.235.240.0/20).

locals {
  network_tag = length(var.tags) > 0 ? var.tags[0] : "trialmatch-bastion"
}

resource "google_service_account" "bastion" {
  project      = var.project_id
  account_id   = "trialmatch-bastion"
  display_name = "TrialMatch bastion (IAP jump host)"
}

resource "google_project_iam_member" "bastion_container_developer" {
  project = var.project_id
  role    = "roles/container.developer"
  member  = "serviceAccount:${google_service_account.bastion.email}"
}

resource "google_project_iam_member" "bastion_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.bastion.email}"
}

resource "google_project_iam_member" "bastion_artifact_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.bastion.email}"
}

# IAP TCP forwarding to VMs (project-level; scope with IAM Conditions in larger orgs).
resource "google_project_iam_member" "iap_tunnel" {
  for_each = toset(var.iap_members)

  project = var.project_id
  role    = "roles/iap.tunnelResourceAccessor"
  member  = each.value
}

resource "google_project_iam_member" "os_login" {
  for_each = toset(var.iap_members)

  project = var.project_id
  role    = "roles/compute.osLogin"
  member  = each.value
}

# Required so OS Login users can use the bastion's attached service account.
resource "google_service_account_iam_member" "bastion_sa_user" {
  for_each = toset(var.iap_members)

  service_account_id = google_service_account.bastion.name
  role               = "roles/iam.serviceAccountUser"
  member             = each.value
}

resource "google_compute_firewall" "allow_iap_ssh" {
  project = var.project_id
  name    = "trialmatch-allow-iap-ssh"
  network = var.network_self_link

  description = "Allow SSH to bastion only from Identity-Aware Proxy"
  direction   = "INGRESS"
  priority    = 1000

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # https://cloud.google.com/iap/docs/using-tcp-forwarding#create-firewall-rule
  source_ranges = ["35.235.240.0/20"]
  target_tags   = var.tags
}

resource "google_compute_instance" "bastion" {
  project      = var.project_id
  name         = var.name
  machine_type = var.machine_type
  zone         = var.zone

  tags = var.tags

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = var.disk_size_gb
      type  = var.disk_type
    }
  }

  network_interface {
    subnetwork = var.subnet_self_link
    # No access_config → no public IP (egress via Cloud NAT).
  }

  service_account {
    email  = google_service_account.bastion.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  metadata = {
    enable-oslogin = "TRUE"
  }

  metadata_startup_script = <<-EOT
    #!/bin/bash
    set -euo pipefail
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y apt-transport-https ca-certificates curl gnupg
    curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
      | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
      > /etc/apt/sources.list.d/google-cloud-sdk.list
    apt-get update
    apt-get install -y google-cloud-cli google-cloud-cli-gke-gcloud-auth-plugin kubectl
    echo "USE_GKE_GCLOUD_AUTH_PLUGIN=True" >> /etc/environment
  EOT

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  allow_stopping_for_update = true

  labels = {
    app     = "trialmatch"
    purpose = "bastion"
  }
}
