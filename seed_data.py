"""
Seed script to create default Super Admin, Admin, Officer accounts,
confidential test applications, and private applicant documents.
"""
import os
import secrets
from datetime import datetime, timezone
from db import init_db, get_db
from security import hash_password

PRIVATE_STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'storage', 'private_documents')

def seed_data():
    init_db()
    os.makedirs(PRIVATE_STORAGE_DIR, exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    now = datetime.now(timezone.utc).isoformat()

    # 1. Create Default Administrative Users
    # In production, passwords are changed upon first login.
    # Passwords hashed with Argon2id.
    users = [
        ('usr_main_admin', 'admin', 'admin@reru.ac.th', '123456', 'ผู้ดูแลระบบ', 'SUPER_ADMIN'),
        ('usr_superadmin', 'superadmin', 'superadmin@reru.ac.th', 'SuperAdmin@RERU2569!', 'นายอภิสิทธิ์ ผู้ดูแลระบบสูงสุด', 'SUPER_ADMIN'),
        ('usr_admin', 'admission_officer', 'admission@reru.ac.th', 'Admin@RERU2569!', 'นางสาวพรพิมล งานรับสมัคร', 'ADMIN'),
        ('usr_viewer', 'doc_checker', 'checker@reru.ac.th', 'Viewer@RERU2569!', 'นายสมเจตน์ เจ้าหน้าที่ตรวจสอบเอกสาร', 'OFFICER_VIEWER')
    ]

    for uid, username, email, raw_pwd, fullname, role in users:
        pwd_hash = hash_password(raw_pwd)
        cursor.execute("""
            INSERT OR REPLACE INTO users (id, username, email, password_hash, full_name, role_id, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (uid, username, email, pwd_hash, fullname, role, now))

    # 2. Create Confidential Sample Applications
    sample_apps = [
        (
            'RERU-69-0001',
            '1459900342812',
            'นายธนากร รัตนกุล',
            '2008-05-14',
            'ชาย',
            '0812345678',
            'thanakorn.r@example.com',
            '123 หมู่ 4 ต.ในเมือง อ.เมือง จ.ร้อยเอ็ด 45000',
            'โรงเรียนร้อยเอ็ดวิทยาลัย',
            3.85,
            'ร้อยเอ็ด',
            'CS',
            'วิทยาการคอมพิวเตอร์',
            'รอบที่ 2 (โควตา)',
            2569,
            'APPROVED',
            'คุณสมบัติครบถ้วน ผลการเรียนดีเด่น มีแฟ้มสะสมงานด้านการแข่งขันโอลิมปิกวิชาการคอมพิวเตอร์'
        ),
        (
            'RERU-69-0002',
            '1409900874125',
            'นางสาวกานดา สุวรรณฉวี',
            '2008-08-22',
            'หญิง',
            '0897654321',
            'kanda.s@example.com',
            '45/2 หมู่ 8 ต.สระคู อ.สุวรรณภูมิ จ.ร้อยเอ็ด 45130',
            'โรงเรียนสุวรรณภูมิพิทยไพศาล',
            3.62,
            'ร้อยเอ็ด',
            'IT',
            'เทคโนโลยีสารสนเทศ',
            'รอบที่ 2 (โควตา)',
            2569,
            'PENDING',
            'รอตรวจทานความชัดเจนของสำเนาบัตรประชาชน'
        ),
        (
            'RERU-69-0003',
            '1479900215984',
            'นายภานุพงศ์ ทิพย์มณฑา',
            '2008-02-10',
            'ชาย',
            '0921144558',
            'panupong.t@example.com',
            '78 หมู่ 1 ต.เมืองทราย อ.เสลภูมิ จ.ร้อยเอ็ด 45120',
            'โรงเรียนเสลภูมิพิทยาคม',
            3.45,
            'ร้อยเอ็ด',
            'MSI',
            'วิทยาการมัลติมีเดียปัญญาประดิษฐ์',
            'รอบที่ 2 (โควตา)',
            2569,
            'PENDING',
            'ส่งเอกสารครบถ้วน รอประกาศผลการคัดเลือก'
        ),
        (
            'RERU-69-0004',
            '1419900452361',
            'นางสาวศิริพร อารีย์เลิศ',
            '2007-11-30',
            'หญิง',
            '0845566778',
            'siriporn.a@example.com',
            '99/1 ต.ขอนแก่น อ.เมือง จ.ร้อยเอ็ด 45000',
            'โรงเรียนสตรีศึกษา',
            3.92,
            'ร้อยเอ็ด',
            'MSI',
            'วิทยาการมัลติมีเดียปัญญาประดิษฐ์',
            'รอบที่ 2 (โควตา)',
            2569,
            'REQUIRES_DOCS',
            'เอกสารใบ ปพ.1 ยังไม่มีตราประทับโรงเรียน เจ้าหน้าที่แจ้งให้แนบเอกสารใหม่'
        ),
        (
            'RERU-69-0005',
            '1439900781249',
            'นายปฏิภาณ กอบเกื้อ',
            '2008-04-18',
            'ชาย',
            '0869988771',
            'patiphan.k@example.com',
            '12 หมู่ 3 ต.อาจสามารถ อ.อาจสามารถ จ.ร้อยเอ็ด 45160',
            'โรงเรียนอาจสามารถวิทยา',
            2.48,
            'ร้อยเอ็ด',
            'IT',
            'เทคโนโลยีสารสนเทศ',
            'รอบที่ 1 (Portfolio)',
            2569,
            'REJECTED',
            'เกรดเฉลี่ยต่ำกว่าเกณฑ์ขั้นต่ำของสาขาวิชา (เกณฑ์ 2.50)'
        )
    ]

    for app in sample_apps:
        cursor.execute("""
            INSERT OR REPLACE INTO applications (
                id, national_id, full_name, dob, gender, phone, email, address,
                school_name, gpax, province, program_code, program_name,
                admission_round, academic_year, status, staff_notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (*app, now, now))

    # 3. Create Sample Protected Documents in Storage Directory (NOT in public folder!)
    sample_docs = [
        ('DOC-69-0001-ID', 'RERU-69-0001', 'id_card', 'national_id_1459900342812.pdf', 'application/pdf', b'%PDF-1.4 [CONFIDENTIAL ID CARD FOR RERU-69-0001]'),
        ('DOC-69-0001-TR', 'RERU-69-0001', 'transcript', 'transcript_gpax_3.85.pdf', 'application/pdf', b'%PDF-1.4 [CONFIDENTIAL TRANSCRIPT GPAX 3.85]'),
        ('DOC-69-0002-ID', 'RERU-69-0002', 'id_card', 'national_id_1409900874125.pdf', 'application/pdf', b'%PDF-1.4 [CONFIDENTIAL ID CARD FOR RERU-69-0002]'),
        ('DOC-69-0003-PF', 'RERU-69-0003', 'portfolio', 'portfolio_panupong.pdf', 'application/pdf', b'%PDF-1.4 [CONFIDENTIAL PORTFOLIO MSI PROJECT]')
    ]

    for did, aid, dtype, filename, mime, content in sample_docs:
        filepath = os.path.join(PRIVATE_STORAGE_DIR, f"{did}_{filename}")
        with open(filepath, 'wb') as f:
            f.write(content)
        filesize = len(content)

        cursor.execute("""
            INSERT OR REPLACE INTO documents (id, application_id, doc_type, file_name, storage_path, file_size, mime_type, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (did, aid, dtype, filename, filepath, filesize, mime, now))

    # 4. Insert Initial Audit Log for Seed
    cursor.execute("""
        INSERT INTO audit_logs (actor_id, actor_role, action, resource_type, resource_id, details, ip_address, created_at)
        VALUES ('SYSTEM', 'SYSTEM', 'SYSTEM_INIT', 'DATABASE', 'ALL', 'Initialized database with default security roles and privacy protections.', '127.0.0.1', ?)
    """, (now,))

    conn.commit()
    conn.close()
    print("Default accounts, confidential applications, and private storage seeded.")

if __name__ == '__main__':
    seed_data()
