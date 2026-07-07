# SecureOps: Technical Specification

Version 1.0
Last updated: July 2026
Status: Draft, pre-implementation

This document is the source of truth for the SecureOps build. It defines what the system does, how its components interact, what data it stores, and what correct and incorrect behavior look like. Code should be generated and reviewed against this specification, not the other way around.

---

## 1. Overview and Problem Statement

### 1.1 What SecureOps is

SecureOps is a production-grade, multi-agent IT Service Management (ITSM) system. It receives incoming incidents and service requests, validates them for security risk before any processing occurs, retrieves relevant knowledge to resolve them, and automatically converts successful resolutions into reusable knowledge base articles.

### 1.2 The problem

Most agentic ITSM prototypes treat security as an afterthought layered on top of a working pipeline, and treat knowledge capture as a manual, after-the-fact process that depends on a human writing up the resolution. Both of these are architectural weaknesses, not implementation details. SecureOps addresses both directly:

- Security validation is the mandatory first checkpoint for every request, not a filter applied later in the pipeline.
- The knowledge base grows automatically from resolved work, rather than depending on someone remembering to document it.

### 1.3 Why ITSM

The person building this system has a background in ServiceNow-based AI architecture (AI Agent Studio, NowAssist, Virtual Agent). ITSM as a domain was largely absent from prior capstone submissions in this course, which makes domain depth a genuine point of differentiation rather than a generic agent demo repackaged with new branding.

### 1.4 Course concepts demonstrated

This project intentionally demonstrates well beyond the rubric's minimum of three key concepts. The required minimum, multi-agent orchestration, MCP, and agent skills, are covered as a baseline. Beyond that, the system also demonstrates context engineering, memory (session and persistent), observability, evaluation, Spec-Driven Development, and a fail-closed security gating pattern. These are listed here for traceability, not as a checklist to pad the document.

---

## 2. Architecture Summary

### 2.1 High-level flow

A request enters the system and passes through five agents in sequence, with conditional routing at several points:

1. Security Guardian validates the input. If validation fails, or if the Guardian itself is unavailable, the request is rejected. Nothing downstream ever sees unvalidated input.
2. Intake Agent classifies the request (category, priority, affected system) and creates the initial ticket record.
3. Knowledge Retrieval Agent searches the vector store for relevant prior resolutions or knowledge articles.
4. Resolution Agent proposes a resolution, using retrieved knowledge where available, and escalates to a human when confidence is low.
5. Knowledge Extraction Agent runs after a resolution is confirmed, and generates a new knowledge base article if the resolution is generalizable.

### 2.2 The fail-closed principle

The Security Guardian's design is intentionally fail-closed. If the Guardian cannot be reached, times out, or returns an ambiguous result, the request is rejected rather than passed through. This is a deliberate architectural stance, not a default, and it is documented here so the reasoning is explicit: in an ITSM context, a false rejection costs a retry, while a false pass-through of a malicious or malformed input can compromise the ticketing system, leak data, or corrupt the knowledge base that later agents rely on.

### 2.3 Tool and library versions

```yaml
runtime:
  python: "3.14"
frameworks:
  google_adk: "2.3.0"
  google_genai: "2.10.0"
models:
  security_guardian: "gemini-2.5-pro"
  orchestrator: "gemini-2.5-pro"
  intake_agent: "gemini-2.5-flash"
  knowledge_retrieval_agent: "gemini-2.5-flash"
  resolution_agent: "gemini-2.5-flash"
  knowledge_extraction_agent: "gemini-2.5-flash"
storage:
  vector_store: "ChromaDB"
  relational_db: "SQLite via SQLAlchemy"
supporting_libraries:
  - "python-dotenv"
  - "fastapi"
  - "uvicorn"
  - "opentelemetry-api"
  - "opentelemetry-sdk"
```

### 2.4 Model selection rationale

Model assignment follows a cost- and risk-aware split rather than a uniform default. The Security Guardian and the orchestrator carry the highest consequence if they make a wrong call: a missed prompt injection or a bad routing decision affects everything downstream. Both use Gemini 2.5 Pro for stronger reasoning. Intake, Knowledge Retrieval, Resolution, and Knowledge Extraction are high-throughput, lower-consequence tasks, and use Gemini 2.5 Flash for speed and cost efficiency.

---

## 3. Agent Specifications

### 3.1 Security Guardian

Responsibility: validate every incoming request before any other agent processes it. Checks for prompt injection attempts, malformed input, data exfiltration attempts, and policy violations.

