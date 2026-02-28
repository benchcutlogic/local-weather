gcp_project_id = "hyperlocal-wx-prod"
base_domain    = "hyperwx.com"

cities = {
  "denver" = {
    name       = "Denver, CO"
    lat        = 39.7392
    lon        = -104.9903
    elev_bands = [1500, 1600, 1700, 1800, 2000]
  },
  "salt-lake-city" = {
    name       = "Salt Lake City, UT"
    lat        = 40.7608
    lon        = -111.8910
    elev_bands = [1300, 1500, 2000, 2500]
  },
  "durango" = {
    name       = "Durango, CO"
    lat        = 37.2753
    lon        = -107.8801
    elev_bands = [2000, 2200, 2500, 2800, 3000]
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
