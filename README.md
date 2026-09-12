# ZenTable — Smart Dining, Reimagined

🌐 **Live at [zentable.in](https://zentable.in)**

A **multi-tenant restaurant management platform** with AR menus, real-time order management, staff workflows, and a full analytics dashboard. Built for restaurants that want a modern, end-to-end digital dining experience.

---

## Features

### For Customers

- **AR Menu** — Scan branch-specific QR codes to view dishes as 3D models in augmented reality
- **Interactive Controls** — Rotate and explore dishes before ordering
- **Digital Menu** — Clean, fast, mobile-friendly branch-aware menu browsing
- **Branch Awareness** — Dynamic layout and data adjustments on public pages (`home`, `menu`, `ar_menu`) based on the selected branch
- **Customer Portal & OAuth** — Secure, dynamic login using Google OAuth2 to access the personalized customer profile (with T&C and Privacy Policy compliance integrated)
- **Order History & Active Tracking** — Real-time order tracking dashboard divided into `🟢 Active Orders` and `📜 Order History` with color-coded status badges, tracking details, and direct redirects back to the originating menu URL

### For Restaurant Staff

- **Waiter** — Table management, order placement, billing, payments (branch-isolated)
- **Kitchen** — Live order queue, mark items ready (branch-isolated)
- **Counter** — Table activation/deactivation, payment collection (branch-isolated)
- **In-house Delivery Flow** — Specialized `delivery` staff role, dedicated delivery management dashboard (`staff_delivery.html`) to view active/assigned orders, and real-time state updates (Dispatched, Delivered) synchronized live across customer and staff views
- **Owner** — Analytics, branch-specific QR generator, staff management, order history, full menu control (add/edit/delete items, categories), restaurant info management, AI-powered **bulk photo-to-menu import** (parse and save entire menus in one action), platform help bot, **Multi-Branch Support**, **Self-Signup with Admin Approval (including integrated T&C / Legal compliance)**
- **Session Protection** — Automatic mid-session expiry detection (`401` handler) across all staff portals that prompts a graceful redirect to login, preventing broken UI states

### For Platform Admins (ZenTable)

> Accessible at [admin.zentable.in](https://admin.zentable.in)

- **Admin Panel** — Manage all restaurants from one place
- **Per-restaurant stats** — Revenue, orders, top dishes
- **Menu management** — Add/edit/delete items and categories for any restaurant (supports bulk imports)
- **Photo to menu** — AI-powered menu extraction from image, for any restaurant
- **3D model management** — Upload/manage `.glb` models per dish (owners cannot upload GLBs)
- **Staff management** — Create, edit, deactivate staff accounts across all restaurants and branches
- **Restaurant onboarding** — Instant setup via admin panel; activate, deactivate, or delete restaurants, **Approve Owner Signups**
- **Blogging Platform** — Built-in blogging system for ZenTable platform and connected restaurants
- **File management & Storage Security** — Upload images/models with automatic **collision prevention** (unique 8-character `_uid` prefix appended to uploaded images) and secure **trash + restore system** (intelligent key parsing to avoid deleting active assets)
- **Subscription & Add-ons Manager** — Dynamic configuration editor within the Billings tab to live-edit pricing, taglines, active feature checklists, and inline customized feature tags for global plans (Basic, Pro, Elite) and add-ons.
- **Smart Payment Sharing & QR Downloads** — Advanced confirm-payment workflow generating fixed-amount UPI payment URLs and dynamic QR codes. Features single-click downloads named dynamically (`client_id + month`), a clipboard copy engine to copy raw QR images directly for instant pasting (`Ctrl+V`) into chats like WhatsApp, and native async Web Share API integration to share the QR image file and custom pre-configured messages simultaneously.
- **DB export** — Full PostgreSQL export as ZIP

---

## Tech Stack

| Layer                    | Technology                                                                                                           |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| Backend                  | Python — FastAPI (with background keep-alive threads)                                                                |
| Database                 | PostgreSQL (psycopg2, ThreadedConnectionPool, Neon DB keep-alive support)                                            |
| Restaurant Config        | PostgreSQL `restaurants` table (JSONB)                                                                               |
| Subscriptions & Add-ons  | PostgreSQL `billing_plans`, `billing_addons`, `subscriptions`, `subscription_addons`, `payment_history`, `email_log` |
| Blog Operations          | PostgreSQL `blog_posts` table                                                                                        |
| Trash & Auto-Purge       | PostgreSQL `trash_meta` table                                                                                        |
| Owner Signup & Approvals | PostgreSQL `owner_signup_requests`, `owners` tables                                                                  |
| Platform Configuration   | PostgreSQL `site_settings` table                                                                                     |
| Frontend                 | HTML, CSS, Vanilla JS (Jinja2 templates)                                                                             |
| AR                       | MindAR + Three.js r128                                                                                               |
| AI                       | Google Gemini API (Chatbot, Photo-to-Menu, Help Bot)                                                                 |
| Auth                     | bcrypt + JWT (cookie-based)                                                                                          |
| Rate Limiting            | slowapi (Global 200/min & Route-specific limits)                                                                     |
| File Storage             | Cloudflare R2 (production) / local (development)                                                                     |

---

## Key Features:

- **Staff Portals**: Role-based access for Waiter, Kitchen, Counter, In-house Delivery, Owner.
- **AR Menu**: 3D menu experience via MindAR + Three.js.
- **AI Integration**: Google Gemini for photo-to-menu import, chatbots, and help bots.
- **Restaurant Management**: Full CRUD operations for menus, items, orders, staff, and restaurants.
- **Admin Dashboard**: Global management for ZenTable platform.
- **Multi-Branch Support**: Restaurants can have multiple branches with isolated data.
- **Subscriptions & Billing**: Full billing lifecycle management with Stripe integration.
- **Trash & Recovery System**: Smart trash management for files and database entries.
- **Owner Self-Signup**: Integrated T&C/Privacy Policy compliance and approval flow.
- **Security**: JWT-based auth, file security, subscription gating, and session management.

---

## Architecture

```mermaid
graph TB
    subgraph Clients ["👥 Client Interfaces"]
        C1["🍽️ Customer<br/>(Menu · AR Menu · Tracking)"]
        C2["🧑‍🍳 Waiter<br/>(Tables · Orders · Billing)"]
        C3["👨‍🍳 Kitchen<br/>(Live Order Queue)"]
        C4["🧾 Counter<br/>(Tables · Payments)"]
        C5["🚚 Delivery<br/>(Dispatch · Status)"]
        C6["👔 Owner<br/>(Analytics · QR · Staff · Menu)"]
        C7["✍️ Blogger<br/>(Draft · Submit)"]
        C8["🛡️ Platform Admin<br/>(Restaurants · Billing · Blog Publish)"]
    end

    subgraph Frontend ["🖥️ Frontend (Jinja2 + Vanilla JS)"]
        templates["HTML Templates & UI"]
        ar["MindAR + Three.js (AR Engine)"]
        ai_chat["AI Chat / Help Bot / Photo-to-Menu"]
        qr_share["Smart QR & Web Share API"]
        editor["Quill Blog Editor<br/>(Draft → Preview → Publish)"]
    end

    subgraph Auth ["🔐 Security & Routing"]
        jwt["JWT Cookie Auth<br/>(role + client_id + branch_id)"]
        oauth["Google OAuth2 (Customer)"]
        gates["Dynamic Feature Gating<br/>(require_feature decorator)"]
    end

    subgraph API ["⚙️ FastAPI Backend (routers/)"]
        direction LR
        r_menu["Menu / Tables / Orders API"]
        r_staff["Staff & Admin API"]
        r_owner["Owner & Branch API"]
        r_blog["Blog API"]
        r_billing["Billing API"]
        r_ai["AI & Chatbot API"]
        bg_tasks["Background Keep-alive +<br/>Daily Billing Cron"]
    end

    subgraph Core ["🧰 Core Modules"]
        glb["GLB Optimizer<br/>(gltf-transform, on upload)"]
        trash["Trash & Auto-Purge"]
        feat["Feature Registry"]
        qr_gen["Dynamic QR / UPI Gen"]
        email["Email Notifications<br/>(7d/1d/grace/expired — Gmail SMTP)"]
    end

    subgraph Data ["🗄️ Data Layer — Neon PostgreSQL (single DB)"]
        db_core[("Core Tables<br/>restaurants · tables · orders · bills<br/>staff · customers")]
        db_billing[("Billing Tables<br/>billing_plans · billing_addons<br/>subscriptions · payment_history · email_log")]
        db_blog[("Blog Tables<br/>blog_posts")]
        storage_split{"USE_R2 flag"}
        storage_r2[("Cloudflare R2<br/>assets.zentable.in")]
        storage_local[("Local Disk<br/>static/assets · private/assets")]
    end

    subgraph External ["🌐 External Integrations"]
        gemini["Google Gemini API"]
        upi["Manual UPI Payment<br/>(Phase 3: Razorpay webhook-ready)"]
        smtp["Gmail SMTP"]
    end

    %% Client flows
    C1 & C2 & C3 & C4 & C5 & C6 --> templates
    C7 --> editor
    C8 --> templates
    C1 --> ar
    C1 & C6 --> ai_chat
    C4 & C6 & C8 --> qr_share

    %% Frontend to Auth
    templates --> jwt
    editor --> jwt
    C1 --> oauth
    jwt --> gates

    %% Auth to API
    gates --> API
    oauth --> r_menu

    %% API internal
    API -.-> bg_tasks

    %% API to Core
    r_staff --> glb
    r_staff --> trash
    gates --> feat
    r_billing --> qr_gen
    r_billing --> email

    %% API to DB
    r_menu --> db_core
    r_staff --> db_core
    r_owner --> db_core
    r_blog --> db_blog
    r_billing --> db_billing

    %% Storage routing
    glb --> storage_split
    trash --> storage_split
    storage_split -->|prod| storage_r2
    storage_split -->|dev| storage_local

    %% External
    r_ai --> gemini
    qr_gen --> upi
    email --> smtp
```

---

## Project Structure

```
zentable/
├── main.py                      # App init, lifespan, static mount, utility routes
├── db/                          # PostgreSQL connection pool & modular DB operations
│   ├── __init__.py              # Convenience package re-exports
│   ├── connection.py            # PostgreSQL pool and connection wrapper
│   ├── admin_db.py              # Platform admin operations
│   ├── billing_db.py            # Subscription & Billing management
│   ├── blog_db.py               # Blog database operations
│   ├── core_db.py               # Core tables, order, and billing operations
│   ├── customer_db.py           # Customer OAuth profiles & orders
│   ├── owner_db.py              # Restaurant owner profiles & approval logic
│   ├── restaurant_db.py         # Restaurant config & trash operations
│   └── staff_db.py              # Restaurant staff accounts & auth
├── feature_registry.py          # Key-label registry for feature gating (Basic, Pro, Elite)
├── check_feature_gates.py       # Audit utility for restaurant feature access & subscription gates
├── auth.py                      # JWT logic — create/verify token, login functions
├── rate_limit.py                # Rate limiting utility using SlowAPI
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
│   ├── customer_auth.py         # Customer login & Google OAuth flow
│   ├── admin.py                 # All admin routes
│   ├── billing.py               # Subscription plans & add-ons manager API
│   ├── owner.py                 # Owner operations & branch management
│   ├── blog.py                  # Blogging platform routes
│   ├── chatbot.py               # Chatbot logic
│   ├── help_chat.py             # Help chat
│   ├── image_to_menu.py         # AI-powered photo-to-menu import
│   └── pages.py                 # All HTML page routes
│
├── templates/                   # Jinja2 HTML templates
│   ├── staff_delivery.html      # Delivery management panel
│   ├── customer_orders.html     # Customer tracking dashboard
│   ├── customer_profile.html    # Customer profile
│   ├── menu.html                # Digital AR menu
│   └── ...
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
git clone https://github.com/mohitjangid-iitd/ZenTable.git
cd ZenTable

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
IS_PROD=false
GEMINI_API_KEY=your-gemini-api-key
SMTP_USER=your-smtp-user
SMTP_PASS=your-smtp-password
ZENTABLE_UPI_ID=your-upi-id-here

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# R2 (optional — local storage when USE_R2=false)
USE_R2=false
R2_ACCOUNT_ID=
R2_ACCESS_KEY=
R2_SECRET_KEY=
R2_BUCKET=
R2_PUBLIC_URL=
```

### Access

| URL                                         | Description                                      |
| ------------------------------------------- | ------------------------------------------------ |
| `http://localhost:8000/`                    | ZenTable landing page                            |
| `http://localhost:8000/{client_id}`         | Restaurant home page                             |
| `http://localhost:8000/{client_id}/menu`    | Digital menu                                     |
| `http://localhost:8000/{client_id}/ar-menu` | AR menu                                          |
| `http://localhost:8000/blog`                | Main ZenTable blog platform                      |
| `http://localhost:8000/blog/{slug}`         | Specific blog post                               |
| `http://localhost:8000/login`               | Staff login                                      |
| `http://localhost:8000/admin`               | ZenTable admin panel (prod: `admin.zentable.in`) |

---

## Adding a Restaurant

Restaurants can now be created directly from the admin panel (`/admin`). No manual JSON files required.

Config structure stored in the DB:

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
  ]
}
```

> [!NOTE]
> **Dynamic Feature Gating & Locking**: Feature access is checked in real-time by querying the restaurant's subscription status against global database records (`billing_plans` & `billing_addons`). APIs are dynamically locked/unlocked via backend decorators (`require_feature`), and front-end interface components adjust automatically.

---

## Staff Roles

| Role       | Access                                                                                                                                    |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `owner`    | Analytics, QR generator, staff management, order history, menu control, restaurant info management, photo-to-menu (AI), platform help bot |
| `waiter`   | Table management, order placement, order lifecycle, billing                                                                               |
| `kitchen`  | Live order queue, mark items as ready                                                                                                     |
| `counter`  | Table activate/deactivate, payment collection                                                                                             |
| `blogger`  | Create and manage blog posts                                                                                                              |
| `delivery` | View active deliveries, manage delivery flow, update delivery states                                                                      |

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

## Testing

ZenTable features over **140 API routes and endpoints**. It includes a robust suite of **~171 automated unit and behavioral tests (90%+ core coverage)**. All database queries and external resources are mocked out, allowing tests to run entirely offline in milliseconds.

To install test dependencies:

```bash
pip install pytest httpx
```

To execute the test suite:

```bash
# Run all tests
SECRET_KEY=test pytest tests/ -v

# Run tests with condensed output
SECRET_KEY=test pytest tests/ -q
```

Refer to [PYTEST_GUIDE.md](tests/PYTEST_GUIDE.md) for full instructions, including writing smoke and behavioral tests.

---

## Deployment

### Production Checklist

- [ ] HTTPS enabled (required for camera/AR access)
- [ ] `USE_R2=true` + R2 credentials set (Render disk is ephemeral)
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
pygltflib
google-genai
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
