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

### 6a. Create config file

Create `data/{client_id}.json` — copy `data/clint_one.json` as reference and update:

- `restaurant` — name, address, timings, contact, social
- `theme` — colors, fonts
- `items` — menu items with images, prices, AR models
- `subscription.features` — which features are enabled

### 6b. Add assets

```
static/assets/{client_id}/
├── logo.png              # Transparent PNG, 500x500px recommended
├── banner.png            # Hero banner, 1920x1080px recommended
├── targets.mind          # AR target file
└── *.jpg                 # Dish images
```

```
private/assets/{client_id}/
└── *.glb                 # 3D models for AR
```

### 6c. Create staff accounts

Use the admin panel at `/admin` to create owner, waiter, kitchen, and counter accounts for the restaurant.

---

## 7. AR Setup

### Create AR target

1. Go to [MindAR Compiler](https://hiukim.github.io/mind-ar-js-doc/tools/compile)
2. Upload restaurant logo or a high-contrast custom marker (1024×1024px recommended)
3. Download `targets.mind`
4. Place in `static/assets/{client_id}/targets.mind`

### 3D models

- Format: `.glb` (compressed GLTF)
- Size: under 5MB per model recommended
- Free sources: [Sketchfab](https://sketchfab.com), [CGTrader](https://cgtrader.com)
- Place in `private/assets/{client_id}/`
- Reference in JSON: `"model": "{client_id}/dish.glb"`

### Optimize 3D models

GLB files optimize karne ke liye — size kam hogi, loading fast hogi.

**Install once:**
```bash
npm install -g @gltf-transform/cli
```

**Run optimizer** (Two Ways):

```bash
# Option 1 — directly from Python script
python glb_optimizer.py input.glb output.glb

# Option 2 — via main.py route (automatically when upload)
# GLB_SECRET should be in .env
```

Save Optimized files in `private/assets/{client_id}/`.

**Note:** AR requires HTTPS in production. Camera API does not work on plain HTTP.

---

## 8. Test on Phone (Local)

```bash
# Find your local IP
ipconfig          # Windows
ifconfig          # Mac/Linux

# Access from phone on same WiFi
http://YOUR_IP:8000/{client_id}/ar-menu
```

---

## 9. Production Deployment

### Checklist

- [ ] HTTPS enabled (required for AR/camera)
- [ ] `DATABASE_URL` set to production PostgreSQL
- [ ] `SECRET_KEY` and `GLB_SECRET` set to strong random values
- [ ] `.env` not committed to Git
- [ ] `create_first_admin.py` run once on server
- [ ] All assets uploaded
- [ ] Tested on Android and iOS

### Run command

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

### Recommended hosting

- DigitalOcean App Platform
- Railway
- Render
- AWS EC2 / Google Cloud Run

---

## Troubleshooting

| Issue | Fix |
|---|---|
| AR camera not starting | HTTPS required — does not work on plain HTTP |
| 3D models not loading | Check file paths in JSON match actual filenames |
| AR target not detecting | Use high-contrast image, good lighting, marker size 10cm+ |
| Fonts not loading | Google Fonts require internet connection |
| DB connection error | Check `DATABASE_URL` in `.env`, verify PostgreSQL is running |
