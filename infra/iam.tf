locals {
  service_accounts = {
    "api"          = "Public FastAPI Cloud Run SA"
    "orchestrator" = "Cloud Workflows & Tasks Orchestrator SA"
    "sandbox"      = "Network-Isolated Python Sandbox SA"
    "render-job"   = "Papermorph Sharded Cloud Run Job SA"
    "voice"        = "Least-Privilege Voice TTS/STT Agent SA"
    "publisher"    = "Publisher & Licence Ledger Agent SA"
    "reaper"       = "Stuck Job Reaper & DLQ Drainer SA"
  }
}

resource "google_service_account" "sa" {
  for_each     = local.service_accounts
  project      = var.project_id
  account_id   = "pm-${each.key}-sa"
  display_name = each.value
}
