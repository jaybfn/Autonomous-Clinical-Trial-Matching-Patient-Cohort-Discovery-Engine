output "instance_name" {
  description = "Bastion VM name"
  value       = google_compute_instance.bastion.name
}

output "zone" {
  description = "Bastion zone"
  value       = google_compute_instance.bastion.zone
}

output "internal_ip" {
  description = "Bastion private IP"
  value       = google_compute_instance.bastion.network_interface[0].network_ip
}

output "service_account_email" {
  description = "Bastion runtime GSA"
  value       = google_service_account.bastion.email
}

output "network_tag" {
  description = "Primary network tag used by IAP SSH firewall"
  value       = local.network_tag
}

output "iap_ssh_command" {
  description = "SSH via IAP (run from laptop / Dev Container)"
  value       = "gcloud compute ssh ${google_compute_instance.bastion.name} --project=${var.project_id} --zone=${var.zone} --tunnel-through-iap"
}
