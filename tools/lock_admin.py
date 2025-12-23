# tools/lock_admin.py
"""
Lock or unlock an admin account.
On unlock, optionally set a new password.

Usage:
  python tools/lock_admin.py lock
  python tools/lock_admin.py unlock
"""

import sys
from pathlib import Path
from getpass import getpass

from werkzeug.security import generate_password_hash

# Ensure project root is on sys.path so "import app.*" works reliably
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal
from app.models import Adminisztrator


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("lock", "unlock"):
        print("Használat: python tools/lock_admin.py lock|unlock")
        return

    action = sys.argv[1]

    nev = input("Admin név: ").strip()
    if not nev:
        print("❌ A név nem lehet üres.")
        return

    db = SessionLocal()
    try:
        admin = db.query(Adminisztrator).filter(Adminisztrator.nev == nev).first()
        if not admin:
            print("❌ Nincs ilyen admin.")
            return

        if action == "lock":
            admin.fiok_allapot = "zárolt"
            db.commit()
            print(f"✅ {nev} fiók zárolva.")
            return

        # ---- UNLOCK ----
        admin.fiok_allapot = "nyitott"
        admin.hiba_probalkozasok = 0

        valasz = input("Szeretnél új jelszót megadni? (i/n): ").strip().lower()
        if valasz == "i":
            pw1 = getpass("Új jelszó: ")
            pw2 = getpass("Új jelszó újra: ")

            if pw1 != pw2:
                print("❌ A két jelszó nem egyezik.")
                return

            if len(pw1) < 8:
                print("❌ A jelszó legyen legalább 8 karakter.")
                return

            admin.jelszo_hash = generate_password_hash(pw1)
            print("🔑 Jelszó frissítve.")

        db.commit()
        print(f"✅ {nev} fiók feloldva és használható.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
