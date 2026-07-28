module "vpc" {
  source = "../../modules/vpc"

  project_id   = var.project_id
  network_name = var.network_name
  subnet_name  = var.subnet_name
  region       = var.region
  subnet_cidr  = var.subnet_cidr
}

module "cloud_nat" {
  source = "../../modules/cloud_nat"

  project_id   = var.project_id
  region       = var.region
  network_name = module.vpc.network_name
  nat_ip_count = var.nat_ip_count
}

module "firewall" {
  source = "../../modules/firewall"

  project_id   = var.project_id
  network_name = module.vpc.network_name
}

# APIs required for Phase 3–4 (idempotent enable).
resource "google_project_service" "phase3" {
  for_each = toset([
    "container.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

module "iam" {
  source = "../../modules/iam"

  project_id = var.project_id

  depends_on = [google_project_service.phase3]
}

module "workload_identity" {
  source = "../../modules/workload_identity"

  project_id    = var.project_id
  gsa_name      = module.iam.runtime_gsa_name
  gsa_email     = module.iam.runtime_gsa_email
  ksa_name      = var.ksa_name
  ksa_namespace = var.ksa_namespace

  # Identity pool exists only after the cluster enables Workload Identity.
  depends_on = [module.gke]
}

module "artifact_registry" {
  source = "../../modules/artifact_registry"

  project_id    = var.project_id
  location      = var.region
  repository_id = var.artifact_repository_id

  depends_on = [google_project_service.phase3]
}

module "gke" {
  source = "../../modules/gke"

  project_id                 = var.project_id
  cluster_name               = var.cluster_name
  region                     = var.region
  network_self_link          = module.vpc.network_self_link
  subnet_self_link           = module.vpc.private_subnet_self_link
  pods_range_name            = module.vpc.pods_range_name
  services_range_name        = module.vpc.services_range_name
  master_ipv4_cidr_block     = var.master_ipv4_cidr_block
  node_count                 = var.gke_node_count
  machine_type               = var.gke_machine_type
  disk_size_gb               = var.gke_disk_size_gb
  disk_type                  = var.gke_disk_type
  node_service_account_email = module.iam.node_gsa_email
  deletion_protection        = var.gke_deletion_protection

  depends_on = [
    google_project_service.phase3,
    module.cloud_nat,
    module.firewall,
    module.iam,
  ]
}

module "pubsub" {
  source = "../../modules/pubsub"

  project_id        = var.project_id
  runtime_gsa_email = module.iam.runtime_gsa_email

  clinical_topic_name        = var.clinical_topic_name
  lab_topic_name             = var.lab_topic_name
  clinical_subscription_name = var.clinical_subscription_name
  lab_subscription_name      = var.lab_subscription_name

  depends_on = [google_project_service.phase3, module.iam]
}

module "secret_manager" {
  source = "../../modules/secret_manager"

  project_id         = var.project_id
  accessor_gsa_email = module.iam.runtime_gsa_email
  secret_ids         = var.secret_ids

  depends_on = [google_project_service.phase3, module.iam]
}

module "ingress" {
  source = "../../modules/ingress"

  project_id   = var.project_id
  address_name = var.ingress_address_name
  domain       = var.ingress_domain

  depends_on = [google_project_service.phase3]
}
