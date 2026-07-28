-- Phase 5: Network policy allowlisting GKE Cloud NAT static IPs (Phase 2).
-- Source of truth: terraform -chdir=infra/terraform/envs/dev output -json nat_static_ips
-- Current applied NAT IPs (dev):
--   136.112.132.174
--   34.61.252.214
-- Do NOT open the policy to the entire Internet.

CREATE OR REPLACE NETWORK POLICY trialmatch_gke_egress_policy
  ALLOWED_IP_LIST = ('136.112.132.174', '34.61.252.214')
  COMMENT = 'Restrict Snowflake access to trialmatch GKE Cloud NAT egress IPs';

-- Attach to the app user once created (uncomment and adjust):
-- ALTER USER TRIALMATCH_APP SET NETWORK_POLICY = trialmatch_gke_egress_policy;
-- Or account-level (stronger): ALTER ACCOUNT SET NETWORK_POLICY = trialmatch_gke_egress_policy;
