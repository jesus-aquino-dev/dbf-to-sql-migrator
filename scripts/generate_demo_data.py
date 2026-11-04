"""Generate fictional FoxPro-style DBF tables to try out dbf2sql.

Writes clientes.dbf, productos.dbf and ventas.dbf with the kind of dirt that
legacy systems accumulate over the years: padded text, empty dates, impossible
dates, garbage in numeric fields, numeric overflow and deleted records.

All names, tax ids and phone numbers are made up.

Usage:
    python scripts/generate_demo_data.py [output_dir]
"""
from __future__ import annotations

import datetime as dt
import random
import struct
import sys
from pathlib import Path

ENCODING = "cp1252"
LANGUAGE_DRIVER_CP1252 = 0x03

FIRST_NAMES = [
    "Juan", "María", "Carlos", "Ana", "Luis", "Rosa", "Pedro", "Carmen",
    "Jorge", "Laura", "Miguel", "Sofía", "Diego", "Lucía", "Fernando", "Patricia",
]
LAST_NAMES = [
    "González", "Benítez", "Martínez", "López", "Giménez", "Vera", "Rodríguez",
    "Ramírez", "Duarte", "Fernández", "Acosta", "Ortiz", "Villalba", "Cáceres", "Núñez",
]
CITIES = [
    "Asunción", "Ciudad del Este", "Encarnación", "Luque", "San Lorenzo", "Capiatá",
    "Lambaré", "Fernando de la Mora", "Limpio", "Villarrica", "Coronel Oviedo",
    "Pedro Juan Caballero",
]
PRODUCTS = [
    ("Yerba mate 1 kg", 32000), ("Azúcar 1 kg", 7500), ("Arroz 1 kg", 9000),
    ("Aceite de girasol 900 ml", 18500), ("Harina 000 1 kg", 6500),
    ("Fideo tallarín 500 g", 5500), ("Leche entera 1 L", 7000),
    ("Café molido 250 g", 24000), ("Galletitas surtidas", 12000),
    ("Detergente 750 ml", 11500), ("Jabón en polvo 800 g", 19000),
    ("Papel higiénico x4", 13500), ("Agua mineral 2 L", 6000),
    ("Gaseosa cola 2 L", 14000), ("Cerveza lata 473 ml", 8500), ("Caña 1 L", 35000),
    ("Chipa 6 unidades", 15000), ("Mandioca 1 kg", 5000), ("Queso Paraguay 1 kg", 48000),
    ("Carne vacuna 1 kg", 52000), ("Pollo entero 1 kg", 26000), ("Huevos x30", 33000),
    ("Tomate 1 kg", 9500), ("Cebolla 1 kg", 7000),
]


def write_dbf(path, fields, rows, deleted=()):
    """Write a dBase III table, a format Visual FoxPro reads natively.

    fields: list of (name, type, length, decimals).
    rows:   list of value lists. A str in a non-text field is written as-is,
            which is how the demo injects invalid values.
    deleted: indexes of rows to flag as deleted.
    """
    header_len = 32 + 32 * len(fields) + 1
    record_len = 1 + sum(length for _, _, length, _ in fields)
    today = dt.date.today()
    deleted = set(deleted)

    with open(path, "wb") as fh:
        fh.write(struct.pack(
            "<BBBBIHH", 0x03, today.year - 1900, today.month, today.day,
            len(rows), header_len, record_len,
        ))
        fh.write(bytes(17) + bytes([LANGUAGE_DRIVER_CP1252]) + bytes(2))
        for name, ftype, length, decimals in fields:
            fh.write(
                name.encode("ascii").ljust(11, b"\0") + ftype.encode("ascii")
                + bytes(4) + bytes([length, decimals]) + bytes(14)
            )
        fh.write(b"\r")
        for i, row in enumerate(rows):
            fh.write(b"*" if i in deleted else b" ")
            for (name, ftype, length, decimals), value in zip(fields, row):
                fh.write(_encode(name, value, ftype, length, decimals))
        fh.write(b"\x1a")


