# Contract tests for the VPC module (run by you with: terraform test).
# Uses mock_provider so no live GCP credentials are required for unit-style checks.

mock_provider "google" {}

variables {
  project_id   = "autonomous-agent-503517"
  network_name = "trialmatch-vpc"
  subnet_name  = "trialmatch-private"
  region       = "us-central1"
  subnet_cidr  = "10.10.0.0/20"
}

run "plan_enables_private_google_access" {
  command = plan

  assert {
    condition     = google_compute_subnetwork.private.private_ip_google_access == true
    error_message = "Private Google Access must be enabled on the private subnet"
  }

  assert {
    condition     = google_compute_network.this.auto_create_subnetworks == false
    error_message = "VPC must not auto-create subnetworks"
  }
}
