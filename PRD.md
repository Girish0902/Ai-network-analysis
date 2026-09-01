# AI-Assisted Criminal Investigation & Intelligence Platform — Product Requirements Document (PRD)

**Version:** 1.0.0
**Last Updated:** September 01, 2026
**Status:** Draft for Review
**Source of Truth:** Phase 0–4 architecture documents, SIH positioning brief, professional Copilot instructions

> This PRD is a **technical-driven consolidation** of the Phase documents (Phase 0 → Phase 4). Where the Phase documents are explicit, this PRD follows them verbatim. Where gaps exist between the product story and the technical phases, this PRD **fills those gaps** with the minimum required behavior and flags them as [GAP-FILL] so reviewers can trace every new requirement back to a decision.

---

## 1. Product Overview\


### 1.1 Product Name
**AI-Assisted Criminal Investigation & Intelligence Platform**
(Brand name to be decided; technical reference name for now.)

### 1.2 Product Objective
To provide authorized investigators with a **secure, case-centric platform** that:

1. Securely ingests heterogeneous evidence (PDFs, scans, tables, handwritten documents, call detail records) while preserving **exact provenance**.
2. Normalizes and extracts **entities, relationships, and events** with **probabilistic entity resolution**.
3. Stores evidence and derived intelligence as a **knowledge graph** with explicit **epistemic tiers** (OBSERVED / DERIVED / PREDICTED).
4. Enables **graph exploration, network analysis, pattern detection, and link prediction** as investigative tools.
5. Provides an **evidence-grounded AI investigation assistant (copilot)** with strict anti-hallucination guardrails.
6. Generates **structured, evidence-referenced investigation reports**.
7. Enforces **role-based access control, immutable evidence, and a tamper-evident audit trail**.

### 1.3 Core Philosophy
**Don't replace the investigator.**

> **Collect → Organize → Connect → Explore → Question → Explain → Report**

The system provides investigative leads and evidence-backed relationships. It **never declares a person guilty**. Link predictions are **leads, not evidence**, and must be verified by an investigator.

### 1.4 Positioning (CRITICAL — READ BEFORE ANY PITCH)
> **"An investigation-centric intelligence layer that works with authorized criminal-justice data and evidence."**

This is **not** a replacement for NATGRID, CCTNS, or ICJS. It is an **investigation layer** that organizes authorized case evidence and provides explainable AI-assisted investigation workflows. Official MHA materials already document NATGRID's data-provider/user-agency integration and ICJS's criminal network link-analysis module; the product must not claim to replace them.

### 1.5 Product Layers (Conceptual Abstraction)
| Layer | Scope |
| :--- | :--- |
| **Governance** | Admin, identity, RBAC, audit |
| **Case Management** | Case creation, evidence, collaboration, permissions |
| **Intelligence** | Knowledge graph, network analysis, pattern detection, link prediction |
| **AI** | Investigation assistant, explanations, report generation |

---

## 2. Users & Roles

### 2.1 Administrator
Controls the platform rather than investigating cases.

**Can:**
- Add / remove investigators (users)
- Assign investigators to cases
- Reassign investigators
- Remove investigators from cases
- Grant exceptional access to a case
- Open a closed case
- Close / archive a case
- Manage permissions
- Review audit activity

### 2.2 Investigator / User
May belong to: Local/State Police, Crime Branch/CID, Cyber Crime Unit, or other authorized investigative/intelligence organization.