```yaml
agent: security_guardian
model: gemini-2.5-pro
position: mandatory_first_checkpoint
failure_mode: fail_closed
input:
  raw_request: string
  user_id: string
  company_id: string
output:
  validation_result: enum [approved, rejected]
  rejection_reason: string, nullable
  risk_flags: list of string
  trace_id: string
```

### 3.2 Intake Agent

Responsibility: classify an approved request and create the ticket record.

```yaml
agent: intake_agent
model: gemini-2.5-flash
input:
  raw_request: string
  user_id: string
  company_id: string
  trace_id: string
output:
  ticket_id: string
  category: string
  priority: enum [low, medium, high, critical]
  affected_system: string
  summary: string
```

### 3.3 Knowledge Retrieval Agent

Responsibility: query ChromaDB for relevant knowledge articles or prior resolved tickets matching the current request.

```yaml
agent: knowledge_retrieval_agent
model: gemini-2.5-flash
input:
  ticket_id: string
  category: string
  summary: string
output:
  matched_articles: list of object
    article_id: string
    similarity_score: float
  confidence: float
```
The confidence threshold of 0.65 was determined empirically, not assumed. Testing against the seeded knowledge base using gemini-embedding-001 showed that genuine matches (a ticket correctly corresponding to a relevant article) scored between 0.70 and 0.80, while an unrelated ticket against the same knowledge base scored 0.60. This reflects a general property of embedding models rather than a limitation specific to this one: cosine similarity between conceptually related but non-identical natural language text typically clusters in the 0.55 to 0.85 range, since the model is measuring semantic proximity, not exact repetition. A threshold set too high, such as 0.75, would reject legitimate matches and force unnecessary escalations, undermining the resolution flywheel this system is built around. The chosen threshold reflects the actual separation observed between true and false matches in this domain's data, and should be re-validated if the knowledge base grows substantially or the embedding model changes.

### 3.4 Resolution Agent

Responsibility: propose a resolution using retrieved knowledge. Escalates to a human when confidence falls below a defined threshold.

```yaml
agent: resolution_agent
model: gemini-2.5-flash
input:
  ticket_id: string
  matched_articles: list of object
  confidence: float
output:
  resolution_text: string, nullable
  action: enum [auto_resolve, escalate]
  escalation_reason: string, nullable
```

### 3.5 Knowledge Extraction Agent

Responsibility: after a resolution is confirmed, determine whether it is generalizable and, if so, write a new knowledge base article.

```yaml
agent: knowledge_extraction_agent
model: gemini-2.5-flash
input:
  ticket_id: string
  resolution_text: string
output:
  article_created: boolean
  article_id: string, nullable
```

---

## 4. Data Contracts

Inter-agent messages carry a consistent envelope so that tracing and logging remain uniform across the pipeline.

```yaml
message_envelope:
  trace_id: string
  timestamp: datetime
  source_agent: string
  destination_agent: string
  payload: object
  user_id: string
  company_id: string
```

Every message that crosses an agent boundary is logged against this envelope, which is what allows the agent_traces table (Section 5) to reconstruct a full request lifecycle after the fact.

---

## 5. Database Schema

SQLite via SQLAlchemy. The schema is intentionally production-shaped rather than minimal, since one of the goals of this submission is to demonstrate that the system is built for real operational use, not a notebook demo.

```yaml
tables:
  tickets:
    id: string, primary_key
    company_id: string, foreign_key
    user_id: string, foreign_key
    category: string
    priority: string
    status: string
    summary: string
    created_at: datetime
    resolved_at: datetime, nullable

  escalations:
    id: string, primary_key
    ticket_id: string, foreign_key
    reason: string
    escalated_at: datetime
    resolved_by: string, nullable

  alerts:
    id: string, primary_key
    ticket_id: string, foreign_key, nullable
    severity: string
    message: string
    created_at: datetime

  users:
    id: string, primary_key
    company_id: string, foreign_key
    name: string
    role: string

  companies:
    id: string, primary_key
    name: string

  security_events:
    id: string, primary_key
    trace_id: string
    event_type: string
    risk_flags: string
    action_taken: string
    created_at: datetime

  knowledge_articles:
    id: string, primary_key
    title: string
    content: string
    source_ticket_id: string, foreign_key, nullable
    created_at: datetime

  agent_traces:
    id: string, primary_key
    trace_id: string
    agent_name: string
    input_summary: string
    output_summary: string
    duration_ms: integer
    created_at: datetime
```

