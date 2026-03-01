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
    name             = string
    state            = optional(string)
    aliases          = optional(list(string), [])
    lat              = number
    lon              = number
    timezone         = optional(string, "America/Denver")
    elev_bands       = list(number)
    terrain_profile  = optional(string)
    seasonal_hazards = optional(list(string), [])
    alert_thresholds = optional(object({
      snow_in_24h_in    = optional(number)
      wind_gust_mph     = optional(number)
      rain_in_1h_in     = optional(number)
      heat_index_f      = optional(number)
      freezing_level_ft = optional(number)
    }))
    branding = optional(object({
      hero_image    = optional(string)
      local_tagline = optional(string)
    }))
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
