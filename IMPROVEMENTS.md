# ZenTable — Platform Overview & Roadmap

## What We Built

ZenTable started as a simple AR menu viewer. It is now a full restaurant management SaaS platform — multi-tenant, multi-role, with real-time order management, billing, analytics, and an augmented reality menu experience.

---

## Current Platform (Live at zentable.in)

### Customer Experience
| Feature | Details |
|---|---|
| AR Menu | Scan QR code, view dishes as 3D models in augmented reality |
| Digital Menu | Mobile-optimized menu with categories, veg/non-veg filters, size variants |
| Restaurant Home Page | Branded landing page with hero, featured dishes, contact info |
| No App Required | Works entirely in the browser |
| Screenshot & Share | Capture and share AR experiences on social media |
| AI Chatbot | Ask questions about menu, timings, and restaurant info |

### Staff Workflows
| Role | Capabilities |
|---|---|
| Owner | Analytics dashboard, QR generator, staff management, order history, full menu control, restaurant info management (name, logo, banner, social links, contact, tables), AI photo-to-menu import, platform help bot |
| Waiter | Table management, order placement, order lifecycle, billing, payments |
| Kitchen | Live order queue, mark individual items as ready |
| Counter | Table activate/deactivate, payment collection |

### Platform Admin (ZenTable) — admin.zentable.in
| Feature | Details |
|---|---|
| Admin Panel | Manage all onboarded restaurants from one dashboard |
| Restaurant management | Create, configure, activate/deactivate, delete restaurants |
| Menu management | Add/edit/delete items and categories for any restaurant |
| Photo to menu | AI-powered menu extraction from image for any restaurant |
| 3D model management | Upload/manage `.glb` models per dish (owners cannot upload GLBs) |
| Staff management | Create and manage staff accounts per restaurant |
| File management | Upload images/models, trash + restore system (30-day recovery) |
| Platform analytics | Revenue, orders, top dishes across all restaurants |
| DB export | Full PostgreSQL export as ZIP |

### Technical Foundation
| Component | Details |
|---|---|
| Backend | Python — FastAPI (modular routers) |
| Database | PostgreSQL (psycopg2, ThreadedConnectionPool) |
| Auth | bcrypt + JWT (cookie-based), role-scoped |
| Multi-tenant | client_id isolation across all DB tables |
| Restaurant Config | JSONB stored in PostgreSQL `restaurants` table |
| AR | MindAR + Three.js r128 — no native app required |
| AI | Google Gemini API — chatbot, photo-to-menu, help bot |
| File Storage | Cloudflare R2 (production) / local (development) |
| GLB Pipeline | Auto-optimize + audit on upload via gltf-transform |
| Trash System | Soft-delete with 30-day recovery, metadata in PostgreSQL |
| Multi-branch ready | DB schema already supports branch_id — upgrade path clear |

---

## Roadmap

### Phase 1 — Completed
- [x] Restaurant home page with full theme customization
- [x] AR menu with 3D models, manual rotation, screenshot/share
- [x] Multi-role staff system (owner, waiter, kitchen, counter)
- [x] Real-time order management and lifecycle tracking
- [x] Billing and payment collection
- [x] Owner analytics dashboard
- [x] Full menu control for owners (add/edit/delete items, categories)
- [x] Restaurant info management (name, logo, banner, social, contact, tables)
- [x] Multi-tenant platform with ZenTable admin panel (admin.zentable.in)
- [x] PostgreSQL backend with JSONB restaurant config
- [x] JWT-based auth (cookie-based, role-scoped)
- [x] Cloudflare R2 integration for file storage
- [x] GLB upload pipeline — auto-optimize + audit via gltf-transform
- [x] Trash system — soft-delete with 30-day recovery
- [x] AI chatbot for customers (Gemini)
- [x] AI photo-to-menu import (owner + admin)
- [x] Platform help bot for owners
- [x] Multi-branch DB schema (upgrade path ready)
- [x] Customer-facing order placement (QR → order directly)
- [x] Push notifications for staff (partial)

### Phase 2 — Next
- [ ] Delivery app integration — Swiggy, Zomato, direct delivery
- [ ] Multi-branch activation (owner manages multiple locations)
- [ ] Manager role (branch-level staff and analytics access)
- [ ] Customer reviews and ratings
- [ ] Gallery section per restaurant

### Phase 3
- [ ] Staff management — attendance tracking, salary management
- [ ] Inventory management — stock tracking, low-stock alerts
- [ ] Table booking / reservations
- [ ] Multi-language support
- [ ] Franchise management system

### Phase 4
- [ ] White-label solution
- [ ] Mobile app (staff-facing)

---

## Key Differentiators

| vs. | ZenTable advantage |
|---|---|
| Traditional menu | 3D visualization, always up-to-date, no printing cost |
| PDF menu | Interactive, shareable, brand building, engagement metrics |
| Other AR solutions | Full staff workflow included, no native app, budget-friendly |
| Generic POS systems | AR experience built-in, JSON-based easy onboarding |

---

*Platform live at [zentable.in](https://zentable.in)*
