"""
create_first_admin.py — Pehla site admin banane ki script
Usage: python create_first_admin.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, create_admin

def main():
    init_db()
    print("\n" + "═"*50)
    print("  MenuAR — First Time Setup")
    print("═"*50)

    print("\n── Site Admin Account ──\n")
    admin_username = input("  Username: ").strip()
    admin_password = input("  Password: ").strip()
    admin_name     = input("  Name: ").strip()

    if create_admin(admin_username, admin_password, admin_name):
        print(f"\n✅ Admin '{admin_username}' created!")
    else:
        print(f"\n⚠️  Admin '{admin_username}' already exists")

    print("\n" + "═"*50 + "\n")

if __name__ == "__main__":
    main()