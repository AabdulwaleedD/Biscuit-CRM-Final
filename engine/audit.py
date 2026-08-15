from pathlib import Path
from datetime import datetime
import pandas as pd
import re


AUDIT_COLUMNS = [
    "Audit ID",
    "Date/Time",
    "User",
    "Action",
    "Record Type",
    "Record ID",
    "Description",
]


def _load_audit_table(path):
    if not path.exists():
        return pd.DataFrame(columns=AUDIT_COLUMNS)

    try:
        df = pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=AUDIT_COLUMNS)

    # Repair legacy/malformed CSVs that may contain a duplicated header
    # stored as an extra first column.
    for column in AUDIT_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df[AUDIT_COLUMNS].copy()


def record_audit(
    file_path,
    user,
    action,
    record_type,
    record_id,
    description
):
    """
    Append a normalized audit event to the CRM audit log.
    """

    path = Path(file_path)
    df = _load_audit_table(path)

    numbers = (
        df["Audit ID"]
        .astype(str)
        .str.extract(r"AUD-(\d+)$", expand=False)
    )
    numbers = pd.to_numeric(numbers, errors="coerce").dropna()
    audit_number = int(numbers.max()) + 1 if not numbers.empty else 1

    new_record = pd.DataFrame([{
        "Audit ID": f"AUD-{audit_number:06d}",
        "Date/Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "User": user,
        "Action": action,
        "Record Type": record_type,
        "Record ID": record_id,
        "Description": description,
    }])

    df = pd.concat([df, new_record], ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

    return new_record.iloc[0]["Audit ID"]
