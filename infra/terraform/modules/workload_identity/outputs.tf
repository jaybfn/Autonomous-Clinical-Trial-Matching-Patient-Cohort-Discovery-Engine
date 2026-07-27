output "gsa_email" {
  description = "GSA email bound to the KSA"
  value       = var.gsa_email
}

output "ksa_name" {
  description = "Kubernetes ServiceAccount name"
  value       = var.ksa_name
}

output "ksa_namespace" {
  description = "Kubernetes namespace"
  value       = var.ksa_namespace
}

output "workload_identity_member" {
  description = "Principal used in the WI IAM binding"
  value       = "serviceAccount:${var.project_id}.svc.id.goog[${var.ksa_namespace}/${var.ksa_name}]"
}

output "ksa_annotation" {
  description = "Value for annotation iam.gke.io/gcp-service-account on the KSA"
  value       = var.gsa_email
}
