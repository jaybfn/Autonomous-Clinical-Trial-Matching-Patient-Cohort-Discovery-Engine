resource "google_container_cluster" "this" {
  project  = var.project_id
  name     = var.cluster_name
  location = var.region

  network    = var.network_self_link
  subnetwork = var.subnet_self_link

  # Separate managed node pool (below).
  remove_default_node_pool = true
  initial_node_count       = 1

  release_channel {
    channel = var.release_channel
  }

  networking_mode = "VPC_NATIVE"
  ip_allocation_policy {
    cluster_secondary_range_name  = var.pods_range_name
    services_secondary_range_name = var.services_range_name
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = true
    master_ipv4_cidr_block  = var.master_ipv4_cidr_block
  }

  master_authorized_networks_config {
    # Private endpoint: only listed CIDRs (bastion subnet) may reach the API server.
    dynamic "cidr_blocks" {
      for_each = var.master_authorized_cidrs
      content {
        cidr_block   = cidr_blocks.value.cidr_block
        display_name = cidr_blocks.value.display_name
      }
    }
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }

  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS"]
  }

  # Dataplane V2 / network policy optional; keep baseline stable for Phase 3.
  deletion_protection = var.deletion_protection
}

resource "google_container_node_pool" "primary" {
  project  = var.project_id
  name     = var.node_pool_name
  location = var.region
  cluster  = google_container_cluster.this.name

  node_count = var.node_count

  node_config {
    machine_type    = var.machine_type
    service_account = var.node_service_account_email
    disk_size_gb    = var.disk_size_gb
    disk_type       = var.disk_type
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    labels = {
      app = "trialmatch"
    }

    tags = ["trialmatch-gke-node"]

    metadata = {
      disable-legacy-endpoints = "true"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}
