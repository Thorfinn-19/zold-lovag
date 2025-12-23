# app/routes/admin.py
from __future__ import annotations

from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, request, redirect, flash, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_, and_

from app.database import SessionLocal
from app.models import Adminisztrator, Bejelentes, Modositas
from flask import jsonify


admin_bp = Blueprint("admin", __name__)

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Jelentkezz be az admin felülethez.", "error")
            return redirect(url_for("admin.admin_page"))
        return fn(*args, **kwargs)
    return wrapper


@admin_bp.get("/admin")
def admin_page():
    return render_template("admin_login.html")


@admin_bp.post("/admin/login")
def admin_login():
    nev = (request.form.get("nev") or "").strip()
    jelszo = request.form.get("jelszo") or ""

    db = SessionLocal()
    try:
        admin = db.query(Adminisztrator).filter(Adminisztrator.nev == nev).first()

        if not admin:
            flash("Hibás név vagy jelszó.", "error")
            return redirect(url_for("admin.admin_page"))

        if admin.fiok_allapot != "nyitott":
            flash("A fiók zárolt.", "error")
            return redirect(url_for("admin.admin_page"))

        ok = check_password_hash(admin.jelszo_hash, jelszo)
        if not ok:
            admin.hiba_probalkozasok = (admin.hiba_probalkozasok or 0) + 1

            if admin.hiba_probalkozasok >= 5:
                admin.fiok_allapot = "zárolt"
                db.commit()
                flash("Túl sok hibás próbálkozás. A fiók zárolva lett.", "error")
                return redirect(url_for("admin.admin_page"))

            db.commit()
            maradt = 5 - admin.hiba_probalkozasok
            flash(f"Hibás név vagy jelszó. Hátralévő próbálkozások: {maradt}", "error")
            return redirect(url_for("admin.admin_page"))

        # siker
        admin.hiba_probalkozasok = 0
        db.commit()

        session["admin_id"] = admin.adminID
        session["admin_nev"] = admin.nev

        flash("Sikeres belépés.", "success")
        return redirect(url_for("admin.dashboard"))


    finally:
        db.close()


@admin_bp.post("/admin/change_password")
def admin_change_password():
    nev = (request.form.get("nev") or "").strip()
    jelszo = request.form.get("jelszo") or ""
    uj_jelszo = request.form.get("uj_jelszo") or ""

    if len(uj_jelszo.strip()) < 8:
        flash("Az új jelszó legyen legalább 8 karakter.", "error")
        return redirect(url_for("admin.admin_page"))

    db = SessionLocal()
    try:
        admin = db.query(Adminisztrator).filter(Adminisztrator.nev == nev).first()

        if not admin:
            flash("Hibás név vagy jelszó.", "error")
            return redirect(url_for("admin.admin_page"))

        if admin.fiok_allapot != "nyitott":
            flash("A fiók zárolt, nem módosítható jelszó.", "error")
            return redirect(url_for("admin.admin_page"))

        ok = check_password_hash(admin.jelszo_hash, jelszo)
        if not ok:
            admin.hiba_probalkozasok = (admin.hiba_probalkozasok or 0) + 1
            if admin.hiba_probalkozasok >= 5:
                admin.fiok_allapot = "zárolt"
                db.commit()
                flash("Túl sok hibás próbálkozás. A fiók zárolva lett.", "error")
                return redirect(url_for("admin.admin_page"))

            db.commit()
            flash("Hibás név vagy jelszó.", "error")
            return redirect(url_for("admin.admin_page"))

        admin.jelszo_hash = generate_password_hash(uj_jelszo)
        admin.hiba_probalkozasok = 0
        db.commit()

        flash("Jelszó sikeresen megváltoztatva.", "success")
        return redirect(url_for("admin.admin_page"))

    finally:
        db.close()

@admin_bp.get("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_nev", None)
    flash("Kijelentkezve.", "success")
    return redirect(url_for("admin.admin_page"))

