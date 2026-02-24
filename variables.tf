variable "gcp_project_id" { type = string }
variable "gcp_region" {
  type    = string
  default = "us-central1"
}
variable "cloudflare_api_token" {
  type      = string
  sensitive = true
}
variable "cloudflare_account_id" { type = string }
variable "cloudflare_zone_id" { type = string }
variable "base_domain" { type = string }

# Scaling to 300 cities means adding strictly to this map in tfvars.
variable "cities" {
  description = "Map of all target cities for the platform."
  type = map(object({
    name       = string
    lat        = number
    lon        = number
    elev_bands = list(number)
  }))
}
