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
