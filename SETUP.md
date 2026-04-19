# ZenTable — Setup Guide

## Prerequisites

- Python 3.11+ (see `.python-version`)
- PostgreSQL (running locally or remote)
- Node.js (for GLB optimization)
- Git

---

## 1. Clone & Install

```bash
git clone <your-repo-url>
cd zentable

pip install -r requirements.txt
```

---

## 2. Environment Variables

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://user:password@host:5432/dbname
SECRET_KEY=your-secret-key-here
GLB_SECRET=your-glb-secret-here
GEMINI_API_KEY=your-gemini-api-key

# R2 (optional — USE_R2=false pe local storage use hogi)
USE_R2=false
R2_ACCOUNT_ID=
R2_ACCESS_KEY=
R2_SECRET_KEY=
R2_BUCKET=
R2_PUBLIC_URL=
```

Generate secure keys:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Run this twice — once for `SECRET_KEY`, once for `GLB_SECRET`.

---

## 3. Database Setup

```bash
python database.py
```

This creates all tables. Safe to run multiple times — uses `CREATE TABLE IF NOT EXISTS`.

Tables created: `tables`, `orders`, `bills`, `staff`, `branches`, `admins`, `restaurants`, `trash_meta`

---

## 4. Create First Admin

```bash
python create_first_admin.py
```

This creates the ZenTable admin account used to access `/admin`.

---

## 5. Run

```bash
uvicorn main:app --reload
```

### Pages

| URL | Description |
|---|---|
| `http://localhost:8000/` | ZenTable landing page |
| `http://localhost:8000/admin/login` | Admin login |
| `http://localhost:8000/admin` | Admin panel |
| `http://localhost:8000/login` | Staff login |
| `http://localhost:8000/{client_id}` | Restaurant home page |
| `http://localhost:8000/{client_id}/menu` | Digital menu (no table) |
| `http://localhost:8000/{client_id}/ar-menu` | AR menu (no table) |
| `http://localhost:8000/{client_id}/table/{table_no}` | Table landing page |
| `http://localhost:8000/{client_id}/table/{table_no}/menu` | Menu for specific table |
| `http://localhost:8000/{client_id}/table/{table_no}/ar-menu` | AR menu for specific table |
| `http://localhost:8000/{client_id}/staff/owner` | Owner dashboard |
| `http://localhost:8000/{client_id}/staff/waiter` | Waiter interface |
| `http://localhost:8000/{client_id}/staff/kitchen` | Kitchen display |
| `http://localhost:8000/{client_id}/staff/counter` | Counter interface |

---

## 6. Onboard a Restaurant

Restaurant config ab JSON files mein nahi hoti — **PostgreSQL `restaurants` table (JSONB)** mein store hoti hai.

### 6a. Admin panel se create karo

`/admin` → "New Restaurant" → fill in details → Create

Ya CLI se:
```bash
python manage_restaurant.py
```

### 6b. Assets upload karo

Admin panel → Restaurant → Assets tab se upload karo:

```
Images (static/assets/{client_id}/ ya R2):
├── logo.png              # Transparent PNG, 500x500px recommended
├── banner.png            # Hero banner, 1920x1080px recommended
├── targets.mind          # AR target file
└── *.jpg / *.webp        # Dish images

3D Models (private/assets/{client_id}/ ya R2):
└── *.glb                 # AR models — auto-optimized on upload
```

**Note:** `USE_R2=true` hone pe files Cloudflare R2 pe jaati hain — local disk pe nahi. Render pe production deployment ke liye R2 zaroori hai (ephemeral disk).

### 6c. Staff accounts banao

Admin panel → Restaurant → Staff tab → Create staff accounts (owner, waiter, kitchen, counter).

---

## 7. AR Setup

### Create AR target

1. Go to [MindAR Compiler](https://hiukim.github.io/mind-ar-js-doc/tools/compile)
2. Upload restaurant logo or a high-contrast custom marker (1024×1024px recommended)
3. Download `targets.mind`
4. Admin panel se upload karo (type: mind)

### 3D models

- Format: `.glb` (compressed GLTF)
- Size: under 3MB recommended (audit report upload pe automatically milta hai)
- Poly count: under 20K for smooth mobile AR
- Free sources: [Sketchfab](https://sketchfab.com), [CGTrader](https://cgtrader.com)
- Admin panel se upload karo (type: model) — auto-optimized ho jaata hai

### GLB Optimizer (manual use)

```bash
# Install once
npm install -g @gltf-transform/cli

# Run manually
python glb_optimizer.py input.glb output.glb
```

Upload pe automatically optimize + audit hota hai agar `gltf-transform` installed ho.

**Note:** AR requires HTTPS in production. Camera API plain HTTP pe kaam nahi karta.

---

## 8. Trash System

Upload pe purani file automatically trash mein jaati hai (30 din tak recoverable).

Admin panel → Trash tab:
- **Restore** — file wapas original location pe
- **Delete** — permanently delete
- **Auto-purge** — 30 din baad server restart pe automatic delete

Trash metadata PostgreSQL `trash_meta` table mein store hoti hai — Render restarts pe safe.

---

## 9. Test on Phone (Local)

```bash
# Find your local IP
ipconfig          # Windows
ifconfig          # Mac/Linux

# Access from phone on same WiFi
http://YOUR_IP:8000/{client_id}/ar-menu
```

---

## 10. Production Deployment

### Checklist

- [ ] HTTPS enabled (required for AR/camera)
- [ ] `DATABASE_URL` set to production PostgreSQL
- [ ] `SECRET_KEY` and `GLB_SECRET` set to strong random values
- [ ] `USE_R2=true` + R2 credentials set (Render disk ephemeral hai)
- [ ] `.env` not committed to Git
- [ ] `create_first_admin.py` run once on server
- [ ] Assets uploaded via admin panel
- [ ] Tested on Android and iOS

### Run command

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

### Recommended hosting

- **Render** (currently used) — free tier available, auto-deploy from Git
- DigitalOcean App Platform
- Railway
- AWS EC2 / Google Cloud Run

---

## Troubleshooting

| Issue | Fix |
|---|---|
| AR camera not starting | HTTPS required — plain HTTP pe kaam nahi karta |
| 3D models not loading | Check JSON mein `model` field ka path — `{client_id}/file.glb` format hona chahiye |
| AR target not detecting | High-contrast image use karo, good lighting, marker size 10cm+ |
| Fonts not loading | Google Fonts require internet connection |
| DB connection error | `DATABASE_URL` in `.env` check karo, PostgreSQL running hai? |
| Upload 500 error (Windows) | File lock issue — `copy2 + os.remove` use hota hai, normal hai |
| GLB audit shows warnings | `npm install -g @gltf-transform/cli` run karo — optimization enable hogi |
| `static_v` undefined error | `templates_env.py` se `templates` import karo — apna instance mat banao routers mein |
