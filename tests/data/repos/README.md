# Test Repositories for Multi-MCP Integration Testing

## Overview

This directory contains a curated collection of **intentionally buggy** test repositories designed to comprehensively validate Multi-MCP's AI-powered code analysis capabilities across all workflows: `codereview`, `chat`, `compare`, and `debate`.

Each repository contains real-world code patterns with known issues spanning security vulnerabilities, concurrency bugs, architectural flaws, and code quality problems. These repositories enable objective, measurable testing of Multi-MCP's ability to detect bugs, explain architecture, compare solutions, and facilitate technical debates.

## Bug Summary Statistics

| Repository | Difficulty | Files | LOC | Total Bugs | Critical | High | Medium | Low |
|------------|-----------|-------|-----|------------|----------|------|--------|-----|
| sql_injection | ⭐ | 1 | ~75 | 5 | 3 | 1 | 1 | 0 |
| async-api | ⭐ | 5 | ~200 | 8 | 2 | 2 | 2 | 2 |
| asynctaskqueue | ⭐⭐ | 5 | ~530 | 8 | 2 | 3 | 2 | 1 |
| dataflowpipeline | ⭐⭐⭐ | 6 | ~600 | 9 | 3 | 3 | 2 | 1 |
| serviceregistry | ⭐⭐⭐ | 5 | ~400 | 6 | 2 | 2 | 1 | 1 |
| configworkflow | ⭐⭐⭐⭐ | 6 | ~500 | 7 | 2 | 2 | 2 | 1 |
| distributedcache | ⭐⭐⭐⭐ | 5 | ~450 | 5 | 2 | 2 | 1 | 0 |
| eventworkflow | ⭐⭐⭐⭐ | 5 | ~400 | 5 | 2 | 2 | 1 | 0 |
| pluginpipeline | ⭐⭐⭐⭐ | 5 | ~400 | 5 | 2 | 2 | 1 | 0 |
| tenantgateway | ⭐⭐⭐⭐ | 5 | ~400 | 5 | 2 | 2 | 1 | 0 |
| servicemesh | ⭐⭐⭐⭐⭐ | 10 | ~1,400 | 5 | 2 | 2 | 1 | 0 |
| mlpipeline | ⭐⭐⭐⭐⭐ | 10 | ~1,500 | 5 | 3 | 2 | 0 | 0 |
| **TOTAL** | | **68** | **~6,855** | **73** | **27** | **25** | **15** | **6** |

**Key Metrics:**
- **12 repositories** with complete golden datasets
- **73 total bugs** documented (27 Critical, 25 High, 15 Medium, 6 Low)
- **68 Python files** across ~6,855 lines of code
- **Difficulty range**: ⭐ (Basic) to ⭐⭐⭐⭐⭐ (Expert)
- **100% coverage** with `expected_findings.yaml` for automated testing

## Purpose

### Primary Goals
1. **Objective Testing**: Provide ground truth datasets for measuring recall, precision, and accuracy
2. **Workflow Validation**: Test all Multi-MCP workflows (codereview, chat, compare, debate)
3. **Complexity Grading**: Validate performance across increasing difficulty levels (⭐ to ⭐⭐⭐⭐⭐)
4. **Domain Coverage**: Cover diverse domains (async APIs, ML pipelines, service mesh, security)
5. **Regression Prevention**: Catch quality degradation in future changes

### Testing Strategy
- **Phase 1**: Basic repos (async-api, asynctaskqueue, sql_injection) - Core functionality
- **Phase 2**: Intermediate repos (dataflowpipeline, serviceregistry, configworkflow) - Cross-file reasoning
- **Phase 3**: Advanced repos (distributedcache, eventworkflow, pluginpipeline, tenantgateway) - Distributed systems
- **Phase 4**: Expert repos (servicemesh, mlpipeline) - Maximum complexity and scale

## Repository Inventory

### Security-Focused Repository

#### sql_injection (⭐ Basic)
- **Domain**: Authentication & Security
- **Files**: 1 Python file
- **Bugs**: 5 total (3 Critical, 1 High, 1 Medium)
- **Focus**: OWASP Top 10 vulnerabilities
- **Key Issues**:
  - SQL injection in authentication (CRITICAL)
  - Plain text password storage (CRITICAL)
  - Weak password policy (HIGH)
