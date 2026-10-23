# SiliconBrains University Security & Access Control Policy

> **Project:** SiliconBrains University
> **Platforms:** Website (Next.js frontend + FastAPI backend/API); no Android application is currently present in this repository.
> **Owner:** SiliconBrains University Engineering / Security Lead
> **Version:** 1.0 · **Last reviewed:** 2026-10-23 · **Next review:** 2027-04-23

This document defines the security standards and access control rules for the project. All contributors must follow it. Items marked **[MUST]** are mandatory, **[SHOULD]** are strongly recommended, **[MAY]** are optional. This policy was reviewed against the live repository code in `web/` and `server/` as of 2026-10-23.

This policy is tailored to the current repository. Application controls are implemented in the web and API code where possible. Operational controls (such as MFA enrollment, cloud account reviews, incident contacts, backups, and protected branch settings) require configuration by the repository and service owners and cannot be enforced by application code alone. Android requirements are not applicable until an Android client is added.

### Project role mapping

| Project role | Policy role | Authority |
|---|---|---|
| Student | User | Own profile, course activity, and student resources |
| Teacher | User / content manager | Assigned teaching resources and course-scoped teaching actions |
| Admin | Admin | Administrative users, courses, notices, and platform operations |
| Guest | Guest | Public pages and public verification only |

Role assignment is controlled through Clerk public metadata by authorized administrators and synchronized to the application database through privileged admin actions and signed Clerk webhooks. The database is authoritative during requests, so stale JWT role claims cannot restore removed privileges. A client-supplied role or user ID is never an authorization grant. There is no separate moderator or super-admin role in the current application.

### Current implementation boundary

- Backend authentication uses Clerk-signed JWTs; backend authorization uses database roles and resource ownership.
- The repository's demo login and development auth bypass are development/test-only and must remain disabled in production.
- The web client authenticates API calls with the `Authorization` header; credentials must not be placed in URLs or browser persistent storage.
- The supplied Android, payment-card, MFA, infrastructure, vendor, incident-response, and legal-compliance controls remain operational obligations or not applicable; this repository does not contain the systems needed to implement them.

---

## Table of Contents

