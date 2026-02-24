# Enable all required GCP APIs via Terraform
# These must be enabled before any resources can be created.

locals {
  required_apis = [
    "bigquery.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "pubsub.googleapis.com",
    "aiplatform.googleapis.com",
    "earthengine.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",       # Required by Cloud Run networking
    "eventarc.googleapis.com",      # For event-driven triggers
    "storage.googleapis.com",       # GCS for commentary JSON
  ]
}

resource "google_project_service" "apis" {
  for_each = toset(local.required_apis)

  project = var.gcp_project_id
  service = each.value

  disable_on_destroy = false # Don't disable APIs if we tear down infra
}
