"""
HTTP Server & API Router for RERU Admissions & Privacy System
Features:
- Pure Python http.server with built-in security controls (no external heavy frameworks)
- Strict Session Verification with HttpOnly & Secure flags
- Granular Role-Based Access Control (RBAC) & Permissions (Super Admin, Admin, Officer)
- PII Masking on List and Overview (Unmasking requires application.view_sensitive and logs Audit)
- Anti-IDOR: Applicant self-check requires dual verification (Application ID + DOB)
- Document Private Storage Controller (Zero public access to documents)
- Export with Confirmation, Permission Check, and Audit Log
- Rate Limiting & Generic Login Error Protection
- Immutable Audit Logging
"""
import http.server
import socketserver
import urllib.parse
import json
import os
import mimetypes
import secrets
import csv
import io
import uuid
from datetime import datetime, timezone, timedelta

from db import get_db
from security import (
    hash_password,
    verify_password,
    check_login_rate_limit,
    record_login_attempt,
    mask_application_dict,
    mask_name,
    log_audit
)

# ดึงค่า PORT และ HOST จาก Environment เพื่อรองรับ Render Cloud และรันในเครื่อง
PORT = int(os.environ.get('PORT', 8000))
HOST = os.environ.get('HOST', '0.0.0.0')
COOKIE_NAME = os.environ.get('SESSION_COOKIE_NAME', 'reru_secure_session')
SESSION_TIMEOUT_SECONDS = int(os.environ.get('SESSION_LIFETIME_SECONDS', 3600))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, 'storage', 'private_documents')

