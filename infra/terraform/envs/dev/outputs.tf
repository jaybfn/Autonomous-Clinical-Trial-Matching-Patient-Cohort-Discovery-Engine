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

output "clinical_topic" {
  description = "Pub/Sub topic for clinical record events"
  value       = module.pubsub.clinical_topic
}

output "lab_topic" {
  description = "Pub/Sub topic for lab update events"
  value       = module.pubsub.lab_topic
}

output "clinical_subscription" {
  description = "Subscription for clinical-records (ingestion pull)"
  value       = module.pubsub.clinical_subscription
}

output "lab_subscription" {
  description = "Subscription for lab-updates (ingestion pull)"
  value       = module.pubsub.lab_subscription
}

output "clinical_dlq_topic" {
  description = "Dead-letter topic for clinical-records"
  value       = module.pubsub.clinical_dlq_topic
}

output "lab_dlq_topic" {
  description = "Dead-letter topic for lab-updates"
  value       = module.pubsub.lab_dlq_topic
}

output "secret_ids" {
  description = "Secret Manager secret IDs (values set out-of-band)"
  value       = module.secret_manager.secret_ids
}

output "ingress_static_ip_name" {
  description = "Global address name for GKE Ingress annotation"
  value       = module.ingress.static_ip_name
}

output "ingress_static_ip_address" {
  description = "Reserved Ingress / HTTPS LB IPv4"
  value       = module.ingress.static_ip_address
}

output "qdrant_disk_name" {
  description = "Persistent disk name for Qdrant storage"
  value       = module.qdrant_disk.disk_name
}

output "qdrant_disk_zone" {
  description = "Zone of the Qdrant persistent disk"
  value       = module.qdrant_disk.zone
}
