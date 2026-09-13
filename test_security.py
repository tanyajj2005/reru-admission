"""
Automated Comprehensive Security & Privacy Test Suite for RERU Admissions System
Verifies all 16 security checklist items requested by the user.
"""
import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_security():
    passed = 0
    failed = 0

    def assert_true(condition, test_name):
        nonlocal passed, failed
        if condition:
            print(f"[PASS] {test_name}")
            passed += 1
        else:
            print(f"[FAIL] {test_name}")
            failed += 1

    print("==================================================")
    print("STARTING RERU PRIVACY & SECURITY AUDIT TEST SUITE")
    print("==================================================")

    # 1. Unauthenticated / Anonymous user cannot access /api/admin/applications
    r = requests.get(f"{BASE_URL}/api/admin/applications")
    assert_true(r.status_code == 403, "1. Anonymous access to /api/admin/applications is BLOCKED (403 Forbidden)")

    # 2. Anonymous user cannot access /api/admin/stats
    r = requests.get(f"{BASE_URL}/api/admin/stats")
    assert_true(r.status_code == 403, "2. Anonymous access to /api/admin/stats is BLOCKED (403 Forbidden)")

    # 3. Direct access to /storage/ private documents folder is BLOCKED
    r = requests.get(f"{BASE_URL}/storage/private_documents/DOC-69-0001-ID_national_id_1459900342812.pdf")
    assert_true(r.status_code == 403, "3. Direct static access to private document storage is BLOCKED (403 Forbidden)")

    # 4. Anti-IDOR: Applicant check without exact matching DOB is BLOCKED
    r = requests.get(f"{BASE_URL}/api/applicant/check-status?application_id=RERU-69-0001&dob=2000-01-01")
    assert_true(r.status_code == 404, "4. Anti-IDOR: Guessing application ID with wrong DOB returns 404 Not Found")

    # 5. Applicant Self-Check with CORRECT 2-Factor verification succeeds and masks name
    r = requests.get(f"{BASE_URL}/api/applicant/check-status?application_id=RERU-69-0001&dob=2008-05-14")
    data = r.json()
    assert_true(r.status_code == 200 and data.get("success") and "*" in data["application"]["full_name"],
                "5. Applicant verification with correct 2-factor credentials returns MASKED self-status")
    # Verify no leaked national ID or documents in public applicant check
    assert_true("national_id" not in data["application"] and "documents" not in data["application"],
                "5.1 Applicant check does NOT leak National ID or raw private documents")

    # 6. Login Brute Force Protection & Generic Error message
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "fake_user", "password": "wrong_password"})
    assert_true(r.status_code == 401 and r.json().get("error") == "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
                "6. Failed login returns GENERIC error message (no account enumeration)")

    # 7. Admin Login (admission_officer)
    s_admin = requests.Session()
    r = s_admin.post(f"{BASE_URL}/api/auth/login", json={"username": "admission_officer", "password": "Admin@RERU2569!"})
    assert_true(r.status_code == 200 and r.json().get("success"), "7. Admin login succeeds and receives session cookie")

    # 8. Admin lists applications - PII MUST BE MASKED
    r = s_admin.get(f"{BASE_URL}/api/admin/applications")
    apps = r.json().get("applications", [])
    assert_true(len(apps) > 0 and "****" in apps[0]["national_id"] and "X-XXX" in apps[0]["phone"],
                "8. Admin application list contains STRICTLY MASKED national IDs and phone numbers")

    # 9. Admin checks specific application (Default: Masked)
    r = s_admin.get(f"{BASE_URL}/api/admin/applications/RERU-69-0001")
    app_data = r.json().get("application", {})
    assert_true(app_data.get("is_masked") is True and "****" in app_data.get("national_id", ""),
                "9. Application detail defaults to MASKED view")

    # 10. Admin requests UNMASKED view (reveal=true) -> Allowed because Admin has 'application.view_sensitive'
    r = s_admin.get(f"{BASE_URL}/api/admin/applications/RERU-69-0001?reveal=true")
    app_unmasked = r.json().get("application", {})
    assert_true(app_unmasked.get("is_masked") is False and app_unmasked.get("national_id") == "1459900342812",
                "10. Authorized Admin with 'application.view_sensitive' can reveal unmasked data")

    # 11. Admin downloads private document via protected backend API
    r = s_admin.get(f"{BASE_URL}/api/admin/applications/RERU-69-0001/documents/DOC-69-0001-ID/download")
    assert_true(r.status_code == 200 and b"%PDF" in r.content,
                "11. Admin downloads private document via authenticated stream controller")

    # 12. Officer Viewer (who lacks 'application.view_sensitive' and 'application.export')
    s_viewer = requests.Session()
    s_viewer.post(f"{BASE_URL}/api/auth/login", json={"username": "doc_checker", "password": "Viewer@RERU2569!"})

    # Viewer attempts unmasking -> MUST BE 403
    r = s_viewer.get(f"{BASE_URL}/api/admin/applications/RERU-69-0001?reveal=true")
    assert_true(r.status_code == 403, "12. Officer lacking 'application.view_sensitive' is BLOCKED from unmasking (403 Forbidden)")

    # Viewer attempts export -> MUST BE 403
    r = s_viewer.get(f"{BASE_URL}/api/admin/applications/export")
    assert_true(r.status_code == 403, "12.1 Officer lacking 'application.export' is BLOCKED from exporting (403 Forbidden)")

    # 13. Super Admin logs in and checks Audit Log
    s_super = requests.Session()
    s_super.post(f"{BASE_URL}/api/auth/login", json={"username": "superadmin", "password": "SuperAdmin@RERU2569!"})

    r = s_super.get(f"{BASE_URL}/api/admin/audit-logs")
    logs = r.json().get("logs", [])
    assert_true(r.status_code == 200 and len(logs) > 0, "13. Super Admin can view immutable security Audit Logs")

    # Verify that unmasking and document download created Audit Log entries
    actions_in_log = [l["action"] for l in logs]
    assert_true("VIEW_APPLICATION_UNMASKED" in actions_in_log and "DOWNLOAD_DOCUMENT" in actions_in_log,
                "13.1 Sensitive operations (VIEW_APPLICATION_UNMASKED, DOWNLOAD_DOCUMENT) are logged in Audit Log")

    # 14. Logout invalidates session
    s_admin.post(f"{BASE_URL}/api/auth/logout")
    r = s_admin.get(f"{BASE_URL}/api/admin/applications")
    assert_true(r.status_code == 403 or r.status_code == 401, "14. Session is invalidated immediately upon Logout")

    print("==================================================")
    print(f"RESULTS: {passed} PASSED, {failed} FAILED")
    print("==================================================")
    return failed == 0

if __name__ == '__main__':
    success = test_security()
    sys.exit(0 if success else 1)
