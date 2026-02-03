/******************************************
	GCS Bucket configuration for Terraform State management
 *****************************************/

terraform {
  backend "gcs" {
    bucket = "dev-tf-state-gcs"
    prefix = "player/terraform/env/dev/workload-identity-federation"
  }
}
