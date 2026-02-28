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

variable "aois" {
  description = "Optional AOI definitions keyed by AOI slug. Supports bbox and/or polygon."
  type = map(object({
    name    = string
    min_lat = optional(number)
    min_lon = optional(number)
    max_lat = optional(number)
    max_lon = optional(number)
    polygon = optional(list(object({ lat = number, lon = number })))
  }))
  default = {}
}

variable "city_aoi_map" {
  description = "Optional city->AOI mapping for custom AOI per city (e.g., durango=>la-plata-county)."
  type        = map(string)
  default     = {}
}
