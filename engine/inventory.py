from pathlib import Path
import pandas as pd


INCOMING_TYPES = {
    "Opening Stock",
    "Stock Received",
    "Stock Return"
}

OUTGOING_TYPES = {
    "Stock Transfer",
    "Stock Sold",
    "Stock Damaged"
}


def load_movements(file_path):
    """
    Load the inventory movement ledger.
    """

    path = Path(file_path)

    if not path.exists():
        return pd.DataFrame(
            columns=[
                "Movement ID",
                "Date",
                "Product ID",
                "Product Name",
                "Movement Type",
                "Quantity",
                "Reference",
                "Source/Destination",
                "Recorded By",
                "Notes"
            ]
        )

    df = pd.read_csv(path)

    if "Quantity" in df.columns:
        df["Quantity"] = pd.to_numeric(
            df["Quantity"],
            errors="coerce"
        ).fillna(0)

    return df


def calculate_product_stock(
    movements,
    product_id
):
    """
    Calculate the current stock of one product.
    """

    if movements.empty:
        return 0

    if "Product ID" not in movements.columns:
        return 0

    product_movements = movements[
        movements["Product ID"].astype(str)
        == str(product_id)
    ].copy()

    if product_movements.empty:
        return 0

    product_movements["Quantity"] = pd.to_numeric(
        product_movements["Quantity"],
        errors="coerce"
    ).fillna(0)

    incoming = product_movements[
        product_movements["Movement Type"].isin(
            INCOMING_TYPES
        )
    ]["Quantity"].sum()

    outgoing = product_movements[
        product_movements["Movement Type"].isin(
            OUTGOING_TYPES
        )
    ]["Quantity"].sum()

    return incoming - outgoing


def calculate_all_stock(movements):
    """
    Calculate stock for every product.

    Returns:
        DataFrame with Product ID and Current Stock.
    """

    if movements.empty:
        return pd.DataFrame(
            columns=[
                "Product ID",
                "Current Stock"
            ]
        )

    required = [
        "Product ID",
        "Movement Type",
        "Quantity"
    ]

    missing = [
        column
        for column in required
        if column not in movements.columns
    ]

    if missing:
        return pd.DataFrame(
            columns=[
                "Product ID",
                "Current Stock"
            ]
        )

    df = movements.copy()

    df["Quantity"] = pd.to_numeric(
        df["Quantity"],
        errors="coerce"
    ).fillna(0)

    df["Signed Quantity"] = df.apply(
        lambda row:
            row["Quantity"]
            if row["Movement Type"]
            in INCOMING_TYPES
            else -row["Quantity"],
        axis=1
    )

    stock = (
        df.groupby("Product ID")[
            "Signed Quantity"
        ]
        .sum()
        .reset_index()
        .rename(
            columns={
                "Signed Quantity": "Current Stock"
            }
        )
    )

    return stock


def check_stock_available(
    movements,
    product_id,
    quantity
):
    """
    Check whether enough stock exists.
    """

    current_stock = calculate_product_stock(
        movements,
        product_id
    )

    return current_stock >= quantity


def get_stock_status(
    current_stock,
    reorder_level
):
    """
    Return a user-friendly inventory status.
    """

    try:
        current_stock = float(current_stock)
        reorder_level = float(reorder_level)
    except (ValueError, TypeError):
        return "Unknown"

    if current_stock <= 0:
        return "Out of Stock"

    if current_stock <= reorder_level:
        return "Low Stock"

    return "Healthy"