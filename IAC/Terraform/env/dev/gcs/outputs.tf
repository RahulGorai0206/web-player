output "gcs_bucket_names" {
  description = "A list of the GCS bucket names."
  value       = [for v in module.gcs_bucket : v.bucket.name]
}