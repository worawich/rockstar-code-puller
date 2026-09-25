# Rockstar Code Puller

หน้าเว็บดึงโค้ดยืนยัน Rockstar จาก Outlook / Hotmail  
ล็อกอินแบบเดียวกับเครื่องมือเมลใน `wichxshop-webmain`

## API

หน้าเว็บยิงไปที่ Outlook service บน VPS:

`http://141.98.17.64:8001`

- `POST /login` — ตรวจ email + password
- `POST /mails` — ดึงรายการเมล
- `POST /mail` — อ่านเนื้อหาเมล แล้วหน้าเว็บหาโค้ด Rockstar เอง

ล็อกอินด้วย email + password แล้ว Graph API ดึงข้อความเมลทั้งหมด  
token จริงอยู่ใน `ids.txt` ฝั่งเซิร์ฟเวอร์

## ขึ้นเว็บโดยไม่ต้องมีโดเมน

วาง `index.html` บน VPS แล้วเปิดพอร์ต 80 เข้าได้ที่

`http://141.98.17.64/`

```bash
sudo mkdir -p /var/www/html
sudo cp index.html /var/www/html/
sudo python3 -m http.server 80 --directory /var/www/html
```

ไม่ต้องจดโดเมนใหม่ `outlo0k.com` / `outlo0k.online` ไม่ได้ใช้แล้ว

## ข้อควรรู้

อย่าอัปโหลด `ids.txt` ขึ้น GitHub