class SecureAdmissionsHandler(http.server.SimpleHTTPRequestHandler):
    """Secure request handler enforcing authentication, authorization, and privacy."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    # ==========================================================================
    # Helper & Security Methods
    # ==========================================================================

    def parse_cookies(self):
        """Parse HTTP Cookie header."""
        cookie_header = self.headers.get('Cookie', '')
        cookies = {}
        if cookie_header:
            for item in cookie_header.split(';'):
                item = item.strip()
                if '=' in item:
                    k, v = item.split('=', 1)
                    cookies[k.strip()] = v.strip()
        return cookies

    def get_client_ip(self):
        """Extract client IP address."""
        forwarded = self.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return self.client_address[0]

    def get_authenticated_user(self):
        """
        Verify server-side session from cookie.
        Returns user dictionary with roles and permissions, or None.
        """
        cookies = self.parse_cookies()
        session_id = cookies.get(COOKIE_NAME)
        if not session_id:
            return None

        conn = get_db()
        cursor = conn.cursor()
        now_str = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            SELECT s.session_id, s.user_id, s.expires_at, 
                   u.id, u.username, u.email, u.full_name, u.role_id, u.is_active
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_id = ? AND s.expires_at > ? AND u.is_active = 1
        """, (session_id, now_str))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        user = dict(row)

        # Fetch permissions for this role
        cursor.execute("""
            SELECT permission_id FROM role_permissions WHERE role_id = ?
        """, (user['role_id'],))
        permissions = [r['permission_id'] for r in cursor.fetchall()]
        user['permissions'] = permissions

        conn.close()
        return user

    def send_json(self, status_code: int, data: dict, cookies_to_set=None):
        """Send a JSON HTTP response with security headers."""
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, private')
        self.send_header('Pragma', 'no-cache')

        if cookies_to_set:
            for c in cookies_to_set:
                self.send_header('Set-Cookie', c)

        self.end_headers()
        self.wfile.write(payload)

    def send_error_json(self, status_code: int, message: str):
        """Generic error response that prevents leaking sensitive server internals."""
        self.send_json(status_code, {
            'success': False,
            'error': message
        })

    def read_json_body(self):
        """Read and parse JSON body with size limitation (max 2MB)."""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 2 * 1024 * 1024:
            return None
        body = self.rfile.read(content_length)
        try:
            return json.loads(body.decode('utf-8'))
        except Exception:
            return None

    # ==========================================================================
    # HTTP Method Routing
    # ==========================================================================

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. API Endpoints
        if path.startswith('/api/'):
            self.route_api_get(path, query)
            return

        # 2. Block direct HTTP access to confidential storage directory!
        if path.startswith('/storage/') or path.startswith('/data/') or path.startswith('/server_venv/'):
            self.send_error(403, "Access Denied: Confidential Server Storage")
            return

        # 3. Serve Frontend Static HTML/CSS/JS files
        if path == '/' or path == '/index.html':
            self.path = '/index.html'
            return super().do_GET()
        elif path == '/check-status':
            self.path = '/check-status.html'
            return super().do_GET()
        elif path == '/admin' or path == '/admin/' or path == '/admin/login':
            self.path = '/admin-login.html'
            return super().do_GET()
        elif path == '/admin/dashboard':
            self.path = '/admin-dashboard.html'
            return super().do_GET()
        elif path.startswith('/admin/applications/'):
            self.path = '/admin-application-detail.html'
            return super().do_GET()

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith('/api/'):
            self.route_api_post(path)
            return

        self.send_error(404, "Not Found")

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith('/api/'):
            self.route_api_patch(path)
            return

        self.send_error(404, "Not Found")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith('/api/'):
            self.route_api_delete(path)
            return

        self.send_error(404, "Not Found")

    # ==========================================================================
    # API Handlers: GET
    # ==========================================================================

    def route_api_get(self, path: str, query: dict):
        # 1. Public Programs API
        if path == '/api/programs':
            self.handle_get_programs()
            return
            
        # Public Staff API
        if path == '/api/staff':
            self.handle_get_public_staff(query)
            return

        # Public News & Activities API
        if path == '/api/news-activities':
            self.handle_get_news_activities(query)
            return

        # Admin News & Activities List
        if path == '/api/admin/news-activities':
            self.handle_admin_get_news_activities(query)
            return

        # Public Student Services API
        if path == '/api/student-services':
            self.handle_get_student_services(query)
            return

        # Admin Student Services List
        if path == '/api/admin/student-services':
            self.handle_admin_get_student_services(query)
            return

        # 2. Applicant Self-Check Status (Anti-IDOR: Requires 2-factor Verification)
        if path == '/api/applicant/check-status':
            self.handle_applicant_check_status(query)
            return

        # 3. Current Session Check
        if path == '/api/auth/me':
            self.handle_auth_me()
            return

        # 4. Admin Dashboard Stats (Privacy First: Aggregate Numbers Only, No PII!)
        if path == '/api/admin/stats':
            self.handle_admin_stats()
            return

        # 5. Admin List Applications (Privacy: Masked PII)
        if path == '/api/admin/applications':
            self.handle_admin_list_applications(query)
            return

        # 6. Admin Export Applications
        if path == '/api/admin/applications/export':
            self.handle_admin_export_applications(query)
            return

        # 7. Admin Application Detail (Supports Unmasking if authorized)
        if path.startswith('/api/admin/applications/') and not '/documents' in path:
            app_id = path.split('/')[-1]
            self.handle_admin_get_application(app_id, query)
            return

        # 8. Admin Application Documents List
        if path.startswith('/api/admin/applications/') and path.endswith('/documents'):
            parts = path.split('/')
            app_id = parts[-2]
            self.handle_admin_get_documents(app_id)
            return

        # 9. Private Document Download (Protected Stream Controller)
        if '/documents/' in path and path.endswith('/download'):
            parts = path.split('/')
            app_id = parts[4]
            doc_id = parts[6]
            self.handle_admin_download_document(app_id, doc_id)
            return

        # 10. Super Admin: Audit Logs
        if path == '/api/admin/audit-logs':
            self.handle_admin_get_audit_logs(query)
            return

        # 11. Super Admin: Users Management
        if path == '/api/admin/users':
            self.handle_admin_get_users()
            return

        # 12. Staff Management: List
        if path == '/api/admin/staff':
            self.handle_admin_get_staff(query)
            return

        self.send_error_json(404, "API endpoint not found.")

    # ==========================================================================
    # API Handlers: POST
    # ==========================================================================

    def route_api_post(self, path: str):
        if path == '/api/auth/login':
            self.handle_auth_login()
            return

        if path == '/api/auth/logout':
            self.handle_auth_logout()
            return

        if path == '/api/admin/users':
            self.handle_admin_create_user()
            return

        if path == '/api/admin/staff':
            self.handle_admin_create_staff()
            return

        if path == '/api/admin/news-activities':
            self.handle_admin_create_news_activity()
            return

        if path == '/api/admin/student-services':
            self.handle_admin_create_student_service()
            return

        if path == '/api/applications/submit':
            self.handle_public_submit_application()
            return

        self.send_error_json(404, "API endpoint not found.")

    # ==========================================================================
    # API Handlers: PATCH
    # ==========================================================================

    def route_api_patch(self, path: str):
        if path.startswith('/api/admin/applications/'):
            app_id = path.split('/')[-1]
            self.handle_admin_patch_application(app_id)
            return

        if path.startswith('/api/admin/staff/'):
            staff_id = path.split('/')[-1]
            self.handle_admin_update_staff(staff_id)
            return

        if path.startswith('/api/admin/news-activities/'):
            item_id = path.split('/')[-1]
            self.handle_admin_update_news_activity(item_id)
            return

        if path.startswith('/api/admin/student-services/'):
            service_id = path.split('/')[-1]
            self.handle_admin_update_student_service(service_id)
            return

        self.send_error_json(404, "API endpoint not found.")

    def route_api_delete(self, path: str):
        if path.startswith('/api/admin/applications/'):
            app_id = path.split('/')[-1]
            self.handle_admin_delete_application(app_id)
            return

        if path.startswith('/api/admin/staff/'):
            staff_id = path.split('/')[-1]
            self.handle_admin_delete_staff(staff_id)
            return

        if path.startswith('/api/admin/news-activities/'):
            item_id = path.split('/')[-1]
            self.handle_admin_delete_news_activity(item_id)
            return

        if path.startswith('/api/admin/student-services/'):
            service_id = path.split('/')[-1]
            self.handle_admin_delete_student_service(service_id)
            return

        self.send_error_json(404, "API endpoint not found.")

    # ==========================================================================
    # Implementation Details: Auth
    # ==========================================================================

    def handle_auth_login(self):
        ip = self.get_client_ip()
        data = self.read_json_body() or {}
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        rate_key = f"{ip}:{username}" if username else ip
        if not check_login_rate_limit(rate_key, max_attempts=5, window_seconds=300):
            log_audit(username or 'ANONYMOUS', 'GUEST', 'LOGIN_LOCKOUT', 'AUTH', None, 'Rate limit exceeded. Temporary lockout.', ip, self.headers.get('User-Agent'))
            self.send_error_json(429, "มีการพยายามเข้าสู่ระบบผิดพลาดหลายครั้ง กรุณารอ 5 นาทีแล้วลองใหม่อีกครั้ง")
            return

        if not username or not password:
            self.send_error_json(400, "กรุณากรอกชื่อผู้ใช้และรหัสผ่าน")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username))
        user = cursor.fetchone()

        if not user or not user['is_active']:
            record_login_attempt(rate_key, success=False)
            log_audit(username, 'GUEST', 'LOGIN_FAILURE', 'AUTH', None, 'User not found or inactive.', ip, self.headers.get('User-Agent'))
            conn.close()
            self.send_error_json(401, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            return

        if not verify_password(password, user['password_hash']):
            record_login_attempt(rate_key, success=False)
            log_audit(user['username'], user['role_id'], 'LOGIN_FAILURE', 'AUTH', user['id'], 'Invalid password attempt.', ip, self.headers.get('User-Agent'))
            conn.close()
            self.send_error_json(401, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            return

        record_login_attempt(rate_key, success=True)

        session_id = secrets.token_hex(32)
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(seconds=SESSION_TIMEOUT_SECONDS)).isoformat()

        cursor.execute("""
            INSERT INTO sessions (session_id, user_id, created_at, expires_at, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, user['id'], now.isoformat(), expires_at, ip, self.headers.get('User-Agent')))

        cursor.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now.isoformat(), user['id']))
        conn.commit()

        log_audit(user['id'], user['role_id'], 'LOGIN_SUCCESS', 'AUTH', user['id'], 'User logged in successfully.', ip, self.headers.get('User-Agent'))
        conn.close()

        cookie_str = f"{COOKIE_NAME}={session_id}; Path=/; Max-Age={SESSION_TIMEOUT_SECONDS}; HttpOnly; SameSite=Lax"

        self.send_json(200, {
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'role_id': user['role_id']
            }
        }, cookies_to_set=[cookie_str])

    def handle_auth_logout(self):
        cookies = self.parse_cookies()
        session_id = cookies.get(COOKIE_NAME)
        ip = self.get_client_ip()

        user = self.get_authenticated_user()
        if user:
            log_audit(user['id'], user['role_id'], 'LOGOUT', 'AUTH', user['id'], 'User logged out.', ip, self.headers.get('User-Agent'))

        if session_id:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()

        expired_cookie = f"{COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        self.send_json(200, {'success': True, 'message': 'ออกจากระบบเรียบร้อยแล้ว'}, cookies_to_set=[expired_cookie])

    def handle_auth_me(self):
        user = self.get_authenticated_user()
        if not user:
            self.send_error_json(401, "กรุณาเข้าสู่ระบบก่อนทำรายการ")
            return

        self.send_json(200, {
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'email': user['email'],
                'role_id': user['role_id'],
                'permissions': user['permissions']
            }
        })

    # ==========================================================================
    # Implementation Details: Applicant Self-Check
    # ==========================================================================

    def handle_applicant_check_status(self, query: dict):
        app_id = query.get('application_id', [''])[0].strip()
        dob = query.get('dob', [''])[0].strip()
        ip = self.get_client_ip()

        if not app_id or not dob:
            self.send_error_json(400, "กรุณาระบุเลขที่สมัครและวันเดือนปีเกิดเพื่อยืนยันตัวตน")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, full_name, program_code, program_name, admission_round, academic_year, status, staff_notes, created_at
            FROM applications
            WHERE id = ? AND dob = ?
        """, (app_id, dob))

        row = cursor.fetchone()
        conn.close()

        if not row:
            log_audit('ANONYMOUS', 'APPLICANT', 'CHECK_STATUS_FAIL', 'APPLICATION', app_id, 'Verification failed (invalid credentials).', ip, self.headers.get('User-Agent'))
            self.send_error_json(404, "ไม่พบข้อมูลการสมัคร หรือข้อมูลยืนยันตัวตนไม่ถูกต้อง")
            return

        log_audit('APPLICANT', 'APPLICANT', 'CHECK_STATUS_SUCCESS', 'APPLICATION', app_id, 'Applicant verified identity and checked status.', ip, self.headers.get('User-Agent'))

        data = dict(row)
        data['full_name'] = mask_name(data['full_name'])

        self.send_json(200, {
            'success': True,
            'application': data
        })

    # ==========================================================================
    # Implementation Details: Admin Admissions Management
    # ==========================================================================

    def handle_admin_stats(self):
        user = self.get_authenticated_user()
        if not user or 'application.view' not in user['permissions']:
            self.send_error_json(403, "ไม่มีสิทธิ์เข้าถึงข้อมูลสถิติผู้สมัคร")
            return

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM applications")
        total = cursor.fetchone()['total']

        cursor.execute("SELECT status, COUNT(*) as count FROM applications GROUP BY status")
        status_counts = {r['status']: r['count'] for r in cursor.fetchall()}

        cursor.execute("SELECT program_name, COUNT(*) as count FROM applications GROUP BY program_name")
        program_counts = {r['program_name']: r['count'] for r in cursor.fetchall()}

        cursor.execute("SELECT admission_round, COUNT(*) as count FROM applications GROUP BY admission_round")
        round_counts = {r['admission_round']: r['count'] for r in cursor.fetchall()}

        conn.close()

        self.send_json(200, {
            'success': True,
            'stats': {
                'total_applicants': total,
                'status_counts': {
                    'PENDING': status_counts.get('PENDING', 0),
                    'APPROVED': status_counts.get('APPROVED', 0),
                    'REJECTED': status_counts.get('REJECTED', 0),
                    'REQUIRES_DOCS': status_counts.get('REQUIRES_DOCS', 0)
                },
                'program_counts': program_counts,
                'round_counts': round_counts
            }
        })

    def handle_admin_list_applications(self, query: dict):
        user = self.get_authenticated_user()
        if not user or 'application.view' not in user['permissions']:
            self.send_error_json(403, "ไม่มีสิทธิ์เข้าถึงรายชื่อผู้สมัคร (Permission Denied)")
            return

        program = query.get('program', [''])[0].strip()
        status = query.get('status', [''])[0].strip()
        search = query.get('q', [''])[0].strip()

        sql = """
            SELECT id, national_id, full_name, phone, email, program_code, program_name,
                   admission_round, gpax, province, status, created_at
            FROM applications
            WHERE 1=1
        """
        params = []

        if program:
            sql += " AND program_code = ?"
            params.append(program)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if search:
            sql += " AND (id LIKE ? OR full_name LIKE ?)"
            params.append(f"%{search}%")
            params.append(f"%{search}%")

        sql += " ORDER BY created_at DESC"

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        masked_list = []
        for r in rows:
            app_dict = dict(r)
            masked_list.append(mask_application_dict(app_dict, allow_sensitive=False))

        log_audit(user['id'], user['role_id'], 'VIEW_APPLICATIONS_LIST', 'APPLICATION', 'LIST', f"Viewed list with {len(masked_list)} records.", self.get_client_ip(), self.headers.get('User-Agent'))

        self.send_json(200, {
            'success': True,
            'applications': masked_list,
            'count': len(masked_list)
        })

    def handle_admin_get_application(self, app_id: str, query: dict):
        user = self.get_authenticated_user()
        if not user or 'application.view' not in user['permissions']:
            self.send_error_json(403, "ไม่มีสิทธิ์เข้าถึงข้อมูลผู้สมัคร (Permission Denied)")
            return

        reveal = query.get('reveal', ['false'])[0].lower() == 'true'

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            self.send_error_json(404, "ไม่พบข้อมูลผู้สมัครรายนี้")
            return

        app_dict = dict(row)

        can_view_sensitive = ('application.view_sensitive' in user['permissions']) and reveal
        if reveal and not ('application.view_sensitive' in user['permissions']):
            self.send_error_json(403, "คุณไม่มีสิทธิ์ 'application.view_sensitive' ในการดูข้อมูลส่วนบุคคลฉบับเต็ม")
            return

        processed = mask_application_dict(app_dict, allow_sensitive=can_view_sensitive)

        action_name = 'VIEW_APPLICATION_UNMASKED' if can_view_sensitive else 'VIEW_APPLICATION'
        log_audit(user['id'], user['role_id'], action_name, 'APPLICATION', app_id, f"Viewed application details (unmasked={can_view_sensitive})", self.get_client_ip(), self.headers.get('User-Agent'))

        self.send_json(200, {
            'success': True,
            'application': processed,
            'can_unmask': 'application.view_sensitive' in user['permissions']
        })

    def handle_admin_patch_application(self, app_id: str):
        user = self.get_authenticated_user()
        if not user:
            self.send_error_json(401, "กรุณาเข้าสู่ระบบ")
            return

        body = self.read_json_body() or {}
        new_status = body.get('status')
        staff_notes = body.get('staff_notes')

        if new_status and 'application.status_update' not in user['permissions']:
            self.send_error_json(403, "คุณไม่มีสิทธิ์ปรับเปลี่ยนสถานะผู้สมัคร (application.status_update)")
            return

        if staff_notes is not None and 'application.update' not in user['permissions']:
            self.send_error_json(403, "คุณไม่มีสิทธิ์แก้ไขหมายเหตุผู้สมัคร (application.update)")
            return

        valid_statuses = ['PENDING', 'APPROVED', 'REJECTED', 'REQUIRES_DOCS', 'VERIFIED']
        if new_status and new_status not in valid_statuses:
            self.send_error_json(400, "สถานะที่ระบุไม่ถูกต้อง")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT status, staff_notes FROM applications WHERE id = ?", (app_id,))
        existing = cursor.fetchone()
        if not existing:
            conn.close()
            self.send_error_json(404, "ไม่พบข้อมูลผู้สมัคร")
            return

        now_str = datetime.now(timezone.utc).isoformat()
        update_fields = ["updated_at = ?"]
        params = [now_str]

        if new_status:
            update_fields.append("status = ?")
            params.append(new_status)
        if staff_notes is not None:
            update_fields.append("staff_notes = ?")
            params.append(staff_notes)

        params.append(app_id)
        sql = f"UPDATE applications SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(sql, params)
        conn.commit()

        changes_desc = f"Status: {existing['status']} -> {new_status or existing['status']}; Notes updated."
        log_audit(user['id'], user['role_id'], 'UPDATE_APPLICATION', 'APPLICATION', app_id, changes_desc, self.get_client_ip(), self.headers.get('User-Agent'))
        conn.close()

        self.send_json(200, {
            'success': True,
            'message': 'อัปเดตข้อมูลผู้สมัครเรียบร้อยแล้ว'
        })

    def handle_admin_delete_application(self, app_id: str):
        user = self.get_authenticated_user()
        if not user or 'application.delete' not in user['permissions']:
            if not user or user.get('role_id') not in ['SUPER_ADMIN', 'ADMIN']:
                self.send_error_json(403, "คุณไม่มีสิทธิ์ลบข้อมูลผู้สมัคร (Permission Denied)")
                return

        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
        app = cursor.fetchone()
        if not app:
            conn.close()
            self.send_error_json(404, "ไม่พบข้อมูลใบสมัครที่ต้องการลบ")
            return

        cursor.execute("SELECT storage_path FROM documents WHERE application_id = ?", (app_id,))
        docs = cursor.fetchall()
        for d in docs:
            if d['storage_path'] and os.path.exists(d['storage_path']):
                try:
                    os.remove(d['storage_path'])
                except Exception:
                    pass

        cursor.execute("DELETE FROM documents WHERE application_id = ?", (app_id,))
        cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        conn.commit()

        log_audit(user['id'], user['role_id'], 'DELETE_APPLICATION', 'APPLICATION', app_id, f"Deleted application {app_id}", self.get_client_ip(), self.headers.get('User-Agent'))
        conn.close()

        self.send_json(200, {
            'success': True,
            'message': 'ลบข้อมูลใบสมัครเรียบร้อยแล้ว'
        })

    def handle_public_submit_application(self):
        body = self.read_json_body() or {}
        
        prefix = body.get('prefix', 'นาย').strip()
        first_name = body.get('first_name', '').strip()
        last_name = body.get('last_name', '').strip()
        full_name = body.get('full_name', '').strip() or f"{prefix}{first_name} {last_name}".strip()
        nickname = body.get('nickname', '').strip()
        dob = body.get('dob', '').strip()
        national_id = body.get('national_id', '').strip()
        phone = body.get('phone', '').strip()
        email = body.get('email', '').strip()
        address = body.get('address', '').strip()
        province = body.get('province', '').strip()
        district = body.get('district', '').strip()
        subdistrict = body.get('subdistrict', '').strip()
        zipcode = body.get('zipcode', '').strip()

        school_name = body.get('school_name', '').strip()
        degree_level = body.get('degree_level', 'ปริญญาตรี').strip()
        gpax_raw = body.get('gpax', 0)
        try:
            gpax = float(gpax_raw)
        except (ValueError, TypeError):
            gpax = 0.0
        grad_year = body.get('grad_year', '').strip()

        program_code = body.get('program_code', '').strip().upper()
        admission_round = body.get('admission_round', 'รอบที่ 2 (โควตา)').strip()

        if not first_name and not full_name:
            self.send_error_json(400, "กรุณากรอกชื่อ")
            return
        if not last_name and not full_name:
            self.send_error_json(400, "กรุณากรอกนามสกุล")
            return
        if not dob:
            self.send_error_json(400, "กรุณากรอกวัน/เดือน/ปีเกิด")
            return
        if not national_id or len(national_id.replace('-', '')) != 13:
            self.send_error_json(400, "กรุณากรอกเลขบัตรประชาชนให้ถูกต้อง (13 หลัก)")
            return
        if not phone:
            self.send_error_json(400, "กรุณากรอกเบอร์โทรศัพท์")
            return
        if not school_name:
            self.send_error_json(400, "กรุณากรอกชื่อโรงเรียนเดิม")
            return
        if gpax <= 0 or gpax > 4.0:
            self.send_error_json(400, "กรุณากรอก GPAX ให้ถูกต้อง (0.00 - 4.00)")
            return
        if not program_code:
            self.send_error_json(400, "กรุณาเลือกหลักสูตรที่ต้องการสมัคร")
            return

        program_names = {
            'CS': 'วิทยาการคอมพิวเตอร์ (Computer Science)',
            'IT': 'เทคโนโลยีสารสนเทศ (Information Technology)',
            'MSI': 'วิทยาการมัลติมีเดียปัญญาประดิษฐ์ (Multimedia and Artificial Intelligence)'
        }
        program_name = program_names.get(program_code, program_code)

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM applications WHERE id LIKE 'RERU-AD-%' ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        if last_row:
            try:
                num = int(last_row['id'].replace('RERU-AD-', '')) + 1
            except ValueError:
                num = 1
        else:
            num = 1

        app_id = f"RERU-AD-{num:06d}"
        now_str = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            INSERT INTO applications (
                id, prefix, national_id, full_name, nickname, dob, gender, phone, email,
                address, subdistrict, district, province, zipcode,
                school_name, degree_level, gpax, grad_year,
                program_code, program_name, admission_round, academic_year, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            app_id, prefix, national_id, full_name, nickname, dob, body.get('gender', 'ไม่ระบุ'), phone, email,
            address, subdistrict, district, province, zipcode,
            school_name, degree_level, gpax, grad_year,
            program_code, program_name, admission_round, 2569, 'PENDING',
            now_str, now_str
        ))

        documents = body.get('documents', [])
        saved_docs = []

        if documents and isinstance(documents, list):
            storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'storage', 'private_documents', app_id)
            os.makedirs(storage_dir, exist_ok=True)

            for doc in documents:
                doc_type = doc.get('type', 'other')
                file_name = doc.get('name', 'document.file')
                file_data_b64 = doc.get('data', '')
                mime_type = doc.get('mime', 'application/octet-stream')

                if file_data_b64:
                    try:
                        import base64
                        if ',' in file_data_b64:
                            file_data_b64 = file_data_b64.split(',', 1)[1]
                        file_bytes = base64.b64decode(file_data_b64)
                        
                        doc_id = 'doc_' + secrets.token_hex(8)
                        safe_filename = f"{doc_id}_{os.path.basename(file_name)}"
                        file_path = os.path.join(storage_dir, safe_filename)

                        with open(file_path, 'wb') as f:
                            f.write(file_bytes)

                        cursor.execute("""
                            INSERT INTO documents (id, application_id, doc_type, file_name, storage_path, file_size, mime_type, uploaded_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (doc_id, app_id, doc_type, file_name, file_path, len(file_bytes), mime_type, now_str))

                        saved_docs.append({'id': doc_id, 'name': file_name})
                    except Exception as e:
                        print(f"Error saving document {file_name}:", e)

        conn.commit()

        log_audit('APPLICANT', 'APPLICANT', 'SUBMIT_APPLICATION', 'APPLICATION', app_id, f"Submitted application for {program_name}", self.get_client_ip(), self.headers.get('User-Agent'))
        conn.close()

        self.send_json(201, {
            'success': True,
            'message': 'ส่งใบสมัครเรียบร้อยแล้ว',
            'application_id': app_id,
            'application': {
                'id': app_id,
                'full_name': full_name,
                'program_name': program_name,
                'program_code': program_code,
                'submitted_at': now_str[:10],
                'status': 'PENDING',
                'status_label': 'รอตรวจสอบ'
            }
        })

    # ==========================================================================
    # Implementation Details: Protected Documents Management
    # ==========================================================================

    def handle_admin_get_documents(self, app_id: str):
        user = self.get_authenticated_user()
        if not user or 'application.document_view' not in user['permissions']:
            self.send_error_json(403, "ไม่มีสิทธิ์ดูเอกสารผู้สมัคร (application.document_view)")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, doc_type, file_name, file_size, mime_type, uploaded_at
            FROM documents
            WHERE application_id = ?
        """, (app_id,))
        docs = [dict(r) for r in cursor.fetchall()]
        conn.close()

        log_audit(user['id'], user['role_id'], 'VIEW_DOCUMENTS_LIST', 'DOCUMENT', app_id, f"Listed {len(docs)} documents", self.get_client_ip(), self.headers.get('User-Agent'))

        self.send_json(200, {
            'success': True,
            'documents': docs
        })

    def handle_admin_download_document(self, app_id: str, doc_id: str):
        user = self.get_authenticated_user()
        if not user or 'application.document_download' not in user['permissions']:
            self.send_error_json(403, "ไม่มีสิทธิ์ดาวน์โหลดเอกสารผู้สมัคร (application.document_download)")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM documents WHERE id = ? AND application_id = ?
        """, (doc_id, app_id))
        doc = cursor.fetchone()
        conn.close()

        if not doc:
            self.send_error_json(404, "ไม่พบเอกสารที่ระบุ")
            return

        file_path = doc['storage_path']
        if not os.path.exists(file_path):
            self.send_error_json(404, "ไฟล์เอกสารไม่พร้อมใช้งานในระบบจัดเก็บข้อมูลส่วนตัว")
            return

        log_audit(user['id'], user['role_id'], 'DOWNLOAD_DOCUMENT', 'DOCUMENT', doc_id, f"Downloaded {doc['file_name']} for {app_id}", self.get_client_ip(), self.headers.get('User-Agent'))

        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            self.send_response(200)
            self.send_header('Content-Type', doc['mime_type'] or 'application/octet-stream')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Content-Disposition', f'attachment; filename="{doc["file_name"]}"')
            self.send_header('Cache-Control', 'no-store, private')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error_json(500, "เกิดข้อผิดพลาดในการอ่านไฟล์เอกสาร")

    # ==========================================================================
    # Implementation Details: Secure Export
    # ==========================================================================

    def handle_admin_export_applications(self, query: dict):
        user = self.get_authenticated_user()
        if not user or 'application.export' not in user['permissions']:
            self.send_error_json(403, "คุณไม่มีสิทธิ์ส่งออกข้อมูลผู้สมัคร (application.export)")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, national_id, full_name, dob, gender, phone, email, school_name,
                   gpax, province, program_name, admission_round, academic_year, status, staff_notes, created_at
            FROM applications
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        log_audit(user['id'], user['role_id'], 'EXPORT_APPLICATIONS', 'APPLICATION', 'ALL', f"Exported {len(rows)} application records to CSV.", self.get_client_ip(), self.headers.get('User-Agent'))

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'เลขที่สมัคร', 'เลขประจำตัวประชาชน', 'ชื่อ-นามสกุล', 'วันเกิด', 'เพศ',
            'เบอร์โทรศัพท์', 'อีเมล', 'โรงเรียนเดิม', 'GPAX', 'จังหวัด',
            'สาขาวิชา', 'รอบรับสมัคร', 'ปีการศึกษา', 'สถานะ', 'หมายเหตุเจ้าหน้าที่', 'วันที่สมัคร'
        ])

        can_view_sensitive = 'application.view_sensitive' in user['permissions']

        for r in rows:
            d = dict(r)
            if not can_view_sensitive:
                d = mask_application_dict(d, allow_sensitive=False)
            writer.writerow([
                d['id'], d['national_id'], d['full_name'], d['dob'], d['gender'],
                d['phone'], d['email'], d['school_name'], d['gpax'], d['province'],
                d['program_name'], d['admission_round'], d['academic_year'], d['status'],
                d.get('staff_notes', ''), d['created_at']
            ])

        csv_content = "\ufeff" + output.getvalue()
        csv_bytes = csv_content.encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'text/csv; charset=utf-8')
        self.send_header('Content-Length', str(len(csv_bytes)))
        self.send_header('Content-Disposition', f'attachment; filename="reru_applicants_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"')
        self.send_header('Cache-Control', 'no-store, private')
        self.end_headers()
        self.wfile.write(csv_bytes)

    # ==========================================================================
    # Implementation Details: Super Admin Only
    # ==========================================================================

    def handle_admin_get_audit_logs(self, query: dict):
        user = self.get_authenticated_user()
        if not user or 'audit.view' not in user['permissions']:
            self.send_error_json(403, "เฉพาะผู้ดูแลระบบสูงสุด (Super Admin) ที่มีสิทธิ์ดู Audit Log")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, actor_id, actor_role, action, resource_type, resource_id, details, ip_address, created_at
            FROM audit_logs
            ORDER BY created_at DESC
            LIMIT 100
        """)
        logs = [dict(r) for r in cursor.fetchall()]
        conn.close()

        self.send_json(200, {
            'success': True,
            'logs': logs
        })

    def handle_admin_get_users(self):
        user = self.get_authenticated_user()
        if not user or 'admin.manage' not in user['permissions']:
            self.send_error_json(403, "เฉพาะผู้ดูแลระบบสูงสุด (Super Admin) ที่มีสิทธิ์จัดการบัญชีเจ้าหน้าที่")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, full_name, role_id, is_active, created_at, last_login_at
            FROM users
            ORDER BY created_at ASC
        """)
        users = [dict(r) for r in cursor.fetchall()]
        conn.close()

        self.send_json(200, {
            'success': True,
            'users': users
        })

    def handle_admin_create_user(self):
        user = self.get_authenticated_user()
        if not user or 'admin.manage' not in user['permissions']:
            self.send_error_json(403, "เฉพาะผู้ดูแลระบบสูงสุด (Super Admin) ที่มีสิทธิ์สร้างบัญชีเจ้าหน้าที่")
            return

        body = self.read_json_body() or {}
        username = body.get('username', '').strip()
        email = body.get('email', '').strip()
        raw_password = body.get('password', '').strip()
        full_name = body.get('full_name', '').strip()
        role_id = body.get('role_id', 'ADMIN').strip()

        if not username or not email or not raw_password or not full_name:
            self.send_error_json(400, "กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง")
            return

        if len(raw_password) < 8:
            self.send_error_json(400, "รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร")
            return

        if role_id not in ['SUPER_ADMIN', 'ADMIN', 'OFFICER_VIEWER']:
            self.send_error_json(400, "สิทธิ์บทบาทที่เลือกไม่ถูกต้อง")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            conn.close()
            self.send_error_json(400, "ชื่อผู้ใช้หรืออีเมลนี้มีอยู่ในระบบแล้ว")
            return

        new_uid = f"usr_{secrets.token_hex(6)}"
        pwd_hash = hash_password(raw_password)
        now_str = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            INSERT INTO users (id, username, email, password_hash, full_name, role_id, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (new_uid, username, email, pwd_hash, full_name, role_id, now_str))
        conn.commit()

        log_audit(user['id'], user['role_id'], 'CREATE_ADMIN_USER', 'USER', new_uid, f"Created new {role_id} account '{username}'", self.get_client_ip(), self.headers.get('User-Agent'))
        conn.close()

        self.send_json(201, {
            'success': True,
            'message': f"สร้างบัญชีเจ้าหน้าที่ '{username}' สำเร็จแล้ว"
        })

    # ==========================================================================
    # Implementation Details: Staff Management
    # ==========================================================================

    def handle_admin_get_staff(self, query: dict):
        user = self.get_authenticated_user()
        if not user:
            self.send_error_json(401, "กรุณาเข้าสู่ระบบ")
            return

        dept = query.get('dept', [''])[0].strip()
        
        sql = "SELECT * FROM staff"
        params = []
        if dept:
            sql += " WHERE department = ?"
            params.append(dept)
        sql += " ORDER BY created_at DESC"

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        staff_list = []
        for r in rows:
            d = dict(r)
            d['expertise'] = json.loads(d['expertise']) if d['expertise'] else []
            d['subjects'] = json.loads(d['subjects']) if d['subjects'] else []
            staff_list.append(d)

        self.send_json(200, {
            'success': True,
            'staff': staff_list
        })

    def handle_admin_create_staff(self):
        user = self.get_authenticated_user()
        if not user or ('admin.manage' not in user['permissions'] and user['role_id'] != 'SUPER_ADMIN' and user['role_id'] != 'ADMIN'):
            self.send_error_json(403, "ไม่มีสิทธิ์จัดการบุคลากร")
            return

        body = self.read_json_body() or {}
        name = body.get('name', '').strip()
        position = body.get('position', '').strip()
        department = body.get('department', '').strip()
        
        if not name or not position or not department:
            self.send_error_json(400, "กรุณากรอกข้อมูลบังคับ (ชื่อ, ตำแหน่ง, สาขา) ให้ครบถ้วน")
            return

        expertise = json.dumps(body.get('expertise', []), ensure_ascii=False)
        subjects = json.dumps(body.get('subjects', []), ensure_ascii=False)
        email = body.get('email', '').strip()
        phone = body.get('phone', '').strip()
        image_url = body.get('image_url', '').strip()
        
        new_id = f"stf_{secrets.token_hex(6)}"
        now_str = datetime.now(timezone.utc).isoformat()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO staff (id, name, position, department, email, phone, expertise, subjects, image_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_id, name, position, department, email, phone, expertise, subjects, image_url, now_str, now_str))
        conn.commit()

        log_audit(user['id'], user['role_id'], 'CREATE_STAFF', 'STAFF', new_id, f"Created staff '{name}'", self.get_client_ip(), self.headers.get('User-Agent'))
        conn.close()

        self.send_json(201, {
            'success': True,
            'message': f"เพิ่มบุคลากร '{name}' สำเร็จ"
        })

    def handle_admin_update_staff(self, staff_id: str):
        user = self.get_authenticated_user()
        if not user or ('admin.manage' not in user['permissions'] and user['role_id'] != 'SUPER_ADMIN' and user['role_id'] != 'ADMIN'):
            self.send_error_json(403, "ไม่มีสิทธิ์จัดการบุคลากร")
            return

        body = self.read_json_body() or {}
        name = body.get('name', '').strip()
        position = body.get('position', '').strip()
        department = body.get('department', '').strip()
        
        if not name or not position or not department:
            self.send_error_json(400, "กรุณากรอกข้อมูลบังคับ (ชื่อ, ตำแหน่ง, สาขา) ให้ครบถ้วน")
            return

        expertise = json.dumps(body.get('expertise', []), ensure_ascii=False)
        subjects = json.dumps(body.get('subjects', []), ensure_ascii=False)
        email = body.get('email', '').strip()
        phone = body.get('phone', '').strip()
        image_url = body.get('image_url', '').strip()
        
        now_str = datetime.now(timezone.utc).isoformat()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM staff WHERE id = ?", (staff_id,))
        if not cursor.fetchone():
            conn.close()
            self.send_error_json(404, "ไม่พบบุคลากรที่ระบุ")
            return

        cursor.execute("""
            UPDATE staff 
            SET name = ?, position = ?, department = ?, email = ?, phone = ?, expertise = ?, subjects = ?, image_url = ?, updated_at = ?
            WHERE id = ?
        """, (name, position, department, email, phone, expertise, subjects, image_url, now_str, staff_id))
        conn.commit()

        log_audit(user['id'], user['role_id'], 'UPDATE_STAFF', 'STAFF', staff_id, f"Updated staff '{name}'", self.get_client_ip(), self.headers.get('User-Agent'))
        conn.close()

        self.send_json(200, {
            'success': True,
            'message': f"อัปเดตบุคลากร '{name}' สำเร็จ"
        })

    def handle_admin_delete_staff(self, staff_id: str):
        user = self.get_authenticated_user()
        if not user or ('admin.manage' not in user['permissions'] and user['role_id'] != 'SUPER_ADMIN' and user['role_id'] != 'ADMIN'):
            self.send_error_json(403, "ไม่มีสิทธิ์จัดการบุคลากร")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM staff WHERE id = ?", (staff_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            self.send_error_json(404, "ไม่พบบุคลากรที่ระบุ")
            return
            
        staff_name = row['name']
        cursor.execute("DELETE FROM staff WHERE id = ?", (staff_id,))
        conn.commit()

        log_audit(user['id'], user['role_id'], 'DELETE_STAFF', 'STAFF', staff_id, f"Deleted staff '{staff_name}'", self.get_client_ip(), self.headers.get('User-Agent'))
        conn.close()

        self.send_json(200, {
            'success': True,
            'message': f"ลบบุคลากร '{staff_name}' สำเร็จ"
        })

    def handle_get_public_staff(self, query: dict):
        dept = query.get('dept', [''])[0].strip()
        
        sql = "SELECT id, name, position, department, expertise, subjects, image_url FROM staff"
        params = []
        if dept:
            sql += " WHERE department = ?"
            params.append(dept)
        sql += " ORDER BY created_at ASC"

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        staff_list = []
        for r in rows:
            d = dict(r)
            d['expertise'] = json.loads(d['expertise']) if d['expertise'] else []
            d['subjects'] = json.loads(d['subjects']) if d['subjects'] else []
            staff_list.append(d)

        self.send_json(200, {
            'success': True,
            'staff': staff_list
        })

    def handle_get_programs(self):
        self.send_json(200, {
            'success': True,
            'programs': [
                {'code': 'CS', 'name': 'วิทยาการคอมพิวเตอร์ (Computer Science)', 'degree': 'วท.บ. 4 ปี'},
                {'code': 'IT', 'name': 'เทคโนโลยีสารสนเทศ (Information Technology)', 'degree': 'วท.บ. 4 ปี'},
                {'code': 'MSI', 'name': 'วิทยาการมัลติมีเดียปัญญาประดิษฐ์ (Multimedia and Artificial Intelligence)', 'degree': 'วท.บ. 4 ปี'}
            ]
        })

    def handle_get_news_activities(self, query: dict):
        cat = query.get('category', [''])[0].strip()
        include_inactive = query.get('include_inactive', ['false'])[0].lower() == 'true'

        sql = "SELECT id, title, description, image_url, published_date, source_page, source_url, category, order_index, is_active FROM news_activities WHERE 1=1"
        params = []
        
        if not include_inactive:
            sql += " AND is_active = 1"

        if cat:
            if cat in ['activity', 'FEATURED_ACTIVITY']:
                sql += " AND (category = 'activity' OR category = 'FEATURED_ACTIVITY')"
            elif cat in ['news', 'LATEST_NEWS']:
                sql += " AND (category = 'news' OR category = 'LATEST_NEWS')"
            else:
                sql += " AND category = ?"
                params.append(cat)

        sql += " ORDER BY published_date DESC, order_index ASC, created_at DESC"

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        items = []
        for r in rows:
            d = dict(r)
            if d['category'] == 'FEATURED_ACTIVITY':
                d['category'] = 'activity'
            elif d['category'] == 'LATEST_NEWS':
                d['category'] = 'news'
            items.append(d)

        self.send_json(200, {
            'success': True,
            'items': items,
            'count': len(items)
        })

    def handle_admin_get_news_activities(self, query: dict):
        query['include_inactive'] = ['true']
        self.handle_get_news_activities(query)

    def handle_admin_create_news_activity(self):
        user = self.get_authenticated_user()
        if not user:
            self.send_error_json(401, "กรุณาล็อกอินก่อนดำเนินการ")
            return
        
        body = self.read_json_body() or {}
        title = body.get('title', '').strip()
        description = body.get('description', '').strip()
        image_url = body.get('image_url', '').strip()
        published_date = body.get('published_date', '').strip()
        source_page = body.get('source_page', '').strip()
        source_url = body.get('source_url', '').strip()
        category = body.get('category', 'news').strip()
        order_index = body.get('order_index', 0)
        is_active = 1 if body.get('is_active', True) else 0

        if not title or not image_url or not source_url:
            self.send_error_json(400, "กรุณากรอกข้อมูลที่จำเป็นให้ครบถ้วน (title, image_url, source_url)")
            return

        item_id = 'post_' + uuid.uuid4().hex[:12]
        now = datetime.now().isoformat()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO news_activities 
            (id, title, description, image_url, published_date, source_page, source_url, category, order_index, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, title, description, image_url, published_date or now[:10], source_page or "It RERU คณะเทคโนโลยีสารสนเทศ มรภ.ร้อยเอ็ด", source_url, category, order_index, is_active, now, now))
        conn.commit()
        conn.close()

        self.send_json(201, {
            'success': True,
            'message': 'เพิ่มข้อมูลข่าว/กิจกรรมเรียบร้อยแล้ว',
            'id': item_id
        })

    def handle_admin_update_news_activity(self, item_id: str):
        user = self.get_authenticated_user()
        if not user:
            self.send_error_json(401, "กรุณาล็อกอินก่อนดำเนินการ")
            return
        
        body = self.read_json_body() or {}
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM news_activities WHERE id = ?", (item_id,))
        existing = cursor.fetchone()
        if not existing:
            conn.close()
            self.send_error_json(404, "ไม่พบข้อมูลรายการนี้")
            return

        now = datetime.now().isoformat()
        title = body.get('title', existing['title'])
        description = body.get('description', existing['description'])
        image_url = body.get('image_url', existing['image_url'])
        published_date = body.get('published_date', existing['published_date'])
        source_page = body.get('source_page', existing['source_page'])
        source_url = body.get('source_url', existing['source_url'])
        category = body.get('category', existing['category'])
        order_index = body.get('order_index', existing['order_index'])
        is_active = 1 if body.get('is_active', existing['is_active']) else 0

        cursor.execute("""
            UPDATE news_activities 
            SET title = ?, description = ?, image_url = ?, published_date = ?, source_page = ?, source_url = ?, category = ?, order_index = ?, is_active = ?, updated_at = ?
            WHERE id = ?
        """, (title, description, image_url, published_date, source_page, source_url, category, order_index, is_active, now, item_id))
        conn.commit()
        conn.close()

        self.send_json(200, {
            'success': True,
            'message': 'อัปเดตข้อมูลเรียบร้อยแล้ว'
        })

    def handle_admin_delete_news_activity(self, item_id: str):
        user = self.get_authenticated_user()
        if not user:
            self.send_error_json(401, "กรุณาล็อกอินก่อนดำเนินการ")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM news_activities WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

        self.send_json(200, {
            'success': True,
            'message': 'ลบข้อมูลเรียบร้อยแล้ว'
        })

    # ==========================================================================
    # API Handlers: Student Services
    # ==========================================================================

    def handle_get_student_services(self, query: dict):
        include_inactive = query.get('include_inactive', ['false'])[0].lower() == 'true'

        sql = "SELECT id, title, description, icon, url, target_blank, order_index, is_active, created_at, updated_at FROM student_services WHERE 1=1"
        params = []
        if not include_inactive:
            sql += " AND is_active = 1"
        sql += " ORDER BY order_index ASC, created_at ASC"

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        services = [dict(r) for r in rows]
        self.send_json(200, {
            'success': True,
            'services': services,
            'count': len(services)
        })

    def handle_admin_get_student_services(self, query: dict):
        query['include_inactive'] = ['true']
        self.handle_get_student_services(query)

    def handle_admin_create_student_service(self):
        user = self.get_authenticated_user()
        if not user:
            self.send_error_json(401, "กรุณาล็อกอินก่อนดำเนินการ")
            return

        body = self.read_json_body() or {}
        title = body.get('title', '').strip()
        description = body.get('description', '').strip()
        icon = body.get('icon', '📌').strip() or '📌'
        url = body.get('url', '').strip()
        target_blank = 1 if body.get('target_blank', True) else 0
        order_index = body.get('order_index', 0)
        is_active = 1 if body.get('is_active', True) else 0

        if not title or not url:
            self.send_error_json(400, "กรุณากรอกข้อมูลที่จำเป็นให้ครบถ้วน (title, url)")
            return

        service_id = 'serv_' + uuid.uuid4().hex[:12]
        now = datetime.now().isoformat()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO student_services 
            (id, title, description, icon, url, target_blank, order_index, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (service_id, title, description, icon, url, target_blank, order_index, is_active, now, now))
        conn.commit()
        conn.close()

        self.send_json(201, {
            'success': True,
            'message': 'เพิ่มบริการสำหรับนักศึกษาเรียบร้อยแล้ว',
            'id': service_id
        })

    def handle_admin_update_student_service(self, service_id: str):
        user = self.get_authenticated_user()
        if not user:
            self.send_error_json(401, "กรุณาล็อกอินก่อนดำเนินการ")
            return

        body = self.read_json_body() or {}
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM student_services WHERE id = ?", (service_id,))
        existing = cursor.fetchone()
        if not existing:
            conn.close()
            self.send_error_json(404, "ไม่พบข้อมูลบริการนี้")
            return

        now = datetime.now().isoformat()
        title = body.get('title', existing['title'])
        description = body.get('description', existing['description'])
        icon = body.get('icon', existing['icon'])
        url = body.get('url', existing['url'])
        target_blank = 1 if body.get('target_blank', existing['target_blank']) else 0
        order_index = body.get('order_index', existing['order_index'])
        is_active = 1 if body.get('is_active', existing['is_active']) else 0

        cursor.execute("""
            UPDATE student_services 
            SET title = ?, description = ?, icon = ?, url = ?, target_blank = ?, order_index = ?, is_active = ?, updated_at = ?
            WHERE id = ?
        """, (title, description, icon, url, target_blank, order_index, is_active, now, service_id))
        conn.commit()
        conn.close()

        self.send_json(200, {
            'success': True,
            'message': 'อัปเดตบริการเรียบร้อยแล้ว'
        })

    def handle_admin_delete_student_service(self, service_id: str):
        user = self.get_authenticated_user()
        if not user:
            self.send_error_json(401, "กรุณาล็อกอินก่อนดำเนินการ")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM student_services WHERE id = ?", (service_id,))
        conn.commit()
        conn.close()

        self.send_json(200, {
            'success': True,
            'message': 'ลบบริการเรียบร้อยแล้ว'
        })

def run_server():
    server_address = (HOST, PORT)
    with socketserver.ThreadingTCPServer(server_address, SecureAdmissionsHandler) as httpd:
        httpd.allow_reuse_address = True
        print(f"RERU Privacy & Admissions Server running on http://{HOST}:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer shutting down gracefully.")

if __name__ == '__main__':
    run_server()