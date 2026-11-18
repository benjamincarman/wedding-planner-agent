variable "project_id" {
  type        = string
  description = "The Google Cloud Project ID to deploy resources to."
  default     = "my-wedding-planner-prod"
}

variable "region" {
  type        = string
  description = "GCP Region for Cloud Run and Secret Manager resources."
  default     = "us-central1"
}

variable "service_name" {
  type        = string
  description = "Name of the Cloud Run agent service."
  default     = "wedding-planner-agent"
}

variable "container_image" {
  type        = string
  description = "Container image URL deployed from Artifact Registry."
  default     = "us-central1-docker.pkg.dev/my-wedding-planner-prod/agent-repo/wedding-planner-agent:latest"
}

variable "github_repository" {
  type        = string
  description = "GitHub repository (owner/repo) allowed to authenticate via Workload Identity Federation."
  default     = "benjamincarman/wedding-planner-agent"

  validation {
    condition     = can(regex("^[^/]+/[^/]+$", var.github_repository))
    error_message = "github_repository must be in 'owner/repo' format."
  }
}
