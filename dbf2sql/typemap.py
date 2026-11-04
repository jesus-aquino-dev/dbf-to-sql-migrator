"""Map DBF field types to SQLAlchemy column types."""
from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, Integer, Numeric, String, Text

# Largest number of digits that always fits in a 32-bit INTEGER.
INTEGER_DIGITS = 9


def sql_type(field):
    """Return the SQLAlchemy type for a dbfread field."""
    ftype = field.type
    if ftype == "C":
        return String(field.length)
    if ftype == "N":
        if field.decimal_count == 0:
            return Integer() if field.length <= INTEGER_DIGITS else BigInteger()
        return Numeric(field.length, field.decimal_count)
    if ftype in ("F", "B"):
        return Float()
    if ftype in ("I", "+"):
        return Integer()
    if ftype == "Y":
        return Numeric(19, 4)
    if ftype == "D":
        return Date()
    if ftype in ("T", "@"):
        return DateTime()
    if ftype == "L":
        return Boolean()
    return Text()


def describe(field):
    """Format a field the way FoxPro shows it, e.g. C(40) or N(12,2)."""
    if field.type in ("C", "N", "F") and field.length:
        if field.decimal_count:
            return f"{field.type}({field.length},{field.decimal_count})"
        return f"{field.type}({field.length})"
    return field.type
