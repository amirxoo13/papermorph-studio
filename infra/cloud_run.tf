# Cloud Run services & jobs managed alongside container builds in Phases 4, 5, 6, 8
output "artifact_registry_repo" {
  value = google_artifact_registry_repository.containers.id
}
