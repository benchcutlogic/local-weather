variable "project_id" {}
variable "region" {}
variable "bq_dataset_id" {}
variable "cities_json" {}
variable "enable_noaa_pubsub_subscription" {
  type    = bool
  default = false
}

resource "google_artifact_registry_repository" "wx_repo" {
  location      = var.region
  repository_id = "weather-services"
  format        = "DOCKER"
}

resource "google_service_account" "ingest_sa" {
  account_id   = "nwp-ingest-sa"
  display_name = "NWP Ingestion Service Account"
}

resource "google_project_iam_member" "ingest_bq_writer" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.ingest_sa.email}"
}

# The Python service parsing GRIB2 byte-ranges via xarray/kerchunk in memory
resource "google_cloud_run_v2_service" "grib_parser" {
  name     = "grib2-byte-parser"
  location = var.region

  template {
    service_account = google_service_account.ingest_sa.email
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.wx_repo.repository_id}/grib2-parser:latest"
      resources {
        limits = { cpu = "2", memory = "8Gi" } # High RAM required for xarray array manipulation
      }
      env {
        name  = "BQ_DATASET"
        value = var.bq_dataset_id
      }
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "CITIES_CONFIG"
        value = var.cities_json
      }
    }
    scaling {
      min_instance_count = 0 # Scale to zero when no model runs
      max_instance_count = 4 # Handle parallel model runs (GFS + HRRR + NAM + ECMWF)
    }
  }
}

# Allow Pub/Sub to invoke Cloud Run
resource "google_cloud_run_v2_service_iam_member" "pubsub_invoker" {
  name     = google_cloud_run_v2_service.grib_parser.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.ingest_sa.email}"
}

# Wire NOAA's Public HRRR Pub/Sub directly to our Cloud Run service
resource "google_pubsub_subscription" "noaa_hrrr_trigger" {
  count = var.enable_noaa_pubsub_subscription ? 1 : 0

  name  = "noaa-hrrr-trigger"
  topic = "projects/gcp-public-data-weather/topics/gcp-public-data-weather-noaa-hrrr"

  push_config {
    push_endpoint = google_cloud_run_v2_service.grib_parser.uri
    oidc_token { service_account_email = google_service_account.ingest_sa.email }
  }

  # Only keep unprocessed messages for 1 hour
  message_retention_duration = "3600s"
  ack_deadline_seconds       = 600 # 10 min to parse GRIB2 byte ranges
}

# Cloud Scheduler fallback: trigger ingestion for GFS/NAM on a schedule
# (in case Pub/Sub notifications aren't available for all models)
resource "google_cloud_scheduler_job" "gfs_ingest_schedule" {
  name      = "gfs-ingest-trigger"
  schedule  = "30 4,10,16,22 * * *" # 30 min after each GFS cycle (00z, 06z, 12z, 18z)
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.grib_parser.uri}/ingest/gfs"
    oidc_token { service_account_email = google_service_account.ingest_sa.email }
  }
}

resource "google_cloud_scheduler_job" "nam_ingest_schedule" {
  name      = "nam-ingest-trigger"
  schedule  = "45 4,10,16,22 * * *"
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.grib_parser.uri}/ingest/nam"
    oidc_token { service_account_email = google_service_account.ingest_sa.email }
  }
}
