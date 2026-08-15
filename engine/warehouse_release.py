from pathlib import Path
from datetime import datetime
import pandas as pd

from .audit import record_audit


# ============================================================
# WAREHOUSE RELEASE ENGINE
# ============================================================

def load_csv(file_path):
    path = Path(file_path)

    if path.exists():
        return pd.read_csv(path)

    return pd.DataFrame()


# ============================================================
# FIND REQUEST
# ============================================================

def get_request(
    approvals_file,
    request_id
):
    approvals = load_csv(approvals_file)

    if approvals.empty:
        raise ValueError("Approval database is empty.")

    if "Request ID" not in approvals.columns:
        raise ValueError(
            "Approval database is missing 'Request ID'."
        )

    matches = approvals[
        approvals["Request ID"].astype(str)
        == str(request_id)
    ]

    if matches.empty:
        raise ValueError(
            f"Request {request_id} was not found."
        )

    return approvals, matches.index[0]


# ============================================================
# GET PRODUCT STOCK
# ============================================================

def get_available_stock(
    products_file,
    movements_file,
    product_id
):
    products = load_csv(products_file)
    movements = load_csv(movements_file)

    if products.empty:
        raise ValueError(
            "Product database is empty."
        )

    product_rows = products[
        products["Product ID"].astype(str)
        == str(product_id)
    ]

    if product_rows.empty:
        raise ValueError(
            f"Product {product_id} was not found."
        )

    # --------------------------------------------------------
    # CALCULATE FROM MOVEMENT LEDGER
    # --------------------------------------------------------

    if not movements.empty:

        if "Quantity" in movements.columns:

            movements["Quantity"] = pd.to_numeric(
                movements["Quantity"],
                errors="coerce"
            ).fillna(0)

        incoming_types = [
            "Opening Stock",
            "Stock Received",
            "Stock Return"
        ]

        outgoing_types = [
            "Stock Transfer",
            "Stock Sold",
            "Stock Damaged"
        ]

        incoming = movements[
            movements["Movement Type"].isin(
                incoming_types
            )
        ]

        outgoing = movements[
            movements["Movement Type"].isin(
                outgoing_types
            )
        ]

        received = incoming[
            incoming["Product ID"].astype(str)
            == str(product_id)
        ]["Quantity"].sum()

        issued = outgoing[
            outgoing["Product ID"].astype(str)
            == str(product_id)
        ]["Quantity"].sum()

        return max(
            0,
            received - issued
        )

    # --------------------------------------------------------
    # FALLBACK TO PRODUCT TABLE
    # --------------------------------------------------------

    row = product_rows.iloc[0]

    return float(
        pd.to_numeric(
            row.get("Current Stock", 0),
            errors="coerce"
        ) or 0
    )


# ============================================================
# RELEASE STOCK
# ============================================================

