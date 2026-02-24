module "analytics" {
  source     = "./modules/analytics"
  project_id = var.gcp_project_id
  region     = var.gcp_region
}

module "notifications" {
  source = "./modules/notifications"
}

module "ingestion" {
  source        = "./modules/ingestion"
  project_id    = var.gcp_project_id
  region        = var.gcp_region
  bq_dataset_id = module.analytics.dataset_id
  cities_json   = jsonencode(var.cities) # Pass city coordinates to the Python ingestor
}

module "ml_and_jobs" {
  source        = "./modules/ml_and_jobs"
  project_id    = var.gcp_project_id
  region        = var.gcp_region
  bq_dataset_id = module.analytics.dataset_id
}

module "edge" {
  source                = "./modules/edge"
  cloudflare_account_id = var.cloudflare_account_id
  cloudflare_zone_id    = var.cloudflare_zone_id
  base_domain           = var.base_domain
  cities                = var.cities
}
