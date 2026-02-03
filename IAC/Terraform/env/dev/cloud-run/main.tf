module "cloud_run_v2" {
  source                           = "../../../modules/cloud-run"
  for_each                         = var.cloud_run
  project_id                       = var.service_project_id
  service_name                     = each.value.service_name
  location                         = each.value.location
  create_service_account           = each.value.create_service_account
  service_account                  = each.value.service_account
  service_labels                   = each.value.service_labels
  cloud_run_deletion_protection    = each.value.cloud_run_deletion_protection
  ingress                          = each.value.ingress
  volumes                          = each.value.volumes
  vpc_access                       = each.value.vpc_access
  containers                       = each.value.containers
  max_instance_request_concurrency = each.value.max_instance_request_concurrency
  template_scaling                 = each.value.scaling
  template_annotations             = each.value.template_annotations
}
