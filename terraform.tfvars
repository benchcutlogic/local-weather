gcp_project_id = "hyperlocal-wx-prod"
base_domain    = "hyperwx.com"

cities = {
  "denver" = {
    name             = "Denver"
    state            = "CO"
    aliases          = ["den"]
    lat              = 39.7392
    lon              = -104.9903
    timezone         = "America/Denver"
    elev_bands       = [1500, 1600, 1700, 1800, 2000]
    terrain_profile  = "plains"
    seasonal_hazards = ["snow", "hail", "high_wind", "fire_smoke"]
    alert_thresholds = {
      snow_in_24h_in    = 6
      wind_gust_mph     = 45
      rain_in_1h_in     = 0.5
      heat_index_f      = 95
      freezing_level_ft = 9000
    }
    branding = {
      local_tagline = "Front Range weather with elevation-aware detail"
    }
  },
  "salt-lake-city" = {
    name             = "Salt Lake City"
    state            = "UT"
    aliases          = ["slc"]
    lat              = 40.7608
    lon              = -111.8910
    timezone         = "America/Denver"
    elev_bands       = [1300, 1500, 2000, 2500]
    terrain_profile  = "foothills"
    seasonal_hazards = ["lake_effect_snow", "inversions", "high_wind"]
    alert_thresholds = {
      snow_in_24h_in    = 8
      wind_gust_mph     = 50
      rain_in_1h_in     = 0.4
      heat_index_f      = 95
      freezing_level_ft = 9500
    }
    branding = {
      local_tagline = "Wasatch-aware forecasts, valley to crest"
    }
  },
  "durango" = {
    name             = "Durango"
    state            = "CO"
    aliases          = ["dgo"]
    lat              = 37.2753
    lon              = -107.8801
    timezone         = "America/Denver"
    elev_bands       = [2000, 2200, 2500, 2800, 3000]
    terrain_profile  = "mountain"
    seasonal_hazards = ["snowpack", "monsoon_flooding", "fire_smoke", "high_wind"]
    alert_thresholds = {
      snow_in_24h_in    = 10
      wind_gust_mph     = 50
      rain_in_1h_in     = 0.6
      heat_index_f      = 92
      freezing_level_ft = 10000
    }
    branding = {
      local_tagline = "Mountain weather for town, trails, and passes"
    }
  }
}

aois = {
  "la-plata-county" = {
    name    = "La Plata County, CO"
    min_lat = 37.00
    min_lon = -108.35
    max_lat = 37.50
    max_lon = -107.45
    polygon = [
      { lat = 37.00, lon = -108.35 },
      { lat = 37.00, lon = -107.45 },
      { lat = 37.50, lon = -107.45 },
      { lat = 37.50, lon = -108.35 }
    ]
  }
}

city_aoi_map = {
  "durango" = "la-plata-county"
}
