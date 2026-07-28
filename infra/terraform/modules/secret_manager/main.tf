resource "google_secret_manager_secret" "this" {
  for_each = toset(var.secret_ids)

  project   = var.project_id
  secret_id = each.value

  labels = {
    app = "trialmatch"
  }

  replication {
    auto {}
  }
}

# IAM only — secret *values* are added out-of-band (gcloud / Console), never in Terraform.
resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each = toset(var.secret_ids)

  project   = var.project_id
  secret_id = google_secret_manager_secret.this[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.accessor_gsa_email}"
}
