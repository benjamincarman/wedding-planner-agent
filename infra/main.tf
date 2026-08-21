terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable Required GCP APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudtrace.googleapis.com",
    "logging.googleapis.com"
  ])
  service            = each.key
  disable_on_destroy = false
}

# 2. Secret Manager for Secure Secret Management
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

# 3. Artifact Registry for Container Storage
resource "google_artifact_registry_repository" "agent_repo" {
  location      = var.region
  repository_id = "agent-repo"
  description   = "Docker repository for Wedding Planner Agent containers"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

# 4. Cloud Run Service Account
resource "google_service_account" "agent_runner_sa" {
  account_id   = "wedding-planner-runner"
  display_name = "Wedding Planner Agent Cloud Run Runner"
}

# 5. Grant Secret Access to Cloud Run SA
resource "google_secret_manager_secret_iam_member" "secret_accessor" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent_runner_sa.email}"
}

# 6. Cloud Run Service Deployment
resource "google_cloud_run_v2_service" "agent_service" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.agent_runner_sa.email
    containers {
      image = var.container_image
      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }
      env {
        name  = "APP_ENV"
        value = "production"
      }
      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_iam_member.secret_accessor
  ]
}

# 7. Make Cloud Run Publicly Accessible (Optional / Configurable)
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.agent_service.location
  service  = google_cloud_run_v2_service.agent_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
