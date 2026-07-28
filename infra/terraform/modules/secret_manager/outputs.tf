output "secret_ids" {
  description = "Created Secret Manager secret IDs"
  value       = sort([for s in google_secret_manager_secret.this : s.secret_id])
}

output "secret_resource_names" {
  description = "Full resource names for applications"
  value = {
    for id, secret in google_secret_manager_secret.this :
    id => secret.name
  }
}
