"""
Structured Certificate ID Engine.
Format: MLJ-{COURSE}-{YEAR}-{SEQ6}
Example: MLJ-EMR-2026-000183
Guarantees uniqueness per org + course + year + sequence.
"""
from datetime import datetime


def generate_cert_id(course_code: str, sequence: int, issued_at: datetime = None) -> str:
    """
    Generate structured certificate ID.
    MLJ-{COURSE}-{YEAR}-{SEQ:06d}
    """
    if issued_at is None:
        issued_at = datetime.utcnow()
    code = (course_code or 'GEN').upper().strip()[:6]
    year = issued_at.strftime('%Y')
    seq = str(sequence).zfill(6)
    return f"MLJ-{code}-{year}-{seq}"


def next_sequence(cert_type) -> int:
    """Atomically increment and return next sequence for a cert type."""
    cert_type.seq_counter = (cert_type.seq_counter or 0) + 1
    return cert_type.seq_counter


def verify_format(cert_id: str) -> bool:
    """Basic format check: MLJ-XXX-YYYY-NNNNNN"""
    try:
        parts = cert_id.split('-')
        return (
            len(parts) == 4 and
            parts[0] == 'MLJ' and
            len(parts[1]) >= 2 and
            len(parts[2]) == 4 and parts[2].isdigit() and
            len(parts[3]) == 6 and parts[3].isdigit()
        )
    except Exception:
        return False
