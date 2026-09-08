"""
models.py — SQLAlchemy ORM models: User and ScanLog.

Matches the schema drafted in the project handoff doc, Section 5.
Run scripts/init_db.py after setting up .env to create these tables in MySQL.
"""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'consumer', 'seller', 'admin'
    created_at = Column(TIMESTAMP, server_default=func.now())

    scans = relationship("ScanLog", back_populates="user")


class ScanLog(Base):
    __tablename__ = "scan_logs"

    scan_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    persona = Column(String(20))  # 'consumer' or 'seller'
    scan_timestamp = Column(TIMESTAMP, server_default=func.now())

    extracted_text = Column(Text)          # raw OCR output
    scope_check_json = Column(Text)        # JSON blob — see rules/json_schema
    declarations_json = Column(Text)       # JSON blob
    font_checks_json = Column(Text)        # JSON blob
    quantity_checks_json = Column(Text)    # JSON blob
    violations_json = Column(Text)         # JSON blob

    overall_status = Column(String(20))    # COMPLIANT / NON_COMPLIANT / PARTIAL / OUT_OF_SCOPE

    user = relationship("User", back_populates="scans")