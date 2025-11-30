# SQL Injection Example

## Overview

This repository contains intentionally vulnerable authentication code designed to test Multi-MCP's security analysis capabilities. It serves as a security-focused test case for validating OWASP Top 10 vulnerability detection.

**Difficulty**: ⭐ (Basic)
**Domain**: Authentication & Security
**Files**: 1 Python file
**Focus**: OWASP Top 10 vulnerabilities

## Purpose

This test repository is used to verify that Multi-MCP workflows can:
- Detect SQL injection vulnerabilities
- Identify insecure password storage practices
- Flag weak security policies
- Recognize data exposure issues
- Reference security standards from CLAUDE.md

## Directory Structure

```
sql_injection/
├── README.md           # This file
├── auth.py             # Vulnerable authentication module
└── CLAUDE.md           # Security standards and guidelines
```

## Known Vulnerabilities

### 🔴 CRITICAL Issues

#### 1. SQL Injection in Authentication (auth.py:17)
**Function**: `authenticate_user()`
**Type**: CWE-89: SQL Injection
**Description**: User input is directly concatenated into SQL query without parameterization.

```python
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
cursor.execute(query)
```

**Impact**: Attacker can bypass authentication, extract data, or modify database.
**Example Attack**: `username = "admin' --"` bypasses password check.

#### 2. SQL Injection in User Creation (auth.py:38)
**Function**: `create_user()`
**Type**: CWE-89: SQL Injection
**Description**: User input concatenated directly into INSERT statement.

```python
query = f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')"
```

**Impact**: Database manipulation, code injection.

#### 3. Plain Text Password Storage (auth.py:38)
**Function**: `create_user()`
**Type**: CWE-256: Unprotected Storage of Credentials
**Description**: Passwords stored without hashing or encryption.

```python
# Password stored directly without hashing
INSERT INTO users (username, password) VALUES ('{username}', '{password}')
```

**Impact**: Complete credential compromise if database is breached.

### 🟠 HIGH Issues

#### 4. Weak Password Policy (auth.py:73)
**Function**: `check_password_strength()`
**Type**: CWE-521: Weak Password Requirements
**Description**: Password policy only requires 4 characters.

```python
return len(password) >= 4  # Should be at least 12 characters!
```

**Impact**: Easily brute-forceable passwords.

### 🟡 MEDIUM Issues

#### 5. Data Exposure via SELECT * (auth.py:59)
**Function**: `get_user_data()`
**Type**: CWE-213: Exposure of Sensitive Information
**Description**: Using SELECT * exposes all columns including potentially sensitive fields.

```python
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

**Impact**: Unintended exposure of sensitive user data (hashed passwords, tokens, etc.).

## Bug Summary

| Severity | Count | Issues |
|----------|-------|--------|
| 🔴 CRITICAL | 3 | SQL Injection (×2), Plain Text Passwords |
| 🟠 HIGH | 1 | Weak Password Policy |
| 🟡 MEDIUM | 1 | SELECT * Data Exposure |
| **Total** | **5** | |

## Security Standards (CLAUDE.md)

The repository includes security guidelines that tests should verify are referenced:
- Always use parameterized queries
- Never store passwords in plain text
- Follow OWASP Top 10 guidelines

## Correct Implementations

### ✅ Parameterized Queries
```python
# CORRECT: Use parameterized queries
cursor.execute(
    "SELECT * FROM users WHERE username = ? AND password = ?",
    (username, password_hash)
)
```

### ✅ Password Hashing
```python
# CORRECT: Hash passwords before storage
import hashlib
password_hash = hashlib.sha256(password.encode()).hexdigest()
cursor.execute(
    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
    (username, password_hash)
)
```

### ✅ Strong Password Policy
```python
# CORRECT: Enforce strong password requirements
def check_password_strength(password: str) -> bool:
    return (
        len(password) >= 12 and
        any(c.isupper() for c in password) and
        any(c.islower() for c in password) and
        any(c.isdigit() for c in password) and
        any(c in "!@#$%^&*" for c in password)
    )
```

### ✅ Explicit Column Selection
```python
# CORRECT: Select only needed columns
cursor.execute(
    "SELECT id, username, email FROM users WHERE id = ?",
    (user_id,)
)
```

## Testing Usage

### Code Review Workflow
```python
request = CodeReviewRequest(
    base_path="tests/data/repos/sql_injection",
    step_number=1,
    content="Perform security audit focusing on OWASP Top 10",
)
```

**Expected Results**:
- ✅ Detect all 3 CRITICAL vulnerabilities
- ✅ Classify SQL injection as CRITICAL
- ✅ Flag plain text password storage
- ✅ Identify weak password policy
- ✅ Find data exposure issue

### Chat Workflow
```python
request = ChatRequest(
    base_path="tests/data/repos/sql_injection",
    content="What security standards should be followed?",
)
```

**Expected Results**:
- ✅ Reference CLAUDE.md security standards
- ✅ Mention parameterized queries
- ✅ Cite OWASP Top 10

### Compare Workflow
```python
request = CompareRequest(
    base_path="tests/data/repos/sql_injection",
    models=["gpt-5-mini", "claude-haiku-4.5", "gemini-2.5-flash"],
    content="Identify all security vulnerabilities in this code",
)
```

**Expected Results**:
- ✅ All models find SQL injection
- ✅ 100% agreement on CRITICAL severity for SQL injection
- ✅ Minimum 3 unique security findings across models

### Debate Workflow
```python
request = DebateRequest(
    base_path="tests/data/repos/sql_injection",
    models=["gpt-5-mini", "claude-haiku-4.5"],
    content="What is the most critical security issue to fix first?",
)
```

**Expected Results**:
- ✅ Models debate priority: SQL injection vs. plain text passwords
- ✅ Structured two-step debate (independent + critique)
- ✅ Clear consensus or voting result

## Success Criteria

### Code Review
- **Recall (Critical)**: 100% (find all 3 CRITICAL issues)
- **Recall (All)**: ≥80% (find at least 4/5 issues)
- **Precision**: ≥90% (minimal false positives)
- **Severity Accuracy**: 100% (correct CRITICAL classification for SQL injection)

### Chat
- **Citation Accuracy**: ≥95% (valid file:line references)
- **Context Usage**: Reference CLAUDE.md security standards
- **Factual Accuracy**: Correctly explain OWASP principles

### Compare
- **Completion Rate**: 100% (all models complete)
- **Critical Agreement**: 100% (all agree SQL injection is CRITICAL)
- **Unique Findings**: ≥3 distinct security issues identified

### Debate
- **Completion**: Both steps complete successfully
- **Trade-offs**: ≥2 security trade-offs discussed
- **Consensus**: Clear recommendation on fix priority

## References

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE-89**: SQL Injection
- **CWE-256**: Unprotected Storage of Credentials
- **CWE-521**: Weak Password Requirements
- **CWE-213**: Exposure of Sensitive Information

## Notes

This code is **intentionally insecure** for testing purposes. Never use this pattern in production code. Always:
- Use parameterized queries or ORM frameworks
- Hash passwords with bcrypt, argon2, or similar
- Enforce strong password policies (≥12 chars, complexity)
- Select only required columns
- Follow OWASP secure coding guidelines
