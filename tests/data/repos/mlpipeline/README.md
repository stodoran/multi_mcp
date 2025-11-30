# Repo10: MLPipeline

**Difficulty:** ⭐⭐⭐⭐⭐ (Advanced)
**Files:** 10
**LOC:** ~1,500
**Bugs:** 5 (3 CRITICAL, 2 HIGH)

## Overview

Machine learning pipeline with feature stores, model versioning, data drift detection, A/B testing, and model serving. Implements online and offline feature computation, model training with hyperparameter tracking, and gradual rollout with canary deployments.

## Architecture

- `pipeline.py` (180 LOC) - End-to-end pipeline orchestrator
- `feature_store.py` (170 LOC) - Feature computation and caching
- `model_registry.py` (160 LOC) - Model versioning with S3 + database
- `drift_detector.py` (150 LOC) - Distribution drift detection
- `trainer.py` (160 LOC) - Model training
- `serving.py` (140 LOC) - Online prediction serving
- `ab_testing.py` (130 LOC) - A/B testing controller
- `preprocessor.py` (140 LOC) - Data preprocessing
- `validator.py` (120 LOC) - Data validation
- `metrics_tracker.py` (150 LOC) - Metrics tracking

## Bugs

### Bug #1 (CRITICAL): Training-Serving Skew from Feature Computation Mismatch
**Severity:** CRITICAL
**Files:** `feature_store.py:67` → `preprocessor.py:34` → `trainer.py:89` → `serving.py:123` → `validator.py:78`

**Description:**
Feature store has two code paths: offline (batch) for training uses Pandas `pd.cut()`, online (streaming) for serving uses Python `bisect.bisect_left()`. These produce DIFFERENT results for boundary values (ages 18, 35, 50).

**Root Cause:**
- `preprocessor.py:42` - Offline: `pd.cut(df['age'], bins=[0, 18, 35, 50, 100])` - right-inclusive: (0, 18], (18, 35], ...
- `preprocessor.py:67` - Online: `bisect.bisect_left([18, 35, 50, 100], age)` - left-inclusive: [18, 35), [35, 50), ...
- `config/pipeline.yaml` - Split configs: `binning_method_offline: pandas_cut`, `binning_method_online: bisect_left`

**Boundary Behavior:**
- Pandas: age=18 → bucket 0 (in range (0, 18])
- Bisect: age=18 → bucket 1 (in range [18, 35))

**Manifestation:**
Model trains on Pandas features, serves with bisect features. For users aged exactly 18, 35, or 50, the model sees different feature values in production, causing prediction drift.

**Decoy Patterns:**
1. Validation at `validator.py:78`: Uses KS test on overall distributions, which passes even with boundary mismatches
2. Feature parity test uses ages [25, 42, 67, 19, 33] - avoids exact boundaries
3. Drift attributed to "seasonal signup patterns" at `drift_detector.py:123`

---

### Bug #2 (CRITICAL): Data Leakage from Future Features in Training
**Severity:** CRITICAL
**Files:** `feature_store.py:89` → `preprocessor.py:134` → `trainer.py:78` → `pipeline.py:45`

**Description:**
Feature store computes `user_total_purchases` WITHOUT time filtering in training mode. Training example at time T includes purchases that happened AFTER T (future leakage). Model learns circular reasoning: "users with 10 purchases likely to purchase" (they already did!).

**Root Cause:**
- `feature_store.py:89` - `filter_by_time=False` in training
- `preprocessor.py:134` - Comment: "Use all data for training to maximize signal"
- Database query: `SELECT COUNT(*) FROM purchases WHERE user_id = ?` (no time filter!)
- Serving correctly filters: `WHERE user_id = ? AND timestamp <= ?`

**Manifestation:**
Model trained on inflated features (future data), but production computes features correctly (past only). Model underpredicts conversion by 30%.

**Decoy Patterns:**
1. Temporal validation at `validator.py:134` checks feature timestamp ≤ label timestamp, but doesn't check if aggregates include future data
2. Comment at `feature_store.py:89` suggests intentional "maximize signal"
3. Test doesn't verify purchases are filtered to timestamp < event time

---

### Bug #3 (CRITICAL): Feature Store Staleness from TTL Misconfiguration
**Severity:** CRITICAL
**Files:** `feature_store.py:89` → `serving.py:45` → `preprocessor.py:67` → `drift_detector.py:201` → `validator.py:156`

**Description:**
Training pipeline updates features every hour with 6-hour aggregation window. Model training runs daily (6 hours). During training, feature snapshot is fixed. In production, serving uses cache with TTL=3600 (1 hour). After deployment, cache expires but features are recomputed with 1-hour aggregation window (not 6-hour).

**Root Cause:**
- `feature_store.py:23` - `CACHE_TTL = 3600` (1 hour)
- `preprocessor.py` - Training: `aggregation_window = 21600` (6 hours), Serving: `aggregation_window = 3600` (1 hour)
- `config/pipeline.yaml` - `feature_ttl: 3600`, `batch_window: 21600`

**Temporal Diagram:**
```
Training (daily, 6h duration):
  T=0: Start, snapshot features [T-6h to T]
  T=6h: Finish, model trained on 6-hour window

Deployment (T+6h):
  Cache warmed with features at T+6h, TTL=1h

Serving:
  T+6h to T+7h: Serve cached features (1-hour window)
  T+7h+: Cache expired, compute fresh (rolling 1-hour window)
```

**Manifestation:**
Model expects 6-hour window distribution, serving provides 1-hour window. Drift detector sees shift but blames "concept drift" not serving-training skew.

