# Buggy Sample Repo 1 - Async API with Storage and Config

This repository simulates a small async service that accepts items over an HTTP-style API, validates them, and stores them on disk using a storage abstraction. It also keeps a simple in-memory cache of the last processed item.

The code is organized as a lightweight imitation of a FastAPI-style stack: an API layer, a service layer, configuration helpers, data models, and a storage component.

## Structure

- `repo1/api.py`
- `repo1/service.py`
- `repo1/models.py`
- `repo1/config.py`
- `repo1/storage.py`

## Severity Definitions

- 🔴 CRITICAL
- 🟠 HIGH
- 🟡 MEDIUM
- 🟢 LOW

## 🔴 Critical Issues
1. Unsanitized user-controlled filenames.
2. Race-prone in-memory cache.

## 🟠 High Issues
1. Nullability mismatch.
2. Exception handling hides root causes.

## 🟡 Medium Issues
1. Conflicting configuration defaults.
2. Implicit type assumptions.

## 🟢 Low Issues
1. Inconsistent naming.
2. Mixed responsibilities.