- **Testing Use**: Security audit, OWASP detection, CLAUDE.md context loading

### Complexity-Graded Repositories

#### async-api (⭐ Basic)
- **Domain**: FastAPI-style async service with storage
- **Files**: 5 Python files
- **Bugs**: 8 total (2 Critical, 2 High, 2 Medium, 2 Low)
- **Key Issues**:
  - Unsanitized filenames → path injection (CRITICAL)
  - Race-prone in-memory cache (CRITICAL)
  - Nullability mismatches (HIGH)
- **Testing Use**: Basic code review, async pattern detection, file I/O security

#### asynctaskqueue (⭐⭐ Intermediate)
- **Domain**: Background job processing with workers and scheduler
- **Files**: 5 Python files (~530 LOC)
- **Bugs**: 8 total (2 Critical, 3 High, 2 Medium, 1 Low)
- **Key Issues**:
  - Async/sync deadlock between scheduler and queue (CRITICAL)
  - Worker pool race condition (CRITICAL)
  - Memory leak in scheduler (HIGH)
- **Testing Use**: Cross-file reasoning, async/sync boundary detection

#### dataflowpipeline (⭐⭐⭐ Intermediate)
- **Domain**: ETL/data transformation framework
- **Files**: 6 Python files
- **Bugs**: 9 total (3 Critical, 3 High, 2 Medium, 1 Low)
- **Key Issues**:
  - State mutation during iteration (CRITICAL)
  - Rollback race condition (CRITICAL)
  - Division by zero in transforms (CRITICAL)
- **Testing Use**: Data pipeline analysis, state management, rollback logic

#### serviceregistry (⭐⭐⭐ Intermediate)
- **Domain**: Microservice discovery and health checking
- **Files**: 5 Python files
- **Bugs**: 6 total (2 Critical, 2 High, 1 Medium, 1 Low)
- **Key Issues**:
  - Shared cache race condition (CRITICAL)
  - Token storage vulnerability (CRITICAL)
  - Health check timeout issues (HIGH)
- **Testing Use**: Distributed system patterns, caching, service discovery

#### configworkflow (⭐⭐⭐⭐ Advanced)
- **Domain**: Configuration-driven workflow engine with plugins
- **Files**: 6 Python files
- **Bugs**: 7 total (2 Critical, 2 High, 2 Medium, 1 Low)
- **Key Issues**:
  - Plugin isolation failure → security breach (CRITICAL)
  - Config precedence bugs (CRITICAL)
  - Workflow state corruption (HIGH)
- **Testing Use**: Plugin architecture, workflow orchestration, configuration management

#### distributedcache (⭐⭐⭐⭐ Advanced)
- **Domain**: Distributed caching with Raft-inspired consensus
- **Files**: 5 Python files
- **Bugs**: 5 total (2 Critical, 2 High, 1 Medium)
- **Key Issues**:
  - Consensus protocol split-brain (CRITICAL)
  - Cache coherence violations (CRITICAL)
  - TTL race conditions (HIGH)
- **Testing Use**: Distributed algorithms, consensus protocols, cache coherence

#### eventworkflow (⭐⭐⭐⭐ Advanced)
- **Domain**: Event-driven workflows with saga pattern
- **Files**: 5 Python files
- **Bugs**: 5 total (2 Critical, 2 High, 1 Medium)
- **Key Issues**:
  - Compensation logic bugs → data inconsistency (CRITICAL)
  - Event ordering violations (CRITICAL)
  - Timeout handling errors (HIGH)
- **Testing Use**: Event sourcing, CQRS, saga patterns, compensation logic

#### pluginpipeline (⭐⭐⭐⭐ Advanced)
- **Domain**: Plugin-based data processing with hot-reload
- **Files**: 5 Python files
- **Bugs**: 5 total (2 Critical, 2 High, 1 Medium)
- **Key Issues**:
  - Hot-reload race conditions (CRITICAL)
  - Resource pool leaks (CRITICAL)
  - Backpressure handling failures (HIGH)
