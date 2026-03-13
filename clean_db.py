"""
clean_db.py — Selective Database & Data Cleanup Tool
Usage: python clean_db.py
"""

import sys
import os
import json
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import init_db, get_db

def line():     print("─" * 48)
def header(t):  print(f"\n{'═'*48}\n  {t}\n{'═'*48}")
def success(m): print(f"  ✅ {m}")
def error(m):   print(f"  ❌ {m}")
def info(m):    print(f"  ℹ  {m}")
def warn(m):    print(f"  ⚠️  {m}")
def pause():    input("\n  Enter dabao continue karne ke liye...")

def confirm(msg):
    return input(f"  {msg} (yes/no): ").strip().lower() == 'yes'

def get_all_restaurants():
    if not os.path.exists("data"):
        return []
    return sorted([f.replace(".json","") for f in os.listdir("data") if f.endswith(".json")])

def get_restaurant_name(client_id):
    try:
        with open(f"data/{client_id}.json", encoding="utf-8") as f:
            return json.load(f).get("restaurant", {}).get("name", client_id)
    except:
        return client_id

# ════════════════════════════════════
# DELETE OPTIONS
# ════════════════════════════════════

def delete_restaurant_orders(client_id):
    """Ek restaurant ke saare orders aur bills delete"""
    conn = get_db()
    # Bills
    bills = conn.execute("SELECT COUNT(*) FROM bills WHERE client_id=?", (client_id,)).fetchone()[0]
    orders = conn.execute("SELECT COUNT(*) FROM orders WHERE client_id=?", (client_id,)).fetchone()[0]
    info(f"Found: {orders} orders, {bills} bills")
    if not confirm(f"'{client_id}' ke saare orders + bills delete karna hai?"):
        conn.close(); info("Cancelled"); return
    conn.execute("DELETE FROM bills WHERE client_id=?", (client_id,))
    conn.execute("DELETE FROM orders WHERE client_id=?", (client_id,))
    conn.commit(); conn.close()
    success(f"'{client_id}' ke {orders} orders aur {bills} bills delete ho gaye!")

def delete_restaurant_staff(client_id):
    """Ek restaurant ki saari staff delete"""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM staff WHERE restaurant_id=?", (client_id,)).fetchone()[0]
    info(f"Found: {count} staff members")
    if not confirm(f"'{client_id}' ki saari staff delete karna hai?"):
        conn.close(); info("Cancelled"); return
    conn.execute("DELETE FROM staff WHERE restaurant_id=?", (client_id,))
    conn.commit(); conn.close()
    success(f"'{client_id}' ke {count} staff members delete ho gaye!")

def delete_restaurant_tables(client_id):
    """Ek restaurant ki tables reset"""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM tables WHERE client_id=?", (client_id,)).fetchone()[0]
    info(f"Found: {count} tables")
    if not confirm(f"'{client_id}' ki saari tables reset karna hai?"):
        conn.close(); info("Cancelled"); return
    conn.execute("DELETE FROM tables WHERE client_id=?", (client_id,))
    conn.commit(); conn.close()
    success(f"'{client_id}' ki {count} tables reset ho gayi!")

def delete_full_restaurant(client_id):
    """Poora restaurant delete — JSON + DB sab"""
    name = get_restaurant_name(client_id)
    warn(f"Ye action PERMANENT hai!")
    info(f"Ye delete hoga: JSON file, staff, orders, bills, tables, assets folder")
    if not confirm(f"'{name}' ({client_id}) POORA delete karna hai?"):
        info("Cancelled"); return

    conn = get_db()
    conn.execute("DELETE FROM orders WHERE client_id=?", (client_id,))
    conn.execute("DELETE FROM bills WHERE client_id=?", (client_id,))
    conn.execute("DELETE FROM tables WHERE client_id=?", (client_id,))
    conn.execute("DELETE FROM staff WHERE restaurant_id=?", (client_id,))
    conn.commit(); conn.close()

    # JSON delete
    json_path = f"data/{client_id}.json"
    if os.path.exists(json_path):
        os.remove(json_path)
        info(f"JSON deleted: {json_path}")

    # Assets folder delete
    assets_path = f"static/assets/{client_id}"
    if os.path.exists(assets_path):
        ans = input(f"  Assets folder bhi delete karna hai? ({assets_path}) (y/n): ").strip().lower()
        if ans == 'y':
            shutil.rmtree(assets_path)
            info(f"Assets deleted: {assets_path}")

    success(f"'{name}' ({client_id}) poora delete ho gaya!")

