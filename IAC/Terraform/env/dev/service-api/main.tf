module "project_services_api" {
  source        = "../../../modules/service-api"
  for_each      = var.project_services_api
  project_id    = each.value.project_id
  activate_apis = each.value.activate_apis
}