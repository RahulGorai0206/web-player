output "cloud_run_service_name" {
  value       = module.cloud_run_v2["player-service"].service_name
  description = "Name of the created service"
}
