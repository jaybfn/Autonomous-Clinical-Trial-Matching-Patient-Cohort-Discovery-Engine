data "google_project" "this" {
  project_id = var.project_id
}

locals {
  topics = {
    clinical = {
      name             = var.clinical_topic_name
      subscription     = var.clinical_subscription_name
      dlq_topic        = "${var.clinical_topic_name}-dlq"
      dlq_subscription = "${var.clinical_topic_name}-dlq-sub"
    }
    lab = {
      name             = var.lab_topic_name
      subscription     = var.lab_subscription_name
      dlq_topic        = "${var.lab_topic_name}-dlq"
      dlq_subscription = "${var.lab_topic_name}-dlq-sub"
    }
  }

  pubsub_service_agent = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_topic" "primary" {
  for_each = local.topics

  project                    = var.project_id
  name                       = each.value.name
  message_retention_duration = var.message_retention_duration

  labels = {
    app = "trialmatch"
  }
}

resource "google_pubsub_topic" "dlq" {
  for_each = local.topics

  project                    = var.project_id
  name                       = each.value.dlq_topic
  message_retention_duration = var.message_retention_duration

  labels = {
    app     = "trialmatch"
    purpose = "dlq"
  }
}

# Pub/Sub service agent must publish to the dead-letter topic before DLQ wiring works.
resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  for_each = local.topics

  project = var.project_id
  topic   = google_pubsub_topic.dlq[each.key].name
  role    = "roles/pubsub.publisher"
  member  = local.pubsub_service_agent
}

resource "google_pubsub_subscription" "primary" {
  for_each = local.topics

  project                    = var.project_id
  name                       = each.value.subscription
  topic                      = google_pubsub_topic.primary[each.key].id
  ack_deadline_seconds       = var.ack_deadline_seconds
  message_retention_duration = var.message_retention_duration
  retain_acked_messages      = false
  enable_message_ordering    = false

  retry_policy {
    minimum_backoff = var.retry_minimum_backoff
    maximum_backoff = var.retry_maximum_backoff
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq[each.key].id
    max_delivery_attempts = var.max_delivery_attempts
  }

  expiration_policy {
    ttl = ""
  }

  labels = {
    app = "trialmatch"
  }

  depends_on = [google_pubsub_topic_iam_member.dlq_publisher]
}

resource "google_pubsub_subscription" "dlq" {
  for_each = local.topics

  project              = var.project_id
  name                 = each.value.dlq_subscription
  topic                = google_pubsub_topic.dlq[each.key].id
  ack_deadline_seconds = var.ack_deadline_seconds

  expiration_policy {
    ttl = ""
  }

  labels = {
    app     = "trialmatch"
    purpose = "dlq"
  }
}

# Pub/Sub service agent needs Subscriber on the primary subscription to forward to DLQ.
resource "google_pubsub_subscription_iam_member" "pubsub_sa_subscriber" {
  for_each = local.topics

  project      = var.project_id
  subscription = google_pubsub_subscription.primary[each.key].name
  role         = "roles/pubsub.subscriber"
  member       = local.pubsub_service_agent
}

# Runtime GSA (Workload Identity): publish events + pull subscriptions.
resource "google_pubsub_topic_iam_member" "runtime_publisher" {
  for_each = local.topics

  project = var.project_id
  topic   = google_pubsub_topic.primary[each.key].name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${var.runtime_gsa_email}"
}

resource "google_pubsub_subscription_iam_member" "runtime_subscriber" {
  for_each = local.topics

  project      = var.project_id
  subscription = google_pubsub_subscription.primary[each.key].name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${var.runtime_gsa_email}"
}

resource "google_pubsub_subscription_iam_member" "runtime_dlq_subscriber" {
  for_each = local.topics

  project      = var.project_id
  subscription = google_pubsub_subscription.dlq[each.key].name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${var.runtime_gsa_email}"
}
