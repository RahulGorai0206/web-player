project_id = "rahul-playground-v1"

gcs_bucket = {
  dev-tf-state-gcs = {
    app_name           = "dev-tf-state-gcs"
    location           = "asia-south2"
    versioning         = true
    storage_class      = "STANDARD"
    bucket_policy_only = true
    force_destroy      = false
    enable_neg         = false
    data_locations     = []
    labels = {
      environment = "dev"
      purpose     = "terraform-state"
    }
    retention_policy = null
  }
  player-movie-bucket = {
    app_name           = "player-movie-bucket"
    location           = "asia-south2"
    versioning         = true
    storage_class      = "STANDARD"
    bucket_policy_only = true
    force_destroy      = false
    enable_neg         = false
    data_locations     = []
    labels = {
      environment = "dev"
      purpose     = "data-collection"
    }
    retention_policy = null
    iam_members = [
      {
        member = "serviceAccount:dev-cloud-run-sa@rahul-playground-v1.iam.gserviceaccount.com"
        role   = "roles/storage.objectViewer"
    }]
  }
}