def _encode(name, value, ftype, length, decimals):
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    elif ftype == "N":
        text = f"{value:.{decimals}f}"
    elif ftype == "D":
        text = value.strftime("%Y%m%d")
    elif ftype == "L":
        text = "T" if value else "F"
    else:
        text = str(value)
    raw = text.encode(ENCODING)
    if len(raw) > length:
        raise ValueError(f"{name}: {text!r} does not fit in {length} bytes")
    return raw.rjust(length) if ftype == "N" else raw.ljust(length)


def random_date(rng, start, end):
    return start + dt.timedelta(days=rng.randint(0, (end - start).days))


def build_clientes(rng):
    fields = [
        ("CODIGO", "N", 6, 0), ("NOMBRE", "C", 40, 0), ("RUC", "C", 15, 0),
        ("CIUDAD", "C", 25, 0), ("TELEFONO", "C", 15, 0), ("FEC_ALTA", "D", 8, 0),
        ("ACTIVO", "L", 1, 0), ("LIM_CRED", "N", 12, 0),
    ]
    rows = []
    for code in range(1, 121):
        rows.append([
            code,
            f"{rng.choice(LAST_NAMES)} {rng.choice(LAST_NAMES)}, {rng.choice(FIRST_NAMES)}",
            f"{rng.randint(800000, 6999999)}-{rng.randint(0, 9)}",
            rng.choice(CITIES),
            f"555-{rng.randint(0, 9999):04d}",
            random_date(rng, dt.date(2008, 1, 1), dt.date(2025, 12, 31)),
            rng.random() > 0.15,
            rng.choice([0, 500000, 1000000, 2500000, 5000000]),
        ])
    rows[0][1] = "Peña Núñez, María José"            # accents must survive
    rows[4][1] = "   gonzález benítez, carlos   "    # padded, lowercase text
    rows[9][5] = None                                # empty date
    rows[14][5] = "20230231"                         # February 31st
    rows[29][5] = "20221345"                         # month 13
    rows[59][5] = "19/05/19"                         # typed as dd/mm/yy
    return fields, rows, ()


def build_productos(rng):
    fields = [
        ("CODIGO", "C", 10, 0), ("DESCRIP", "C", 50, 0), ("PRECIO", "N", 12, 0),
        ("STOCK", "N", 8, 0), ("FEC_ACT", "D", 8, 0),
    ]
    rows = [
        [f"P{n:04d}", name, price, rng.randint(0, 500),
         random_date(rng, dt.date(2024, 1, 1), dt.date(2026, 9, 30))]
        for n, (name, price) in enumerate(PRODUCTS, start=1)
    ]
    rows[3][3] = "12A"          # letter typed into a number
    rows[7][2] = "1.500.000"    # thousands separators stored as text
    rows[10][3] = "********"    # FoxPro numeric overflow
    return fields, rows, ()


def build_ventas(rng):
    fields = [
        ("NRO", "N", 8, 0), ("FECHA", "D", 8, 0), ("CLIENTE", "N", 6, 0),
        ("PRODUCTO", "C", 10, 0), ("CANTIDAD", "N", 6, 0), ("TOTAL", "N", 14, 0),
        ("ANULADA", "L", 1, 0),
    ]
    rows = []
    for nro in range(1, 1501):
        product = rng.randrange(len(PRODUCTS))
        qty = rng.randint(1, 12)
        rows.append([
            nro,
            random_date(rng, dt.date(2025, 1, 1), dt.date(2026, 9, 30)),
            rng.randint(1, 120),
            f"P{product + 1:04d}",
            qty,
            PRODUCTS[product][1] * qty,
            rng.random() < 0.03,
        ])
    return fields, rows, (100, 777)


def generate(output_dir, seed=2026):
    """Write the three demo tables into output_dir and return their paths."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    paths = []
    for name, build in [("clientes", build_clientes), ("productos", build_productos),
                        ("ventas", build_ventas)]:
        fields, rows, deleted = build(rng)
        path = output_dir / f"{name}.dbf"
        write_dbf(path, fields, rows, deleted)
        paths.append(path)
    return paths


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo_data")
    for path in generate(target):
        print(f"wrote {path}")
