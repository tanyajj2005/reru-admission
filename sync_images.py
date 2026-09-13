import os, json, shutil, secrets
from datetime import datetime, timezone
import db

def sync():
    conn = db.get_db()
    cursor = conn.cursor()
    
    # ensure dest folder exists
    os.makedirs('images/staff', exist_ok=True)
    
    files = os.listdir('image')
    
    # get existing staff
    cursor.execute("SELECT id, name FROM staff")
    existing_staff = cursor.fetchall()
    
    for f in files:
        if not f.lower().endswith('.jpg') and not f.lower().endswith('.png'):
            continue
            
        # e.g., 'อ.กล้า msi.jpg' -> 'อ.กล้า', 'msi'
        base = os.path.splitext(f)[0]
        parts = base.split(' ')
        if len(parts) >= 2:
            dept = parts[-1].upper() # 'MSI', 'CS', 'IT'
            raw_name = ' '.join(parts[:-1]) # 'อ.กล้า'
        else:
            dept = 'CS'
            raw_name = base
            
        # copy file
        dest_filename = f"{secrets.token_hex(4)}_{f}"
        dest_path = os.path.join('images', 'staff', dest_filename)
        shutil.copy2(os.path.join('image', f), dest_path)
        
        image_url = f"images/staff/{dest_filename}"
        
        # Check if already in DB
        matched_id = None
        for row in existing_staff:
            # simple match: if raw_name without 'อ.' is in the full name
            clean_name = raw_name.replace('อ.', '').replace('ดร.', '').strip()
            if clean_name in row['name']:
                matched_id = row['id']
                break
                
        if matched_id:
            # Update existing
            cursor.execute("UPDATE staff SET image_url = ?, department = ? WHERE id = ?", (image_url, dept, matched_id))
            print(f"Updated {row['name']} with {image_url}")
        else:
            # Insert new
            new_id = f"stf_{secrets.token_hex(6)}"
            now_str = datetime.now(timezone.utc).isoformat()
            expertise = json.dumps(["อยู่ระหว่างปรับปรุง"], ensure_ascii=False)
            subjects = json.dumps(["อยู่ระหว่างปรับปรุง"], ensure_ascii=False)
            
            cursor.execute("""
                INSERT INTO staff (id, name, position, department, email, phone, expertise, subjects, image_url, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_id, raw_name, "อาจารย์", dept, "", "", expertise, subjects, image_url, now_str, now_str))
            print(f"Inserted new staff {raw_name} ({dept}) with {image_url}")
            
    conn.commit()
    conn.close()

if __name__ == '__main__':
    sync()
