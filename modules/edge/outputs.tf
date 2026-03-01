output "d1_database_id" {
  description = "UUID of the Cloudflare D1 database (hyperlocal_weather_db)"
  value       = cloudflare_d1_database.global_db.id
}