def release_stock(
    approvals_file,
    products_file,
    movements_file,
    audit_file,
    request_id,
    released_by,
    approved_quantity=None,
    destination="Sales / Distribution",
    notes=""
):
    """
    Release warehouse stock for an approved stock request.

    Workflow:

    Pending Approval
          ↓
       Approved
          ↓
    Warehouse Release
          ↓
    Stock Movement
          ↓
    Inventory Updated
    """

    # --------------------------------------------------------
    # LOAD REQUEST
    # --------------------------------------------------------

    approvals, request_index = get_request(
        approvals_file,
        request_id
    )

    request = approvals.loc[
        request_index
    ]

    request_type = str(
        request.get(
            "Request Type",
            ""
        )
    )

    if request_type.lower() != "stock request":

        raise ValueError(
            "Only Stock Request records can be "
            "released through the warehouse."
        )

    # --------------------------------------------------------
    # CHECK APPROVAL
    # --------------------------------------------------------

    status = str(
        request.get(
            "Status",
            ""
        )
    )

    if status != "Approved":

        raise ValueError(
            f"Request {request_id} cannot be released. "
            f"Current status: {status}"
        )

    # --------------------------------------------------------
    # PRODUCT INFORMATION
    # --------------------------------------------------------

    product_id = request.get(
        "Product ID",
        ""
    )

    product_name = request.get(
        "Product Name",
        ""
    )

    if not product_id:

        raise ValueError(
            "Stock request does not contain a Product ID."
        )

    # --------------------------------------------------------
    # REQUESTED QUANTITY
    # --------------------------------------------------------

    requested_quantity = float(
        pd.to_numeric(
            request.get(
                "Quantity",
                0
            ),
            errors="coerce"
        ) or 0
    )

    if requested_quantity <= 0:

        raise ValueError(
            "Requested quantity must be greater than zero."
        )

    # --------------------------------------------------------
    # APPROVED QUANTITY
    # --------------------------------------------------------

    if approved_quantity is None:

        approved_quantity = requested_quantity

    approved_quantity = float(
        approved_quantity
    )

    if approved_quantity <= 0:

        raise ValueError(
            "Approved quantity must be greater than zero."
        )

    if approved_quantity > requested_quantity:

        raise ValueError(
            "Approved quantity cannot exceed "
            "requested quantity."
        )

    # --------------------------------------------------------
    # CHECK STOCK
    # --------------------------------------------------------

    available_stock = get_available_stock(
        products_file,
        movements_file,
        product_id
    )

    if approved_quantity > available_stock:

        raise ValueError(
            f"Insufficient stock for {product_name}. "
            f"Available: {available_stock:,.0f}, "
            f"Requested: {approved_quantity:,.0f}"
        )

    # --------------------------------------------------------
    # LOAD MOVEMENTS
    # --------------------------------------------------------

    movements = load_csv(
        movements_file
    )

    # --------------------------------------------------------
    # GENERATE MOVEMENT ID
    # --------------------------------------------------------

    movement_id = (
        f"STOCK-{len(movements) + 1:06d}"
    )

    release_date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # --------------------------------------------------------
    # CREATE STOCK MOVEMENT
    # --------------------------------------------------------

    new_movement = pd.DataFrame(
        [
            {
                "Movement ID": movement_id,
                "Date": release_date,
                "Product ID": product_id,
                "Product Name": product_name,
                "Movement Type": "Stock Transfer",
                "Quantity": approved_quantity,
                "Reference": request_id,
                "Source/Destination": destination,
                "Recorded By": released_by,
                "Notes": notes
            }
        ]
    )

    movements = pd.concat(
        [
            movements,
            new_movement
        ],
        ignore_index=True
    )

    movements.to_csv(
        movements_file,
        index=False
    )

    # --------------------------------------------------------
    # UPDATE REQUEST
    # --------------------------------------------------------

    approvals.loc[
        request_index,
        "Status"
    ] = "Completed"

    approvals.loc[
        request_index,
        "Decision Date"
    ] = release_date

    existing_comment = str(
        approvals.loc[
            request_index,
            "Comment"
        ]
    )

    release_comment = (
        f"Warehouse released "
        f"{approved_quantity:,.0f} units "
        f"to {destination}."
    )

    if existing_comment in [
        "",
        "nan"
    ]:
        final_comment = release_comment
    else:
        final_comment = (
            existing_comment
            + " | "
            + release_comment
        )

    approvals.loc[
        request_index,
        "Comment"
    ] = final_comment

    approvals.to_csv(
        approvals_file,
        index=False
    )

    # --------------------------------------------------------
    # AUDIT LOG
    # --------------------------------------------------------

    record_audit(
        audit_file,
        released_by,
        "WAREHOUSE RELEASE",
        "Stock Request",
        request_id,
        (
            f"{approved_quantity:,.0f} units of "
            f"{product_name} released from warehouse "
            f"to {destination}. "
            f"Movement ID: {movement_id}"
        )
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    remaining_stock = (
        available_stock
        - approved_quantity
    )

    return {
        "request_id": request_id,
        "movement_id": movement_id,
        "product_id": product_id,
        "product_name": product_name,
        "quantity_released": approved_quantity,
        "previous_stock": available_stock,
        "remaining_stock": remaining_stock,
        "destination": destination,
        "status": "Completed",
        "released_by": released_by,
        "release_date": release_date
    }


# ============================================================
# RELEASE HISTORY
# ============================================================

def get_release_history(
    movements_file
):
    """
    Return stock transfers created through
    warehouse release.
    """

    movements = load_csv(
        movements_file
    )

    if movements.empty:
        return movements

    if "Movement Type" not in movements.columns:
        return pd.DataFrame()

    return movements[
        movements["Movement Type"]
        == "Stock Transfer"
    ].copy()