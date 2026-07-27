output "network_name" {
  description = "VPC network name for GKE / later modules"
  value       = module.vpc.network_name
}

output "network_self_link" {
  description = "VPC self link"
  value       = module.vpc.network_self_link
}

output "private_subnet_name" {
  description = "Private subnet name"
  value       = module.vpc.private_subnet_name
}

output "private_subnet_self_link" {
  description = "Private subnet self link"
  value       = module.vpc.private_subnet_self_link
}

output "nat_static_ips" {
  description = "Static Cloud NAT IPs — allowlist these in Snowflake network policy (Phase 5)"
  value       = module.cloud_nat.nat_static_ips
}

output "region" {
  description = "Deployment region"
  value       = var.region
}
