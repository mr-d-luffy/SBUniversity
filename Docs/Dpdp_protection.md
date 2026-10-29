# DPDP_Protection.md

> **Digital Personal Data Protection (DPDP) Compliance & Security Standard**
> Reusable baseline for any website, web app, mobile app, or API serving users in India.

| Field | Value |
|---|---|
| Project name | `<PROJECT_NAME>` |
| Data Fiduciary (legal entity) | `<COMPANY_LEGAL_NAME>` |
| Document owner | `<NAME / ROLE>` |
| Data Protection Officer / Grievance Officer | `<NAME, EMAIL, PHONE>` |
| Version | 1.0 |
| Last reviewed | `<YYYY-MM-DD>` |
| Next review | Every 6 months, or on any major feature / vendor change |

> **Disclaimer:** This is an engineering and compliance checklist, not legal advice. Have a qualified Indian data-protection lawyer review the final policies, notices, and contracts before launch.

---

## 1. Legal Framework (India)

| Law / Rule | Relevance |
|---|---|
| **Digital Personal Data Protection Act, 2023 (DPDP Act)** | Core law for digital personal data |
| **DPDP Rules, 2025** (notified 14 Nov 2025) | Operational rules: notice, consent, security, breach, children, retention |
| **IT Act, 2000** (s. 43A, 72A, 66 etc.) and **SPDI Rules, 2011** | Remain in force during the transition period |
| **CERT-In Directions, 2022** | Report cyber incidents within **6 hours**; keep ICT logs for **180 days** (in India) |
| Sector rules (RBI, SEBI, IRDAI, ABDM/health, etc.) | Apply on top, if your product is in those sectors |

### 1.1 Commencement timeline (verify before relying; dates may be updated by MeitY)

| Date | What applies |
|---|---|
| 13 Nov 2025 | Data Protection Board provisions and procedural framework in force |
| 13 Nov 2026 | Consent Manager registration and related obligations |
| **13 May 2027** | Notice, consent, security safeguards, breach reporting, retention, children's data, SDF obligations, cross-border rules |

**Engineering rule:** build to the final (May 2027) standard now. Retrofitting consent and logging later costs far more.

### 1.2 Key terms

- **Data Principal**: the individual the data is about (your user). For a child or a person with disability, includes the parent / lawful guardian.
- **Data Fiduciary**: whoever decides the purpose and means of processing (you).
- **Data Processor**: anyone processing on your behalf (cloud, SMS, analytics, payment, CRM vendors).
- **Significant Data Fiduciary (SDF)**: notified by the government based on volume, sensitivity, risk. Has extra duties (Section 10).
- **Consent Manager**: registered entity that lets users manage consent across fiduciaries.

---

## 2. Scope: Do You Need This?

You are covered if you process **digital personal data** of individuals **in India**, or process outside India in connection with offering goods or services to people in India.

Personal data includes: name, phone, email, address, IP address, device ID, advertising ID, geolocation, photos/voice, login identifiers, order/payment history, behavioural analytics tied to a person.

**Exemptions are narrow** (personal/domestic use, certain state functions, some research/archival uses). Assume you are covered.

---

## 3. Core Principles (Engineering Translation)

| Principle | What to build |
|---|---|
| **Lawful & transparent** | Valid consent or a listed "legitimate use"; plain-language notice |
| **Purpose limitation** | Each data field mapped to one stated purpose |
| **Data minimisation** | Collect only what the feature needs; no "just in case" fields |
| **Accuracy** | Users can correct their data; validation on input |
| **Storage limitation** | Retention schedule + automated deletion jobs |
| **Security safeguards** | Encryption, access control, logging, backups (Section 8) |
| **Accountability** | Records, audits, vendor contracts, named owners |

---

## 4. Data Inventory & Mapping (Do This First)

Maintain a living register (spreadsheet or table in repo `/docs/data-map`).

| Data field | Source (form/SDK/API) | Purpose | Lawful basis (consent / legitimate use) | Storage location & region | Processor(s) with access | Retention | Deletion method |
|---|---|---|---|---|---|---|---|
| Email | Signup form | Account login, receipts | Consent | `<DB, region>` | `<Email vendor>` | Account life + 90 days | Hard delete + backups expiry |
| Phone | Signup / OTP | Authentication | Consent | | `<SMS vendor>` | | |
| Device ID / IP | App SDK / server logs | Fraud prevention, security | Legitimate use / consent | | | 12 months min log retention | |
| `<add rows>` | | | | | | | |

