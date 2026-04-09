# ZenTable — Smart Dining, Reimagined

🌐 **Live at [zentable.in](https://zentable.in)**

A **multi-tenant restaurant management platform** with AR menus, real-time order management, staff workflows, and a full analytics dashboard. Built for restaurants that want a modern, end-to-end digital dining experience.

---

## Features

### For Customers
- **AR Menu** — Scan QR codes to view dishes as 3D models in augmented reality
- **Interactive Controls** — Rotate and explore dishes before ordering
- **Digital Menu** — Clean, fast, mobile-friendly menu browsing

### For Restaurant Staff
- **Waiter** — Table management, order placement, billing, payments
- **Kitchen** — Live order queue, mark items ready
- **Counter** — Table activation/deactivation, payment collection
- **Owner** — Full analytics, QR generator, staff management, order history

### For Platform Admins (ZenTable)
- **Admin Panel** — Manage all restaurants from one place
- **Per-restaurant stats** — Revenue, orders, top dishes
- **Staff management** — Create, edit, deactivate staff accounts
- **Restaurant onboarding** — Admin panel se instant setup
- **File management** — Upload images/models, trash + restore system
- **DB export** — Full PostgreSQL export as ZIP

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python — FastAPI |
| Database | PostgreSQL (psycopg2, ThreadedConnectionPool) |
| Restaurant Config | PostgreSQL `restaurants` table (JSONB) |
| Frontend | HTML, CSS, Vanilla JS (Jinja2 templates) |
| AR | MindAR + Three.js r128 |
| Auth | bcrypt + JWT (cookie-based) |
| File Storage | Cloudflare R2 (production) / local (development) |

---

## Project Structure

```
zentable/
├── main.py                      # App init, lifespan, static mount, utility routes
├── database.py                  # PostgreSQL setup + all DB functions (psycopg2)
├── auth.py                      # JWT logic — create/verify token, login functions
├── helpers.py                   # Shared helpers — get_client_data, require_auth, etc.
├── r2.py                        # Cloudflare R2 client + helper functions
├── glb_token.py                 # GLB signed token create/verify
├── trash_utils.py               # Trash file management — move, restore, delete, purge
├── templates_env.py             # Shared Jinja2 instance (globals: static_v, site)
├── site_config.py               # ZenTable platform branding
├── glb_optimizer.py             # GLB optimization + audit
├── manage_restaurant.py         # Restaurant onboarding CLI
├── create_first_admin.py        # First admin setup script
├── clean_db.py                  # DB cleanup utility
├── requirements.txt
├── .python-version              # Python 3.11
│
├── routers/
│   ├── __init__.py
│   ├── menu.py                  # GET /api/menu/{client_id}, GET /glb/{token}
│   ├── tables.py                # Table activate/close/summary API
│   ├── orders.py                # Orders + Bills API
│   ├── login.py                 # Login/logout routes
│   ├── admin.py                 # All admin routes
│   └── pages.py                 # All HTML page routes
│
├── templates/                   # Jinja2 HTML templates
├── static/
│   ├── css/
│   ├── js/
│   └── assets/
│       ├── zentable/            # Platform branding
│       ├── clint_one/           # Restaurant 1 — images + targets.mind
│       └── clint_two/           # Restaurant 2 — images + targets.mind
│
├── private/
│   ├── assets/
│   │   ├── clint_one/           # Restaurant 1 — .glb 3D models
│   │   └── clint_two/           # Restaurant 2 — .glb 3D models
│   └── trash/                   # Trashed files (local mode only)
│
└── Public_HTML/
    └── google...html            # Google Search Console verification
```

---

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL
- Node.js (for GLB optimization via gltf-transform)

### Installation

```bash
# Clone
git clone <your-repo-url>
cd zentable

# Install dependencies
pip install -r requirements.txt

# Install GLB optimizer (optional but recommended)
npm install -g @gltf-transform/cli

# Create first admin account
python create_first_admin.py

# Run
uvicorn main:app --reload
```

### Environment Variables

Create a `.env` file in the project root:
```
DATABASE_URL=postgresql://user:password@host:5432/dbname
SECRET_KEY=your-secret-key-here
GLB_SECRET=your-glb-secret-here

# R2 (optional — USE_R2=false pe local storage)
USE_R2=false
R2_ACCOUNT_ID=
R2_ACCESS_KEY=
R2_SECRET_KEY=
R2_BUCKET=
R2_PUBLIC_URL=
```

### Access

| URL | Description |
|---|---|
| `http://localhost:8000/` | ZenTable landing page |
| `http://localhost:8000/{client_id}` | Restaurant home page |
| `http://localhost:8000/{client_id}/menu` | Digital menu |
| `http://localhost:8000/{client_id}/ar-menu` | AR menu |
| `http://localhost:8000/login` | Staff login |
| `http://localhost:8000/admin` | ZenTable admin panel |

---

## Adding a Restaurant

Restaurants ab admin panel se directly create ho jaate hain (`/admin`). Manual JSON files ki zaroorat nahi.

Config structure jo DB mein store hoti hai:

```json
{
  "restaurant": {
    "name": "Restaurant Name",
    "num_tables": 10,
    "tagline": "Your tagline here",
    "logo": "/static/assets/client_id/logo.png",
    "banner": "/static/assets/client_id/banner.png",
    "description": "About your restaurant",
    "cuisine_type": "North Indian",
    "phone": "+91 XXXXX XXXXX",
    "email": "contact@restaurant.com",
    "address": "Full address",
    "timings": {
      "lunch": "12:00 PM - 3:30 PM",
      "dinner": "7:00 PM - 11:30 PM",
      "closed": "Monday"
    },
    "social": {
      "instagram": "https://instagram.com/...",
      "facebook": "",
      "twitter": ""
    }
  },
  "theme": {
    "primary_color": "#D4AF37",
    "secondary_color": "#1a1a1a",
    "accent_color": "#8B4513",
    "text_color": "#333333",
    "background": "#ffffff",
    "font_primary": "Playfair Display",
    "font_secondary": "Poppins"
  },
  "items": [
    {
      "name": "Butter Chicken",
      "description": "Tender chicken in rich tomato-butter gravy",
      "image": "/static/assets/client_id/butter_chicken.jpg",
      "price": "INR 450",
      "veg": false,
      "featured": true,
      "category": "Main Course",
      "ingredients": "Chicken, Tomatoes, Butter, Cream",
      "model": "client_id/dish.glb",
      "position": "0 0 0",
      "scale": "2 2 2",
      "rotation": "0 0 0",
      "auto_rotate": true,
      "rotate_speed": 8000
    }
  ],
  "subscription": {
    "active": true,
    "features": ["basic", "ordering", "analytics", "ar_menu"]
  }
}
```

---

## Staff Roles

| Role | Access |
|---|---|
| `owner` | Analytics, QR generator, staff management, full order history |
| `waiter` | Table management, order placement, order lifecycle, billing |
| `kitchen` | Live order queue, mark items as ready |
| `counter` | Table activate/deactivate, payment collection |

---

## AR Setup

### Creating AR Targets

1. Go to [MindAR Compiler](https://hiukim.github.io/mind-ar-js-doc/tools/compile)
2. Upload restaurant logo or menu cover image (1024×1024px recommended, high contrast)
3. Download `targets.mind`
4. Upload via admin panel → Assets

### 3D Model Requirements

- Format: `.glb` (compressed GLTF)
- Size: under 3MB recommended (auto-audited on upload)
- Poly count: under 20K recommended for mobile AR
- Scale/position/rotation configurable per item in config

Free model sources: Sketchfab, TurboSquid, CGTrader

---

## Deployment

### Production Checklist

- [ ] HTTPS enabled (required for camera/AR access)
- [ ] `USE_R2=true` + R2 credentials set (Render disk ephemeral hai)
- [ ] `create_first_admin.py` run once on server
- [ ] Real images and 3D models uploaded via admin panel
- [ ] Tested on Android + iOS devices

### Hosting

Currently deployed on **Render** with **Cloudflare R2** for file storage and **Render PostgreSQL** as database.

---

## Dependencies

```
fastapi
uvicorn[standard]
jinja2
python-multipart
bcrypt
python-jose[cryptography]
psycopg2-binary
python-dotenv
boto3
```

Full list in `requirements.txt`.

---

## License

Proprietary — All rights reserved.

This codebase is the intellectual property of ZenTable.
No part of this software may be copied, modified, distributed,
or used without explicit written permission from the authors.

---

Built by [Mohit Jangid](mailto:mohitjangid.phs.iitd@gmail.com)
