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

output "cluster_name" {
  description = "Private GKE cluster name"
  value       = module.gke.cluster_name
}

output "cluster_endpoint" {
  description = "Private GKE control-plane endpoint"
  value       = module.gke.cluster_endpoint
}

output "artifact_registry_url" {
  description = "Docker repository URL for CI image push"
  value       = module.artifact_registry.repository_url
}

output "runtime_gsa_email" {
  description = "Workload Identity runtime GSA email"
  value       = module.iam.runtime_gsa_email
}

output "node_gsa_email" {
  description = "GKE node pool GSA email"
  value       = module.iam.node_gsa_email
}

output "ksa_annotation" {
  description = "Annotate KSA with iam.gke.io/gcp-service-account = this value"
  value       = module.workload_identity.ksa_annotation
}

output "workload_identity_member" {
  description = "KSA principal bound as workloadIdentityUser"
  value       = module.workload_identity.workload_identity_member
}