**Rules**
- No field goes to production without a row in this table.
- Update the table in the same PR that adds or changes a data field.
- Flag anything sensitive: financial, health, biometrics, precise location, children's data, government IDs (Aadhaar, PAN).

---

## 5. Consent Management

### 5.1 Requirements for valid consent

Consent must be **free, specific, informed, unconditional, unambiguous**, given by a **clear affirmative action**, and limited to the stated purpose.

### 5.2 Implementation checklist

- [ ] Standalone **consent notice** shown *before or at* collection, never buried in Terms & Conditions
- [ ] Notice states: (a) what personal data, (b) why (itemised purposes), (c) how to withdraw consent, (d) how to exercise rights, (e) how to complain to the Data Protection Board
- [ ] Notice available in **English and any of the 22 Eighth Schedule languages** (offer the user's choice)
- [ ] **No pre-ticked boxes**; no bundled consent (marketing consent separate from service consent)
- [ ] Service not denied for refusing consent to data **not necessary** for that service
- [ ] **Withdrawal is as easy as giving** consent (one-tap in settings)
- [ ] On withdrawal: stop processing and delete data (and instruct processors to delete) unless law requires retention
- [ ] **Consent record stored**: user ID, timestamp, notice version, purposes consented, channel, withdrawal timestamp
- [ ] Re-consent when purposes change materially
- [ ] Permissions (camera, contacts, location, notifications) requested **just-in-time** with context, not all at app launch

### 5.3 Suggested consent log schema

```sql
CREATE TABLE consent_log (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL,
  purpose_code    VARCHAR(64) NOT NULL,   -- e.g. 'ACCOUNT', 'MARKETING_EMAIL'
  notice_version  VARCHAR(16) NOT NULL,
  status          VARCHAR(16) NOT NULL,   -- 'GRANTED' | 'WITHDRAWN'
  language        VARCHAR(8),
  channel         VARCHAR(16),            -- 'WEB' | 'ANDROID' | 'IOS' | 'API'
  ip_hash         VARCHAR(64),
  user_agent_hash VARCHAR(64),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Append-only. Never update or delete rows; add a new row on change.
```

### 5.4 Legitimate uses (consent not required, still need notice where applicable)

Examples: voluntarily provided data for a specified purpose where the user did not object; compliance with law or court orders; medical emergencies; employment-related purposes; disaster response. Document the basis for each use. **Do not stretch these to cover marketing or analytics.**

---

## 6. Children's Data (Under 18)

- [ ] Age gate at signup (self-declaration at minimum; stronger verification for higher-risk services)
- [ ] **Verifiable parental/guardian consent** before processing a child's data
- [ ] **No tracking, behavioural monitoring, or targeted advertising** directed at children
- [ ] No processing likely to cause detrimental effect on a child's well-being
- [ ] Parent verification method documented (e.g. DigiLocker / government-ID-linked token, or other approved method per Rules)
- [ ] Separate, simple-language notice for minors/parents

---

## 7. Data Principal Rights (Build These as Features)

| Right | Product requirement | Suggested SLA |
|---|---|---|
| **Access / summary** | "Download my data" and "What data do you hold, and who did you share with" | Within 30 days (target: instant self-serve) |
| **Correction & completion** | Editable profile; request form for fields users can't edit | Within 30 days |
| **Erasure** | "Delete my account" with real deletion (Section 10) | Within 30 days; backups expire per schedule |
| **Withdraw consent** | Settings toggle per purpose | Immediate |
| **Grievance redressal** | Visible contact + ticketing | Acknowledge in 48 hrs; resolve within **90 days max** (target: 7-15) |
| **Nominate** another person to exercise rights on death/incapacity | Nominee field in account settings | |

**Rules**
- Verify identity before disclosing or deleting (OTP to registered contact).
- Log every request and outcome (who, when, what, status).
- Users must be told they can escalate to the **Data Protection Board of India** if the grievance is unresolved.

---

## 8. Security Safeguards (Technical Baseline)

The Rules require "reasonable security safeguards." Treat the list below as the **minimum**. Failure here carries the highest penalty tier.

### 8.1 Encryption

- [ ] **In transit:** TLS 1.2+ everywhere (prefer 1.3); HSTS enabled; no mixed content; certificate pinning in mobile apps for sensitive APIs
- [ ] **At rest:** AES-256 for databases, object storage, backups, device storage; managed KMS for keys
- [ ] **Field-level encryption** or tokenisation for highly sensitive fields (ID numbers, financial data, health data)
- [ ] Keys rotated on schedule; never stored in code or repo; separate keys per environment
- [ ] Passwords hashed with **Argon2id** (or bcrypt cost ≥ 12); never reversible encryption; never logged

### 8.2 Access control

- [ ] **Least privilege** and role-based access (RBAC) for staff, services, and DB users
- [ ] **MFA mandatory** for admin panels, cloud consoles, source control, CI/CD, and production databases
- [ ] No shared accounts; individual named access only
- [ ] Quarterly access reviews; same-day revocation on offboarding
- [ ] Production data **never** copied to dev/staging unless masked or anonymised
- [ ] Session management: short-lived tokens, refresh rotation, secure cookies (`HttpOnly`, `Secure`, `SameSite`)

### 8.3 Application security

- [ ] Follow **OWASP Top 10** (web/API) and **OWASP MASVS** (mobile)
- [ ] Input validation, parameterised queries / ORM; output encoding; CSRF protection
- [ ] Rate limiting and bot protection on login, OTP, signup, password reset
- [ ] Security headers: `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options` / `frame-ancestors`, `Referrer-Policy`, `Permissions-Policy`
- [ ] Secrets scanning in CI; dependency scanning (SCA) and automated patching
- [ ] SAST + DAST in the pipeline; **third-party penetration test before launch and at least annually**
- [ ] Do not put personal data in URLs, query strings, push-notification bodies, or client-side logs
- [ ] Mobile: disable screenshots on sensitive screens, use Keychain / Android Keystore, root/jailbreak detection for high-risk apps, obfuscate release builds
- [ ] API: authenticate and authorise **every** request; object-level authorisation checks (prevent IDOR)

### 8.4 Logging & monitoring

- [ ] Log access to personal data (who, what, when, from where) without storing the data itself in logs
- [ ] **Retain logs for at least 1 year** (DPDP Rules) and **180 days within India** for CERT-In purposes. Use the longer period
- [ ] Centralised, tamper-evident log storage; sync clocks to NTP (NIC/NPL sources per CERT-In)
- [ ] Alerts for: mass data export, failed-login spikes, privilege changes, access from unusual geographies, DB dump activity

### 8.5 Backups & resilience

- [ ] Encrypted, access-controlled backups; tested restores (at least quarterly)
- [ ] Defined RPO / RTO; disaster recovery runbook
- [ ] Backup retention aligned to retention schedule, so deleted data ages out of backups on a defined timeline

### 8.6 Infrastructure

- [ ] Network segmentation; private subnets for databases; no public DB endpoints
- [ ] WAF and DDoS protection on public endpoints
- [ ] Infrastructure as code; hardened images; CIS benchmarks
- [ ] Cloud storage buckets private by default; automated misconfiguration scanning

---

## 9. Personal Data Breach Response

**All** personal data breaches must be reported. There is no "low risk" exemption.

### 9.1 Obligations

| Who | Deadline |
|---|---|
| **Affected users** | Without delay, in plain language: what happened, likely impact, steps taken, what they should do, contact person |
| **Data Protection Board** | Intimation **without delay**, then a **detailed report within 72 hours** (nature, extent, timing, cause, mitigation, findings about the person responsible, notices sent) |
| **CERT-In** | Within **6 hours** of noticing a reportable cyber incident (`incident@cert-in.org.in`) |
| **Sector regulator** (RBI/SEBI/IRDAI etc.) | Per sector rules |

### 9.2 Incident response runbook

1. **Detect & triage:** open incident ticket, assign incident commander, start timeline log
2. **Contain:** isolate systems, revoke credentials/tokens, block attacker access
3. **Preserve evidence:** snapshots and logs (don't wipe)
4. **Assess:** which data, how many users, what cause, ongoing or stopped
5. **Notify:** CERT-In (6h) → DPB → affected users → regulators, using pre-approved templates
6. **Eradicate & recover:** patch root cause, rotate all secrets, restore from clean backups
7. **Post-incident review** within 7 days: root cause, fixes, owners, deadlines
8. **Update** risk register, tests, and this document

- [ ] Run a **tabletop breach drill at least twice a year**
- [ ] Keep an up-to-date contact tree (legal, CTO, DPO, PR, vendors, CERT-In)
- [ ] Contractually require processors to notify you **within 24 hours** of any suspected breach

---

## 10. Retention & Deletion

### 10.1 Rule

Erase personal data when (a) the user withdraws consent, or (b) the purpose is no longer served, **unless** a law requires retention. Tell the user **at least 48 hours before** erasure triggered by inactivity (where applicable).

### 10.2 Inactivity rule (large platforms)

For **e-commerce, online gaming, and social media** services above the prescribed user thresholds, personal data must be erased after **3 years of user inactivity** (with prior notice). Build this in even if you're below the threshold; it's good hygiene.

### 10.3 Retention schedule template

| Data category | Retention | Legal basis for keeping | Disposal |
|---|---|---|---|
| Account profile | Account life + 30 days | Service | Hard delete |
| Transaction / invoice records | 8 years | Companies Act / GST / Income Tax | Archive, restricted access, then delete |
| Security & access logs | 1 year minimum (180 days in India for CERT-In) | DPDP Rules / CERT-In | Auto-expire |
| Support tickets | 2 years | Dispute handling | Anonymise |
| Marketing profile | Until consent withdrawn | Consent | Hard delete |
| Analytics events | 13 months, pseudonymised | Consent | Auto-expire |

### 10.4 Deletion engineering checklist

- [ ] Single "delete user" workflow that cascades across DBs, caches, search indexes, object storage, analytics, and **third-party processors**
- [ ] Scheduled jobs for retention expiry with audit logs
- [ ] Soft-delete only as a short grace window (≤ 30 days), then hard-delete
- [ ] Anonymisation is irreversible (no re-identification keys kept)
- [ ] Deletion proof recorded (without the deleted data)

---

## 11. Third Parties, Processors & Cross-Border Transfers

### 11.1 Processor management

- [ ] Maintain a **vendor register**: name, service, data shared, location, security certifications (ISO 27001 / SOC 2), contract date
- [ ] Sign a **Data Processing Agreement (DPA)** with every processor covering: processing only on your instructions, security safeguards, sub-processor approval, breach notice (24h), deletion/return on exit, audit rights, assistance with user rights requests
- [ ] **You stay liable** for your processors' failures. Vet before onboarding and review yearly
- [ ] Share the minimum data necessary; prefer pseudonymised IDs

### 11.2 Cross-border transfers

DPDP uses a "permitted unless restricted" model: transfers are allowed except to countries the Government notifies as restricted.

- [ ] Track the **current restricted-country list** and any sectoral localisation rules (e.g. RBI payments data must be stored in India; some government/health contexts require localisation)
- [ ] Prefer **India-region hosting** for primary personal data stores
- [ ] Disclose transfers in your privacy notice
- [ ] Apply the same safeguards contractually to overseas processors

### 11.3 SDKs, analytics & ad tech (mobile and web)

- [ ] Audit every SDK and tag for what personal data it collects and where it sends it
- [ ] Load analytics / advertising / session-replay tools **only after consent**
- [ ] Disable or restrict advertising ID collection unless consented
- [ ] Mask personal data in session-replay and error tracking tools
- [ ] Cookie banner with granular, equally prominent **Accept / Reject** options; strictly necessary cookies only by default

---

## 12. Significant Data Fiduciary (SDF) Extra Duties

Applies only if the Government notifies you. Prepare early if you handle large volumes or sensitive data.

- [ ] Appoint a **Data Protection Officer** based in India, reporting to the board / senior management
- [ ] Appoint an **independent data auditor**
- [ ] Conduct annual **Data Protection Impact Assessments (DPIA)** and **audits**; submit reports to the Board
- [ ] Verify that algorithmic software you deploy is not likely to pose risk to user rights
- [ ] Observe any localisation restrictions the Government specifies for certain data

---

## 13. Required Public-Facing Documents

Keep these in `/legal/` in the repo and version them.

### 13.1 Privacy Notice (website footer + app store listing + in-app)
Must include: data collected, purposes, legal basis, retention, sharing / processors, cross-border transfer, user rights, how to withdraw consent, grievance officer contact, DPB complaint route, notice version & date.

### 13.2 Other documents
- [ ] Terms of Service
- [ ] Cookie Policy and consent banner
- [ ] Children's / Parental Consent Notice (if applicable)
- [ ] Grievance Redressal page (officer name, email, response timelines)
- [ ] Internal: Data Retention Policy, Incident Response Plan, Access Control Policy, Vendor Management Policy, Employee Data-Handling Policy

### 13.3 Store requirements
- [ ] **Google Play Data Safety** form and **Apple App Privacy** labels match actual behaviour (inconsistencies cause rejection and legal exposure)
- [ ] Privacy policy URL live and working in both stores
- [ ] In-app account deletion path available (required by both stores)

---

## 14. Governance & Accountability

| Item | Owner | Frequency |
|---|---|---|
| Data map update | Engineering lead | Every feature release |
| Access review | Security / IT | Quarterly |
| Vendor review | DPO / Legal | Annually |
| Penetration test | Security | Annually + major changes |
| Breach drill | Incident commander | Twice yearly |
| Staff privacy training | HR / DPO | At onboarding + annually |
| Policy review | Legal / DPO | Every 6 months |
| Backup restore test | DevOps | Quarterly |

- [ ] Privacy by Design: a **Privacy Review** step in every feature spec / PR template
- [ ] Risk register for privacy and security risks, with owners and due dates
- [ ] Staff confidentiality agreements; security awareness training and phishing simulations

---

## 15. Penalties (Maximum, per DPDP Act Schedule)

| Breach | Max penalty |
|---|---|
| Failure to implement reasonable security safeguards | **₹250 crore** |
| Failure to notify the Board / users of a breach | **₹200 crore** |
| Breach of children's-data obligations | **₹200 crore** |
| Breach of SDF additional obligations | **₹150 crore** |
| Breach of Data Principal duties | ₹10,000 |
| Breach of a voluntary undertaking accepted by the Board | Up to the penalty for the underlying breach |
| Any other breach of the Act or Rules | **₹50 crore** |

Penalties are set by the Data Protection Board considering the nature, gravity, duration, repeat history, mitigation, and your cooperation.

---

## 16. Pre-Launch Compliance Checklist

### Legal
- [ ] Data map complete; lawful basis defined for each purpose
- [ ] Privacy notice, ToS, cookie policy published
- [ ] Grievance officer appointed and published
- [ ] DPAs signed with all processors

### Product
- [ ] Consent UI (granular, no pre-ticks, easy withdrawal) + consent log
- [ ] Rights features: access, correction, deletion, withdrawal, nominee
- [ ] Age gate and parental consent flow (if minors possible)
- [ ] Cookie / SDK consent gating

### Security
- [ ] TLS, encryption at rest, KMS, secrets management
- [ ] RBAC + MFA + least privilege
- [ ] Logging with ≥ 1-year retention; monitoring and alerts
- [ ] Penetration test passed; critical/high findings fixed
- [ ] Backup and restore tested

### Operations
- [ ] Incident response plan + CERT-In / DPB contact templates
- [ ] Retention schedule automated
- [ ] Staff trained
- [ ] Store listings (Play Data Safety / Apple Privacy labels) accurate

---

## 17. Developer Quick Rules (Pin in Your README)

1. **No personal data without a purpose, a consent record, and a retention date.**
2. Never log passwords, OTPs, tokens, full ID numbers, or full card numbers.
3. Never use production personal data in dev or test.
4. Never hardcode secrets; never commit `.env` files.
5. Every new third-party SDK or API needs a privacy review first.
6. Every endpoint returning personal data needs authentication **and** authorisation checks.
7. Every new data field means a data-map update in the same PR.
8. If you suspect a breach, **report it immediately**. Never wait to be sure.

---

## 18. PR Template Snippet (Privacy Review)

```markdown
## Privacy & Security Review
- [ ] Adds / changes personal data fields?  If yes, data map updated
- [ ] Purpose + lawful basis + retention defined
- [ ] Consent flow / notice updated if purpose changed
- [ ] New third-party SDK / API?  If yes, vendor review + DPA done
- [ ] Data encrypted in transit and at rest
- [ ] Access control and authorization tested
- [ ] No personal data in logs / URLs / analytics payloads
- [ ] Deletion and export paths cover the new data
```

---

## 19. Change Log

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | `<YYYY-MM-DD>` | `<Name>` | Initial version |

---

## 20. Official References

- Digital Personal Data Protection Act, 2023 and DPDP Rules, 2025: MeitY (`meity.gov.in`)
- CERT-In Directions, 28 April 2022 (`cert-in.org.in`)
- IT Act, 2000 and SPDI Rules, 2011 (`meity.gov.in`)
- OWASP Top 10 and OWASP MASVS (`owasp.org`)

> **Review the legal commencement dates and any new MeitY notifications or Board guidance before each release. Rules and thresholds can change.**