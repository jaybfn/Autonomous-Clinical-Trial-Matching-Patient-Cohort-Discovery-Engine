data "google_project" "this" {
  project_id = var.project_id
}

locals {
  runtime_roles = var.runtime_roles
  node_roles    = var.node_roles
}

resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = var.runtime_account_id
  display_name = "trialmatch runtime (Workload Identity)"
  description  = "Pod identity for agents / API — no JSON keys"
}

resource "google_service_account" "nodes" {
  project      = var.project_id
  account_id   = var.node_account_id
  display_name = "trialmatch GKE nodes"
  description  = "Node pool identity — logging, monitoring, image pull"
}

resource "google_project_iam_member" "runtime" {
  for_each = toset(local.runtime_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "nodes" {
  for_each = toset(local.node_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.nodes.email}"
}

# Allow GKE / Cloud Services to use the custom node SA (no keys).
resource "google_service_account_iam_member" "nodes_cloudservices_sa_user" {
  service_account_id = google_service_account.nodes.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${data.google_project.this.number}@cloudservices.gserviceaccount.com"
}

resource "google_service_account_iam_member" "nodes_container_engine_sa_user" {
  service_account_id = google_service_account.nodes.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:service-${data.google_project.this.number}@container-engine-robot.iam.gserviceaccount.com"
}