- **Testing Use**: Plugin systems, backpressure, stream processing, hot-reload

#### tenantgateway (⭐⭐⭐⭐ Advanced)
- **Domain**: Multi-tenant API gateway with rate limiting
- **Files**: 5 Python files
- **Bugs**: 5 total (2 Critical, 2 High, 1 Medium)
- **Key Issues**:
  - Tenant isolation bypass (CRITICAL)
  - Rate limit bypass via race condition (CRITICAL)
  - Circuit breaker state corruption (HIGH)
- **Testing Use**: Multi-tenancy, rate limiting, circuit breakers, API gateway patterns

#### servicemesh (⭐⭐⭐⭐⭐ Expert)
- **Domain**: Service mesh with discovery, load balancing, circuit breakers
- **Files**: 10 Python files (~1,400 LOC)
- **Bugs**: 5 total (2 Critical, 2 High, 1 Medium)
- **Key Issues**:
  - Circuit breaker state coordination failures (CRITICAL)
  - Load balancer race conditions (CRITICAL)
  - Health check propagation delays (HIGH)
- **Testing Use**: Service mesh patterns, distributed tracing, large codebase scalability

#### mlpipeline (⭐⭐⭐⭐⭐ Expert)
- **Domain**: ML pipeline with feature stores, model versioning, A/B testing
- **Files**: 10 Python files (~1,500 LOC)
- **Bugs**: 5 total (3 Critical, 2 High)
- **Key Issues**:
  - Data drift detection failures (CRITICAL)
  - Feature store consistency bugs (CRITICAL)
  - Model versioning race conditions (CRITICAL)
- **Testing Use**: ML pipelines, feature engineering, A/B testing, canary deployments

## Repository Structure

Each repository follows a consistent structure:

```
<repo-name>/
├── README.md               # Detailed bug descriptions, testing guidance
├── <repo-name>/           # Source code directory
│   ├── __init__.py
│   ├── *.py              # Python modules with intentional bugs
│   └── CLAUDE.md         # (Optional) Project-specific guidelines
└── expected_findings.yaml # (To be created) Ground truth for testing
```

## Testing Workflows

### 1. Code Review (`codereview`)

**Purpose**: Detect bugs across all severity levels

**Test Scenarios**:
- Security-focused review (sql_injection)
- Basic bug detection (async-api)
- Cross-file analysis (asynctaskqueue, dataflowpipeline)
- Complex system review (servicemesh, mlpipeline)

**Success Criteria**:
- Critical bug recall: ≥90%
- Overall recall: ≥80%
- Precision: ≥85%
- Severity accuracy: ≥90%

### 2. Chat (`chat`)

**Purpose**: Answer questions about codebase architecture and bugs

**Test Scenarios**:
- Architecture questions (dataflowpipeline, configworkflow)
- Bug explanations (asynctaskqueue deadlock)
- Code navigation (servicemesh, mlpipeline)
- Documentation context (sql_injection CLAUDE.md)

**Success Criteria**:
- Citation accuracy: ≥95%
- Multi-file tracing: ≥3 files cited
- Factual accuracy: ≥90%

### 3. Compare (`compare`)

**Purpose**: Get diverse perspectives on complex issues

**Test Scenarios**:
- Bug severity assessment (async-api, asynctaskqueue)
- Architecture evaluation (servicemesh, mlpipeline)
- Security analysis (sql_injection)

**Success Criteria**:
- Completion rate: 100%
- Critical finding agreement: ≥80%
- Insight diversity: ≥3 unique insights

### 4. Debate (`debate`)

**Purpose**: Resolve ambiguous design decisions through structured discussion

**Test Scenarios**:
- Bug fix approaches (asynctaskqueue deadlock)
- Architecture decisions (distributedcache consensus protocol)
- Performance vs. safety trade-offs (eventworkflow)

**Success Criteria**:
- Two-step completion: 100%
- Trade-off identification: ≥3 trade-offs
- Consensus reached: Clear recommendation

## Golden Dataset Standard

Each repository should include an `expected_findings.yaml` file for objective testing:

