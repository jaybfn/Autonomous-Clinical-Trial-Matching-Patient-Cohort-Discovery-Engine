output "network_name" {
  description = "VPC network name"
  value       = google_compute_network.this.name
}

output "network_id" {
  description = "VPC network ID"
  value       = google_compute_network.this.id
}

output "network_self_link" {
  description = "VPC network self link"
  value       = google_compute_network.this.self_link
}

output "private_subnet_name" {
  description = "Private subnet name"
  value       = google_compute_subnetwork.private.name
}

output "private_subnet_id" {
  description = "Private subnet ID"
  value       = google_compute_subnetwork.private.id
}

output "private_subnet_self_link" {
  description = "Private subnet self link"
  value       = google_compute_subnetwork.private.self_link
}

output "region" {
  description = "Subnet region"
  value       = google_compute_subnetwork.private.region
}

output "pods_range_name" {
  description = "Secondary IP range name for GKE pods"
  value       = "gke-pods"
}

output "services_range_name" {
  description = "Secondary IP range name for GKE services"
  value       = "gke-services"
}
