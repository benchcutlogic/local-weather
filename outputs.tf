output "d1_database_id" {
  description = "Cloudflare D1 database UUID — store as CLOUDFLARE_D1_DATABASE_ID GitHub secret"
  value       = module.edge.d1_database_id
}
