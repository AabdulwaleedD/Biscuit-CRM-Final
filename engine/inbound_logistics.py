from pathlib import Path
from datetime import datetime
import pandas as pd
from .ids import generate_year_id
from .audit import record_audit

COLUMNS = [
    "Receipt ID", "Expected Date", "Supplier", "Truck ID", "Registration Number",
    "Driver ID", "Driver Name", "Product ID", "Product Name", "Expected Quantity",
    "Received Quantity", "Variance", "Unit", "Status", "Arrival Time", "Received Time", "Notes"
]

VALID_STATUSES = ["Expected", "In Transit", "Arrived", "Receiving", "Received", "Short Received", "Cancelled"]


def _load(path):
    path = Path(path)
    if path.exists():
        try:
            df = pd.read_csv(path)
        except Exception:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[COLUMNS].copy()


def create_inbound_receipt(file_path, audit_file, supplier, truck_id, registration,
                           driver_id, driver_name, product_id, product_name,
                           expected_date, expected_qty, unit, notes, created_by):
    df = _load(file_path)
    receipt_id = generate_year_id("GRN", file_path)
    row = {
        "Receipt ID": receipt_id,
        "Expected Date": expected_date,
        "Supplier": supplier,
        "Truck ID": truck_id,
        "Registration Number": registration,
        "Driver ID": driver_id,
        "Driver Name": driver_name,
        "Product ID": product_id,
        "Product Name": product_name,
        "Expected Quantity": float(expected_qty),
        "Received Quantity": 0,
        "Variance": 0,
        "Unit": unit,
        "Status": "Expected",
        "Arrival Time": "",
        "Received Time": "",
        "Notes": notes,
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(file_path, index=False)
    record_audit(audit_file, created_by, "CREATE INBOUND", "Goods Receipt", receipt_id,
                 f"Expected {expected_qty:g} {unit} of {product_name} from {supplier}.")
    return row


def update_inbound_status(file_path, audit_file, receipt_id, new_status, updated_by):
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid inbound status: {new_status}")
    df = _load(file_path)
    matches = df.index[df["Receipt ID"].astype(str) == str(receipt_id)]
    if len(matches) == 0:
        raise ValueError(f"Goods receipt {receipt_id} was not found.")
    i = matches[0]
    df.loc[i, "Status"] = new_status
    if new_status == "Arrived" and not str(df.loc[i, "Arrival Time"]).strip():
        df.loc[i, "Arrival Time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df.to_csv(file_path, index=False)
    record_audit(audit_file, updated_by, "UPDATE INBOUND", "Goods Receipt", receipt_id,
                 f"Inbound shipment status changed to {new_status}.")
    return df.loc[i].to_dict()


def receive_goods(file_path, movements_file, audit_file, receipt_id, received_qty, received_by):
    df = _load(file_path)
    matches = df.index[df["Receipt ID"].astype(str) == str(receipt_id)]
    if len(matches) == 0:
        raise ValueError(f"Goods receipt {receipt_id} was not found.")
    i = matches[0]
    current_status = str(df.loc[i, "Status"]).strip()
    if current_status in {"Received", "Short Received"}:
        raise ValueError(f"Goods receipt {receipt_id} has already been received and cannot be posted twice.")
    expected = float(pd.to_numeric(df.loc[i, "Expected Quantity"], errors="coerce") or 0)
    received = float(received_qty)
    if received <= 0:
        raise ValueError("Received quantity must be greater than zero.")
    variance = received - expected
    status = "Received" if variance == 0 else "Short Received" if variance < 0 else "Received"
    df.loc[i, "Received Quantity"] = received
    df.loc[i, "Variance"] = variance
    df.loc[i, "Status"] = status
    df.loc[i, "Received Time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df.to_csv(file_path, index=False)

    movements_path = Path(movements_file)
    if movements_path.exists():
        try:
            movements = pd.read_csv(movements_path)
        except Exception:
            movements = pd.DataFrame()
    else:
        movements = pd.DataFrame()
    movement_columns = ["Movement ID", "Date", "Product ID", "Product Name", "Movement Type", "Quantity", "Reference", "User", "Notes"]
    for c in movement_columns:
        if c not in movements.columns:
            movements[c] = ""
    numbers = pd.to_numeric(movements.get("Movement ID", pd.Series(dtype=str)).astype(str).str.extract(r"STK-(\d+)$", expand=False), errors="coerce").dropna()
    next_num = int(numbers.max()) + 1 if not numbers.empty else 1
    movement_id = f"STK-{next_num:06d}"
    movement = {
        "Movement ID": movement_id,
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Product ID": df.loc[i, "Product ID"],
        "Product Name": df.loc[i, "Product Name"],
        "Movement Type": "Stock Received",
        "Quantity": received,
        "Reference": receipt_id,
        "User": received_by,
        "Notes": f"Goods received from {df.loc[i, 'Supplier']} via truck {df.loc[i, 'Truck ID']}.",
    }
    movements = pd.concat([movements[movement_columns], pd.DataFrame([movement])], ignore_index=True)
    movements.to_csv(movements_path, index=False)
    record_audit(audit_file, received_by, "RECEIVE GOODS", "Goods Receipt", receipt_id,
                 f"Received {received:g} {df.loc[i, 'Unit']} of {df.loc[i, 'Product Name']}; variance {variance:g}.")
    return {**df.loc[i].to_dict(), "Movement ID": movement_id}
