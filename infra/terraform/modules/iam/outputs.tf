output "runtime_gsa_email" {
  description = "Runtime GSA email (Workload Identity)"
  value       = google_service_account.runtime.email
}

output "runtime_gsa_name" {
  description = "Runtime GSA resource name"
  value       = google_service_account.runtime.name
}

output "node_gsa_email" {
  description = "Node-pool GSA email"
  value       = google_service_account.nodes.email
}

output "runtime_roles" {
  description = "Roles bound to the runtime GSA"
  value       = var.runtime_roles
}

output "node_roles" {
  description = "Roles bound to the node GSA"
  value       = var.node_roles
}