**Decoy Patterns:**
1. Cache warming comment looks correct but doesn't address window mismatch
2. Feature freshness validation only runs in batch jobs, not online serving
3. Drift detection increases threshold after TTL, masking the skew

---

### Bug #4 (HIGH): Model Version Mismatch from Registry Race Condition
**Severity:** HIGH
**Files:** `model_registry.py:89` → `serving.py:45` → `ab_testing.py:123` → `pipeline.py:78`

**Description:**
Model registry stores models in S3 with metadata in database. When new model is deployed: (1) Upload model to S3 (slow, 30 seconds), (2) Update database (fast, 100ms). Race condition: Database updates BEFORE S3 upload completes. Serving nodes see new version in database, try to download from S3, get 404.

**Root Cause:**
- `model_registry.py:89` - `upload_task = s3.upload_async(model_path)` - fire and forget!
- `model_registry.py:102` - `db.update_version(model_id, new_version)` - immediate
- `serving.py:67` - Download attempts before upload completes
- `serving.py:78` - Retry: 3 times × 1s delay = 3s total, but upload takes 30s
- `ab_testing.py:123` - Routes traffic based on `db_version` not `loaded_version`

**Manifestation:**
Serving nodes fall back to cached model (N-1) but metrics show version N. A/B test results corrupted—both control and experiment serve same model.

**Decoy Patterns:**
1. Atomic transaction comment at `model_registry.py:89` - database update is atomic but doesn't wait for S3
2. S3 pre-check exists in serving code but not registry code
3. Version validation logs warning but continues anyway

---

### Bug #5 (HIGH): Concept Drift Undetected Due to Binned Comparison
**Severity:** HIGH
**Files:** `drift_detector.py:45` → `metrics_tracker.py:89` → `feature_store.py:156` → `validator.py:178`

**Description:**
Drift detector compares training vs production using KS test on binned histograms (20 bins). Feature `user_age` shifted from mean=35 to mean=38. This is significant drift, but binning masks it. With bins [0-5, 5-10, ..., 95-100], both distributions look similar. KS test on binned data: p=0.3 (no drift). KS test on raw data: p=0.001 (significant drift).

**Root Cause:**
- `drift_detector.py:67` - Fixed `NUM_BINS = 20`
- `drift_detector.py:112` - KS test on binned histograms: `ks_2samp(binned_train, binned_prod)`
- Age range 0-100 with 20 bins → 5-year bins
- Shift from mean=35 (bin 7) to mean=38 (still bin 7)

**Manifestation:**
Binning loses information about within-bin variance. Mean shift from 35 to 38 (0.3 std deviations) is masked because both fall in same bin.

**Statistical Analysis:**
```
Training: mean=35, std=10, N=1M
Production: mean=38, std=10, N=1M

Raw KS test: p ≈ 0.001 (significant)
Binned KS test: p ≈ 0.3 (not significant)
```

**Decoy Patterns:**
1. Statistical power comment claims bins preserve power, but synthetic test used dramatic shifts
2. Adaptive binning increases bins for high variance, not for shift type
3. Sensitivity test uses mean shift 30 → 60 (6 std), masking subtle 35 → 38 shift

---

## Configuration Files

### `config/pipeline.yaml`
```yaml
cache:
  feature_ttl: 3600  # 1 hour - BUG #3: Mismatch with training window

training:
  batch_window: 21600  # 6 hours - BUG #3: Different from serving
  use_future_features: true  # BUG #2: Causes data leakage

serving:
  aggregation_window: 3600  # 1 hour - BUG #3: Different from training
  download_timeout: 5  # seconds - BUG #4: Too short for 30s upload

registry:
  async_upload: true  # BUG #4: Fire-and-forget S3 uploads
  wait_for_upload: false  # BUG #4: Don't wait for S3

drift:
  num_bins: 20  # BUG #5: Fixed binning loses statistical power

features:
  binning_method_offline: pandas_cut  # BUG #1: Right-inclusive
  binning_method_online: bisect_left  # BUG #1: Left-inclusive
```

## Testing Challenges

These bugs evade standard testing because:

- **Unit tests** mock infrastructure (cache never expires, S3 uploads instant)
- **Small data volumes** miss boundary value issues (tests avoid ages 18, 35, 50)
- **Synthetic data** lacks real-world temporal dimension
- **Development configs** disable problematic features
- **Dramatic test shifts** hide subtle real-world drift (mean 30→60 vs 35→38)
- **Short runs** don't see cache expiry, memory leaks, staleness
- **Mocked S3** has instant uploads, not 30-second delays

## Detection Requirements

- Understanding of training-serving skew and feature engineering
- Knowledge of temporal data leakage and point-in-time correctness
- Familiarity with cache TTL, warmup, and freshness semantics
- Understanding of statistical drift detection and binning effects
- Knowledge of model versioning and deployment patterns
- Understanding of A/B testing and version routing
- Familiarity with boundary semantics (inclusive/exclusive)
- Configuration-driven bug detection (YAML + code)

## Boundary Value Analysis

### Bug #1 Test Cases
```python
# Training (Pandas pd.cut, right-inclusive):
age=17 → bucket 0  # (0, 18]
age=18 → bucket 0  # (0, 18]  ← BOUNDARY
age=19 → bucket 1  # (18, 35]

# Serving (bisect_left, left-inclusive):
age=17 → bucket 0  # [0, 18)
age=18 → bucket 1  # [18, 35)  ← BOUNDARY (different!)
age=19 → bucket 1  # [18, 35)
```

Ages 18, 35, 50 exhibit training-serving skew due to boundary semantics.
