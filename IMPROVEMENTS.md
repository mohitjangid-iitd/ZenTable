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

### Staff Workflows
| Role | Capabilities |
|---|---|
| Owner | Analytics dashboard, QR generator, staff management, full order history |
| Waiter | Table management, order placement, order lifecycle, billing, payments |
| Kitchen | Live order queue, mark individual items as ready |
| Counter | Table activate/deactivate, payment collection |

### Platform Admin (ZenTable)
| Feature | Details |
|---|---|
| Admin Panel | Manage all onboarded restaurants from one dashboard |
| Restaurant management | Create, configure, delete restaurants |
| Staff management | Create and manage staff accounts per restaurant |
| Platform analytics | Revenue, orders, top dishes across all restaurants |

### Technical Foundation
| Component | Details |
|---|---|
| Backend | Python — FastAPI |
| Database | SQLite → PostgreSQL (migration ready) |
| Auth | bcrypt + session-based, role-scoped |
| Multi-tenant | client_id isolation across all DB tables |
| AR | MindAR + Three.js — no native app required |
| Config | JSON-based per restaurant (menu, theme, branding) |
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
- [x] Multi-tenant platform with ZenTable admin panel
- [x] Multi-branch DB schema (upgrade path ready)

### Phase 2 — Next (3 months)
- [ ] Multi-branch activation (owner manages multiple locations)
- [ ] Manager role (branch-level staff and analytics access)
- [ ] Customer reviews and ratings
- [ ] Gallery section per restaurant

### Phase 3 — 6 months
- [x] Customer-facing order placement (QR → order directly)
- [x] Push notifications for staff (partial)
- [ ] Table booking / reservations
- [ ] Multi-language support

### Phase 4 — 12 months
- [ ] Franchise management system
- [ ] Staff management — attendance tracking, salary management
- [ ] Inventory management — stock tracking, low-stock alerts
- [ ] Delivery app integration — Swiggy, Zomato, direct delivery
- [ ] White-label solution
- [ ] Partner API
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
