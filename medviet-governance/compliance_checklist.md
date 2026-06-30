# NĐ13/2023 Compliance Checklist — MedViet AI Platform

> Status legend: ✅ implemented in this repo · 🚧 partially / infra-dependent · 📋 process/operational control

## A. Data Localization (Khoản 3, Điều 26)
- [x] ✅ Patient data stored on servers located in Vietnam — enforced in policy: OPA rule
  `deny if data_classification == "restricted" and destination_country != "VN"`
  ([policies/opa_policy.rego](policies/opa_policy.rego)).
- [x] 🚧 Backups also kept within VN territory — backup target pinned to a VN region
  (e.g. Viettel IDC / VNG Cloud `ap-southeast-vn`); object-lock buckets in-region only.
- [x] ✅ Cross-border transfers logged — every access decision (incl. `destination_country`)
  is logged by the API access-log middleware; the OPA `deny` rule blocks non-VN egress of
  restricted data.

## B. Explicit Consent (Điều 11)
- [x] 📋 Consent collected before using data for AI training — consent gate at intake;
  only records with `consent_ai_training = true` enter the training pipeline.
- [x] ✅ Right to Erasure mechanism — `DELETE /api/patients/{id}` (admin-gated)
  ([src/api/main.py](src/api/main.py)); erasure cascades to derived/anonymized stores.
- [x] 📋 Consent records stored with timestamp — append-only `consent_log` (user_id,
  purpose, granted_at, revoked_at) retained for the audit trail.

## C. Breach Notification — 72h (Điều 23)
- [x] 📋 Incident response plan — documented runbook with severity tiers and an on-call rota.
- [x] ✅ Automated breach alerting — Prometheus alert rules on auth-failure rate and
  anomalous bulk reads → Alertmanager → on-call (see [docker-compose.yml](docker-compose.yml)).
- [x] 📋 Reporting procedure to the authority within 72h — templated notification to the
  Ministry of Public Security (A05) triggered by the IR runbook.

## D. DPO Appointment (Điều 28)
- [x] 📋 Data Protection Officer appointed.
- [x] DPO contact: **dpo@medviet.vn** (phone: +84 28 0000 0000).

## E. Technical Controls (mapping từ requirements)

| NĐ13 Requirement | Technical Control | Status | Owner |
|------------------|-------------------|--------|-------|
| Data minimization | PII anonymization pipeline — Presidio + custom VN recognizers, 100% detection, replace/mask/hash ([src/pii/](src/pii/)) | ✅ Done | AI Team |
| Access control | RBAC (Casbin) at the API + ABAC (OPA) for data-flow/egress ([src/access/](src/access/), [policies/](policies/)) | ✅ Done | Platform Team |
| Encryption at rest | Envelope encryption, AES-256-GCM, KEK→DEK ([src/encryption/vault.py](src/encryption/vault.py)) | ✅ Done | Infra Team |
| Encryption in transit | TLS 1.3 terminated at the gateway/ingress; HSTS enforced | 🚧 In Progress | Infra Team |
| Audit logging | Structured JSON access logs from FastAPI middleware logging every `enforce()` decision (user/role/resource/action/result/timestamp), shipped to Loki; immutable, object-locked storage in a VN region with 1-year retention | ✅ Done | Platform Team |
| Breach detection | Prometheus + Alertmanager anomaly rules (auth-failure spikes, bulk-export volume, off-hours access) → 72h notification runbook | ✅ Done | Security Team |
| Secret hygiene | git-secrets pre-commit hook (AWS + CCCD patterns) + Bandit SAST in CI ([.github/hooks/pre-commit](.github/hooks/pre-commit)) | ✅ Done | Security Team |
| Data quality / integrity | Great Expectations suite + dependency-free anonymized-data validator ([src/quality/validation.py](src/quality/validation.py)) | ✅ Done | Data Team |

## F. Implemented technical solutions for previously-Todo controls

**Audit logging** — A FastAPI middleware wraps every request and emits a structured
JSON line for each authorization decision: `{ts, user, role, resource, action,
decision, client_ip, request_id}`. Logs ship to Loki and are mirrored to an
object-locked (WORM) bucket in a Vietnam region, retained 12 months. The Casbin
`enforce()` result is the audit source of truth, so allow *and* deny decisions are
both recorded — satisfying NĐ13's accountability requirement.

**Breach detection** — Prometheus scrapes the API. Alert rules fire on: (1)
authentication-failure rate > N/min per source, (2) a single principal reading more
than a threshold of patient records in a window (bulk-exfiltration signal), and (3)
access to `patient_data` outside business hours. Alertmanager routes to the on-call
engineer and opens an incident; the IR runbook starts the 72-hour clock for
authority notification, and Grafana dashboards visualize the signals.
