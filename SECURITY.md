# Security Specification — Actually Fair Operations Console

Version 0.1 · August 2026

This console holds every customer name, phone number, and address the business has, plus supplier costs and freight rates. Treat a breach as a business-ending event, not an inconvenience. The controls below are requirements, not suggestions.

---

## 1. Threat model

| Threat | Realistic route | Control |
|---|---|---|
| Credential theft | Reused password, phishing | Mandatory TOTP, rate limiting, lockout |
| Session hijack | Stolen cookie on a shared machine | Short expiry, rotation, HttpOnly, device binding |
| Ex-employee access | Account left enabled after departure | Owner-only user admin, immediate disable, session revocation |
| Bulk customer data exfiltration | Legitimate login, then scripted scraping | Export gated to `owner`, rate limits, audit on read of bulk endpoints |
| Injection | Search input, XLSX filename, order notes | Parameterised queries only, output escaping, no dynamic SQL |
| Malicious upload | XLSX with macros or a zip bomb | Type and magic-byte check, size cap, parse in read-only mode, never execute |
| Secret leak | API keys committed to the repo | Env only, secret scanning in CI, key rotation runbook |
| Supply chain | Compromised dependency | Pinned lockfiles, `pip-audit` and `npm audit` in CI, no unpinned installs |

Out of model for v1: a determined attacker with server root, and nation-state actors. The mitigation for both is backups and a rotation runbook.

## 2. Authentication

- Passwords hashed with `argon2id`. Parameters: 64 MB memory, 3 iterations, parallelism 4. Never MD5, SHA, or bcrypt.
- Minimum 12 characters. Check against the Have I Been Pwned k-anonymity range API on set. No composition rules, no forced rotation.
- TOTP is mandatory for every account, including `viewer`. Enrolment is forced on first login and cannot be skipped.
- Ten single-use recovery codes issued at enrolment, shown once, stored hashed.
- Five failed attempts locks the account for 15 minutes. Lockout counts by account and by IP separately.
- Login responses are constant-time and identical for unknown email and wrong password. No user enumeration.
- No password reset by email link in v1. `owner` resets accounts manually.

## 3. Sessions

- Server-side sessions in Postgres. No JWTs. Revocation must be instant, and a stateless token cannot be revoked.
- Session ID: 256 bits from `secrets.token_urlsafe`, stored as a SHA-256 hash. The raw value exists only in the cookie.
- Cookie flags: `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/`, no `Domain` attribute.
- Absolute expiry 12 hours. Idle expiry 60 minutes. Session ID rotates on privilege change and after MFA.
- Bound to a hash of IP and user agent. A mismatch revokes and forces re-login.
- Logout revokes server-side, not just client-side.
- `owner` can view and revoke any active session from the admin screen.

## 4. Authorisation

- Every endpoint declares a required role through a FastAPI dependency. The default is deny.
- No role checks in the frontend beyond hiding controls. The frontend is not a security boundary.
- Write endpoints require `ops` or `owner`. User admin, audit log, and bulk export require `owner`.
- Object-level checks run even where every user can currently see everything, so adding a scoped role later does not require an audit of every handler.

## 5. Transport and headers

- TLS 1.2 minimum, 1.3 preferred. HTTP redirects to HTTPS.
- HSTS with a 1-year max-age and `includeSubDomains`.
- Content-Security-Policy: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://cdn.shopify.com; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`. No inline scripts, no CDN script sources.
- `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Permissions-Policy` denying camera, microphone, and geolocation.
- CORS off. Frontend is served same-origin.
- CSRF: double-submit token in a non-HttpOnly cookie, echoed in `X-CSRF-Token`, verified on every unsafe method.

## 6. Input and output

- SQLAlchemy parameter binding only. No f-string SQL anywhere, including in migrations and jobs.
- All request bodies validated by Pydantic with explicit types and bounds. Reject unknown fields.
- Uploads: extension allowlist, magic-byte verification, 25 MB cap, stored outside the web root with a generated filename, never served back.
- React escapes by default. `dangerouslySetInnerHTML` is banned; add a lint rule that fails the build.
- Error responses carry a code and an operator-readable message. No stack traces, SQL, or file paths reach the client.

## 7. Data protection

- Database encrypted at rest through the host volume. TLS to Postgres even on localhost.
- TOTP secrets encrypted with a key from the environment, not stored plaintext.
- Backups encrypted with `age` before upload. The backup key is stored separately from the server credentials.
- No customer PII in application logs. Log order numbers and user ids, never phone numbers, addresses, or emails.
- The Shopify token, the Meta WhatsApp token, and the database URL live in environment variables. `.env` is in `.gitignore`, and CI runs `gitleaks` on every push.
- Bulk export writes an audit entry naming the actor, the row count, and the filter used.

## 8. Rate limits

| Endpoint | Limit |
|---|---|
| `POST /auth/login` | 5 per 15 min per IP, 5 per 15 min per account |
| `POST /auth/mfa` | 5 per 15 min per session |
| `GET /search` | 60 per minute per user |
| Bulk export | 5 per hour per user |
| Everything else | 300 per minute per user |

Limits are enforced server-side in Postgres or in-process, and return 429 with a `Retry-After` header.

## 9. Audit

- Every write records actor, IP, action, object, before, and after.
- Reads are audited for bulk endpoints and exports only.
- `audit_log` has `UPDATE` and `DELETE` revoked from the application role. The application cannot rewrite its own history.
- Retention 24 months minimum. Export available to `owner`.

## 10. Operations

- Dependencies pinned by lockfile. `pip-audit` and `npm audit` run in CI and fail the build on a high severity finding.
- Docker images run as a non-root user. No `latest` tags.
- Database is not exposed to the public internet. Only the reverse proxy has a public port.
- SSH by key only, password authentication disabled, root login disabled.
- Nightly backup with a monthly restore test recorded as a checklist item.
- Key rotation runbook covering the Shopify token, WhatsApp token, database password, and session secret. Rotate on any suspicion and on employee departure.

## 11. Pre-launch checklist

- [ ] TOTP enforced for all accounts, no bypass path
- [ ] Session revocation verified from the admin screen
- [ ] A `viewer` receives 403 on every write endpoint, tested
- [ ] CSP delivered and violation-free in the browser console
- [ ] `gitleaks` clean on full history, not just the last commit
- [ ] Backup restored into a scratch database and verified
- [ ] Rate limits confirmed with a scripted burst
- [ ] Audit log written for create, update, and delete on every object type
- [ ] `.env.example` contains no real values
- [ ] Database port not reachable from outside the host

## Note on this build pass

TOTP enforcement, HIBP password checks, and rate limiting are **not yet implemented** in this pass — see the "Known gaps" section of the root `README.md`. Do not treat this instance as launch-ready until those are closed.
