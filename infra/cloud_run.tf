# Pinned immutable @sha256 container digests built by Cloud Build
locals {
  container_digests = {
    pm_sandbox    = "us-central1-docker.pkg.dev/gen-lang-client-0484425781/papermorph/pm-sandbox@sha256:998334a833971a295cbb27352266752489a401481649f365a1b923f2b70690dd"
    pm_api        = "us-central1-docker.pkg.dev/gen-lang-client-0484425781/papermorph/pm-api@sha256:7dfcc937afbc9ab64b1d875fc931dcdf9c8f8bd032d7dd6524a621ea27c84790"
    pm_render_job = "us-central1-docker.pkg.dev/gen-lang-client-0484425781/papermorph/pm-render-job@sha256:78315a6693154a3cf8ecc533364dc2ad7ede29637a8b8a6058e488890053a355"
  }
}

output "artifact_registry_repo" {
  value = google_artifact_registry_repository.containers.id
}

output "container_digests" {
  value = local.container_digests
}
