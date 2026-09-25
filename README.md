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

ถ้าเปิดหน้าเว็บผ่าน HTTPS (เช่น GitHub Pages) เบราว์เซอร์จะบล็อกเรียก HTTP  
ให้เปิด `index.html` ตรงๆ หรือใส่ HTTPS ให้พอร์ต 8001

## ออนไลน์หน้าเว็บผ่าน GitHub Pages

เครื่องนี้ยังไม่มี Git จึงต้องติดตั้งก่อน: [https://git-scm.com/download/win](https://git-scm.com/download/win)

จากนั้นในโฟลเดอร์โปรเจกต์:

```powershell
git init
git add .
git commit -m "Add Outlook login and Rockstar code puller"
gh repo create rockstar-code-puller --public --source=. --remote=origin --push
```

ถ้ายังไม่มี `gh` ให้สร้างรีโปว่างบน github.com แล้ว:

```powershell
git remote add origin https://github.com/USERNAME/rockstar-code-puller.git
git branch -M main
git push -u origin main
```

เปิด GitHub Pages:

1. เข้า repo บน GitHub
2. **Settings → Pages**
3. Source เลือก **Deploy from a branch**
4. Branch เลือก `main` โฟลเดอร์ `/ (root)`
5. กด Save

ได้ลิงก์ประมาณ `https://USERNAME.github.io/rockstar-code-puller/`

ไฟล์ `CNAME` ชี้ `outlo0k.online`  
ถ้าจะใช้โดเมนนี้กับหน้าเว็บ ต้องไปที่ DNS ของโดเมนแล้วเพิ่มเรคคอร์ดตามที่ GitHub บอก  
**อย่าใช้โดเมนเดียวกันกับหลังบ้าน** — หน้าเว็บอยู่ GitHub Pages หลังบ้านอยู่ VPS คนละโฮสต์ เช่น `api.outlo0k.online`

## ข้อควรรู้

ใช้กับเมลที่คุณมีสิทธิ์เท่านั้น  
อย่าอัปโหลด `ids.txt` ขึ้น GitHub
