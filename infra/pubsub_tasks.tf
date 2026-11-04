resource "google_pubsub_topic" "dlq" {
  name    = "papermorph-dlq"
  project = var.project_id
}

resource "google_pubsub_topic" "stage_events" {
  name    = "papermorph-stage-events"
  project = var.project_id
}

resource "google_pubsub_subscription" "stage_events_sub" {
  name    = "papermorph-stage-events-sub"
  topic   = google_pubsub_topic.stage_events.id
  project = var.project_id

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 5
  }
}

resource "google_cloud_tasks_queue" "job_queue" {
  name     = "papermorph-job-queue"
  location = var.region
  project  = var.project_id

  rate_limits {
    max_concurrent_dispatches = 10
    max_dispatches_per_second = 5
  }

  retry_config {
    max_attempts = 5
  }
}
