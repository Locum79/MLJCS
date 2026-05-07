"""
Luhn-based certificate ID generator.
Format: MLJ{INITIALS}{SEQUENCE}{LUHN_CHECK}{MMYY}
Example: MLJJS00142MAR25
"""
from datetime import datetime


def _luhn_checksum(number_str: str) -> int:
    """Compute Luhn check digit for a numeric string."""
    digits = [int(d) for d in number_str]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for d in even_digits:
        total += sum(divmod(d * 2, 10))
    return total % 10


def _luhn_check_digit(partial: str) -> str:
    """Return the check digit that makes partial pass Luhn."""
    check = (10 - _luhn_checksum(partial + '0')) % 10
    return str(check)


def _encode_initials(initials: str) -> str:
    """Convert initials to 2-digit numeric for Luhn base."""
    result = ''
    for ch in initials[:2].upper():
        result += str(ord(ch) - 55) if ch.isalpha() else str(ord(ch) - 48)
    return result.zfill(4)


def generate_certificate_id(first_name: str, surname: str, sequence: int, issued_at: datetime = None) -> str:
    """
    Generate MLJ Luhn ID.
    e.g. MLJJS0014{check}MAR25
    """
    if issued_at is None:
        issued_at = datetime.utcnow()

    initials = (first_name[0] + surname[0]).upper() if first_name and surname else 'XX'
    month_str = issued_at.strftime('%b').upper()[:3]   # MAR
    year_str = issued_at.strftime('%y')                # 25
    seq_str = str(sequence).zfill(4)                   # 0014

    # Build numeric base for Luhn: encode initials as digits + sequence
    numeric_base = _encode_initials(initials) + seq_str
    check = _luhn_check_digit(numeric_base)

    return f"MLJ{initials}{seq_str}{check}{month_str}{year_str}"


def verify_certificate_id(cert_id: str) -> bool:
    """Verify a certificate ID passes Luhn check."""
    try:
        # Extract the numeric portion: skip 'MLJ', take initials (2 alpha), then 5 digits
        stripped = cert_id[3:]     # remove MLJ
        initials = stripped[:2]    # e.g. JS
        numeric_part = stripped[2:7]  # 5 digits: 4 seq + 1 check
        numeric_base = _encode_initials(initials) + numeric_part[:4]
        check_digit = int(numeric_part[4])
        expected = int(_luhn_check_digit(numeric_base))
        return check_digit == expected
    except Exception:
        return False