**Authorization model (three dimensions):**
- **Identity** — who the person is (unique ID, e.g. `2026-CID-01842` vs. `2026-DRUG-02917`; final format follows the organization's identity system).
- **Role** — what they can do.
- **Case assignment** — which cases they can access.

**Can (within assigned/permitted cases):**
- Create a case
- View assigned cases
- Search cases
- Open permitted cases
- Upload / add evidence
- Investigate
- Explore graphs
- Ask the AI assistant questions
- Confirm / reject review edges
- Generate reports

### 2.3 Identity, NOT Department
Two people named "Ramesh Kumar" have different unique IDs. Role and case assignment, not department name, determine access.

---

## 3. Case Access Model

### 3.1 Normal Access
```
User Login → Identity + Role Verification → Assigned Cases → Case Workspace
```

### 3.2 Unassigned Case (Request Access)
```
Search Case → No Access → Request Access → Admin Review
Approved? → Yes: View | No: Denied
```

### 3.3 Closed Historical Case
Closed cases can be exposed as **Reference Case → Read-only access** for authorized investigators studying related investigations. Useful for learning from prior cases without allowing modification.

---

## 4. Evidence Principles

- **Immutability:** Once evidence is uploaded, an investigator cannot permanently delete it.
- **Retention:** Evidence is retained; changes are audited.
- **Access control:** Access is governed by case-level authorization.
- **Exceptional actions:** Only administrative/legal procedures can govern exceptional removal or retention actions.
- **Prototype representation:** **Immutable Evidence + Audit Trail.**

---

## 5. User Workflow (Frozen for Presentation)

```
LOGIN → DASHBOARD
  Create Case          |        View Cases
       ↓               |      ┌──────────┴──────────┐
  Upload Evidence      |  Assigned Case      Request Access
       ↓               |       ↓                  ↓
  Case Workspace       |                     Admin Approval
       ↓               |
  INVESTIGATION WORKSPACE
       ↓
  ┌───────────────┼───────────────┐
  ↓               ↓               ↓
Explore Graph  AI Assistant  Generate Report
Entity/Hops     Questions    Investigation
Relationships   Cross-case   Summary
Case history    Evidence     Findings
```

> Users should **not** see OCR, parsing, embeddings, regex, or Pandas in this workflow. From the user's perspective: **Upload Evidence → Case Workspace Ready → Investigation.**

---

## 6. The Three Core Investigation Modules

### 6.1 Module 1 — Explore Graph (🔵 "Understand the network")
Answers: **"What relationships already exist in my data?"**

Capabilities:
- Search a person, phone number, organization, location, vehicle, account
- Expand connections
- Explore 1-hop, 2-hop, 3-hop, etc.
- View related cases
- View relationship types
- Filter entities
- Inspect supporting evidence

**Clicking a node reveals:**
- What is this entity?
- Where did this relationship come from?
- Which evidence supports it?
- Is this entity present in another case? *(cross-case linking)*

### 6.2 Module 2 — AI Investigation Assistant (🟣 "Ask questions about the evidence")
Answers: **"Ask questions about the evidence."** Natural-language investigation (distinct from visual graph exploration).

**Example queries:**
- "Show all known associates of Ramesh Kumar."
- "What cases are associated with this phone number?"
- "Show connections between A and B within three hops."
- "How many cases contain this person?"
- "What financial relationships exist between these entities?"
- "What evidence supports the relationship between A and B?"

**Answer contract (required):**
`Answer + supporting entities + evidence references + confidence / qualification` — never an unsupported LLM response.

### 6.3 Module 3 — Generate Investigation Report (🟢 "Convert findings into an actionable summary")
Produces a **structured, human-readable investigation summary** (not a dump of everything discovered).

**Report structure (9 sections):**
1. **Case Information** — Case ID, status, investigating officer, agency/team, date/time
2. **Case Summary** — short description
3. **Key Entities** — Persons, Organizations, Locations, Phone numbers, Vehicles, Accounts
4. **Relationship Summary** — natural-language statements (e.g., "Person A and Person B have 48 recorded communications during the investigated period.")
5. **Timeline** — chronologically ordered events
6. **Network Findings** — central entities, groups/clusters, strong relationships, cross-case relationships
7. **Pattern Findings** — repeated entities, transactions, phone numbers, locations, other patterns
8. **Potential Investigation Leads** — phrased as leads to verify ("The system identified a possible relationship between A and C. Verify against source records."), never as guilt
9. **Evidence References** — every important conclusion points back to source evidence

---

## 7. Network Analysis vs. Pattern Detection vs. Link Prediction

| Module | Main Question | Example |
| :--- | :--- | :--- |
| **Network Analysis** | What does the current network look like? Who is highly connected? | Degree/centrality, components |
| **Pattern Detection** | What suspicious/repeated behavior exists? | Same phone/account repeatedly appears across cases |
| **Link Prediction** | What potentially hidden relationship should be investigated? | A and B may have an indirect relationship |

> **In one sentence:** Network Analysis maps the known network. Pattern Detection finds meaningful behavior in it. Link Prediction identifies possible relationships worth investigating.

**Critical rule:** Link prediction is a **lead, not evidence**. The investigator must verify it.

---

## 8. Functional Requirements (By Phase)

> The following functional requirements are organized **by phase** (Phase 0 → Phase 4) to mirror the technical architecture documents. Each phase section lists: objective, technical stack, pipeline steps, required behaviors, and [GAP-FILL] requirements.

---

### PHASE 0 — SECURITY & CORE PLATFORM

**Objective:** Establish the authentication, authorization (RBAC), and audit foundation.

**Technical Stack (per Phase 0 doc):**
- FastAPI
- PostgreSQL 16
- SQLAlchemy 2.0
- Alembic (migrations)
- Pydantic v2
- python-jose (JWT)
- bcrypt (password hashing)

#### FR-P0-01 — Authentication
The system shall authenticate authorized users using a unique identity.

**Required flows:**
- `POST /auth/signup` — hash password (bcrypt), default role `INVESTIGATOR`
- `POST /auth/login` — validate credentials, generate JWT with `{user_id, role}`

#### FR-P0-02 — JWT & Dependency Injection Pipeline
```
User (Browser/UI)
   │
   ├─ POST /auth/signup  →  Hash password (bcrypt)  →  Default role INVESTIGATOR
   └─ POST /auth/login   →  Validate credentials   →  Generate JWT (user_id, role)
   │
   ▼
JWT Bearer Token Issued
   │
   ▼
FastAPI Dependency Injection Pipeline
   │
   ├─ get_current_user — Decode & verify JWT; check user is active
   ├─ require_admin
   │     • Is role == "admin"? → Yes: Grant | No: 403 Forbidden
   │     • (Controls logs, approvals, system configurations)
   └─ require_case_access
         • Is role == "admin"? → Yes: Auto-permit
         • No → Check CaseAccess
         • status == "approved"? → Yes: Allow entry | No: 403 Forbidden
   │
   ▼
Investigation Workspace (Graph, Upload, Copilot)
```

#### FR-P0-03 — Role-Based Access Control (RBAC)
- **Admin Master** vs. **Scanned Case Access** (case-level authorization)
- Admin auto-permits; non-admin must have an approved `CaseAccess` record
- Denied → HTTP 403 Forbidden with a clear, non-informative error

#### FR-P0-04 — Tamper-Evident Audit Logging
All security-relevant events are logged in a tamper-evident store. See §11 (Audit Trail).

#### [GAP-FILL] FR-P0-05 — Admin Console
The PRD product story (FR-01..FR-03) requires an Admin workflow; Phase 0 covers auth but **not the admin UI/API**. Add:
- User management (add / deactivate / remove investigator)
- Case assignment / reassignment
- Access-request approval queue (Approve / Deny)
- Case status transitions (open / close / archive / reopen)
- Exceptional-access grant
- Audit-log review view

#### [GAP-FILL] FR-P0-06 — Data-at-Rest Encryption Policy (NFR addendum)
Law-enforcement data requires explicit security policy across **all three stores** (PostgreSQL, MinIO/S3, Neo4j):
- Encrypt data at rest in PostgreSQL, MinIO/S3, and Neo4j
- Encrypt data in transit (TLS everywhere)
- Define a data-retention policy and a legal-gate deletion procedure
- Mask sensitive fields by role where required (see FR-P0-08)

#### [GAP-FILL] FR-P0-07 — Evidence Access Auditing
Audit **access** to evidence objects, not only uploads (who opened which document/BBox, when).

#### [GAP-FILL] FR-P0-08 — Field-Level / Masking by Role
Sensitive fields (phone numbers, bank accounts, etc.) shall be maskable so non-privileged roles cannot read the full value. This is a [GAP-FILL] tied to the "minimum necessary access" privacy requirement.

---

### PHASE 1 — SECURE INGESTION & MULTI-SCRIPT VISION PARSING

**Objective:** Securely ingest heterogeneous raw evidence and convert it into a **structured, provenance-bound** Unified Evidence JSON.

**Technical Stack (per Phase 1 doc):**
- MIME validation (libmagic)
- Antivirus scan (ClamAV)
- SHA-256 evidence hashing
- Immutable raw storage (MinIO/S3)
- Celery worker + Redis queue (async processing)
- pandas / openpyxl (tabular)
- PyMuPDF (native digital PDF)
- OpenCV (denoise)
- Surya layout detection / DocLayNet / YOLO
- PaddleOCR (Indic / English)
- Indic HTR models (Devanagari)
- Surya Table / TATR (table region parsing)

#### FR-P1-01 — Secure Ingestion Layer
- MIME validation (libmagic)
- Antivirus scan (ClamAV)
- SHA-256 evidence hashing (tamper-evident fingerprint)
- Immutable raw storage (MinIO / S3) — original file is never modified

#### FR-P1-02 — Document & Page Router
- Format inspection
- Page-by-page content + text-presence analysis
- Route each document to the correct engine branch

#### FR-P1-03 — Branch 1: Tabular Engine (Native) — CDRs, Bank Statements
- pandas / openpyxl parser
- Strict schema validation

#### FR-P1-04 — Branch 2: Native Digital PDF Engine — Digital briefs, reports
- PyMuPDF text/block dump
- Native bounding-box (bbox) coordinates

#### FR-P1-05 — Branch 3: Scanned / Visual Pipeline — FIRs, field notes, scans
- Preprocessing: Denoise, Deskew, CLAHE (OpenCV)
- Layout & region detection (Surya / DocLayNet / YOLO) — segment printed vs. handwriting; identify table coordinates
- **Printed region OCR** (Surya / PaddleOCR) — Hindi, Marathi, English
- **Handwritten HTR** (evaluated Indic HTR) — Devanagari models
- **Table region parser** (Surya Table / TATR) — grid & cell coordinates

#### FR-P1-06 — Encoding & Representation Normalization
- Unicode Normalization (NFC for Indic scripts)
- ZWJ / ZWNJ & diacritic preservation
- Strip non-printable ASCII control bytes

#### FR-P1-07 — Document Reconstruction
- Standardize page coordinates to a common canvas
- Preserve spatial reading order
- Link text/table tokens to their source bbox

#### FR-P1-08 — Unified Evidence JSON (Output Payload)
```
{
  case_id,
  doc_sha256,
  page_number,
  block_id,
  bbox (coordinates [x1,y1], [x2,y2], [x3,y3], [x4,y4]),
  extraction_method,
  confidence,
  detected_language,
  text,
  structured_tables
}
```

#### [GAP-FILL] FR-P1-09 — Unified Evidence Payload Schema Versioning
The Unified Evidence JSON will evolve across iterations. Add a top-level `schema_version` field from day one to enable safe migrations of already-stored S3 objects.

#### [GAP-FILL] FR-P1-10 — Async Pipeline Observability
Celery + Redis is used but lacks failure tracking. Add:
- Per-task traceable `request_id`
- Poison-queue / dead-letter handling for failed ingestion
- Structured error logging that links back to `case_id + doc_sha256`

---

### PHASE 2 — INFORMATION EXTRACTION & PROBABILISTIC RESOLUTION

**Objective:** Convert normalized evidence into **graph-ready entities, relationships, and events** with provenance and confidence, resolving the same real-world entity across mentions.

**Output Payload (per Phase 2 doc):** Canonical Entities • Review Edges • Evidence Pointers • BBoxes

#### FR-P2-01 — Investigative Cleaning & Data Normalization
- Standardize: Phone (E.164), Vehicle (HSRP), ISO Datetimes
- Validate: IMEI (Luhn algorithm), PAN, Bank IFSC
- Normalize: Devanagari script; strip honorific prefixes
- **Maintain exact character-offset mapping to Phase 1 bounding boxes** (provenance integrity)

#### FR-P2-02 — Dual-Track Entity (Mention) Extraction
**Track A — Deterministic Extractor** (compiled regex & rules):
- PHONE_NUMBER, IMEI, VEHICLE_NO, IP_ADDR, BANK_ACCOUNT, IPC_SEC

**Track B — Contextual NER Extractor** (GLiNER-Multi / IndicBERT-v2):
- PERSON, ALIAS, LOCATION, GANG_ORG, WEAPON, POLICE_STN

**(MahaRoBERTa also referenced as a contextual model option.)**

#### FR-P2-03 — Intra-Document Relation & Event Extraction
Extract edges between **local mentions BEFORE global entity merging** (order is critical).

- Tabular / CDR parser → `CALLED {duration, tower_id, time}`
- Dependency parsing / OpenIE → `OPERATED_VEHICLE`, `ACCUSED_OF`
- Spatial / temporal extraction → anchor events to timestamps and locations

#### FR-P2-04 — Probabilistic Entity Resolution Pipeline
1. **Blocking Engine** → Indic Soundex; City / District boundaries
2. **Multi-Factor Match Scoring** → Jaro-Winkler similarity; embeddings; biometrics
3. **Probabilistic Linkage** → Fellegi-Sunter / Splink scoring

**Threshold logic:**
| Score | Decision | Action |
| :--- | :--- | :--- |
| `≥ 0.85` | MATCH | Merge into CANONICAL Entity ID; retain all mention lineages |
| `0.50 ≤ score < 0.85` | REVIEW_REQUIRED | Keep as separate candidate entity; create `POSSIBLE_SAME_AS` edge; investigator confirmation |
| `< 0.50` | NO_MATCH | Distinct Entity |

#### FR-P2-05 — Graph-Ready Evidence Payload
- **Nodes** → Canonical Entities / Candidate Identities
- **Edges** → Investigative Relations / Review Edges
- **Dual Confidence Scores** → `extraction_conf` + `resolution_conf`
- **Lineage Trace** → `doc_id → page → block_id → bbox`

#### [GAP-FILL] FR-P2-06 — Resolution Scaling Target
Given the NFR "1 → 100 → 1000 cases," document the blocking strategy per entity type and define a benchmark target for merge latency to avoid O(blocks²) blowup on uncached Splink blocking.

---

### PHASE 3 — NEO4J INGESTION & INVESTIGATIVE ANALYSIS PIPELINE

**Objective:** Ingest graph-ready evidence into a multi-tenant Neo4j graph, then provide network analysis, GNN link prediction, and a hybrid retrieval / constrained GraphRAG engine.

**Output Payload (per Phase 3 doc):** Canonical Entities • Review Edges • Evidence Pointers • BBoxes

#### FR-P3-01 — Neo4j Knowledge Graph Ingestion Engine
**Nodes:** Person, Phone, Vehicle, Account, Case, Evidence
**Edges:** Explicit epistemic tiers: `OBSERVED` / `DERIVED` / `PREDICTED`
**Dual Evidence Binding:** Node-level **and** edge-level lineage

#### FR-P3-02 — Multi-Tenant Graph
The Neo4j graph is multi-tenant; case-level isolation is enforced (see FR-P0-03 case access).

#### FR-P3-03 — Graph Data Science (GDS) — Structural Metrics Only
Neo4j GDS:
- Structural connectivity
- Bridge / broker analysis
- Community partitioning (Leiden)
- PageRank, Betweenness, Leiden

**Constraint: No subjective labeling.** GDS reports structure; it does not attach subjective "gang/criminal" labels.

#### FR-P3-04 — GNN Link Prediction Layer (Analytical Subgraph — PREDICTED)
- PyG heterogeneous embeddings
- R-GCN Link Prediction engine
- GNNExplainer model-subgraph attribution paths
- Outputs flagged as **UNVERIFIED LEAD** (PREDICTED tier)

#### FR-P3-05 — Hybrid Retrieval Engine
- Graph traversal + vector retrieval
- Constrained path search
- Entity-anchored subgraphs
- Narrative chunk vectors
- **Presidio / PII-protected** (personal data protected before retrieval/response)

#### FR-P3-06 — Investigative Pattern & Anomaly Engine
Detect (explainable) patterns:
- **Cyclic financial paths** (circular funds)
- **Shared infrastructure** (phones / vehicles across suspects)
- **Spatio-temporal CDR co-location** anomalies

#### FR-P3-07 — Constrained GraphRAG Query Fusion
1. **Query Intent Analyzer** → target entity + relationship constraint
2. **Traversal Path Assembler** → retains edge evidence BBoxes
3. **Epistemic Context Formatter** → OBSERVED vs PREDICTED distinction
4. **Strict Evidence Guardrail** → falls back if ungrounded

#### FR-P3-08 — Investigator Copilot & Dashboard
- Evidence-grounded answers with `[Doc, Page, BBox]`
- Clear separation of **Verified Facts** vs **Investigative Leads**
- Interactive Subgraph Explorer with canvas jump-to-BBox
- Self-hosted vLLM local inference server (see FR-P3-10)

#### FR-P3-09 — [GAP-FILL] Explanation-By-Definition for Patterns & Leads
Every pattern hit and link-prediction lead must expose:
- `pattern_id` / model reference
- the fired conditions / attribution path
- the supporting evidence BBoxes
so a reviewer can verify. Tie each result back to evidence like RAG answers do.

#### FR-P3-10 — [GAP-FILL] Self-Hosted LLM Serving
"Self-Hosted vLLM Local Inference Server" (referenced in the all-phases integration doc) is specified here:
- Self-hosted vLLM for local/private inference
- Model choice configurable; no external LLM for sensitive data unless authorized
- Strict grounded rule: fallback to "Insufficient Evidence"

#### FR-P3-11 — [GAP-FILL] Permission-Aware Retrieval
The RAG retriever must take the requesting user's authorized `case_id` set as a **hard filter inside the traversal**, not applied after retrieval, to prevent information leakage across cases.

#### FR-P3-12 — [GAP-FILL] Investigation Memory (Review Actions)
Confirmed/rejected `POSSIBLE_SAME_AS` and `PREDICTED` edges must **persist**:
- Neo4j labels/states for review (e.g., `CONFIRMED`, `REJECTED`, `PENDING`)
- Copilot / lead-drawer confirmation UI
- Audit every review action (who, when, decision)
- Enable case handover: the investigation context remains with the case

---

### PHASE 4 — INVESTIGATOR WORKSPACE (SYSTEM ARCHITECTURE)

**Objective:** Frontend workspace → backend services → storage & persistence for graph exploration, evidence inspection, and AI-assisted investigation.

#### FR-P4-01 — Frontend Workspace (Next.js / React)
**Stack:** Next.js 14, React 18, Tailwind CSS, shadcn/ui

**Graph Canvas** (Cytoscape.js or Vis-Network; fcose layout):
- Interactive graph visualization
- Entity / relationship exploration
- Node click → entity details + supporting evidence

**Evidence Document Viewer**:
- PDF Canvas + dynamic BBox
- Evidence document rendering
- Jump-to-bounding-box highlighting

**AI Copilot & Lead Drawer**:
- Chat, Citations, Alerts
- Evidence-grounded assistance
- Investigative-lead presentation

#### FR-P4-02 — Backend Services (FastAPI)
**Case & Subgraph API:**
- Filter by `case_id`
- Cross-case expansion
- Merge-review approval

**Evidence File Service:**
- S3 signed-URL retrieval
- Normalization / BBox API
- PDF page rendering

**GraphRAG Assistant API:**
- Context Assembly
- Fallback Guardrail
- Automated Report Generation

#### FR-P4-03 — Storage & Persistence
| Store | Purpose |
| :--- | :--- |
| **Neo4j Knowledge Graph** | Nodes, Edges, Review Flags |
| **MinIO / S3 Object Store** | Raw PDF / Image evidence |
| **PostgreSQL Relational DB** | Cases, Users, Audit Logs |

#### FR-P4-04 — [GAP-FILL] Report Generation Data Contract
Phase 4 lists "Automated Report Generation Engine (ReportLab / WeasyPrint)" but does not specify the report structure. Implement the **9-section report** from §6.3: every conclusion joins to source evidence BBoxes (see FR-13).

---

## 9. Non-Functional Requirements (NFR)

### 9.1 Security
- Strong authentication (JWT + bcrypt)
- Role-based access + case-level authorization
- Encryption in transit (TLS)
- **Encryption at rest** (all three stores) — [GAP-FILL formalized]
- Secure secrets management
- Input validation, sanitized outputs, parameterized queries (OWASP)

### 9.2 Privacy
- Minimum-necessary access
- Sensitive-data protection (incl. field masking) — [GAP-FILL]
- Controlled sharing
- Auditability

### 9.3 Integrity
- Evidence immutability
- Source traceability (BBox lineage)
- Tamper-evident audit logs

### 9.4 Performance
- Common investigation queries → acceptable response time
- Graph exploration must remain usable as network size increases
- Define a resolution-merge latency benchmark — [GAP-FILL]

### 9.5 Scalability
- Support 1 case → 100 cases → 1000+ cases without redesign
- Multi-tenant Neo4j with case-level isolation

### 9.6 Availability
- Resilient against service failures
- Preserve investigation data

### 9.7 Explainability
- Every major AI-generated insight is traceable to available evidence
- Epistemic tiers + confidence + attribution paths

### 9.8 Maintainability
- Modular services so OCR, NLP, graph analytics, and LLM components evolve independently
- Versioned schemas — [GAP-FILL]

### 9.9 Observability
- Structured logging with `request_id` through async pipeline — [GAP-FILL]
- Metrics/traces for ingestion tasks — [GAP-FILL]

---

## 10. Product Functional Requirements (Cross-Phase, per FR number)

### FR-01 — Authentication
Authenticate users with a unique identity; determine identity, role, organization/agency, and permissions.

### FR-02 — Role-Based Access Control
Restrict functionality by role. Admin: manage users, assign/remove users, grant access, manage case status. Investigator: create/access assigned cases, upload evidence, investigate, explore graphs, ask AI, generate reports.

### FR-03 — Case Management
Investigator: create/view/search/open permitted cases, add evidence, update investigation. Admin: assign, reassign, open, close/archive, control access.

### FR-04 — Evidence Management
Support heterogeneous evidence: PDFs, scanned documents, text, CSV, structured records, call records, financial records, FIR-related documents, other case documents. Preserve source references.

### FR-05 — Evidence Processing
Process heterogeneous input into a common investigation representation:
```
Raw Evidence → Parsing/OCR → Cleaning & Normalization → Entity Extraction → Relationship Extraction → Cross-Case Linking → Knowledge Graph
```
*(This belongs in technical architecture, not user flow.)*

### FR-06 — Entity Management
Identify: Person, Organization, Phone, Location, Vehicle, Account, Event, Date/time.

### FR-07 — Relationship Extraction
Identify relationships such as:
```
Person → called → Person
Person → owns → Vehicle
Person → used → Phone
Person → transferred → Money
Person → associated with → Case
```

### FR-08 — Knowledge Graph
Entities = Nodes; Relationships = Edges; Evidence = Source. Basis for graph exploration.

### FR-09 — Network Analysis
Support: degree/centrality, connected components, communities/clusters, multi-hop exploration, relationship filtering.

### FR-10 — Pattern Detection
Detect: repeated entities, repeated numbers, shared accounts, repeated locations, repeated relationships, temporal patterns.

### FR-11 — Link Prediction
Identify potential relationships not explicitly present. Output is a **potential investigative lead**, not a factual assertion.

### FR-12 — AI Investigation Assistant
Natural-language querying over authorized case data. Must: understand investigation questions, retrieve relevant entities/relationships, answer using available evidence, cite/support, and avoid inventing unsupported facts.

### FR-13 — Report Generation
Generate: case summary, entity summary, relationship findings, timeline, network findings, pattern findings, investigation leads, evidence references.

### FR-14 — Audit Trail
Log: login, case access, evidence upload, permission changes, evidence-related actions, case status changes, report generation, administrative actions.

---

## 11. Audit Trail (Detailed)

The tamper-evident audit log must capture (FR-14 + Phase 0):
| Event Type | Fields (minimum) |
| :--- | :--- |
| Login / Logout | user_id, timestamp, session/request_id |
| Case access (incl. read/denied) | user_id, case_id, action, timestamp, result |
| Evidence upload | case_id, doc_sha256, user_id, timestamp, store reference |
| Permission changes | admin_id, target_user, target_case, before/after, timestamp |
| Evidence-related actions | case_id, doc_sha256, block/bbox, user_id, action, timestamp |
| Case status changes | admin_id, case_id, before/after status, timestamp |
| Report generation | user_id, case_id, report_id, timestamp |
| Administrative actions | admin_id, action, target, timestamp |
| **Merge-review decisions** [GAP-FILL] | user_id, edge_id, decision (CONFIRMED/REJECTED), timestamp |
| **Evidence access** [GAP-FILL] | user_id, case_id, doc_sha256, page, timestamp |

> The audit log must be **tamper-evident** (e.g., hash-chained or append-only with signature verification).

---

## 12. Technical Architecture (Consolidated)

```
USER / ADMIN
      │
      ▼
FRONTEND (Next.js 14 / React 18 / Tailwind / shadcn-ui)
  ├─ Graph Canvas (Cytoscape.js / Vis-Network / fcose)
  ├─ Evidence Document Viewer (PDF Canvas + dynamic BBox)
  └─ AI Copilot & Lead Drawer (Chat / Citations / Alerts)
      │
      ▼
BACKEND API (FastAPI)
  ├─ Auth & RBAC (JWT, require_admin, require_case_access)
  ├─ Case & Subgraph API (case_id filter, cross-case, merge approval)
  ├─ Evidence File Service (S3 signed URL, normalization/BBox, PDF render)
  └─ GraphRAG Assistant API (context assembly, guardrail, report)
      │
      ├──────────────────────┬──────────────────────┐
      ▼                      ▼                      ▼
AUTH & RBAC          CASE MANAGEMENT        EVIDENCE MGMT.
  │                      │                      │
      ▼                      ▼                      ▼
        EVIDENCE PROCESSING (Phase 1: OCR + Parsing + Cleaning)
                        │
                        ▼
        NLP / INFORMATION EXTRACTION (Phase 2: Entities + Relations)
                        │
                        ▼
        PROBABILISTIC ENTITY RESOLUTION (Splink + blocking)
                        │
                        ▼
        NEO4j MULTI-TENANT KNOWLEDGE GRAPH (Phase 3)
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   NETWORK          PATTERN          LINK
   ANALYSIS        DETECTION        PREDICTION
   (GDS)           (Anomaly)        (R-GCN)
        └───────────────┼───────────────┘
                        ▼
        CONSTRAINED GraphRAG ENGINE (vLLM + pgvector + Neo4j)
                        ▼
        AI INVESTIGATION ASSISTANT (Copilot)
                        ▼
        EXPLAINABLE FINDINGS → INVESTIGATION REPORT (Phase 4)

STORAGE:
  ├─ Neo4j Knowledge Graph (nodes, edges, review flags)
  ├─ MinIO / S3 (raw PDF / image evidence, immutable, SHA-256)
  └─ PostgreSQL 16 (cases, users, audit logs) + pgvector
```

### Suggested Tech Stack
| Layer | Technology |
| :--- | :--- |
| Frontend | React / TypeScript (Next.js 14) |
| UI | Tailwind / shadcn/ui |
| Backend | Python + FastAPI |
| Auth | JWT (python-jose) + bcrypt |
| Relational DB | PostgreSQL 16 + pgvector |
| Graph DB | Neo4j (multi-tenant) |
| Object Store | MinIO / S3 |
| Queue | Celery + Redis |
| OCR | PaddleOCR / Surya / Tesseract / Indic HTR |
| NLP | GLiNER / IndicBERT / MahaRoBERTa |
| Data processing | Python / Pandas / openpyxl |
| Graph analytics | Neo4j GDS, NetworkX |
| Graph ML | PyG (R-GCN), GNNExplainer |
| LLM | Self-hosted vLLM local inference |
| RAG | Graph-traversal + pgvector context fusion |
| Visualization | Cytoscape.js / Vis-Network / React Flow / D3 |
| Deployment | Docker |

> **Do not lock every library before testing.** The architecture describes capabilities; final stack is selected based on benchmark results.

---

## 13. Data Model (Consolidated & [GAP-FILL] completed)

### 13.1 Entity Types (Nodes)
- **Person** (canonical / candidate) — with `extraction_conf`, `resolution_conf`, lineage
- **Organization** / GANG_ORG
- **Phone** — normalized E.164
- **Vehicle** — HSRP normalized
- **Account** — bank account
- **Location** — city/district boundaries
- **Event** — with spatial/temporal anchor
- **Case**
- **Evidence** — with `doc_sha256`, provenance

### 13.2 Relationship / Edge Types
- `CALLED` — `{duration, tower_id, time}`
- `OPERATED_VEHICLE`
- `ACCUSED_OF`
- `OWNS` (Person → Vehicle)
- `USED` (Person → Phone)
- `TRANSFERRED_MONEY` (Person → Account)
- `ASSOCIATED_WITH_CASE` (Entity → Case)
- `POSSIBLE_SAME_AS` — review edge (candidate identity)
- Generic relational edges from relation extraction

### 13.3 Edge Epistemic Tiers
`OBSERVED` (direct evidence lineage) | `DERIVED` (document/computation) | `PREDICTED` (link-prediction lead; flagged UNVERIFIED)

### 13.4 [GAP-FILL] Review State (Investigation Memory)
Add review state on candidate/predicted edges: `PENDING` / `CONFIRMED` / `REJECTED`, with reviewed-by + timestamp.

### 13.5 Unified Evidence JSON Schema
```
schema_version: string          // [GAP-FILL]
case_id: string
doc_sha256: string
page_number: int
block_id: string
bbox: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
extraction_method: string
confidence: float
detected_language: string
text: string
structured_tables: array
```

### 13.6 Graph-Ready Evidence Payload
```
nodes: canonical/candidate entities (with dual confidence + lineage)
edges: investigative relations / review edges (with epistemic tier + lineage)
```
- Dual confidence scores: `extraction_conf` + `resolution_conf`
- Lineage trace: `doc_id → page → block_id → bbox`

---

## 14. Error Handling & Guardrails

### 14.1 Constrained GraphRAG Guardrail
If grounding is insufficient, the assistant **must** return `"Insufficient Evidence"` rather than a fabricated answer (FR-P3-07 step 4).

### 14.2 Lead vs. Fact Separation
- **Verified Facts** (OBSERVED/DERIVED with evidence) vs. **Investigative Leads** (PREDICTED / low confidence)
- UI must visually separate them; leads require investigator verification

### 14.3 Error Messaging (Corporate Standard — per Copilot instructions)
- Specific and actionable: "Email format invalid: missing @ symbol," not "Invalid input"
- Include error codes for programmatic handling
- Suggest remediation steps
- Log full context (non-sensitive) for debugging

---

## 15. Feasibility & Viability

### 15.1 Feasibility
Prototype feasibility is **high**, provided the prototype does **not** integrate with real government systems for the hackathon.

**MVP uses:**
```
Synthetic / legally available sample data
  → Document ingestion
  → OCR/NLP
  → Entity extraction
  → Knowledge graph
  → Graph analytics
  → AI assistant
  → Report
```

**What is difficult (deployment considerations):**
1. Real-world data integration
2. Data quality
3. Multilingual documents
4. Entity resolution
5. False relationships
6. LLM hallucination
7. Security
8. Government authorization
9. Large-scale graph performance

### 15.2 Viability
Strong because this is an **investigation layer**, not a replacement for national infrastructure.

```
Existing systems → Authorized data → Your investigation layer → Investigator
```

---

## 16. Research Required Before Building

1. **Existing Indian systems:** NATGRID, CCTNS, ICJS, NCRB, I4C, e-Forensics, relevant criminal-justice data systems
2. **Knowledge graphs:** entity-relationship modeling, property graphs, knowledge graphs, graph databases, entity resolution
3. **Criminal network analysis:** degree/betweenness centrality, community detection, connected components, multi-hop, temporal networks
4. **Link prediction:** common neighbors, Jaccard, Adamic-Adar, preferential attachment, graph embeddings, GNNs (defer GNNs for prototype)
5. **NLP:** NER, relation extraction, entity resolution, coreference resolution, multilingual NLP, information extraction
6. **OCR:** printed/scanned, Indian-language OCR, noisy OCR, handwriting (if relevant)
7. **RAG/LLM:** RAG, Graph-RAG, evidence-grounded generation, citation/traceability, hallucination mitigation, **permission-aware retrieval**

---

## 17. SIH Presentation Alignment (Six Slides)

### SLIDE 1 — TITLE
Project Name, Problem Statement ID + Title, Team Name, College/Institution, Team Members. One visual: **Evidence → Network → AI → Investigation.**

### SLIDE 2 — PROBLEM UNDERSTANDING
**"From Fragmented Evidence to Actionable Investigation"** — multiple sources, different formats, manual correlation, hidden relationships, slow investigation.

### SLIDE 3 — PROPOSED SOLUTION
**"An AI-assisted, case-centric investigation platform that converts heterogeneous evidence into an explainable criminal intelligence graph."**

Three major capabilities: **Explore Graph, AI Investigation Assistant, Generate Investigation Report.**
Three differentiators: **Case-centric, Explainable, Permission-controlled.**

### SLIDE 4 — TECHNICAL APPROACH & ARCHITECTURE
```
Evidence → OCR/Parsing → Cleaning & Normalization → Entity + Relation Extraction
→ Entity Resolution → Cross-Case Linking → Knowledge Graph
     → Network / Pattern / Link Analysis
     → AI Investigation Assistant
     → Investigation Report
```
Side tech stack: React, FastAPI/Python, PostgreSQL, Neo4j, OCR, NLP, Graph analytics/ML, LLM/RAG, Docker.

### SLIDE 5 — FEASIBILITY & VIABILITY
Technical feasibility, challenges, mitigation. Most important line: **"Prototype is feasible without direct access to classified government databases."**

### SLIDE 6 — IMPACT, BENEFITS & SUSTAINABILITY
Impact, users, future scope (authorized ICJS/NATGRID integration, multilingual, advanced graph ML, real-time intelligence).

> **Positioning to remember:** Present as an "investigation-centric intelligence layer," never as a NATGRID/ICJS replacement.

---

## 18. Glossary / Definitions

| Term | Definition |
| :--- | :--- |
| Evidence | Any uploaded source document/file with SHA-256 fingerprint |
| Unified Evidence JSON | Normalized, provenance-bound representation of evidence (cases, pages, blocks, bboxes, tables) |
| Entity | A person, org, phone, vehicle, account, location, event, etc. |
| Mention | An occurrence of an entity in a specific document block |
| Canonical Entity | The resolved, merged global identity |
| Candidate Identity | A provisional, unresolved entity awaiting review |
| Review Edge | `POSSIBLE_SAME_AS` between candidates |
| Epistemic Tier | OBSERVED / DERIVED / PREDICTED truth-assignment of a fact or edge |
| BBox | Bounding box coordinates linking text to source document position |
| Lineage | `doc_id → page → block_id → bbox` provenance trace |
| GDS | Neo4j Graph Data Science (PageRank, Betweenness, Leiden) |
| GraphRAG | Retrieval-augmented generation over the knowledge graph |
| UNVERIFIED LEAD | A PREDICTED-tier, not-yet-confirmed investigation lead |

---

## 19. Open Questions / Future Decisions

1. Final brand/product name.
2. Entity ID format — must follow the organization's identity system (not hard-coded).
3. Model song selection for OCR/NER/LLM — final after benchmarks; do not lock now.
4. Government integration strategy — future authorized integration, not prototype scope.
5. HTR handwriting model — evaluate relevance & availability per evidence type.

---

## 20. Requirements Coverage Matrix

| Requirement | Source Document | Phase | Status |
| :--- | :--- | :--- | :--- |
| FR-P0-01..04 | Phase 0 | 0 | Implemented in phase doc |
| FR-P0-05..08 | [GAP-FILL] | 0 | Added — admin console, encryption, access audit, masking |
| FR-P1-01..08 | Phase 1 | 1 | Implemented in phase doc |
| FR-P1-09..10 | [GAP-FILL] | 1 | Added — schema versioning, observability |
| FR-P2-01..05 | Phase 2 | 2 | Implemented in phase doc |
| FR-P2-06 | [GAP-FILL] | 2 | Added — resolution scaling target |
| FR-P3-01..08 | Phase 3 | 3 | Implemented in phase doc |
| FR-P3-09..12 | [GAP-FILL] | 3 | Added — explanation, vLLM, permission-aware retrieval, investigation memory |
| FR-P4-01..03 | Phase 4 | 4 | Implemented in phase doc |
| FR-P4-04 | [GAP-FILL] | 4 | Added — report data contract |
| FR-01..14 | Product story | Cross | Consolidated |
| NFR security/privacy | Product story + [GAP-FILL] | Cross | Added encryption/masking |
| Audit trail | Phase 0 + FR-14 + [GAP-FILL] | Cross | Extended with review/access events |

---

## 21. Revision History
| Version | Date | Author | Change |
| :--- | :--- | :--- | :--- |
| 1.0.0 | 2026-09-01 | Dev Team / AI Assistant | Initial consolidated PRD from Phase 0–4 docs + gap-fill |
