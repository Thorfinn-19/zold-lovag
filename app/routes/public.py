# app/routes/public.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from flask import Blueprint, render_template, request, redirect, flash, url_for, jsonify

from app.database import SessionLocal
from app.models import Bejelentes
import os


public_bp = Blueprint("public", __name__)

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@public_bp.get("/")
def index():
    return render_template(
        "index.html",
        google_maps_key=os.environ.get("GOOGLE_MAPS_API_KEY", "")
    )



@public_bp.post("/bejelentes")
def create_bejelentes():
    cim = (request.form.get("cim") or "").strip()
    leiras = (request.form.get("leiras") or "").strip()

    koord_szel_raw = (request.form.get("koord_szel") or "").strip()
    koord_hossz_raw = (request.form.get("koord_hossz") or "").strip()

    koord_szel = None
    koord_hossz = None

    if koord_szel_raw:
        try:
            koord_szel = float(koord_szel_raw)
        except ValueError:
            flash("A szélességi koordináta nem szám.", "error")
            return redirect(url_for("public.index"))

    if koord_hossz_raw:
        try:
            koord_hossz = float(koord_hossz_raw)
        except ValueError:
            flash("A hosszúsági koordináta nem szám.", "error")
            return redirect(url_for("public.index"))

    has_cim = bool(cim)
    has_coords = (koord_szel is not None and koord_hossz is not None)

    if not (has_cim or has_coords):
        flash("Adj meg címet vagy mindkét koordinátát (lat + lng).", "error")
        return redirect(url_for("public.index"))

    foto_url = None
    foto = request.files.get("foto")
    if foto and foto.filename:
        safe_name = f"{int(datetime.utcnow().timestamp())}_{foto.filename}".replace(" ", "_")
        save_path = UPLOAD_DIR / safe_name
        foto.save(save_path)
        foto_url = f"/static/uploads/{safe_name}"

    db = SessionLocal()
    try:
        bej = Bejelentes(
            datum_ido=datetime.utcnow(),
            cim=cim if cim else None,
            koord_szel=koord_szel,
            koord_hossz=koord_hossz,
            leiras=leiras if leiras else None,
            foto_url=foto_url,
            statusz="beérkezett",
        )
        db.add(bej)
        db.commit()
        flash("Bejelentés sikeresen rögzítve!", "success")
    except Exception:
        db.rollback()
        flash("Hiba történt mentés közben. Próbáld újra.", "error")
    finally:
        db.close()

    return redirect(url_for("public.index"))


@public_bp.get("/bejelentesek")
def list_bejelentesek():
    db = SessionLocal()
    try:
        items = (
            db.query(Bejelentes)
            .order_by(Bejelentes.datum_ido.desc())
            .limit(200)
            .all()
        )

        result = []
        for b in items:
            result.append({
                "bejelentesID": b.bejelentesID,
                "datum_ido": b.datum_ido.isoformat(sep=" ", timespec="seconds") if b.datum_ido else None,
                "cim": b.cim,
                "koord_szel": float(b.koord_szel) if b.koord_szel is not None else None,
                "koord_hossz": float(b.koord_hossz) if b.koord_hossz is not None else None,
                "statusz": b.statusz,
                "prioritas": b.prioritas,
                "hulladek_tipus": b.hulladek_tipus,
                "mennyiseg": b.mennyiseg,
            })

        return jsonify(result)
    finally:
        db.close()
