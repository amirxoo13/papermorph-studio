resource "google_workflows_workflow" "papermorph_pipeline" {
  name            = "papermorph-pipeline"
  region          = var.region
  project         = var.project_id
  description     = "Papermorph Studio 23-Agent Stage State Machine Workflow"
  service_account = google_service_account.sa["orchestrator"].id
  source_contents = file("${path.module}/../services/workflows/papermorph_pipeline.yaml")
}
