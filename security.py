"""
Privacy & Security Utilities
- Argon2id Password Hashing
- Personal Identifiable Information (PII) Masking
- Rate Limiting and Brute Force Mitigation
- Secure Session Management
- Audit Logging
"""
import re
import secrets
import hashlib
import time
from datetime import datetime, timezone, timedelta
from db import get_db

# Try importing argon2, fallback to PBKDF2-HMAC-SHA256 if needed
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    ph = PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16
    )
    USE_ARGON2 = True
except ImportError:
    USE_ARGON2 = False

def hash_password(password: str) -> str:
    """Securely hash password using Argon2id or fallback to PBKDF2."""
    if USE_ARGON2:
        return ph.hash(password)
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"pbkdf2:sha256:100000${salt}${hashed.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored hash."""
    if USE_ARGON2 and not hashed.startswith('pbkdf2:'):
        try:
            return ph.verify(hashed, password)
        except Exception:
            return False
    elif hashed.startswith('pbkdf2:'):
        parts = hashed.split('$')
        if len(parts) == 3:
            salt = parts[1]
            check = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
            return secrets.compare_digest(check.hex(), parts[2])
    return False

# ==============================================================================
# PII Masking Utilities
# ==============================================================================

def mask_national_id(nid: str) -> str:
    """
    Format 13-digit Thai national ID:
    Example input: 1234567890123
    Masked: 1-2345-****-**-3
    """
    if not nid:
        return ""
    clean = re.sub(r'\D', '', str(nid))
    if len(clean) == 13:
        return f"{clean[0]}-{clean[1:5]}-****-**-{clean[-1]}"
    return clean[:2] + "****" + clean[-2:] if len(clean) >= 4 else "****"

def mask_phone(phone: str) -> str:
    """
    Format Phone:
    Example input: 0812345678
    Masked: 08X-XXX-5678
    """
    if not phone:
        return ""
    clean = re.sub(r'\D', '', str(phone))
    if len(clean) == 10:
        return f"{clean[:2]}X-XXX-{clean[-4:]}"
    elif len(clean) == 9:
        return f"{clean[:2]}X-XX-{clean[-4:]}"
    return clean[:3] + "XXX" + clean[-3:] if len(clean) >= 6 else "XXX-XXXX"

def mask_email(email: str) -> str:
    """
    Format Email:
    Example input: somchai@example.ac.th
    Masked: s***@example.ac.th
    """
    if not email or '@' not in email:
        return ""
    user, domain = email.split('@', 1)
    if len(user) <= 1:
        masked_user = user + "***"
    elif len(user) == 2:
        masked_user = user[0] + "***"
    else:
        masked_user = user[0] + "***" + user[-1]
    return f"{masked_user}@{domain}"

def mask_name(name: str) -> str:
    """
    Format Name for applicant check:
    Example input: นายสมชาย ใจดี
    Masked: นายส**าย ใ**ดี
    """
    if not name:
        return ""
    parts = name.strip().split()
    masked_parts = []
    for part in parts:
        if len(part) <= 2:
            masked_parts.append(part[0] + "*")
        else:
            masked_parts.append(part[0] + "**" + part[-1])
    return " ".join(masked_parts)

def mask_address(addr: str) -> str:
    """Mask detailed street/house address to preserve general privacy."""
    if not addr:
        return ""
    parts = addr.split()
    if len(parts) > 2:
        return "*** " + " ".join(parts[-2:])
    return "*** [ที่อยู่ถูกปิดบังตามนโยบายความเป็นส่วนตัว]"

def mask_application_dict(app: dict, allow_sensitive: bool = False) -> dict:
    """Return application data with appropriate masking applied based on permissions."""
    if allow_sensitive:
        return {**app, "is_masked": False}
    
    masked = dict(app)
    masked["national_id"] = mask_national_id(app.get("national_id", ""))
    masked["phone"] = mask_phone(app.get("phone", ""))
    masked["email"] = mask_email(app.get("email", ""))
    masked["address"] = mask_address(app.get("address", ""))
    masked["is_masked"] = True
    return masked

# ==============================================================================
# Rate Limiting & Brute Force Protection
# ==============================================================================

def check_login_rate_limit(key: str, max_attempts: int = 5, window_seconds: int = 300) -> bool:
    """
    Returns True if user/IP is ALLOWED to attempt login.
    Returns False if currently LOCKED OUT.
    """
    conn = get_db()
    cursor = conn.cursor()
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat()
    
    cursor.execute("""
        SELECT COUNT(*) as failures FROM login_attempts 
        WHERE username_or_ip = ? AND success = 0 AND attempt_time > ?
    """, (key, cutoff))
    
    row = cursor.fetchone()
    failures = row['failures'] if row else 0
    conn.close()
    return failures < max_attempts

def record_login_attempt(key: str, success: bool):
    """Record login attempt in database."""
    conn = get_db()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO login_attempts (username_or_ip, attempt_time, success)
        VALUES (?, ?, ?)
    """, (key, now_str, 1 if success else 0))
    conn.commit()
    conn.close()

# ==============================================================================
# Audit Logging
# ==============================================================================

def log_audit(actor_id: str, actor_role: str, action: str, resource_type: str, resource_id: str = None, details: str = None, ip: str = None, user_agent: str = None):
    """Write an immutable audit log record."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        now_str = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_role, action, resource_type, resource_id, details, ip_address, user_agent, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (actor_id, actor_role, action, resource_type, resource_id, details, ip, user_agent, now_str))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AUDIT LOG ERROR] Failed to write log: {e}")
