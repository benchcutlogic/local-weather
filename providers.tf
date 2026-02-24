terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google     = { source = "hashicorp/google", version = "~> 5.15" }
    cloudflare = { source = "cloudflare/cloudflare", version = "~> 4.25" }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}
