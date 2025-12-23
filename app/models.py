#models.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    DECIMAL,
    ForeignKey,
    Integer,
    NVARCHAR,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Adminisztrator(Base):
    __tablename__ = "Adminisztrator"

    adminID = Column(Integer, primary_key=True, autoincrement=True)
    nev = Column(NVARCHAR(100), nullable=False)
    jelszo_hash = Column(NVARCHAR(255), nullable=False)
    fiok_allapot = Column(NVARCHAR(15), nullable=False)
    hiba_probalkozasok = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint(
            "fiok_allapot IN (N'nyitott', N'zárolt')",
            name="CK_Adminisztrator_fiok_allapot",
        ),
    )

    modositasok = relationship("Modositas", back_populates="adminisztrator")


class Bejelentes(Base):
    __tablename__ = "Bejelentes"

    bejelentesID = Column(Integer, primary_key=True, autoincrement=True)
    datum_ido = Column(DateTime, nullable=False, default=datetime.utcnow)

    cim = Column(NVARCHAR(255), nullable=True)
    koord_szel = Column(DECIMAL(9, 6), nullable=True)
    koord_hossz = Column(DECIMAL(9, 6), nullable=True)

    leiras = Column(Text, nullable=True)              # NVARCHAR(MAX)
    foto_url = Column(NVARCHAR(500), nullable=True)

    statusz = Column(NVARCHAR(15), nullable=False, default="beérkezett")
    prioritas = Column(NVARCHAR(15), nullable=True)
    hulladek_tipus = Column(NVARCHAR(50), nullable=True)
    mennyiseg = Column(NVARCHAR(200), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "statusz IN (N'beérkezett', N'folyamatban', N'lezárt')",
            name="CK_Bejelentes_statusz",
        ),
        CheckConstraint(
            "(prioritas IS NULL) OR (prioritas IN (N'alacsony', N'közepes', N'magas'))",
            name="CK_Bejelentes_prioritas",
        ),
        CheckConstraint(
            "(koord_szel IS NULL) OR (koord_szel BETWEEN -90 AND 90)",
            name="CK_Bejelentes_koord_szel",
        ),
        CheckConstraint(
            "(koord_hossz IS NULL) OR (koord_hossz BETWEEN -180 AND 180)",
            name="CK_Bejelentes_koord_hossz",
        ),
        CheckConstraint(
            "(cim IS NOT NULL) OR (koord_szel IS NOT NULL AND koord_hossz IS NOT NULL)",
            name="CK_Bejelentes_check_location",
        ),
    )

    modositasok = relationship("Modositas", back_populates="bejelentes")


class Modositas(Base):
    __tablename__ = "Modositas"

    modositasiID = Column(Integer, primary_key=True, autoincrement=True)

    bejelentesID = Column(Integer, ForeignKey("Bejelentes.bejelentesID"), nullable=False)
    adminID = Column(Integer, ForeignKey("Adminisztrator.adminID"), nullable=False)

    datum_ido = Column(DateTime, nullable=False, default=datetime.utcnow)

    mezo = Column(NVARCHAR(20), nullable=False)
    regi_ertek = Column(NVARCHAR(200), nullable=True)
    uj_ertek = Column(NVARCHAR(200), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "mezo IN (N'státusz', N'prioritás', N'hulladék tipus', N'mennyiség')",
            name="CK_Modositas_mezo",
        ),
    )

    bejelentes = relationship("Bejelentes", back_populates="modositasok")
    adminisztrator = relationship("Adminisztrator", back_populates="modositasok")
