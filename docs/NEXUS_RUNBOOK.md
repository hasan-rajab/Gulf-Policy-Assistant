# NEXUS Local Runbook

1. Copy `.env.example` to `.env` and change shared-demo secrets.
2. Start the stack with `docker compose up --build`.
3. Open the frontend at `http://localhost:3000`.
4. Employee demo: `employee@gulfhorizon.local` / `Demo123!`.
5. Knowledge-admin demo: `admin@gulfhorizon.local` / `Admin123!`.

The employee account can query authorized knowledge and request controlled actions. The knowledge-admin account additionally demonstrates restricted knowledge access, ingestion, evaluation, audit verification, action approval, and action execution.

Before a cloud deployment, run `infra/migrate_nexus_acl.sql` against an existing BigQuery corpus or provision a new corpus with `infra/bigquery.sql`. Populate `ACCESS_PROFILES_JSON` from trusted identity/directory data and do not expose the private backend directly to end users.
