module "analytics" {
  source     = "./modules/analytics"
  project_id = var.gcp_project_id
  region     = var.gcp_region

  depends_on = [google_project_service.apis]
}

module "notifications" {
  source = "./modules/notifications"

  depends_on = [google_project_service.apis]
}

module "ingestion" {
  source                       = "./modules/ingestion"
  project_id                   = var.gcp_project_id
  region                       = var.gcp_region
  bq_dataset_id                = module.analytics.dataset_id
  cities_json                  = jsonencode(var.cities) # Pass city coordinates to the Python ingestor
  aois_json                    = jsonencode(var.aois)
  city_aoi_map_json            = jsonencode(var.city_aoi_map)
  deploy_service_account_email = "deploy-ci@${var.gcp_project_id}.iam.gserviceaccount.com"

  edge_cache_purge_url   = var.edge_cache_purge_url
  edge_cache_purge_token = var.edge_cache_purge_token

  depends_on = [google_project_service.apis]
}

module "ml_and_jobs" {
  source        = "./modules/ml_and_jobs"
  project_id    = var.gcp_project_id
  region        = var.gcp_region
  bq_dataset_id = module.analytics.dataset_id
  cities_json   = jsonencode(var.cities)

  depends_on = [google_project_service.apis]
}

module "edge" {
  source                = "./modules/edge"
  cloudflare_account_id = var.cloudflare_account_id
  cloudflare_zone_id    = var.cloudflare_zone_id
  base_domain           = var.base_domain
  cities                = var.cities
  cache_purge_token     = var.edge_cache_purge_token
}
