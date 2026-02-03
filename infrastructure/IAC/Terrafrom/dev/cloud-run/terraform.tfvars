service_project_id = "rahul-playground-v1"
cloud_run = {
  "player-service" = {
    service_name                  = "dev-player-service-asia-south2-cr"
    execution_environment         = "EXECUTION_ENVIRONMENT_GEN2"
    location                      = "asia-south2"
    create_service_account        = false
    service_account               = "dev-cloud-run-sa@rahul-playground-v1.iam.gserviceaccount.com"
    cloud_run_deletion_protection = true
    ingress                       = "INGRESS_TRAFFIC_ALL"
    service_labels = {
      tier    = "web"
      env     = "dev"
      purpose = "player-service"
    }
    containers = [
      {
        container_image = "asia-south2-docker.pkg.dev/rahul-playground-v1/dev-player-images-gar/player-service:latest"
        container_name  = "player-service"
        ports = {
          container_port = 5500
          name           = "http1"
        }

        resources = {
          cpu_idle          = true
          startup_cpu_boost = true
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }
        startup_probe = {
          initial_delay_seconds = 30
          timeout_seconds       = 240
          period_seconds        = 240
          failure_threshold     = 2
          tcpSocket = {
            port         = 5500
          }
        }
      }
    ]
    max_instance_request_concurrency = "10"
    scaling = {
      # Required due to slow cold start.
      min_instance_count = 0
      max_instance_count = 1
    }
  }
}