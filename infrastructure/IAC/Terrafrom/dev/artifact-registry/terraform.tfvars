project_id = "rahul-playground-v1"

repo = {
  repo_01 = {
    repo_name   = "dev-player-images-gar"
    region      = "asia-south2"
    format      = "DOCKER"
    description = "For Docker Images"
    labels = {
      environment = "dev",
      purpose     = "cloud-function",
    }
    immutable_tags = false,
    cleanup_policies = {
      "policy_1" = {
        action = "DELETE",
        condition = {
          tag_state  = "UNTAGGED",
          older_than = "7d"
        }
      },
      "policy_2" = {
        action = "DELETE",
        condition = {
          tag_state    = "TAGGED",
          tag_prefixes = ["main", "master"]
          older_than   = "10d"
        }
      },
      "policy_3" = {
        action = "KEEP",
        condition = {
          tag_state    = "TAGGED",
          tag_prefixes = ["dev", "staging", "production", "v"]
        }
      }
    }
  },
}