def delete_all_orders_all():
    """Saare restaurants ke orders + bills delete"""
    conn = get_db()
    o = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    b = conn.execute("SELECT COUNT(*) FROM bills").fetchone()[0]
    info(f"Total: {o} orders, {b} bills (saare restaurants)")
    warn("Ye saare restaurants ka data delete karega!")
    if not confirm("Aage badhna hai?"):
        conn.close(); info("Cancelled"); return
    conn.execute("DELETE FROM orders")
    conn.execute("DELETE FROM bills")
    conn.commit(); conn.close()
    success(f"Saare {o} orders aur {b} bills delete ho gaye!")

def delete_all_staff_all():
    """Saare staff delete (admins nahi)"""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM staff").fetchone()[0]
    info(f"Total: {count} staff members (saare restaurants)")
    warn("Admins delete NAHI honge")
    if not confirm("Saari staff delete karna hai?"):
        conn.close(); info("Cancelled"); return
    conn.execute("DELETE FROM staff")
    conn.commit(); conn.close()
    success(f"{count} staff members delete ho gaye!")

def reset_full_db():
    """Nuclear option — poora DB wipe"""
    warn("YE POORA DATABASE DELETE KAR DEGA!")
    warn("Orders, Bills, Tables, Staff — sab kuch!")
    warn("Admins bhi delete ho jayenge!")
    if not confirm("Sachchi mein poora DB reset karna hai?"):
        info("Cancelled"); return
    if not confirm("Last chance — pakka?"):
        info("Cancelled"); return
    conn = get_db()
    conn.execute("DELETE FROM orders")
    conn.execute("DELETE FROM bills")
    conn.execute("DELETE FROM tables")
    conn.execute("DELETE FROM staff")
    conn.execute("DELETE FROM admins")
    conn.execute("DELETE FROM sqlite_sequence")
    conn.commit(); conn.close()
    success("Poora DB reset ho gaya! Ab create_first_admin.py chalao.")

# ════════════════════════════════════
# RESTAURANT MENU
# ════════════════════════════════════

def restaurant_menu():
    header("Restaurant Select Karo")
    restaurants = get_all_restaurants()
    if not restaurants:
        error("Koi restaurant nahi mila"); pause(); return

    print()
    for i, r in enumerate(restaurants, 1):
        name = get_restaurant_name(r)
        print(f"  {i}. {r} — {name}")
    print()

    try:
        choice = int(input("  Number choose karo: ").strip())
        client_id = restaurants[choice - 1]
    except (ValueError, IndexError):
        error("Invalid choice"); pause(); return

    name = get_restaurant_name(client_id)
    header(f"{name} ({client_id})")
    print("  1. Orders + Bills delete karo")
    print("  2. Staff delete karo")
    print("  3. Tables reset karo")
    print("  4. Orders + Bills + Tables + Staff sab delete karo")
    print("  5. POORA restaurant delete karo (JSON bhi)")
    print("  0. Back")
    line()

    sub = input("  Option: ").strip()
    if   sub == '1': delete_restaurant_orders(client_id)
    elif sub == '2': delete_restaurant_staff(client_id)
    elif sub == '3': delete_restaurant_tables(client_id)
    elif sub == '4':
        warn("Ye restaurant ka sara dynamic data delete karega")
        if confirm("Confirm?"):
            delete_restaurant_orders(client_id)
            delete_restaurant_tables(client_id)
            delete_restaurant_staff(client_id)
    elif sub == '5': delete_full_restaurant(client_id)
    elif sub == '0': return
    else: error("Invalid")

    pause()

# ════════════════════════════════════
# MAIN MENU
# ════════════════════════════════════

def main():
    init_db()
    while True:
        header("MenuAR — Database Cleanup Tool")

        # DB stats
        conn = get_db()
        o = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        b = conn.execute("SELECT COUNT(*) FROM bills").fetchone()[0]
        s = conn.execute("SELECT COUNT(*) FROM staff").fetchone()[0]
        a = conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
        conn.close()
        print(f"\n  DB Status: {o} orders | {b} bills | {s} staff | {a} admins\n")

        print("  1. Kisi ek restaurant ka data manage karo")
        print("  2. Saare restaurants ke orders + bills delete karo")
        print("  3. Saari staff delete karo (saare restaurants)")
        print("  4. ⚠️  Poora DB reset karo (nuclear option)")
        print("  0. Exit")
        line()

        choice = input("  Option: ").strip()
        if   choice == '1': restaurant_menu()
        elif choice == '2': delete_all_orders_all(); pause()
        elif choice == '3': delete_all_staff_all(); pause()
        elif choice == '4': reset_full_db(); pause()
        elif choice == '0': print("\n  Bye! 👋\n"); break
        else: error("Invalid option")

if __name__ == "__main__":
    main()
