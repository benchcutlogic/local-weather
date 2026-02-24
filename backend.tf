terraform {
  backend "gcs" {
    bucket = "hyperlocal-wx-tf-state-prod" # Must be created manually via GCP Console first
    prefix = "terraform/state"
    # GCS natively handles state locking. No DynamoDB lock table needed.
  }
}
