# Remote state backend — configure bucket/prefix for your project.
# Create the GCS bucket separately (or via bootstrap) before terraform init -backend-config.

terraform {
  backend "gcs" {
    # Set via: terraform init -backend-config=backend.hcl
    # Example backend.hcl (local, gitignored if you add it):
    #   bucket = "autonomous-agent-503517-tf-state"
    #   prefix = "trialmatch/dev"
  }
}
