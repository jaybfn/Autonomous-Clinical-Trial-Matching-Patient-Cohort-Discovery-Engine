# Contract tests for the GKE module (run with: terraform test).
# Uses mock_provider so no live GCP credentials are required.

mock_provider "google" {}

variables {
  project_id                 = "autonomous-agent-503517"
  cluster_name               = "trialmatch-gke"
  region                     = "us-central1"
  network_self_link          = "projects/autonomous-agent-503517/global/networks/trialmatch-vpc"
  subnet_self_link           = "projects/autonomous-agent-503517/regions/us-central1/subnetworks/trialmatch-private"
  node_service_account_email = "trialmatch-nodes@autonomous-agent-503517.iam.gserviceaccount.com"
  master_authorized_cidrs = [
    {
      cidr_block   = "10.10.0.0/20"
      display_name = "trialmatch-private-subnet"
    }
  ]
}

run "plan_private_cluster_with_workload_identity" {
  command = plan

  assert {
    condition     = google_container_cluster.this.private_cluster_config[0].enable_private_nodes == true
    error_message = "GKE nodes must be private"
  }

  assert {
    condition     = google_container_cluster.this.private_cluster_config[0].enable_private_endpoint == true
    error_message = "GKE control plane endpoint must be private"
  }

  assert {
    condition     = google_container_cluster.this.remove_default_node_pool == true
    error_message = "Default node pool must be removed in favor of a managed pool"
  }

  assert {
    condition     = google_container_cluster.this.workload_identity_config[0].workload_pool == "autonomous-agent-503517.svc.id.goog"
    error_message = "Workload Identity pool must be enabled"
  }

  assert {
    condition     = length(google_container_cluster.this.master_authorized_networks_config[0].cidr_blocks) == 1
    error_message = "Private master must authorize the bastion/private subnet CIDR"
  }
}
