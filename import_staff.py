import json
from datetime import datetime, timezone
import secrets
from db import get_db

conn = get_db()
cursor = conn.cursor()

# Clear existing staff
cursor.execute("DELETE FROM staff")

now_str = datetime.now(timezone.utc).isoformat()

staff_members = [
    {
        "name": "ผู้ช่วยศาสตราจารย์ ดร.นิธิศ วังโน",
        "position": "ผู้ช่วยศาสตราจารย์",
        "department": "CS",
        "expertise": ["อยู่ระหว่างปรับปรุง"],
        "subjects": ["อยู่ระหว่างปรับปรุง"],
        "image_url": "images/staff/nithit.jpg"
    },
    {
        "name": "ผู้ช่วยศาสตราจารย์วาทินี ดวงอ่อนนาม",
        "position": "ผู้ช่วยศาสตราจารย์",
        "department": "CS",
        "expertise": ["อยู่ระหว่างปรับปรุง"],
        "subjects": ["อยู่ระหว่างปรับปรุง"],
        "image_url": "images/staff/watinee.jpg"
    },
    {
        "name": "อาจารย์วรพจน์ พรหมจักร",
        "position": "อาจารย์",
        "department": "CS",
        "expertise": ["อยู่ระหว่างปรับปรุง"],
        "subjects": ["อยู่ระหว่างปรับปรุง"],
        "image_url": "images/staff/worapot.jpg"
    },
    {
        "name": "นายฉัตรฐพล ต้นสุวรรณ",
        "position": "เจ้าหน้าที่",
        "department": "CS",
        "expertise": ["อยู่ระหว่างปรับปรุง"],
        "subjects": ["อยู่ระหว่างปรับปรุง"],
        "image_url": "images/staff/chattapon.jpg"
    },
    {
        "name": "นางสาววิภาวี หงษ์สามสิบเอ็ด",
        "position": "เจ้าหน้าที่",
        "department": "CS",
        "expertise": ["อยู่ระหว่างปรับปรุง"],
        "subjects": ["อยู่ระหว่างปรับปรุง"],
        "image_url": "images/staff/wipawee.jpg"
    }
]

for s in staff_members:
    new_id = f"stf_{secrets.token_hex(6)}"
    exp_str = json.dumps(s['expertise'], ensure_ascii=False)
    sub_str = json.dumps(s['subjects'], ensure_ascii=False)
    
    cursor.execute("""
        INSERT INTO staff (id, name, position, department, email, phone, expertise, subjects, image_url, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (new_id, s['name'], s['position'], s['department'], "", "", exp_str, sub_str, s['image_url'], now_str, now_str))

conn.commit()
conn.close()
print("Staff imported successfully!")
