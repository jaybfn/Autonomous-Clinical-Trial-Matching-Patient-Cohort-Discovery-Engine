resource "google_service_account_iam_member" "workload_identity_user" {
  service_account_id = var.gsa_name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.ksa_namespace}/${var.ksa_name}]"
}
