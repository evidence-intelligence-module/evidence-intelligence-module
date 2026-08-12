# Phase 0 Research: Evidence Generation Pipeline

Resolves the `NEEDS CLARIFICATION` items left in `plan.md`'s Technical Context. Where `hld.md` already fixed a decision, that decision is treated as given, not re-derived here — this file only resolves what existing docs left open.

## 1. Relational storage engine

**Decision**: PostgreSQL with the PostGIS extension.

**Rationale**: `hld.md` §4 already defines a relational schema (`evidence_requests`, `satellite_analysis_results`, `model_component_results`, `weather_correlation_results`, `evidence_packages`) with explicit foreign keys — a relational engine is implied by the schema itself, not a new choice. `evidence_requests.geometry` is a field boundary/point (spec.md Key Entities), which needs native geometry storage and spatial queries (e.g., "within 5km" / "within 10km" spatial-alignment scoring, spec.md causation factors) — PostGIS is the standard fit for a Python/GEE-adjacent stack with no licensing conflict with the module's public-tier cost posture (HLD §8).

**Alternatives considered**:
- *MongoDB* — rejected; the schema HLD already defines is relational with FKs (`request_id` referenced across four other tables), not document-shaped.
- *DynamoDB / vendor-managed NoSQL* — rejected; would commit to a specific cloud vendor that no existing document names, and has weaker native geometry/spatial-query support than PostGIS.
- *MySQL/MariaDB* — rejected; geometry/spatial support is less mature than PostGIS for the spatial-alignment scoring this module needs (evidence-flow-spec.md §5).

## 2. Testing framework

**Decision**: pytest.

**Rationale**: De facto standard for Python 3.11 services; supports the contract/integration/unit test separation already reflected in the project structure (plan.md), and has mature fixtures/mocking support for external services (GEE API, weather APIs) that this module depends on but shouldn't call in unit tests.

**Alternatives considered**:
- *unittest (stdlib)* — rejected; more boilerplate for fixture/parametrization-heavy tests (many model components, many peril types) with no offsetting benefit.
- *nose2* — rejected; not actively maintained relative to pytest.

## 3. Target platform / deployment shape

**Decision**: Linux containers (Docker image), deployed to cloud compute.

**Rationale**: `hld.md` §7 states compute is "cloud-based" without naming a specific vendor or platform. Every primary dependency (GEE Python API, scikit-learn, WOFOST/InfoCrop, ReportLab) runs natively on Linux/Python; containerizing avoids prematurely committing to a specific cloud vendor's proprietary deployment model that no existing document specifies.

**Alternatives considered**:
- *VM-based deployment* — rejected; less portable across the "cloud-based" compute HLD leaves unspecified, no advantage over containers here.
- *Vendor-specific serverless (e.g., a named FaaS product)* — rejected; would over-commit to a vendor choice that isn't in any source document, and the CSM assimilation component (WOFOST/InfoCrop runs) is a poor fit for typical serverless time/memory limits.

## 4. Scale / concurrency target

**Decision**: Not resolved here — explicitly deferred.

**Rationale**: No source document (`README.md`, `constitution.md`, `hld.md`, `modeling-approach.md`, `evidence-flow-spec.md`) states an expected request volume, concurrency target, or claims-scale figure. Inventing one would violate this repo's convention against unsourced figures (`CLAUDE.md`). Phase 1 design below (data model, API contract) does not depend on this number — it only becomes load-bearing at infrastructure-sizing time. Full reasoning and recommendation: [`issue/open query - expected request volume and concurrency target.md`](./issue/open%20query%20-%20expected%20request%20volume%20and%20concurrency%20target.md).

**Alternatives considered**: N/A — no candidate figures exist in any source document to weigh against each other.

## Output

All `NEEDS CLARIFICATION` items from `plan.md`'s Technical Context are resolved above, except Scale/Scope, which is deliberately left open and tracked as an issue rather than guessed. This does not block Phase 1 — data model and contracts are scale-agnostic.
