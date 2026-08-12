# Production authentication: IAP + private Cloud Run backend

The local demo intentionally uses a portable application JWT. The recommended enterprise deployment does **not** expose the FastAPI service to employee browsers.

## Request path

1. Employee opens the Next.js Cloud Run service.
2. Identity-Aware Proxy (IAP) authenticates and authorizes the employee/Google Group.
3. Next.js receives the IAP-authenticated identity header.
4. The Next.js server route obtains a Google-signed ID token for the private FastAPI Cloud Run audience.
5. FastAPI is invokable only by the web tier's service account through Cloud Run IAM.
6. The web tier forwards the employee email as `X-User-Email` for conversation ownership/audit context.

Because the backend is private, an external client cannot simply forge `X-User-Email` and reach it.

## Enable IAP

The deployment script requests direct IAP protection on the **web** Cloud Run service with `--iap --no-allow-unauthenticated`. Then grant the relevant employees or Google Group the IAP-Secured Web App User role. If this is the first IAP setup in a project without an organization, Google Cloud may require one-time OAuth setup in the Console.

For a real bank, also consider:

- Workforce Identity Federation if the workforce identities live outside Google identity
- context-aware access requirements
- disabling direct paths not covered by the chosen IAP topology
- short retention for conversation content
- Cloud Audit Logs and security monitoring
- CMEK/VPC Service Controls/data residency assessment based on the bank's policy and regulator requirements
