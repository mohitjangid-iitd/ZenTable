# ZenTable — Smart Dining, Reimagined

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
- **Restaurant onboarding** — JSON-based config, instant setup

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python — FastAPI |
| Database | SQLite (`data/orders.db`) |
| Static data | JSON files (`data/{client_id}.json`) |
| Frontend | HTML, CSS, Vanilla JS |
| AR | MindAR + Three.js |
| Auth | bcrypt + session-based |

---

## Project Structure

```
zentable/
├── main.py                      # FastAPI routes
├── database.py                  # SQLite setup + all DB functions
├── auth.py                      # Login, session, role management
├── site_config.py               # ZenTable platform branding
├── manage_restaurant.py         # Restaurant onboarding CLI
├── create_first_admin.py        # First admin setup script
├── clean_db.py                  # DB cleanup utility
├── requirements.txt
│
├── data/
│   ├── orders.db                # SQLite database
│   ├── clint_one.json           # Restaurant 1 config (menu + theme + info)
│   └── clint_two.json           # Restaurant 2 config
│
├── templates/
│   ├── landing.html             # ZenTable marketing page
│   ├── home.html                # Restaurant home page
│   ├── menu.html                # Digital menu
│   ├── ar_menu.html             # AR menu experience
│   ├── login.html               # Staff login
│   ├── staff_owner.html         # Owner dashboard
│   ├── staff_waiter.html        # Waiter interface
│   ├── staff_kitchen.html       # Kitchen display
│   ├── staff_counter.html       # Counter interface
│   ├── admin.html               # ZenTable admin panel
│   └── admin_login.html         # Admin login
│
├── static/
│   ├── css/                     # Per-role stylesheets
│   ├── js/                      # Per-role JS files
│   └── assets/
│       ├── zentable/            # Platform branding assets
│       ├── clint_one/           # Restaurant 1 images + AR assets
│       └── clint_two/           # Restaurant 2 images + AR assets
│
└── private/
    └── assets/
        ├── clint_one/           # Restaurant 1 — .glb models + targets.mind
        └── clint_two/           # Restaurant 2 — .glb models + targets.mind
```

---

## Setup

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
# Clone
git clone <your-repo-url>
cd zentable

# Install dependencies
pip install -r requirements.txt

# Create first admin account
python create_first_admin.py

# Initialize database and run
python main.py
```

### Access

| URL | Description |
|---|---|
| `http://localhost:8000/` | ZenTable landing page |
| `http://localhost:8000/{client_id}` | Restaurant home page |
| `http://localhost:8000/{client_id}/menu` | Digital menu |
| `http://localhost:8000/{client_id}/ar-menu` | AR menu |
| `http://localhost:8000/{client_id}/login` | Staff login |
| `http://localhost:8000/admin` | ZenTable admin panel |

---

## Adding a Restaurant

Each restaurant is a JSON file in `data/` and an assets folder in `static/assets/`.

### 1. Create config file — `data/{client_id}.json`

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
      "facebook": "https://facebook.com/...",
      "twitter": "https://twitter.com/..."
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
    "features": ["basic", "ordering", "analytics", "ar_menu"]
  }
}
```

### 2. Add assets

```
static/assets/{client_id}/    ← logo, banner, dish images, targets.mind
private/assets/{client_id}/   ← .glb 3D models (not publicly listed)
```

### 3. Seed tables in DB

```python
from database import seed_tables
seed_tables("client_id", num_tables=10)
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
4. Place in `static/assets/{client_id}/targets.mind`

### 3D Model Requirements

- Format: `.glb` (compressed GLTF)
- Size: under 5MB recommended
- Default orientation: facing forward at `0 0 0`
- Scale and position configurable per item in JSON

Free model sources: Sketchfab, TurboSquid, CGTrader

---

## Deployment

### Production Checklist

- [ ] HTTPS enabled (required for camera/AR access)
- [ ] Real images and 3D models added
- [ ] `create_first_admin.py` run once on server
- [ ] Environment variables set (if any)
- [ ] Tested on Android + iOS devices

### Recommended Hosting

- DigitalOcean App Platform
- Railway
- Render
- AWS EC2 / Google Cloud Run

---

## Dependencies

```
fastapi
uvicorn[standard]
jinja2
python-multipart
bcrypt
```

Full list in `requirements.txt`.

---

## License

MIT License — free to use for commercial projects.

---

Built by [Mohit Jangid](mailto:mohitjangid.phs.iitd@gmail.com)
