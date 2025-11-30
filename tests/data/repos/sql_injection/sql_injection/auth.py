"""Authentication module with security vulnerabilities."""

import sqlite3


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user against database.

    SECURITY ISSUE: SQL Injection vulnerability!
    User input is directly concatenated into SQL query.
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # VULNERABILITY: SQL Injection
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor.execute(query)

    result = cursor.fetchone()
    conn.close()

    return result is not None


def create_user(username: str, password: str) -> bool:
    """Create new user account.

    SECURITY ISSUES:
    1. Password stored in plain text (no hashing)
    2. SQL Injection vulnerability
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # VULNERABILITY: Plain text password storage
    # VULNERABILITY: SQL Injection
    query = f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')"

    try:
        cursor.execute(query)
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def get_user_data(user_id: int):
    """Get user data by ID.

    SECURITY ISSUE: Using SELECT * exposes all columns
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # VULNERABILITY: SELECT * can expose sensitive data
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

    result = cursor.fetchone()
    conn.close()

    return result


def check_password_strength(password: str) -> bool:
    """Check if password meets minimum requirements.

    SECURITY ISSUE: Weak password policy
    """
    # VULNERABILITY: Too permissive password policy
    return len(password) >= 4  # Should be at least 12 characters!
