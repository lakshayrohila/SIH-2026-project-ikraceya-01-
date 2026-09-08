"""
crud.py — database read/write helpers for scan_logs.

Called by:
  - pages/3_Results.py -> save_scan()
  - pages/4_History.py -> get_scan_history()

Builds the JSON blobs via app.utils.json_schema.build_scan_record() before
writing, so the storage shape always matches the spec's Section 12 schema.
"""

import json

from app.db.database import get_session
from app.db.models import ScanLog
from app.utils.json_schema import build_scan_record


def save_scan(user_id: int, persona: str, pipeline_result: dict) -> int:
    """
    Persist a completed scan to MySQL.

    Returns the new scan_id on success. Raises on failure (caller in
    pages/3_Results.py already wraps this in a try/except).
    """
    record = build_scan_record(user_id, persona, pipeline_result)

    session = get_session()
    try:
        scan = ScanLog(
            user_id=user_id,
            persona=persona,
            extracted_text=record["extracted_text"],
            scope_check_json=json.dumps(record["scope_check"]),
            declarations_json=json.dumps(record["declarations"]),
            font_checks_json=json.dumps(record["font_checks"]),
            quantity_checks_json=json.dumps(record["quantity_checks"]),
            violations_json=json.dumps(record["violations"]),
            overall_status=record["overall_status"],
        )
        session.add(scan)
        session.commit()
        session.refresh(scan)
        return scan.scan_id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_scan_history(user_id: int) -> list[dict]:
    """
    Fetch this user's past scans, most recent first.

    Returns a list of flat dicts (ready for pandas.DataFrame in
    pages/4_History.py) — JSON columns are parsed back into Python objects.
    """
    session = get_session()
    try:
        scans = (
            session.query(ScanLog)
            .filter_by(user_id=user_id)
            .order_by(ScanLog.scan_timestamp.desc())
            .all()
        )

        records = []
        for scan in scans:
            records.append({
                "scan_id": scan.scan_id,
                "persona": scan.persona,
                "scan_timestamp": scan.scan_timestamp,
                "overall_status": scan.overall_status,
                "extracted_text": scan.extracted_text,
                "violations": json.loads(scan.violations_json) if scan.violations_json else [],
            })
        return records
    finally:
        session.close()


def get_scan_by_id(scan_id: int) -> dict | None:
    """Fetch a single scan's full detail (used for a future 'view details' drill-down)."""
    session = get_session()
    try:
        scan = session.query(ScanLog).filter_by(scan_id=scan_id).first()
        if scan is None:
            return None

        return {
            "scan_id": scan.scan_id,
            "user_id": scan.user_id,
            "persona": scan.persona,
            "scan_timestamp": scan.scan_timestamp,
            "overall_status": scan.overall_status,
            "extracted_text": scan.extracted_text,
            "scope_check": json.loads(scan.scope_check_json) if scan.scope_check_json else {},
            "declarations": json.loads(scan.declarations_json) if scan.declarations_json else {},
            "font_checks": json.loads(scan.font_checks_json) if scan.font_checks_json else {},
            "quantity_checks": json.loads(scan.quantity_checks_json) if scan.quantity_checks_json else {},
            "violations": json.loads(scan.violations_json) if scan.violations_json else [],
        }
    finally:
        session.close()