1. [Scope & Principles](#1-scope--principles)
2. [Roles & Permissions (RBAC)](#2-roles--permissions-rbac)
3. [Authentication](#3-authentication)
4. [Authorization](#4-authorization)
5. [Session & Token Management](#5-session--token-management)
6. [API & Backend Security](#6-api--backend-security)
7. [Website Security](#7-website-security)
8. [Android Security](#8-android-security)
9. [Data Protection & Privacy](#9-data-protection--privacy)
10. [Secrets Management](#10-secrets-management)
11. [Infrastructure & Environment Access](#11-infrastructure--environment-access)
12. [Source Code & CI/CD Security](#12-source-code--cicd-security)
13. [Dependency & Supply Chain Security](#13-dependency--supply-chain-security)
14. [Logging, Monitoring & Auditing](#14-logging-monitoring--auditing)
15. [Incident Response](#15-incident-response)
16. [Security Testing](#16-security-testing)
17. [Onboarding & Offboarding](#17-onboarding--offboarding)
18. [Compliance Checklists](#18-compliance-checklists)
19. [Appendix](#19-appendix)

---

## 1. Scope & Principles

### 1.1 Scope
Applies to: website (frontend), backend/API services, databases, cloud infrastructure, CI/CD pipelines, source repositories, third-party services, and all people with access to them. Android requirements apply only if an Android client is introduced.

### 1.2 Core Principles
| Principle | Meaning |
|---|---|
| **Least privilege** | Grant only the minimum access needed, for the minimum time. |
| **Defense in depth** | Multiple layers of controls; never rely on a single one. |
| **Zero trust** | Never trust the client, network, or internal service by default. Verify every request. |
| **Secure by default** | Default configs are locked down; access is opt-in. |
| **Fail securely** | On error, deny access and reveal nothing sensitive. |
| **Separation of duties** | No single person can deploy, approve, and audit their own change. |
| **Auditability** | Every sensitive action is logged and attributable. |

---

## 2. Roles & Permissions (RBAC)

### 2.1 Application Roles (end users)

| Role | Description | Typical Permissions |
|---|---|---|
| **Guest** | Unauthenticated visitor | View public pages and verify public credentials |
| **Student** | Enrolled learner | Own profile, courses, exams, results, tasks, and learning tools |
| **Teacher** | Teaching staff | Assigned courses, exams, tasks, and course-scoped whiteboards |
| **Admin** | Platform administrator | Manage users, courses, notices, and administrative operations |

The application has no separate Premium, Moderator, or Super Admin role. Privileged role changes are restricted to admin-authorized backend operations.

### 2.2 Project Permission Matrix

| Resource / Action | Guest | Student | Teacher | Admin |
|---|:--:|:--:|:--:|:--:|
| View public pages | ✅ | ✅ | ✅ | ✅ |
| View / edit own profile | ❌ | ✅ | ✅ | ✅ |
| Access own learning data | ❌ | ✅ | ✅ | ✅ |
| Access assigned teaching data | ❌ | ❌ | ✅ | ✅ |
| View other users' data | ❌ | ❌ | ❌ | ✅ |
| Manage users and roles | ❌ | ❌ | ❌ | ✅ |
| Access audit logs | ❌ | ❌ | ❌ | ✅ (read) |

### 2.3 Team / Internal Roles

| Role | Access |
|---|---|
| **Developer** | Dev + staging environments; read-only on production logs (masked) |
| **QA** | Staging; test data only |
| **DevOps / SRE** | Infrastructure, CI/CD, deployments; production via just-in-time access |
| **Security Lead** | Read access to all logs & configs; manages security tooling |
| **Product / Support** | Admin panel with limited, audited data access |
| **Contractor / Vendor** | Time-boxed, scoped access to specific resources only |

### 2.4 Rules
- **[MUST]** Roles are assigned by an authorized owner, never self-assigned.
- **[MUST]** Access is role-based, not user-based; avoid one-off permission grants.
- **[MUST]** Review all privileged access **quarterly**; remove what is not needed.
- **[SHOULD]** Admin/Super Admin accounts are separate from daily-use accounts.
- **[SHOULD]** Use time-bound (just-in-time) elevation for production access.

---

## 3. Authentication

### 3.1 Passwords
- **[MUST]** Minimum 12 characters; check against breached-password lists.
- **[MUST]** Hash with **Argon2id** (preferred), **bcrypt** (cost ≥ 12), or **scrypt**. Never MD5/SHA1/plain SHA256.
- **[MUST]** Never log, email, or display passwords.
- **[SHOULD]** Do not force periodic rotation unless compromise is suspected.
- **[MUST]** Rate-limit login attempts and apply progressive lockout / CAPTCHA.

### 3.2 Multi-Factor Authentication (MFA)
| Account Type | MFA |
|---|---|
| Super Admin / Admin | **[MUST]** (TOTP, hardware key, or passkey; avoid SMS) |
| Internal team (code, cloud, CI/CD) | **[MUST]** |
| End users | **[SHOULD]** offer optional MFA / passkeys |

### 3.3 Social / SSO Login
- **[MUST]** Use OAuth 2.0 + OpenID Connect with **PKCE** (mandatory for Android and SPAs).
- **[MUST]** Validate `state`, `nonce`, `aud`, `iss`, and signature on ID tokens.
- **[MUST]** Whitelist exact redirect URIs; no wildcards.

### 3.4 Account Recovery
- **[MUST]** Reset links are single-use, expire in ≤ 15–30 minutes, and are high-entropy.
- **[MUST]** Use generic responses ("If the account exists, an email was sent") to prevent account enumeration.
- **[MUST]** Notify the user via email/push on password change, email change, or MFA change.

### 3.5 Registration & Verification
- **[MUST]** Verify email (and phone, if used) before granting full access.
- **[SHOULD]** Bot protection (CAPTCHA / device attestation) on signup and login.

---

## 4. Authorization

- **[MUST]** Enforce authorization **server-side on every request**. Hiding buttons/screens in the website or Android app is **not** security.
- **[MUST]** Deny by default; explicitly allow.
- **[MUST]** Prevent **IDOR / BOLA**: verify the requesting user owns or may access the object ID (`/orders/123`), not just that they are logged in.
- **[MUST]** Prevent privilege escalation: users must not be able to modify their own `role`, `isAdmin`, `permissions`, or `userId` via request body (avoid mass assignment; use allow-lists / DTOs).
- **[MUST]** Check function-level access (e.g., `/admin/*` endpoints require admin role).
- **[SHOULD]** Centralize authorization logic (middleware/policy layer) rather than scattering checks.
- **[SHOULD]** For complex needs, use ABAC/policy engines (e.g., OPA, Casbin) in addition to RBAC.
- **[MUST]** Log authorization failures.

**Example (pseudo-code):**
```js
// Good: server-side ownership check
const order = await Order.findById(req.params.id);
if (!order || order.userId !== req.user.id) return res.status(404).end();
```

---

## 5. Session & Token Management

### 5.1 Website Sessions
- **[MUST]** Cookies: `HttpOnly; Secure; SameSite=Lax` (or `Strict`), scoped to the correct domain/path.
- **[MUST]** Regenerate the session ID on login and privilege change.
- **[MUST]** Idle timeout (e.g., 30 min) and absolute timeout (e.g., 12 h); shorter for admin panels.
- **[MUST]** Invalidate sessions server-side on logout, password change, and account disable.
- **[MUST]** CSRF protection (anti-CSRF tokens or SameSite + custom header) for cookie-based auth.

### 5.2 Tokens (JWT / Bearer / API)
- **[MUST]** Short-lived access tokens (5–15 min) + rotating refresh tokens.
- **[MUST]** Refresh token reuse detection → revoke the whole token family.
- **[MUST]** Sign with strong algorithms (RS256/ES256/EdDSA); **reject `alg: none`**; pin the allowed algorithm.
- **[MUST]** Validate `exp`, `iat`, `iss`, `aud`; keep claims minimal (no sensitive data in JWT payload).
- **[MUST]** Provide a token revocation mechanism (denylist or short TTL + server-side session).
- **[MUST NOT]** Store tokens in `localStorage` on the website if avoidable (XSS-exposed); prefer `HttpOnly` cookies.

### 5.3 Android Token Storage
- **[MUST]** Store tokens in **EncryptedSharedPreferences** or **Jetpack DataStore + Android Keystore**-backed encryption.
- **[MUST NOT]** Store tokens/passwords in plain `SharedPreferences`, SQLite, logs, or external storage.
- **[SHOULD]** Require biometric re-auth (`BiometricPrompt`) for sensitive actions.

---

## 6. API & Backend Security

### 6.1 Transport
- **[MUST]** HTTPS/TLS 1.2+ everywhere (prefer TLS 1.3); redirect HTTP → HTTPS.
- **[MUST]** HSTS with `includeSubDomains` (and preload when ready).
- **[MUST]** Internal service-to-service traffic encrypted (mTLS where feasible).

### 6.2 Input & Output
- **[MUST]** Validate all input server-side (type, length, format, range) using allow-lists.
- **[MUST]** Use parameterized queries / ORM; never concatenate SQL/NoSQL queries.
- **[MUST]** Encode output contextually to prevent XSS; sanitize rich text with a vetted library.
- **[MUST]** Prevent SSRF: validate/allow-list outbound URLs, block internal IP ranges and metadata endpoints.
- **[MUST]** Validate file uploads: type (by content, not extension), size limits, random filenames, store outside web root, malware scan, serve from a separate domain/bucket.
- **[MUST]** Prevent XXE, deserialization attacks, command injection, and path traversal.

### 6.3 Abuse Protection
- **[MUST]** Rate limiting & throttling per IP, user, and API key.
- **[SHOULD]** WAF in front of public endpoints; bot management on auth endpoints.
- **[SHOULD]** Request size limits and timeouts.

### 6.4 API Design
- **[MUST]** Return generic error messages to clients; log details server-side. No stack traces in production.
- **[MUST]** Use correct HTTP verbs and status codes; do not expose sensitive data in URLs/query strings.
- **[SHOULD]** Version APIs and retire old versions; maintain an API inventory (no shadow/zombie APIs).
- **[SHOULD]** Return only necessary fields (avoid excessive data exposure).
- **[MUST]** Disable unused HTTP methods and debug/admin endpoints in production.

### 6.5 CORS
- **[MUST]** Allow-list exact origins; never `*` with credentials; do not reflect the `Origin` header blindly.

---

## 7. Website Security

### 7.1 Security Headers
| Header | Recommended Value |
|---|---|
| `Content-Security-Policy` | Strict policy; avoid `unsafe-inline` / `unsafe-eval`; use nonces/hashes |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` / CSP `frame-ancestors` | `DENY` or `SAMEORIGIN` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Disable unused features (camera, mic, geolocation, etc.) |
| `Cross-Origin-Opener-Policy` | `same-origin` |
| `Cross-Origin-Resource-Policy` | `same-site` (or as needed) |

### 7.2 Frontend Rules
- **[MUST]** Avoid `innerHTML`, `document.write`, `eval`; use framework escaping (React/Vue/Angular defaults) and never bypass it with unsanitized data.
- **[MUST]** Use Subresource Integrity (SRI) for third-party scripts/styles.
- **[MUST]** Do not embed secrets, API keys with write access, or internal URLs in frontend bundles.
- **[MUST]** Disable source maps in production, or restrict access to them.
- **[SHOULD]** Add `rel="noopener noreferrer"` on external `target="_blank"` links.
- **[SHOULD]** Disable autocomplete on sensitive fields where appropriate.

### 7.3 Admin Panel
- **[MUST]** Separate route/subdomain, MFA required, IP allow-list or VPN where possible.
- **[MUST]** All admin actions audited; destructive actions need confirmation / re-authentication.
- **[SHOULD]** Do not expose admin panel discoverability (no links from public pages, `robots.txt` is not security).

### 7.4 Cookies & Privacy
- **[MUST]** Cookie consent banner where legally required (GDPR/ePrivacy/DPDP).
- **[SHOULD]** Minimize third-party trackers; review all third-party scripts.

### 7.5 Hosting & Server
- **[MUST]** Disable directory listing; remove default pages and server version banners.
- **[MUST]** Keep OS, web server, runtime, and framework patched.
- **[MUST]** Separate environments (dev/staging/prod) with separate databases and credentials.

---

## 8. Android Security (not applicable to the current repository)

No Android project or `AndroidManifest.xml` is maintained here. The controls below are requirements for any future Android client, not implemented or release-ready configurations.

### 8.1 App Configuration (`AndroidManifest.xml`)
- **[MUST]** `android:allowBackup="false"` (or use `dataExtractionRules` / `fullBackupContent` to exclude sensitive data).
- **[MUST]** `android:debuggable="false"` in release builds.
- **[MUST]** Components (`Activity`, `Service`, `Receiver`, `Provider`) are `android:exported="false"` unless explicitly required; protect exported ones with permissions.
- **[MUST]** `android:usesCleartextTraffic="false"`; use a Network Security Config.
- **[MUST]** Request only the minimum permissions; request at runtime with clear rationale.
- **[SHOULD]** Use `FLAG_SECURE` on screens showing sensitive data (blocks screenshots/recents preview).

### 8.2 Network Security
- **[MUST]** Enforce HTTPS only via `network_security_config.xml`.
- **[SHOULD]** Certificate pinning (pin to public key / SPKI with backup pins and a rotation plan).
- **[MUST NOT]** Disable certificate/hostname validation, even in debug builds shipped to users.

No Android network-security configuration or certificate pins are present because there is no Android client in this repository. Do not copy sample pins into a release; establish a verified primary/backup pin and rotation plan if a client is introduced.

### 8.3 Data Storage
- **[MUST]** Use app-private internal storage; never store sensitive data on external storage.
- **[MUST]** Encrypt sensitive local data (Android Keystore, EncryptedSharedPreferences, SQLCipher for databases).
- **[MUST]** Clear sensitive data from memory/clipboard when no longer needed; do not log sensitive data (strip `Log.d/v` in release).
- **[SHOULD]** Disable keyboard caching for sensitive inputs (`textNoSuggestions`, `inputType=textPassword`).

### 8.4 Code Protection
- **[MUST]** Enable **R8/ProGuard** minification and obfuscation for release builds.
- **[MUST NOT]** Hard-code API secrets, private keys, or credentials in code, `strings.xml`, `BuildConfig`, or assets. Anything shipped in the APK can be extracted.
- **[SHOULD]** Root/jailbreak, emulator, hook (Frida), and tamper detection for high-risk apps.
- **[SHOULD]** Use **Play Integrity API** to verify app/device integrity and attest requests server-side.

### 8.5 Inter-App & Component Security
- **[MUST]** Validate all Intent extras, deep links, and App Links; verify with `assetlinks.json` (use verified App Links over custom schemes).
- **[MUST]** Use `PendingIntent.FLAG_IMMUTABLE` unless mutability is required.
- **[MUST]** Prevent WebView risks: disable JavaScript unless required, disable file access (`setAllowFileAccess(false)`), avoid `addJavascriptInterface` with untrusted content, restrict loaded URLs to an allow-list.
- **[SHOULD]** Use `FileProvider` for sharing files; never expose `file://` URIs.

### 8.6 Build, Signing & Distribution
- **[MUST]** Use **Play App Signing**; protect upload keys/keystores (never commit them to Git).
- **[MUST]** Distribute only via official channels (Google Play); enable Play Protect.
- **[MUST]** Target a recent `targetSdkVersion` and keep libraries updated.
- **[SHOULD]** Reproducible, CI-built releases signed in a protected pipeline.

### 8.7 Authentication on Device
- **[SHOULD]** Use `BiometricPrompt` + Keystore keys with `setUserAuthenticationRequired(true)` for sensitive operations.
- **[MUST]** Auto-lock / session timeout after inactivity for sensitive apps.

---

## 9. Data Protection & Privacy

### 9.1 Data Classification

| Level | Examples | Handling |
|---|---|---|
| **Public** | Marketing pages, public docs | No restrictions |
| **Internal** | Internal docs, non-sensitive configs | Authenticated team access |
| **Confidential** | User PII, emails, phone, addresses | Encrypted, role-restricted, audited |
| **Restricted** | Passwords, tokens, payment data, health/government IDs, keys | Strongest controls, minimal access, never logged |

### 9.2 Encryption
- **[MUST]** Encrypt data **in transit** (TLS) and **at rest** (AES-256 / provider-managed KMS).
- **[MUST]** Encrypt backups; test restores regularly.
- **[SHOULD]** Field-level encryption for highly sensitive fields.
- **[MUST]** Use vetted libraries; never roll your own crypto.

### 9.3 Privacy & Compliance
- **[MUST]** Collect only necessary data (data minimization) and define retention periods.
- **[MUST]** Publish a Privacy Policy and Terms; obtain valid consent where required.
- **[MUST]** Support user rights: access, correction, export, deletion (GDPR / CCPA / India DPDP Act, as applicable).
- **[MUST]** Mask sensitive data in logs, analytics, error reports, and non-production environments (use synthetic/anonymized data).
- **[MUST]** If handling payments, use a PCI-DSS compliant provider; never store raw card data or CVV.
- **[MUST]** Complete the Google Play **Data safety** form accurately.

---

## 10. Secrets Management

- **[MUST NOT]** Commit secrets (API keys, passwords, tokens, certificates, keystores, `.env`) to Git.
- **[MUST]** Store secrets in a secrets manager (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, HashiCorp Vault, or CI/CD encrypted secrets).
- **[MUST]** Use separate secrets per environment; rotate regularly and immediately on suspected exposure.
- **[MUST]** Enable secret scanning (e.g., GitHub secret scanning, `gitleaks`, `trufflehog`) in pre-commit and CI.
- **[SHOULD]** Prefer short-lived, scoped credentials (IAM roles, OIDC federation) over long-lived keys.
- **[MUST]** If a secret leaks: revoke → rotate → investigate → purge from Git history.

**`.gitignore` essentials:**
```gitignore
.env
.env.*
*.keystore
*.jks
keystore.properties
local.properties
google-services.json   # if it contains restricted keys; review per policy
*.pem
*.p12
secrets/
```

> Note: Client-side keys (e.g., Firebase/Maps) are not truly secret — restrict them by **package name + SHA-256 fingerprint** (Android), **HTTP referrer** (web), and API scope in the provider console.

---

## 11. Infrastructure & Environment Access

- **[MUST]** Separate **dev / staging / production** with different accounts/projects, credentials, and data.
- **[MUST]** No direct production database access from developer laptops; use bastion/VPN + audited, time-limited sessions.
- **[MUST]** Databases are not publicly accessible; restrict by private network/security groups/firewall.
- **[MUST]** Cloud IAM follows least privilege; no shared accounts; no use of root/owner accounts for daily work.
- **[MUST]** Enable cloud audit logging (CloudTrail / Cloud Audit Logs / Activity Log).
- **[SHOULD]** Infrastructure as Code with peer-reviewed changes; scan IaC for misconfigurations (tfsec, checkov).
- **[SHOULD]** Harden servers/containers: non-root users, minimal base images, read-only filesystems, patched images.
- **[MUST]** Automated, encrypted, tested backups with defined RPO/RTO.
- **[SHOULD]** DDoS protection / CDN (e.g., Cloudflare, CloudFront).

### Access Request Process
1. Requester submits access request (ticket) with justification, scope, and duration.
2. Resource owner / manager approves.
3. Access granted with least privilege and an expiry date.
4. Access is logged and reviewed quarterly.
5. Access revoked automatically at expiry or role change.

---

## 12. Source Code & CI/CD Security

### 12.1 Repository
- **[MUST]** MFA required for all repo members; SSO where available.
- **[MUST]** Protected `main`/`release` branches: no direct pushes, no force pushes, required PR reviews (≥ 1–2), required passing checks.
- **[MUST]** CODEOWNERS for security-sensitive paths (auth, payments, infra, CI).
- **[SHOULD]** Signed commits/tags.
- **[MUST]** Least-privilege repo permissions (Read / Write / Maintain / Admin).

### 12.2 CI/CD Pipeline
- **[MUST]** Pipeline secrets stored in the CI secrets store, masked in logs.
- **[MUST]** Separate build and deploy permissions; production deploy requires approval.
- **[MUST]** Pin third-party actions/plugins to commit SHAs or exact versions.
- **[MUST]** Run security checks on every PR: SAST, dependency scan, secret scan, lint, tests.
- **[SHOULD]** Ephemeral, isolated runners; no long-lived credentials (use OIDC).
- **[SHOULD]** Generate SBOMs and sign build artifacts.

### 12.3 Secure SDLC
- **[MUST]** Threat model new features touching auth, payments, or PII.
- **[MUST]** Security review in PR checklist (see [Appendix](#191-pull-request-security-checklist)).
- **[SHOULD]** Security training for developers annually.

---

## 13. Dependency & Supply Chain Security

- **[MUST]** Track dependencies (npm/yarn, Gradle/Maven, pip, etc.) and enable automated alerts (Dependabot / Renovate).
- **[MUST]** Run dependency vulnerability scans in CI (`npm audit`, OWASP Dependency-Check, Snyk, `osv-scanner`).
- **[MUST]** Commit lockfiles; use verified/trusted sources and checksums (Gradle dependency verification).
- **[SHOULD]** Remove unused dependencies; minimize third-party SDKs in the Android app (each adds permissions & data collection).
- **[SHOULD]** Vet new libraries: maintenance, popularity, license, known CVEs.
- **[MUST]** Patch SLA: Critical ≤ 7 days · High ≤ 14 days · Medium ≤ 30 days · Low ≤ 90 days.

---

## 14. Logging, Monitoring & Auditing

### 14.1 What to Log
- Authentication events (login success/failure, MFA, password resets, lockouts)
- Authorization failures and privilege changes
- Admin actions and data exports
- Access to sensitive records
- Configuration and infrastructure changes
- Input validation failures, rate-limit hits, suspicious patterns

### 14.2 Log Rules
- **[MUST]** Include timestamp (UTC), user/service ID, IP, action, resource, result, and request/correlation ID.
- **[MUST NOT]** Log passwords, tokens, full card numbers, secrets, or unnecessary PII.
- **[MUST]** Protect logs from tampering; centralize in a SIEM/log platform; restrict access.
- **[MUST]** Retain logs per policy (e.g., 90 days hot, 1 year archive) and legal requirements.

### 14.3 Monitoring & Alerting
- **[SHOULD]** Alerts for: brute force, impossible travel, new admin creation, mass data export, repeated 401/403, WAF blocks, unusual API spikes, crashes with security impact.
- **[SHOULD]** Uptime and certificate-expiry monitoring.
- **[SHOULD]** Android: use Crashlytics/Play Console vitals and Play Integrity verdict trends.

---

## 15. Incident Response

### 15.1 Severity Levels
| Level | Definition | Response Time |
|---|---|---|
| **SEV-1 Critical** | Active breach, data leak, full outage | Immediate (≤ 1 h) |
| **SEV-2 High** | Exploitable vulnerability, partial compromise | ≤ 4 h |
| **SEV-3 Medium** | Limited impact, no confirmed exploitation | ≤ 1 business day |
| **SEV-4 Low** | Minor/informational | ≤ 1 week |

### 15.2 Response Phases
1. **Detect & Report** — Report vulnerabilities through the [GitHub Security Advisories page](https://github.com/Silicon-Brains/SBUniversity/security/advisories/new). The project owner must designate and publish a private incident-response contact and channel before production launch.
2. **Triage** — Assess scope, severity, affected systems and data.
3. **Contain** — Revoke tokens/keys, disable accounts, isolate systems, block IPs, push kill-switch/force-update for Android if needed.
4. **Eradicate** — Remove root cause, patch vulnerabilities, rotate all exposed secrets.
5. **Recover** — Restore from clean backups, monitor closely.
6. **Notify** — Inform affected users, partners, and regulators within legal deadlines (e.g., GDPR: 72 hours; India CERT-In: 6 hours for specified incidents).
7. **Post-mortem** — Blameless review within 5 business days; track corrective actions to completion.

### 15.3 Contacts
| Role | Name | Contact |
|---|---|---|
| Incident Commander | To be designated by the project owner | Configure in the production incident runbook |
| Security Lead | To be designated by the project owner | Configure in the production incident runbook |
| Engineering Lead | To be designated by the project owner | Configure in the production incident runbook |
| Legal / DPO | To be designated by the project owner | Configure in the production incident runbook |
| Communications | To be designated by the project owner | Configure in the production incident runbook |

### 15.4 Vulnerability Disclosure
- Publish a `security.txt` at `/.well-known/security.txt` and a responsible-disclosure policy.
- Acknowledge reports within 72 hours; fix and credit reporters per policy.

---

## 16. Security Testing

| Activity | Frequency | Notes |
|---|---|---|
| SAST (static analysis) | Every PR | e.g., SonarQube, Semgrep, CodeQL, Android Lint |
| Dependency scanning | Every PR + daily | Dependabot, Snyk, OSV |
| Secret scanning | Every commit | gitleaks, trufflehog |
| DAST (web/API) | Weekly / pre-release | OWASP ZAP, Burp Suite |
| Mobile app analysis | Every release | MobSF, manual review |
| Penetration test | Annually + after major changes | Independent third party |
| Backup restore test | Quarterly | Verify RPO/RTO |
| Access review | Quarterly | All privileged and third-party access |
| Incident response drill | Twice a year | Tabletop exercise |

**Reference standards:** OWASP Top 10, OWASP API Security Top 10, OWASP ASVS, OWASP MASVS & MASTG (mobile), OWASP Cheat Sheets, CIS Benchmarks, NIST SP 800-63 (identity).

---

## 17. Onboarding & Offboarding

### 17.1 Onboarding Checklist
- [ ] Identity verified; NDA / confidentiality agreement signed
- [ ] Company SSO account created; MFA enrolled
- [ ] Role-based access granted (least privilege, ticket-tracked)
- [ ] Password manager provided
- [ ] Device secured (disk encryption, screen lock, updates, endpoint protection)
- [ ] Security policy read and acknowledged
- [ ] Security training completed

### 17.2 Offboarding Checklist (same day as departure)
- [ ] Disable SSO and all accounts
- [ ] Revoke repo, cloud, CI/CD, admin panel, and third-party tool access
- [ ] Revoke personal access tokens, SSH keys, API keys
- [ ] Rotate shared secrets the person knew
- [ ] Transfer ownership of resources/documents
- [ ] Recover devices; wipe if needed
- [ ] Review recent activity logs
- [ ] Remove from Play Console / Firebase / app stores / DNS / domain registrar

### 17.3 Third-Party / Contractors
- **[MUST]** Written agreement with security obligations.
- **[MUST]** Scoped, time-limited access with a named sponsor; revoke at contract end.
- **[SHOULD]** Assess vendor security (questionnaire, certifications such as SOC 2 / ISO 27001).

---

## 18. Compliance Checklists

### 18.1 Website Release Checklist
- [ ] HTTPS enforced, HSTS enabled, valid certificate
- [ ] Security headers configured (CSP, X-Content-Type-Options, frame protections, etc.)
- [ ] Cookies `HttpOnly`, `Secure`, `SameSite`
- [ ] CSRF protection active
- [ ] Input validation + output encoding verified
- [ ] Authorization checks on every endpoint (including IDOR tests)
- [ ] Rate limiting on login, signup, reset, and APIs
- [ ] No secrets, source maps, or debug endpoints in production
- [ ] Error pages are generic; stack traces disabled
- [ ] Dependencies scanned and up to date
- [ ] Admin panel protected (MFA, restricted access)
- [ ] Logging and alerting working
- [ ] Backups configured and tested
- [ ] Privacy policy & cookie consent in place

### 18.2 Android Release Checklist
- [ ] `debuggable=false`, `allowBackup=false`, cleartext traffic disabled
- [ ] Only necessary permissions; exported components reviewed
- [ ] R8/ProGuard enabled; logs stripped from release
- [ ] No hard-coded secrets or private keys in APK/AAB
- [ ] Tokens stored via Keystore/EncryptedSharedPreferences
- [ ] TLS enforced; certificate pinning configured (with backup pins)
- [ ] Deep links verified; Intents/WebViews hardened
- [ ] Play Integrity checks integrated where needed
- [ ] `FLAG_SECURE` on sensitive screens
- [ ] Signed with Play App Signing; keystore secured
- [ ] Third-party SDKs reviewed; Data safety form accurate
- [ ] MobSF / static scan results reviewed
- [ ] `targetSdkVersion` meets current Play requirements

### 18.3 Backend / API Release Checklist
- [ ] Authentication & authorization tested for all roles
- [ ] BOLA/IDOR, mass assignment, SSRF, injection tests passed
- [ ] Secrets sourced from secret manager
- [ ] DB not public; least-privilege DB accounts
- [ ] Rate limiting, timeouts, and request size limits configured
- [ ] CORS locked to approved origins
- [ ] Audit logging for sensitive actions
- [ ] Monitoring, alerting, and on-call set up

---

## 19. Appendix

### 19.1 Pull Request Security Checklist
- [ ] No secrets or credentials added
- [ ] Authentication/authorization enforced server-side for new endpoints
- [ ] Inputs validated; outputs encoded; queries parameterized
- [ ] Sensitive data not logged or exposed in responses
- [ ] New dependencies reviewed and scanned
- [ ] Error handling does not leak internals
- [ ] Tests cover security-relevant behavior (negative cases)

### 19.2 Quick Reference — Common Threats & Controls

| Threat | Primary Control |
|---|---|
| Broken access control / IDOR | Server-side ownership & role checks on every request |
| Credential stuffing / brute force | Rate limiting, MFA, breached-password check, CAPTCHA |
| XSS | Output encoding, strict CSP, avoid `innerHTML` |
| CSRF | SameSite cookies + anti-CSRF tokens |
| SQL/NoSQL injection | Parameterized queries, validation |
| SSRF | Outbound allow-list, block internal ranges |
| Session hijacking | Secure cookies, short TTL, rotation, TLS |
| Reverse engineering (Android) | R8, no secrets in app, server-side logic, Play Integrity |
| Insecure local storage (Android) | Keystore, EncryptedSharedPreferences, no external storage |
| MITM | TLS, HSTS, certificate pinning |
| Leaked secrets | Secrets manager, scanning, rotation |
| Supply-chain attacks | Pinned versions, lockfiles, scanning, SBOM |
| Insider threat / over-privilege | Least privilege, audit logs, access reviews |

### 19.3 Policy Governance
- This document is reviewed at least **every 6 months** and after any major incident or architecture change.
- Exceptions require written approval from the Security Lead, a documented risk assessment, and an expiry date.
- Violations may result in access revocation and disciplinary action.

### 19.4 Change Log

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-10-23 | SiliconBrains University Engineering | Repository-tailored policy and implementation scope |

---

### 19.5 Repository implementation status

**Implemented in this repository**

- Clerk JWT signature verification pins RS256 and requires `exp`, `iat`, and `sub`; production requires configured issuer and audience validation.
- Development token bypass is refused in production; bearer tokens are accepted only in the Authorization header.
- Role-based API checks and resource ownership checks are enforced by the backend; authentication/authorization denials are logged.
- Existing account roles are database-authoritative; role updates require Clerk synchronization and failed provider updates do not change the local role.
- Production startup rejects debug/bypass mode, missing Clerk/webhook/storage settings, non-HTTPS or wildcard CORS origins, and disabled rate limiting.
- API errors are generic in production; request IDs and baseline security headers are attached; only the versioned API is mounted.
- Rate limiting is atomic in Redis and fails closed in production when the limiter is unavailable.
- Audio and profile-image uploads enforce size limits and content signatures; local storage is development-only and path-confined.
- The web applies a nonce-based CSP and standard browser security headers; `security.txt` publishes the disclosure channel.
- Dependabot is configured for weekly updates; pinned-action CI runs CodeQL, npm/Python dependency audits, and Gitleaks on pull requests and daily.
- The production frontend dependency audit passes. The full npm audit still reports five high-severity findings through `braces` in Next.js ESLint development tooling; no fixed `braces` release is available yet. Keep the CI alert active and update the lint toolchain when upstream publishes a fix.

**Deployment or organizational actions still required**

- Configure Clerk MFA/passkeys, account recovery policy, verified email requirements, and the production JWT issuer/audience values.
- Configure real HTTPS/TLS termination, HSTS at the edge, private database/network access, separate environments and credentials, encrypted backups, restore tests, monitoring, alerting, and log retention.
- Configure GitHub MFA, branch protection, required reviews/checks, CODEOWNERS, GitHub security-alert settings, required CI checks, SBOMs, and protected deployment approvals; add Python dependency lock/verification and scheduled DAST.
- Assign incident-response and privacy/legal contacts; approve a data-retention schedule, privacy/terms notices, consent and data-subject request procedures, and vendor access reviews.
- Configure malware scanning for uploads and verify that the Supabase bucket is private and access-controlled.
- Perform periodic independent penetration tests, access reviews, and incident-response exercises.
- Android release and Play Store controls are not applicable because this repository contains no Android application.

These deployment actions are requirements, not claims that the external services are already configured. Review the policy every six months and whenever the architecture or applicable law changes.
