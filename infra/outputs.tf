output "cloud_run_service_url" {
  description = "The deployed Cloud Run service URL for the Wedding Planner Agent."
  value       = google_cloud_run_v2_service.agent_service.uri
}

output "artifact_registry_repo" {
  description = "Artifact Registry Docker repository URL."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.agent_repo.repository_id}"
}

output "secret_manager_secret_id" {
  description = "Secret Manager secret ID for GEMINI_API_KEY."
  value       = google_secret_manager_secret.gemini_api_key.id
}

output "workload_identity_provider" {
  description = "The fully qualified resource name of the Workload Identity Provider for GitHub Actions."
  value       = google_iam_workload_identity_pool_provider.github_provider.name
}

output "deployer_service_account_email" {
  description = "Service Account email to configure in GitHub Actions."
  value       = google_service_account.agent_runner_sa.email
}
