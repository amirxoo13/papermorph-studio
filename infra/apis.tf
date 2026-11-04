locals {
  enabled_apis = [
    "serviceusage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudbilling.googleapis.com",
    "billingbudgets.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "workflows.googleapis.com",
    "workflowexecutions.googleapis.com",
    "eventarc.googleapis.com",
    "eventarcpublishing.googleapis.com",
    "cloudtasks.googleapis.com",
    "pubsub.googleapis.com",
    "cloudscheduler.googleapis.com",
    "firestore.googleapis.com",
    "firebaserules.googleapis.com",
    "firebase.googleapis.com",
    "firebaseapphosting.googleapis.com",
    "identitytoolkit.googleapis.com",
    "firebaseappcheck.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",
    "discoveryengine.googleapis.com",
    "documentai.googleapis.com",
    "texttospeech.googleapis.com",
    "speech.googleapis.com",
    "dlp.googleapis.com",
    "secretmanager.googleapis.com",
    "binaryauthorization.googleapis.com",
    "containerscanning.googleapis.com",
    "bigquery.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com"
  ]
}

resource "google_project_service" "required" {
  for_each           = toset(local.enabled_apis)
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}
