# Contract tests for the bastion / IAP module (terraform test).

mock_provider "google" {}

variables {
  project_id        = "autonomous-agent-503517"
  region            = "us-central1"
  zone              = "us-central1-a"
  network_self_link = "projects/autonomous-agent-503517/global/networks/trialmatch-vpc"
  subnet_self_link  = "projects/autonomous-agent-503517/regions/us-central1/subnetworks/trialmatch-private"
  iap_members       = ["user:dev@example.com"]
}

run "plan_private_bastion_with_iap_ssh" {
  command = plan

  assert {
    condition     = length(google_compute_instance.bastion.network_interface[0].access_config) == 0
    error_message = "Bastion must not have a public IP"
  }

  assert {
    condition     = contains(google_compute_instance.bastion.tags, "trialmatch-bastion")
    error_message = "Bastion must carry trialmatch-bastion network tag"
  }

  assert {
    condition     = contains(google_compute_firewall.allow_iap_ssh.source_ranges, "35.235.240.0/20")
    error_message = "SSH firewall must allow only IAP forwarder ranges"
  }

  assert {
    condition     = google_compute_instance.bastion.metadata["enable-oslogin"] == "TRUE"
    error_message = "OS Login must be enabled on the bastion"
  }
}
