terraform {
  backend "gcs" {
    bucket = "dev-tf-state-gcs"
    prefix = "player/terraform/env/dev/gcs/"
  }
}