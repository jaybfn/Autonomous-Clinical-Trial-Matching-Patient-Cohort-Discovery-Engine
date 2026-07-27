output "nat_static_ips" {
  description = "Static external IP addresses used by Cloud NAT (allowlist in Snowflake)"
  value       = google_compute_address.nat[*].address
}

output "nat_address_names" {
  description = "Names of reserved NAT addresses"
  value       = google_compute_address.nat[*].name
}

output "router_name" {
  description = "Cloud Router name"
  value       = google_compute_router.this.name
}

output "nat_name" {
  description = "Cloud NAT name"
  value       = google_compute_router_nat.this.name
}
