variable "project_id" {}
variable "region" {}
variable "bq_dataset_id" {}

resource "google_service_account" "ml_sa" {
  account_id   = "llm-and-gee-sa"
  display_name = "LLM Commentary & GEE Service Account"
}

resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.ml_sa.email}"
}

resource "google_project_iam_member" "bq_reader" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.ml_sa.email}"
}

resource "google_project_iam_member" "bq_writer" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.ml_sa.email}"
}

# Cloud Run Service for Gemini LLM Commentary Generation
# Queries BigQuery for forecast + drift + terrain context, generates conversational commentary
resource "google_cloud_run_v2_service" "llm_commentary" {
  name     = "gemini-forecast-commentary"
  location = var.region

  template {
    service_account = google_service_account.ml_sa.email
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/weather-services/llm-commentary:latest"
      resources {
        limits = { cpu = "1", memory = "2Gi" }
      }
      env {
        name  = "BQ_DATASET"
        value = var.bq_dataset_id
      }
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 10 # Handle burst when all 200 cities regenerate
    }
  }
}

# Allow unauthenticated access (the commentary endpoint is called by Cloudflare Workers)
resource "google_cloud_run_v2_service_iam_member" "commentary_public" {
  name     = google_cloud_run_v2_service.llm_commentary.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# EARTH ENGINE ASYNC ORCHESTRATION
# Triggers Python GEE extraction script every 24 hours to pull RTMA verification into BQ
resource "google_cloud_scheduler_job" "gee_verification" {
  name      = "gee-daily-rtma-verification"
  schedule  = "0 4 * * *" # 4 AM UTC daily
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.llm_commentary.uri}/trigger-gee-rtma"
    oidc_token { service_account_email = google_service_account.ml_sa.email }
  }
}

# Terrain context refresh — run annually or on-demand
resource "google_cloud_scheduler_job" "gee_terrain_refresh" {
  name      = "gee-annual-terrain-refresh"
  schedule  = "0 6 1 1 *" # January 1st, 6 AM UTC
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.llm_commentary.uri}/trigger-gee-terrain"
    oidc_token { service_account_email = google_service_account.ml_sa.email }
  }
}

# Commentary generation trigger — runs after each ingestion cycle
resource "google_cloud_scheduler_job" "commentary_generation" {
  name      = "commentary-generation-trigger"
  schedule  = "0 5,11,17,23 * * *" # 1 hour after each GFS cycle
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.llm_commentary.uri}/generate-all"
    oidc_token { service_account_email = google_service_account.ml_sa.email }
  }
}
