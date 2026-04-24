"""
manage_restaurant.py — Restaurant & Staff Management CLI
Usage: python manage_restaurant.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    init_db, get_db,
    create_staff, get_staff_list,
    update_staff_password, toggle_staff_active, delete_staff,
    seed_tables
)

# ── Helpers ──
def line():    print("─" * 48)
def header(t): print(f"\n{'═'*48}\n  {t}\n{'═'*48}")
def success(m): print(f"  ✅ {m}")
def error(m):   print(f"  ❌ {m}")
def info(m):    print(f"  ℹ  {m}")

def pause():
    input("\n  Enter dabao continue karne ke liye...")

def ask(prompt, default=None):
    """Input lo — default ho toh Enter se skip"""
    if default is not None:
        val = input(f"  {prompt} [{default}]: ").strip()
        return val if val else default
    val = input(f"  {prompt}: ").strip()
    return val

def ask_optional(prompt):
    """Optional field — Enter se skip"""
    val = input(f"  {prompt} (optional, Enter to skip): ").strip()
    return val if val else ""

def restaurant_exists(client_id: str) -> bool:
    return os.path.exists(f"data/{client_id}.json")

def get_staff_by_id(staff_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM staff WHERE id=?", (staff_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def print_staff_table(staff_list):
    if not staff_list:
        info("Koi staff nahi mila")
        return
    print(f"\n  {'ID':<5} {'Name':<20} {'Username':<18} {'Role':<10} {'Active'}")
    line()
    for s in staff_list:
        active = "✅" if s["is_active"] else "❌"
        print(f"  {s['id']:<5} {s['name']:<20} {s['username']:<18} {s['role']:<10} {active}")
    print()

# ════════════════════════════════
# REGISTER RESTAURANT
# ════════════════════════════════

def register_restaurant():
    header("Naya Restaurant Register")

    # ── Required fields ──
    print("\n  [ Required ]\n")
    client_id = ask("Restaurant ID (e.g. pinky_hotel)").lower().replace(" ", "_")
    if not client_id:
        error("Restaurant ID required"); pause(); return

    if restaurant_exists(client_id):
        error(f"'{client_id}' already exists!")
        pause(); return

    name = ask("Restaurant Name")
    if not name:
        error("Name required"); pause(); return

    try:
        num_tables = int(ask("Number of tables", "6"))
    except ValueError:
        num_tables = 6

    # ── Optional fields ──
    print("\n  [ Optional — Enter dabao skip karne ke liye ]\n")
    tagline      = ask_optional("Tagline")
    description  = ask_optional("Description")
    cuisine_type = ask_optional("Cuisine Type (e.g. North Indian)")
    phone        = ask_optional("Phone")
    email        = ask_optional("Email")
    address      = ask_optional("Address")

    print("\n  [ Timings ]\n")
    lunch  = ask_optional("Lunch timings (e.g. 12:00 PM - 3:30 PM)")
    dinner = ask_optional("Dinner timings (e.g. 7:00 PM - 11:30 PM)")
    closed = ask_optional("Closed on (e.g. Monday)")

    print("\n  [ Social Media ]\n")
    instagram = ask_optional("Instagram URL")
    facebook  = ask_optional("Facebook URL")
    twitter   = ask_optional("Twitter/X URL")

    # ── Build JSON ──
    data = {
        "restaurant": {
            "name":         name,
            "num_tables":   num_tables,
            "tagline":      tagline      or f"Welcome to {name}",
            "logo":         f"/static/assets/{client_id}/logo.png",
            "banner":       f"/static/assets/{client_id}/banner.png",
            "description":  description  or "",
            "cuisine_type": cuisine_type or "",
            "phone":        phone        or "",
            "email":        email        or "",
            "address":      address      or "",
            "timings": {
                "lunch":  lunch  or "",
                "dinner": dinner or "",
                "closed": closed or ""
            },
            "social": {
                "instagram": instagram or "",
                "facebook":  facebook  or "",
                "twitter":   twitter   or ""
            }
        },
        "theme": {
            "primary_color":   "#D4AF37",
            "secondary_color": "#1a1a1a",
            "accent_color":    "#8B4513",
            "text_color":      "#333333",
            "background":      "#ffffff",
            "font_primary":    "Playfair Display",
            "font_secondary":  "Poppins"
        },
        "items": []
    }

    # ── Save JSON ──
    os.makedirs("data", exist_ok=True)
    json_path = f"data/{client_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # ── Seed tables in DB ──
    seed_tables(client_id, num_tables)

    # ── Create assets folder ──
    os.makedirs(f"static/assets/{client_id}", exist_ok=True)

    success(f"Restaurant '{name}' ({client_id}) register ho gaya!")
    info(f"JSON: data/{client_id}.json")
    info(f"Assets folder: static/assets/{client_id}/")
    info(f"Tables: {num_tables} tables seeded")
    info("Logo aur banner: static/assets/{client_id}/ mein manually rakho")

    # ── Owner add karna chahoge? ──
    print()
    add_owner = input("  Abhi owner account banana hai? (y/n): ").strip().lower()
    if add_owner == 'y':
        _add_staff_for(client_id)

    pause()

# ════════════════════════════════
# STAFF MANAGEMENT
# ════════════════════════════════

def _add_staff_for(client_id):
    """Staff add karo — internal helper"""
    print(f"\n  Roles: owner | kitchen | waiter | counter | blogger")
    line()
    while True:
        print("\n  Staff details:")
        name     = ask("Name")
        username = ask("Username").lower()
        password = ask("Password")
        role     = ask("Role (owner/kitchen/waiter/counter/blogger)").lower()

        if not all([name, username, password, role]):
            error("Sab fields required hain"); continue
        if role not in ["owner", "kitchen", "waiter", "counter", "blogger"]:
            error("Invalid role"); continue

        if create_staff(client_id, username, password, name, role):
            success(f"'{name}' ({role}) add ho gaya!")
        else:
            error(f"Username '{username}' already exists")

        more = input("\n  Aur staff add karna hai? (y/n): ").strip().lower()
        if more != 'y':
            break

def add_staff():
    header("Staff Add Karo")
    client_id = ask("Restaurant ID")
    if not client_id:
        error("Required"); pause(); return
    if not restaurant_exists(client_id):
        error(f"Restaurant '{client_id}' nahi mila (JSON file check karo)")
        pause(); return
    _add_staff_for(client_id)
    pause()

def view_staff():
    header("Staff List Dekho")
    client_id = ask("Restaurant ID")
    if not client_id:
        error("Required"); pause(); return
    staff = get_staff_list(client_id)
    print(f"\n  Restaurant: {client_id}")
    print_staff_table(staff)
    pause()

def change_password():
    header("Password Change Karo")
    client_id = ask("Restaurant ID")
    staff = get_staff_list(client_id)
    if not staff:
        error("Koi staff nahi mila"); pause(); return
    print_staff_table(staff)
    try:
        staff_id = int(ask("Staff ID"))
    except ValueError:
        error("Invalid ID"); pause(); return
    member = get_staff_by_id(staff_id)
    if not member or member["restaurant_id"] != client_id:
        error("Staff nahi mila"); pause(); return
    new_pass = ask(f"'{member['name']}' ka naya password")
    if not new_pass:
        error("Password required"); pause(); return
    confirm = input("  Confirm (y/n): ").strip().lower()
    if confirm != 'y':
        info("Cancelled"); pause(); return
    update_staff_password(staff_id, new_pass)
    success(f"'{member['name']}' ka password update ho gaya!")
    pause()

def toggle_staff():
    header("Staff Activate / Deactivate")
    client_id = ask("Restaurant ID")
    staff = get_staff_list(client_id)
    if not staff:
        error("Koi staff nahi mila"); pause(); return
    print_staff_table(staff)
    try:
        staff_id = int(ask("Staff ID"))
    except ValueError:
        error("Invalid ID"); pause(); return
    member = get_staff_by_id(staff_id)
    if not member or member["restaurant_id"] != client_id:
        error("Staff nahi mila"); pause(); return
    current   = "Active" if member["is_active"] else "Inactive"
    new_state = not bool(member["is_active"])
    new_label = "Activate" if new_state else "Deactivate"
    confirm = input(f"  '{member['name']}' abhi {current} hai — {new_label} karna hai? (y/n): ").strip().lower()
    if confirm != 'y':
        info("Cancelled"); pause(); return
    toggle_staff_active(staff_id, new_state)
    success(f"'{member['name']}' {new_label}d!")
    pause()

def remove_staff():
    header("Staff Delete Karo")
    client_id = ask("Restaurant ID")
    staff = get_staff_list(client_id)
    if not staff:
        error("Koi staff nahi mila"); pause(); return
    print_staff_table(staff)
    try:
        staff_id = int(ask("Staff ID"))
    except ValueError:
        error("Invalid ID"); pause(); return
    member = get_staff_by_id(staff_id)
    if not member or member["restaurant_id"] != client_id:
        error("Staff nahi mila"); pause(); return
    confirm = input(f"  ⚠️  '{member['name']}' permanently delete karna hai? (yes/no): ").strip().lower()
    if confirm != 'yes':
        info("Cancelled"); pause(); return
    delete_staff(staff_id)
    success(f"'{member['name']}' delete ho gaya!")
    pause()

def list_all_restaurants():
    header("Saare Restaurants")
    data_dir = "data"
    if not os.path.exists(data_dir):
        error("data/ folder nahi mila"); pause(); return
    restaurants = [f.replace(".json","") for f in os.listdir(data_dir) if f.endswith(".json")]
    if not restaurants:
        info("Koi restaurant nahi mila"); pause(); return
    print(f"\n  {'Restaurant ID':<25} {'Name':<25} {'Staff Count'}")
    line()
    for r in sorted(restaurants):
        try:
            with open(f"data/{r}.json", encoding="utf-8") as f:
                rdata = json.load(f)
            rname = rdata.get("restaurant", {}).get("name", "—")
        except:
            rname = "—"
        staff = get_staff_list(r)
        print(f"  {r:<25} {rname:<25} {len(staff)} members")
    print()
    pause()

def edit_restaurant_info():
    header("Restaurant Info Edit Karo")
    client_id = ask("Restaurant ID")
    json_path = f"data/{client_id}.json"
    if not os.path.exists(json_path):
        error(f"'{client_id}' nahi mila"); pause(); return

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    r = data["restaurant"]
    print(f"\n  Current name: {r.get('name','')}")
    print(f"  Current tables: {r.get('num_tables','')}")
    print(f"  Current phone: {r.get('phone','')}")
    print(f"  Current email: {r.get('email','')}")
    print()
    info("Sirf jo change karna hai vo daalo, baaki Enter se skip karo")
    print()

    name    = ask_optional(f"Name [{r.get('name','')}]")
    tagline = ask_optional(f"Tagline [{r.get('tagline','')}]")
    phone   = ask_optional(f"Phone [{r.get('phone','')}]")
    email   = ask_optional(f"Email [{r.get('email','')}]")
    address = ask_optional(f"Address [{r.get('address','')}]")

    print("\n  [ Social ]\n")
    instagram = ask_optional(f"Instagram [{r.get('social',{}).get('instagram','')}]")
    facebook  = ask_optional(f"Facebook [{r.get('social',{}).get('facebook','')}]")
    twitter   = ask_optional(f"Twitter [{r.get('social',{}).get('twitter','')}]")

    if name:    r["name"]    = name
    if tagline: r["tagline"] = tagline
    if phone:   r["phone"]   = phone
    if email:   r["email"]   = email
    if address: r["address"] = address
    if instagram: r.setdefault("social",{})["instagram"] = instagram
    if facebook:  r.setdefault("social",{})["facebook"]  = facebook
    if twitter:   r.setdefault("social",{})["twitter"]   = twitter

    data["restaurant"] = r
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    success(f"'{client_id}' updated!")
    pause()

# ════════════════════════════════
# MAIN MENU
# ════════════════════════════════

def main():
    init_db()
    while True:
        header("MenuAR — Restaurant Manager")
        print("  1. Saare restaurants dekho")
        print("  2. Naya restaurant register karo")
        print("  3. Restaurant info edit karo")
        print("  ─")
        print("  4. Staff add karo")
        print("  5. Staff list dekho")
        print("  6. Staff password change karo")
        print("  7. Staff activate / deactivate karo")
        print("  8. Staff delete karo")
        print("  ─")
        print("  0. Exit")
        line()

        choice = input("  Option: ").strip()

        if   choice == '1': list_all_restaurants()
        elif choice == '2': register_restaurant()
        elif choice == '3': edit_restaurant_info()
        elif choice == '4': add_staff()
        elif choice == '5': view_staff()
        elif choice == '6': change_password()
        elif choice == '7': toggle_staff()
        elif choice == '8': remove_staff()
        elif choice == '0': print("\n  Bye! 👋\n"); break
        else: error("Invalid option")

if __name__ == "__main__":
    main()
