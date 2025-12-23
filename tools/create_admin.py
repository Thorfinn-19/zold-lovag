# tools/create_admin.py
"""
Create a new admin in the Adminisztrator table with a hashed password.

Usage:
  python tools/create_admin.py

Notes:
- Requires DB access (same as the running app).
- Uses Windows auth by default via app/database.py.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from getpass import getpass
from werkzeug.security import generate_password_hash

from app.database import SessionLocal
from app.models import Adminisztrator



def main():
    nev = input("Admin név: ").strip()
    if not nev:
        print("A név nem lehet üres.")
        return

    pw1 = getpass("Jelszó: ")
    pw2 = getpass("Jelszó újra: ")
    if pw1 != pw2:
        print("A két jelszó nem egyezik.")
        return
    if len(pw1) < 8:
        print("A jelszó legyen legalább 8 karakter.")
        return

    db = SessionLocal()
    try:
        exists = db.query(Adminisztrator).filter(Adminisztrator.nev == nev).first()
        if exists:
            print("Ilyen névvel már létezik admin.")
            return

        admin = Adminisztrator(
            nev=nev,
            jelszo_hash=generate_password_hash(pw1),
            fiok_allapot="nyitott",
            hiba_probalkozasok=0,
        )
        db.add(admin)
        db.commit()
        print(f"Admin létrehozva: {nev}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
