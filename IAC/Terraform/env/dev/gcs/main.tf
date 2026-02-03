module "gcs_bucket" {
  source             = "../../../modules/cloud_storage"
  project_id         = var.project_id
  for_each           = var.gcs_bucket
  name               = each.value.app_name
  location           = each.value.location
  enable_neg         = each.value.enable_neg
  data_locations     = each.value.data_locations
  versioning         = each.value.versioning
  storage_class      = each.value.storage_class
  bucket_policy_only = each.value.bucket_policy_only
  force_destroy      = each.value.force_destroy
  labels             = each.value.labels
  retention_policy   = each.value.retention_policy
  iam_members        = each.value.iam_members
  cors               = each.value.cors
  lifecycle_rules    = each.value.lifecycle_rules
  tag_bindings       = each.value.tag_bindings
  soft_delete_policy = each.value.soft_delete_policy
  website            = each.value.website
}

resource "google_storage_managed_folder_iam_member" "member" {
  for_each       = var.gcs_managed_folder_iam_bindings
  bucket         = each.value.bucket_name
  managed_folder = each.value.bucket_folder
  member         = each.value.member
  role           = each.value.role
}
