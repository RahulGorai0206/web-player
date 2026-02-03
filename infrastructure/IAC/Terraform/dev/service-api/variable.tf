/******************************************
  Providers Variables
 *****************************************/

variable "project_id" {
  description = "Existing Base project"
  type        = string
}

/******************************************
        Service API variables
 *****************************************/

variable "project_services_api" {
  type = map(
    object(
      {
        project_id                  = string
        activate_apis               = list(string)
        disable_dependent_services  = optional(bool)
        disable_services_on_destroy = optional(bool)
      }
    )
  )
  default = {}
}
