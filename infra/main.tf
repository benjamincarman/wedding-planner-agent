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

# 8. Workload Identity Federation (Keyless GitHub Actions OIDC Authentication)
resource "google_iam_workload_identity_pool" "github_pool" {
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions Pool"
  description               = "Workload Identity Pool for GitHub Actions keyless deployments"
}

resource "google_iam_workload_identity_pool_provider" "github_provider" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Provider"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# 9. Allow GitHub Actions to impersonate the Service Account
resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = google_service_account.agent_runner_sa.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool.name}/*"
}

# 10. Grant Deployment IAM Roles to the Service Account
resource "google_project_iam_member" "sa_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.agent_runner_sa.email}"
}

resource "google_project_iam_member" "sa_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.agent_runner_sa.email}"
}

resource "google_project_iam_member" "sa_cloudbuild_editor" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${google_service_account.agent_runner_sa.email}"
}

resource "google_service_account_iam_member" "sa_user_self" {
  service_account_id = google_service_account.agent_runner_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.agent_runner_sa.email}"
}