```yaml
metadata:
  repo_name: async-api
  difficulty: 1
  total_bugs: 8

critical_bugs:
  - id: async-api-c1
    file: storage.py
    line: 45
    type: path_injection
    category: security
    description: "Unsanitized filename allows directory traversal"
    severity: CRITICAL
    keywords: ["unsanitized", "filename", "path", "injection"]

# ... more bugs by severity
```

## Testing Implementation

### Phase 1: Basic Repos (Weeks 1-2)
- Repos: async-api, asynctaskqueue, sql_injection
- Tests: 9 scenarios (3 repos × 3 workflows)
- Goal: Validate core functionality
- Golden datasets: Required ✅

### Phase 2: Intermediate Repos (Weeks 3-4)
- Repos: dataflowpipeline, serviceregistry, configworkflow
- Tests: 6-12 scenarios
- Goal: Cross-file reasoning, architectural understanding
- Golden datasets: Required ✅

### Phase 3: Advanced Repos (Weeks 5-6)
- Repos: distributedcache, eventworkflow, pluginpipeline, tenantgateway
- Tests: 16-32 scenarios
- Goal: Distributed systems, advanced patterns
- Golden datasets: Phase 3 deliverable

### Phase 4: Expert Repos (Weeks 7-8)
- Repos: servicemesh, mlpipeline
- Tests: 16-24 scenarios
- Goal: Maximum complexity, scalability validation
- Golden datasets: Phase 4 deliverable

## Performance Targets

### Per-Repo Timing
- **Small repos** (⭐-⭐⭐): 10-30 seconds
- **Medium repos** (⭐⭐⭐-⭐⭐⭐⭐): 30-60 seconds
- **Large repos** (⭐⭐⭐⭐⭐): 60-120 seconds

### Cost Targets
- **Per-test**: ~$0.001-$0.004 (using gpt-5-mini)
- **Full suite**: <$5 per run
- **CI strategy**:
  - PR checks: Phase 1 only (~$0.10)
  - Nightly: Full suite (~$5)

## Running Tests

```bash
# Install dependencies
uv sync

# Run Phase 1 tests only (fast PR checks)
RUN_E2E=1 pytest tests/integration/test_repos_phase1.py -n auto -v

# Run security tests only
RUN_E2E=1 pytest tests/integration/ -m security -v

# Run all repo integration tests (nightly)
RUN_E2E=1 pytest tests/integration/test_repos*.py -n auto -v

# Skip slow/expensive tests
pytest tests/integration/ -m "not slow and not expensive"
```

## Contributing Test Repositories

### Adding a New Test Repository

1. **Create repository structure**:
   ```bash
   mkdir -p tests/data/repos/<repo-name>/<repo-name>
   ```

2. **Add intentionally buggy code**:
   - Include 5-10 Python files
   - Document bugs inline with comments
   - Cover multiple severity levels

3. **Create README.md**:
   - Document all known bugs with locations
   - Specify severity levels (CRITICAL, HIGH, MEDIUM, LOW)
   - Provide testing guidance

4. **Create expected_findings.yaml**:
   - List all bugs with precise locations
   - Include keywords for fuzzy matching
   - Categorize by severity

5. **Add test scenarios**:
   - Update test scenario matrix in `docs/repos-v2.md`
   - Implement integration tests
   - Validate metrics

### Quality Checklist

- [ ] README.md with complete bug descriptions
- [ ] expected_findings.yaml with all bugs catalogued
- [ ] Bugs span multiple severity levels
- [ ] Code is realistic and domain-relevant
- [ ] Inline comments document vulnerabilities
- [ ] Testing scenarios defined
- [ ] Difficulty rating assigned

## Related Documentation

- **Testing Plan**: `docs/repos-v2.md` - Comprehensive integration testing strategy
- **Test Implementation**: `tests/integration/test_repos_*.py` - Test code
- **Validation Helpers**: `tests/integration/helpers/validation.py` - Metric calculation
- **Project Setup**: `CLAUDE.md` - Development guidelines

## Notes

⚠️ **Warning**: All code in these repositories is **intentionally vulnerable and buggy**. Never use these patterns in production code. These repositories exist solely for testing Multi-MCP's analysis capabilities.

## License

These test repositories are part of the Multi-MCP project and are provided for testing purposes only.
