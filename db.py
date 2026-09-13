"""
Database Schema & Initialization for RERU Privacy & Admissions System
Uses SQLite with WAL mode, parameterized queries, and strict role/permission models.
"""
import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'reru_admissions.db')

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Roles Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT
    );
    """)

    # 2. Permissions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS permissions (
        id TEXT PRIMARY KEY,
        description TEXT NOT NULL
    );
    """)

    # 3. Role Permissions Join Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS role_permissions (
        role_id TEXT NOT NULL,
        permission_id TEXT NOT NULL,
        PRIMARY KEY (role_id, permission_id),
        FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
        FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
    );
    """)

    # 4. Users Table (Super Admins, Admins, Staff)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role_id TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        last_login_at TEXT,
        FOREIGN KEY (role_id) REFERENCES roles(id)
    );
    """)

    # 5. Sessions Table (Server-side Session Control)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        ip_address TEXT,
        user_agent TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 6. Login Attempts Table (Brute Force Protection)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS login_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username_or_ip TEXT NOT NULL,
        attempt_time TEXT NOT NULL,
        success INTEGER NOT NULL
    );
    """)

    # 7. Applications Table (Confidential Applicant Data)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id TEXT PRIMARY KEY, -- e.g. RERU-AD-000001
        prefix TEXT NOT NULL DEFAULT 'นาย', -- นาย, นางสาว, อื่น ๆ
        national_id TEXT NOT NULL, -- 13 digits, confidential
        full_name TEXT NOT NULL,
        nickname TEXT,
        dob TEXT NOT NULL, -- YYYY-MM-DD
        gender TEXT,
        phone TEXT NOT NULL,
        email TEXT,
        address TEXT NOT NULL,
        subdistrict TEXT,
        district TEXT,
        province TEXT NOT NULL,
        zipcode TEXT,
        
        school_name TEXT NOT NULL,
        degree_level TEXT DEFAULT 'ปริญญาตรี',
        gpax REAL NOT NULL,
        grad_year TEXT,
        
        program_code TEXT NOT NULL, -- CS, IT, MSI
        program_name TEXT NOT NULL,
        admission_round TEXT NOT NULL DEFAULT 'รอบที่ 2 (โควตา)', -- Round 1, 2, 3
        academic_year INTEGER NOT NULL DEFAULT 2569,
        status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED, REQUIRES_DOCS, VERIFIED
        staff_notes TEXT,
        
        applicant_token_hash TEXT, -- Optional token for applicant self-management
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 8. Private Documents Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        application_id TEXT NOT NULL,
        doc_type TEXT NOT NULL, -- id_card, transcript, photo, portfolio
        file_name TEXT NOT NULL,
        storage_path TEXT NOT NULL, -- secure private path, NOT public!
        file_size INTEGER NOT NULL,
        mime_type TEXT NOT NULL,
        uploaded_at TEXT NOT NULL,
        FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
    );
    """)

    # 9. Audit Logs Table (Strict Immutability)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_id TEXT, -- User ID or 'APPLICANT' or 'SYSTEM'
        actor_role TEXT,
        action TEXT NOT NULL, -- e.g. LOGIN, VIEW_APPLICATION, VIEW_SENSITIVE, EXPORT_APPLICATIONS
        resource_type TEXT NOT NULL, -- APPLICATION, DOCUMENT, USER
        resource_id TEXT,
        ip_address TEXT,
        user_agent TEXT,
        details TEXT, -- JSON or human description (NEVER contains raw password/national ID)
        created_at TEXT NOT NULL
    );
    """)

    # 10. Staff Table (Faculty & Staff Management)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        position TEXT NOT NULL,
        department TEXT NOT NULL, -- CS, IT, MSI
        email TEXT,
        phone TEXT,
        expertise TEXT, -- JSON array stored as text
        subjects TEXT, -- JSON array stored as text
        image_url TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 11. News & Activities Table (Facebook Sync / Fallback)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news_activities (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        image_url TEXT NOT NULL,
        published_date TEXT NOT NULL,
        source_page TEXT NOT NULL, -- e.g. "It RERU คณะเทคโนโลยีสารสนเทศ มรภ.ร้อยเอ็ด"
        source_url TEXT NOT NULL,
        category TEXT NOT NULL, -- "activity" or "news" (or "FEATURED_ACTIVITY" / "LATEST_NEWS")
        order_index INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 12. Student Services Table ( บริการสำหรับนักศึกษา )
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_services (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        icon TEXT NOT NULL DEFAULT '🎓',
        url TEXT NOT NULL,
        target_blank INTEGER DEFAULT 0,
        order_index INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # Populate Default Permissions and Roles
    permissions = [
        ('application.view', 'ดูข้อมูลผู้สมัครทั่วไป (Masked)'),
        ('application.view_sensitive', 'ดูข้อมูลผู้สมัครที่มีความละเอียดอ่อนแบบเต็ม (Unmasked)'),
        ('application.update', 'แก้ไขข้อมูลผู้สมัคร'),
        ('application.status_update', 'ปรับปรุงสถานะการสมัคร'),
        ('application.document_view', 'ดูเอกสารของผู้สมัคร'),
        ('application.document_download', 'ดาวน์โหลดเอกสารของผู้สมัคร'),
        ('application.export', 'Export รายชื่อผู้สมัคร'),
        ('admin.manage', 'จัดการบัญชี Admin'),
        ('audit.view', 'ดูประวัติ Audit Log')
    ]

    for pid, pdesc in permissions:
        cursor.execute("INSERT OR IGNORE INTO permissions (id, description) VALUES (?, ?)", (pid, pdesc))

    roles = [
        ('SUPER_ADMIN', 'ผู้ดูแลระบบสูงสุด', 'มีสิทธิ์ครบทุกประการและจัดการผู้ใช้งานในระบบ'),
        ('ADMIN', 'เจ้าหน้าที่ฝ่ายทะเบียนและรับสมัคร', 'ดูและจัดการข้อมูลผู้สมัครตามสิทธิ์ที่กำหนด'),
        ('OFFICER_VIEWER', 'เจ้าหน้าที่ตรวจเอกสารเบื้องต้น', 'ดูข้อมูลทั่วไปเท่านั้น')
    ]

    for rid, rname, rdesc in roles:
        cursor.execute("INSERT OR IGNORE INTO roles (id, name, description) VALUES (?, ?, ?)", (rid, rname, rdesc))

    # Assign permissions
    # SUPER_ADMIN gets everything
    for pid, _ in permissions:
        cursor.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES ('SUPER_ADMIN', ?)", (pid,))

    # ADMIN permissions (Strictly NO admin.manage, NO audit.view)
    admin_perms = [
        'application.view',
        'application.view_sensitive',
        'application.update',
        'application.status_update',
        'application.document_view',
        'application.document_download'
    ]
    for pid in admin_perms:
        cursor.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES ('ADMIN', ?)", (pid,))

    # OFFICER_VIEWER permissions
    cursor.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES ('OFFICER_VIEWER', 'application.view')")
    cursor.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES ('OFFICER_VIEWER', 'application.document_view')")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
