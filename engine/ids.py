from pathlib import Path
import pandas as pd
import re


def generate_id(prefix, file_path, digits=6):
    """
    Generate the next sequential ID for a CSV-backed prototype table.

    Example:
    CUST-000001
    SALE-2026-000001
    INV-2026-000001
    """

    path = Path(file_path)

    if not path.exists():
        return f"{prefix}{1:0{digits}d}"

    try:
        df = pd.read_csv(path)
    except Exception:
        return f"{prefix}{1:0{digits}d}"

    if df.empty:
        return f"{prefix}{1:0{digits}d}"

    id_column = None

    possible_columns = [
        "Customer ID",
        "Product ID",
        "Sale ID",
        "Invoice ID",
        "Payment ID",
        "Movement ID",
        "Request ID",
        "Expenditure ID",
        "Truck ID",
        "Delivery ID",
        "Document ID"
    ]

    for column in possible_columns:
        if column in df.columns:
            id_column = column
            break

    if id_column is None:
        return f"{prefix}{1:0{digits}d}"

    numbers = (
        df[id_column]
        .astype(str)
        .str.extract(r"(\d+)$")[0]
    )

    numbers = pd.to_numeric(
        numbers,
        errors="coerce"
    ).dropna()

    next_number = (
        int(numbers.max()) + 1
        if not numbers.empty
        else 1
    )

    return f"{prefix}{next_number:0{digits}d}"


def generate_year_id(prefix, file_path, year=None, digits=6):
    """
    Generate IDs such as:
    SALE-2026-000001
    INV-2026-000001
    REQ-2026-000001
    EXP-2026-000001

    The generator deliberately searches all ID columns for the requested
    prefix. This prevents collisions when a CSV contains several ID types,
    such as approvals containing both APR and REQ/EXP identifiers.
    """
    from datetime import datetime

    if year is None:
        year = datetime.now().year

    path = Path(file_path)
    fallback = f"{prefix}-{year}-{1:0{digits}d}"

    if not path.exists():
        return fallback

    try:
        df = pd.read_csv(path)
    except Exception:
        return fallback

    if df.empty:
        return fallback

    pattern = rf"^{re.escape(prefix)}-{year}-(\d+)$"
    numbers = []

    for column in df.columns:
        if not str(column).endswith("ID"):
            continue
        extracted = (
            df[column]
            .astype(str)
            .str.extract(pattern, expand=False)
        )
        numeric_values = pd.to_numeric(
            extracted, errors="coerce"
        ).dropna()
        if not numeric_values.empty:
            numbers.extend(numeric_values.tolist())

    next_number = int(max(numbers)) + 1 if numbers else 1
    return f"{prefix}-{year}-{next_number:0{digits}d}"
