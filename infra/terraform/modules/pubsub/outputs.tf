output "clinical_topic" {
  description = "clinical-records topic name"
  value       = google_pubsub_topic.primary["clinical"].name
}

output "lab_topic" {
  description = "lab-updates topic name"
  value       = google_pubsub_topic.primary["lab"].name
}

output "clinical_subscription" {
  description = "clinical-records subscription name"
  value       = google_pubsub_subscription.primary["clinical"].name
}

output "lab_subscription" {
  description = "lab-updates subscription name"
  value       = google_pubsub_subscription.primary["lab"].name
}

output "clinical_dlq_topic" {
  description = "clinical-records dead-letter topic"
  value       = google_pubsub_topic.dlq["clinical"].name
}

output "lab_dlq_topic" {
  description = "lab-updates dead-letter topic"
  value       = google_pubsub_topic.dlq["lab"].name
}

output "topic_names" {
  description = "Map of primary topic names"
  value = {
    clinical = google_pubsub_topic.primary["clinical"].name
    lab      = google_pubsub_topic.primary["lab"].name
  }
}

output "subscription_names" {
  description = "Map of primary subscription names"
  value = {
    clinical = google_pubsub_subscription.primary["clinical"].name
    lab      = google_pubsub_subscription.primary["lab"].name
  }
}
