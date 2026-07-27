output "allow_internal_rule_name" {
  description = "Name of the internal allow firewall rule"
  value       = google_compute_firewall.allow_internal.name
}

output "allow_health_checks_rule_name" {
  description = "Name of the health-check allow firewall rule"
  value       = google_compute_firewall.allow_health_checks.name
}