@admin_bp.get("/admin/dashboard")
@login_required
def dashboard():
    statusz = (request.args.get("statusz") or "").strip()
    hely = (request.args.get("hely") or "").strip()
    date_from = (request.args.get("date_from") or "").strip()  # YYYY-MM-DD
    date_to = (request.args.get("date_to") or "").strip()      # YYYY-MM-DD

    filters = []

    if statusz:
        filters.append(Bejelentes.statusz == statusz)

    # időpont szűrés (nap pontossággal)
    def parse_date(s):
        return datetime.strptime(s, "%Y-%m-%d")

    if date_from:
        try:
            dtf = parse_date(date_from)
            filters.append(Bejelentes.datum_ido >= dtf)
        except ValueError:
            flash("Hibás 'date_from' formátum (YYYY-MM-DD).", "error")

    if date_to:
        try:
            # date_to nap vége: +1 nap, < következő nap
            dtt = parse_date(date_to)
            filters.append(Bejelentes.datum_ido < (dtt.replace(hour=0, minute=0, second=0, microsecond=0) ))
            # (ha akarod, később napvége-logicát finomítjuk)
        except ValueError:
            flash("Hibás 'date_to' formátum (YYYY-MM-DD).", "error")

    # helyszín szűrés:
    # - ha "lat,lng" formátum, akkor koordinátára szűrünk kb. egyezéssel
    # - különben cím LIKE
    if hely:
        if "," in hely:
            try:
                lat_s, lng_s = [x.strip() for x in hely.split(",", 1)]
                lat = float(lat_s)
                lng = float(lng_s)
                eps = 0.0005  # ~50m körül (nagyságrend)
                filters.append(and_(
                    Bejelentes.koord_szel != None,
                    Bejelentes.koord_hossz != None,
                    Bejelentes.koord_szel.between(lat - eps, lat + eps),
                    Bejelentes.koord_hossz.between(lng - eps, lng + eps),
                ))
            except ValueError:
                filters.append(Bejelentes.cim.ilike(f"%{hely}%"))
        else:
            filters.append(Bejelentes.cim.ilike(f"%{hely}%"))

    db = SessionLocal()
    try:
        q = db.query(Bejelentes).order_by(Bejelentes.datum_ido.desc())
        if filters:
            q = q.filter(*filters)

        bejelentesek = q.limit(300).all()
        return render_template(
            "admin_dashboard.html",
            bejelentesek=bejelentesek,
            admin_nev=session.get("admin_nev"),
            filters={
                "statusz": statusz,
                "hely": hely,
                "date_from": date_from,
                "date_to": date_to,
            }
        )
    finally:
        db.close()

@admin_bp.post("/admin/bejelentes/<int:bejelentes_id>/update")
@login_required
def update_bejelentes(bejelentes_id: int):
    admin_id = int(session["admin_id"])

    uj_statusz = (request.form.get("statusz") or "").strip() or None
    uj_prioritas = (request.form.get("prioritas") or "").strip() or None
    uj_tipus = (request.form.get("hulladek_tipus") or "").strip() or None
    uj_menny = (request.form.get("mennyiseg") or "").strip() or None

    db = SessionLocal()
    try:
        b = db.query(Bejelentes).filter(Bejelentes.bejelentesID == bejelentes_id).first()
        if not b:
            flash("Nincs ilyen bejelentés.", "error")
            return redirect(url_for("admin.dashboard"))

        changes = []

        def add_change(field_label, old, new):
            if (old or "") != (new or ""):
                changes.append((field_label, old, new))

        add_change("státusz", b.statusz, uj_statusz or b.statusz)  # státusz ne legyen None
        add_change("prioritás", b.prioritas, uj_prioritas)
        add_change("hulladék tipus", b.hulladek_tipus, uj_tipus)
        add_change("mennyiség", b.mennyiseg, uj_menny)

        # alkalmazzuk a változásokat
        if uj_statusz:
            b.statusz = uj_statusz
        if uj_prioritas is not None:
            b.prioritas = uj_prioritas
        if uj_tipus is not None:
            b.hulladek_tipus = uj_tipus
        if uj_menny is not None:
            b.mennyiseg = uj_menny

        # Modositas rekordok
        now = datetime.utcnow()
        for mezo, regi, uj in changes:
            # a DB-ben NVARCHAR(200) -> itt biztosan rövid értékeket tárolunk
            m = Modositas(
                bejelentesID=b.bejelentesID,
                adminID=admin_id,
                datum_ido=now,
                mezo=mezo,
                regi_ertek=(regi if regi is not None else None),
                uj_ertek=(uj if uj is not None else ""),
            )
            db.add(m)

        db.commit()

        if changes:
            flash("Módosítások mentve és naplózva.", "success")
        else:
            flash("Nem történt változás.", "success")

        return redirect(url_for("admin.dashboard"))

    except Exception:
        db.rollback()
        flash("Hiba mentés közben.", "error")
        return redirect(url_for("admin.dashboard"))
    finally:
        db.close()

@admin_bp.get("/admin/modositasok")
@login_required
def list_modositasok():
    db = SessionLocal()
    try:
        items = (
            db.query(Modositas)
            .order_by(Modositas.datum_ido.desc())
            .limit(500)
            .all()
        )

        result = []
        for m in items:
            result.append({
                "modositasID": m.modositasiID,
                "bejelentesID": m.bejelentesID,
                "adminID": m.adminID,
                "datum_ido": m.datum_ido.isoformat(sep=" ", timespec="seconds") if m.datum_ido else None,
                "mezo": m.mezo,
                "regi_ertek": m.regi_ertek,
                "uj_ertek": m.uj_ertek,
            })

        return jsonify(result)
    finally:
        db.close()
