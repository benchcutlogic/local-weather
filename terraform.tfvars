gcp_project_id = "hyperlocal-wx-prod"
base_domain    = "hyperlocalwx.com"

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
