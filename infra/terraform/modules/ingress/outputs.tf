output "static_ip_name" {
  description = "Global address resource name (use in Ingress annotation)"
  value       = google_compute_global_address.ingress.name
}

output "static_ip_address" {
  description = "Reserved global IPv4 for the Ingress / HTTPS LB"
  value       = google_compute_global_address.ingress.address
}

output "ssl_certificate_name" {
  description = "Managed SSL cert name (null when domain unset)"
  value       = try(google_compute_managed_ssl_certificate.ingress[0].name, null)
}

output "domain" {
  description = "Configured public hostname (empty if deferred)"
  value       = var.domain
}
