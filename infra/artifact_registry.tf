resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = "papermorph"
  description   = "Papermorph Studio container images"
  format        = "DOCKER"
  project       = var.project_id
}
