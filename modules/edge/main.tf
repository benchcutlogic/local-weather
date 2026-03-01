variable "cloudflare_account_id" {}
variable "cloudflare_zone_id" {}
variable "base_domain" {}
variable "cities" { type = map(any) }
variable "cache_purge_token" {
  type      = string
  sensitive = true
  default   = ""
}

terraform {
  required_providers {
    cloudflare = { source = "cloudflare/cloudflare" }
  }
}

# 1. ONE Global D1 Database (For all crowdsourced reports, sharded by a city_slug column)
resource "cloudflare_d1_database" "global_db" {
  account_id = var.cloudflare_account_id
  name       = "hyperlocal_weather_db"
}

# 2. ONE Unified Astro Project
resource "cloudflare_pages_project" "wx_frontend" {
  account_id        = var.cloudflare_account_id
  name              = "hyperlocal-wx-app"
  production_branch = "main"
  build_config {
    build_command   = "npm run build"
    destination_dir = "dist"
  }
  deployment_configs {
    production {
      d1_databases = { DB = cloudflare_d1_database.global_db.id }
    }
  }
}

# 3. DYNAMIC LOOP: Creates 200+ distinct DNS subdomains pointing to the single App
resource "cloudflare_record" "city_dns" {
  for_each = var.cities

  zone_id = var.cloudflare_zone_id
  name    = each.key # Uses map key (e.g., 'denver', 'salt-lake-city')
  value   = "${cloudflare_pages_project.wx_frontend.name}.pages.dev"
  type    = "CNAME"
  proxied = true
}

# 4. Bind Custom Domains to Cloudflare Pages dynamically
resource "cloudflare_pages_domain" "city_domains" {
  for_each = var.cities

  account_id   = var.cloudflare_account_id
  project_name = cloudflare_pages_project.wx_frontend.name
  domain       = "${each.key}.${var.base_domain}"

  depends_on = [cloudflare_record.city_dns]
}

# 5. ONE Edge API Worker (Paywall validation & caching)
resource "cloudflare_worker_script" "api_gateway" {
  account_id = var.cloudflare_account_id
  name       = "wx-api-gateway"
  content    = file("${path.module}/worker.js")
  module     = true

  d1_database_binding {
    name        = "DB"
    database_id = cloudflare_d1_database.global_db.id
  }

  plain_text_binding {
    name = "COMMENTARY_BASE_URL"
    text = "https://storage.googleapis.com/hyperlocal-wx-commentary"
  }

  plain_text_binding {
    name = "FORECAST_TTL_SECONDS"
    text = "300"
  }

  plain_text_binding {
    name = "CACHE_PURGE_TOKEN"
    text = var.cache_purge_token
  }
}

# 6. Bind API routes per city to the single worker
resource "cloudflare_worker_route" "api_routes" {
  for_each    = var.cities
  zone_id     = var.cloudflare_zone_id
  pattern     = "api.${each.key}.${var.base_domain}/*"
  script_name = cloudflare_worker_script.api_gateway.name
}
