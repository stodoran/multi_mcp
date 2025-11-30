# DataFlowPipeline

## Bug Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 3 |
| 🟠 High | 3 |
| 🟡 Medium | 2 |
| 🟢 Low | 1 |
| **Total** | **9** |

## Description

DataFlowPipeline is a flexible data transformation framework that processes records through configurable validation, transformation, and error handling stages. The framework supports building complex data pipelines by chaining together validators, transformers, and loaders in a composable architecture.

The system provides base classes for creating custom pipeline stages, built-in validators for type and range checking, transformation operators for data manipulation, error handlers with rollback capabilities, and data models for structured records. It supports both sequential and parallel execution modes for high-throughput scenarios.

Users can construct pipelines by combining stages, validate incoming data against schemas, transform and enrich records through multiple operations, handle errors with automatic rollback of previous stages, and load processed data to final destinations. The framework is designed for ETL workloads, data quality pipelines, and real-time data processing applications.

## Directory Structure

```
repo2/
  README.md
  dataflowpipeline/
    __init__.py           # Package exports
    pipeline.py           # Pipeline orchestrator and execution engine
    stages.py             # Base Stage class and concrete implementations
    validators.py         # Data validation logic and validators
    transforms.py         # Transform operators for data manipulation
    handlers.py           # Error handling and rollback logic
    models.py             # Data models and record structures
```

## Component Overview

- **pipeline.py**: Orchestrates record flow through multiple stages. Manages execution order, error handling delegation, and supports both sequential and parallel processing modes. Tracks processing metrics and coordinates stage interactions.

- **stages.py**: Defines the base Stage abstraction and concrete implementations (ValidatorStage, TransformStage, LoaderStage). Each stage processes records and supports rollback operations for error recovery.

- **validators.py**: Provides validation logic including type checking, range validation, and schema version validation. Validators return validated data or indicate failures for the pipeline to handle.

- **transforms.py**: Implements transformation operators that modify record data. Includes scaling, filtering, division, and currency conversion transforms. Each transform receives input data and returns modified output.

- **handlers.py**: Manages error handling with support for rollback operations across all stages. Includes retry logic and coordinated cleanup when pipeline processing fails.

- **models.py**: Defines data structures for pipeline records including base Record class and specialized FinancialRecord for monetary amounts. Handles type coercion and field validation.

## Known Issues

⚠️ **This repository contains intentional bugs for testing bug detection systems.**

### 🔴 Critical Issues (3 total)

1. **In-place mutation causing data corruption in parallel execution**: Transform operators modify input dictionaries directly using key assignment instead of creating copies. The pipeline assumes immutability and reuses the same dictionary reference across parallel transformation stages running in concurrent threads. Multiple stages simultaneously mutate shared data causing unpredictable corruption and race conditions.

2. **Silent numeric precision loss in financial calculations**: Data models define monetary amount fields as integers for storage. Transform operators perform division operations that return floating-point values with fractional cents. The model's automatic type coercion silently truncates these fractions to integers, causing cumulative precision loss that violates financial calculation requirements and can result in significant discrepancies.

3. **Transitive None propagation causing crashes deep in pipeline**: Validators return None to indicate validation failure. The pipeline checks whether results equal the boolean False, but None is not False, so None values pass the check. These None values propagate to transformation stages which attempt to call dictionary methods on them, triggering AttributeError crashes with confusing stack traces far from the actual validation failure point.

### 🟠 High Issues (3 total)

4. **Partial rollback leaving data in inconsistent state**: Error handlers attempt to rollback all pipeline stages when failures occur. However, only some stage types implement the rollback method properly—ValidatorStage and TransformStage have working implementations but LoaderStage uses only a no-op base class implementation. When errors occur after loading, validation and transform state is cleared but loaded data remains, breaking referential integrity.

5. **Schema version drift between producers and consumers**: Data models were upgraded to version 2 adding a currency field with default value. Transform operators still emit version 1 records without this field. Validators silently accept both versions without enforcement. Downstream consumers expecting version 2 records encounter missing field errors when processing version 1 output.

6. **Decimal precision loss in transformation chains**: Transform operators receive Decimal values for currency calculations but implicitly convert them to float during intermediate operations. Each conversion step loses precision beyond 2 decimal places. Through multi-stage transformation chains, accumulated precision loss violates requirements for financial data integrity.

### 🟡 Medium Issues (2 total)

7. **Validator execution order dependencies causing confusing errors**: Validators expect to execute in specific order—type validators must run before range validators to ensure proper types for comparison. The pipeline allows arbitrary validator ordering through configuration. When range validators run before type validators, cryptic type mismatch errors occur instead of clear validation failures about incorrect data types.

8. **Inconsistent metric tracking across pipeline boundaries**: The pipeline tracks "records processed" counting all input records. Individual stages track "records passed" counting only successfully processed records. When validation failures occur, these metrics diverge significantly. Monitoring dashboards display inconsistent totals making it impossible to accurately track throughput and failure rates.

### 🟢 Low Issues (1 total)

9. **Misleading error message obscuring root cause**: Transform operators raise ValueError with message "Invalid transform" when receiving wrong input data types. The message wording suggests the transform configuration is invalid rather than the input data being malformed. Developers waste time investigating transform setup instead of data schema issues.

## Expected Behavior

The pipeline should process records through stages without data corruption, maintaining immutability by creating copies when needed. Numeric operations should preserve precision appropriate for the data type, especially for financial calculations. Validation failures should be clearly propagated without allowing invalid data to reach transformation stages. All stages should fully participate in rollback operations to maintain data consistency. Schema versions should be explicitly validated and enforced. Metrics should be consistent across all components.

## Usage Example

```python
from dataflowpipeline import (
    Pipeline, ValidatorStage, TransformStage, LoaderStage,
    TypeValidator, RangeValidator, ScaleTransform,
    RollbackHandler, FinancialRecord
)

# Create validators
type_validator = TypeValidator({'amount': int, 'customer_id': str})
range_validator = RangeValidator('amount', min_val=0, max_val=1000000)

# Create transforms
scale_transform = ScaleTransform('amount', factor=1.08)  # Add 8% tax

# Build pipeline stages
validator_stage = ValidatorStage(
    'validation',
    [type_validator, range_validator]
)
transform_stage = TransformStage('transform', [scale_transform])
loader_stage = LoaderStage('loader', storage_path='./output')

# Create pipeline
stages = [validator_stage, transform_stage, loader_stage]
error_handler = RollbackHandler(stages)
pipeline = Pipeline(stages, error_handler, parallel=False)

# Process records
records = [
    {'record_id': '1', 'amount': 100, 'customer_id': 'C001'},
    {'record_id': '2', 'amount': 250, 'customer_id': 'C002'}
]

results = pipeline.process_batch(records)
print(f"Processed {len(results)} records")
print(f"Total processed: {pipeline.get_processed_count()}")
```