---

## 6. Security Model

The Security Guardian is the only agent permitted to make the initial pass or reject decision. No other agent in the pipeline receives unvalidated input under any circumstance, including retries and partial failures.

Checks performed by the Guardian include detection of prompt injection patterns, attempts to extract system instructions or other users' data, malformed or oversized input, and requests that fall outside the ITSM domain entirely. Any rejection is logged to the security_events table with the specific risk flags that triggered it, along with the trace_id so the event can be correlated with the rest of the request lifecycle if one exists.

Escalation to a human is a separate mechanism from security rejection. Escalation happens when the Resolution Agent has low confidence in a proposed fix. Rejection happens when the Security Guardian determines the input itself should not proceed. These are tracked in separate tables (escalations and security_events) because they represent different failure categories and should not be conflated in reporting.

---

## 7. Knowledge Flywheel

When a ticket is resolved, either automatically by the Resolution Agent or manually after escalation, the Knowledge Extraction Agent evaluates whether the resolution is generalizable, meaning it would plausibly help with a future, similar ticket rather than being specific to one user's environment. If so, it writes a new row to knowledge_articles, which becomes immediately searchable by the Knowledge Retrieval Agent through ChromaDB. This creates a compounding effect: the more tickets the system resolves, the more knowledge it accumulates, and the less often the Resolution Agent needs to escalate over time.

---

## 8. Evaluation Scenarios

These scenarios are written in Given/When/Then form, following the Behavior-Driven Development approach described in the Day 5 course material. They define what correct behavior looks like, what wrong behavior looks like, and the edge cases the system must handle deliberately rather than by accident.

### Scenario 1: Normal auto-resolution

```
Given a valid, well-formed incident request about a known issue category
When the request passes the Security Guardian and Knowledge Retrieval finds a high-confidence match
Then the Resolution Agent should auto-resolve the ticket
And the Knowledge Extraction Agent should evaluate the resolution for reuse
```

### Scenario 2: Low-confidence escalation

```
Given a valid incident request with no strong match in the knowledge base
When Knowledge Retrieval returns a confidence score below the escalation threshold
Then the Resolution Agent should escalate rather than attempt an auto-resolution
And an entry should be written to the escalations table with the reason
```

### Scenario 3: Prompt injection attempt

```
Given an incoming request that contains an embedded instruction attempting to override agent behavior
When the Security Guardian evaluates the request
Then the request should be rejected before reaching the Intake Agent
And a security_events entry should be created with the relevant risk flags
```

### Scenario 4: Security Guardian unavailable

```
Given the Security Guardian service is unreachable or times out
When any request is submitted
Then the request should be rejected
And no request should ever reach the Intake Agent while the Guardian is unavailable
```

### Scenario 5: Out-of-domain request

```
Given a request unrelated to ITSM, such as a general knowledge question
When the Security Guardian evaluates the request
Then the request should be rejected as out of scope
And the rejection reason should distinguish this from a security risk rejection
```

---

## 9. Out of Scope for This Submission

The following were part of the original architectural exploration but are explicitly deprioritized for this submission, given the timeline. They are named here rather than silently dropped, since the reasoning itself is a documented trade-off, consistent with the Day 5 material's emphasis on architecture as a series of explicit decisions.

- **Cloud Run deployment.** The rubric accepts a public GitHub repository with detailed setup instructions as an alternative to a live deployed demo. Given the scoring weight (70 of 100 points on code quality and documentation), time is better spent on the codebase and README than on deployment infrastructure.
- **A2A protocol (Agent Card).** Valuable for demonstrating cross-agent interoperability, but additive to the required minimum concept count. Treated as a stretch goal only if time remains after the core system is complete.
- **Microsoft Docs MCP server consumption.** Same reasoning as above. The system is designed so this can be added later as an additional tool on the Knowledge Retrieval Agent without changing the existing architecture.

---

## Appendix: Glossary

- **Trace ID**: a unique identifier assigned to a request when it first enters the system, used to correlate all downstream agent activity, logs, and database writes back to that single request.
- **Fail-closed**: a design principle where, in the event of uncertainty or unavailability, the system defaults to rejecting or blocking rather than allowing an action to proceed.
- **Knowledge flywheel**: the self-reinforcing cycle where resolved tickets generate new knowledge articles, which in turn improve future resolution confidence and reduce escalation rates.