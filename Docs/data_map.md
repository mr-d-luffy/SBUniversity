# SiliconBrains University data map

Last reviewed: 1 November 2026. This is an engineering inventory derived from the current repository. Confirm hosting regions, processor contracts, backup lifetimes, and operational retention with the deployment owner before relying on those details in a public notice.

| Data | Source | Purpose | Current storage / processors | Retention and deletion |
|---|---|---|---|---|
| Name, email, avatar, Clerk user ID, role and status | Clerk authentication webhook | Account access, identity, role-based features | Application database; Clerk is the identity provider | Account lifetime; account deletion removes the database user and requests Clerk deletion. Confirm backups and provider expiry. |
| Student code, department, batch, academic term, verification state, phone, optional date of birth, QR token and photo path | Admin profile tools, student profile and Clerk webhook | Student identity card, academic administration and credential verification | Application database; Supabase Storage when configured | Account lifetime / institutional record needs. No automated expiry schedule is present. |
| Employee code, department, verification state, designation and bio | Admin profile tools | Teacher identity and course administration | Application database | Account lifetime / institutional record needs. No automated expiry schedule is present. |
| Enrolments, courses, exam attempts and answers, results, tasks, submissions, certificates and rankings | Platform use and institutional administration | Deliver learning and assessment features and preserve academic outcomes | Application database; Redis for ranking/cache state | While needed for academic service. Student account deletion cascades some related records; verify all external/cache copies and legal retention exceptions. |
| Planner entries, assistant sessions/messages, community messages, whiteboard sessions/messages/strokes, activity summaries | User-generated platform activity | Provide the feature requested by the user | Application database; configured AI provider receives assistant prompts/context. Community text and audio are encrypted in the browser before storage; the database also holds public device keys, encrypted key envelopes, and chat metadata. | Community conversation/message rows and associated key-envelope rows are deleted after 10 hours without a new message; cleanup runs about once a minute and is also triggered by chat requests. Browser device and conversation keys have no application TTL. Uploaded encrypted audio objects are stored separately and are not removed by the conversation-row cleanup; external/local object retention is not established here. Other feature data has no common retention schedule. |
| Request path, method, response status, duration, IP address, user agent and actor ID | API security middleware | Security monitoring and troubleshooting | Application database (`security_request_events`); high-frequency Community Chat and whiteboard polling GETs, health checks, and admin security-feed GETs are excluded to avoid write/latency overhead and telemetry noise | The API runs a daily cleanup for rows older than 30 days while the service is running. This does not establish retention of hosting/provider logs or backups; confirm those separately. |
| Administrative audit actions and actor/entity references | Administrative actions | Accountability and investigation | Application database (`audit_logs`) | No automatic expiry job is present. Minimize identifiers and define a retention period. |
| Uploaded images, voice messages, course files and generated PDFs | User or staff uploads / application generation | Profile, chat, course, result and certificate features | Local storage in development; Supabase Storage when configured | Some feature-specific deletion exists. Account deletion does not yet guarantee removal of every stored object. |

## Processor and deployment notes

- Authentication: Clerk (`web` Clerk integration and `server/app/api/v1/auth_webhooks.py`).
- Object storage: Supabase Storage when `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are configured; otherwise local `server/storage_local` storage.
- Database and hosting: deployment-configured; region is not defined in this repository.
- Cache/ranking: Redis (`REDIS_URL`); ranking and cached account-derived values need review on deletion.
- AI: the backend assistant uses its configured AI provider (`GEMINI_API_KEY`); confirm provider, region, request logging and retention from the production configuration.
- No analytics, advertising or session-replay SDK was found in the web application during this review. Recheck when dependencies or tags change.

## Follow-up required

1. Deployment owner to complete provider names, data regions, DPAs, backup expiry and contact owner.
2. Approve retention periods for security request events, audit logs, and feature data; confirm provider/backup retention.
3. Extend deletion/expiry workflows to remove uploaded objects (including encrypted Community Chat audio) and user-derived cache entries, and record a privacy-minimal deletion receipt.
4. Decide and implement the age/guardian workflow before enabling unsupervised child self-registration.
5. Reconcile the public notice with actual processor configuration and the institution's academic-record retention requirements.
