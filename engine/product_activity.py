from pathlib import Path
import pandas as pd


def load_csv(path):
    path = Path(path)

    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def get_product_activity(product_id):
    """
    Returns a complete Product 360° activity profile.

    Product
        ↓
    Inventory Movements
        ↓
    Sales
        ↓
    Invoices
    """

    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"

    products_file = data_dir / "products.csv"
    movements_file = data_dir / "inventory_movements.csv"
    sales_file = data_dir / "sales.csv"
    sale_items_file = data_dir / "sale_items.csv"
    invoices_file = data_dir / "invoices.csv"

    product_id = str(product_id).strip()

    products = load_csv(products_file)
    movements = load_csv(movements_file)
    sales = load_csv(sales_file)
    sale_items = load_csv(sale_items_file)
    invoices = load_csv(invoices_file)

    if products.empty or "Product ID" not in products.columns:
        return None

    product_rows = products[
        products["Product ID"].astype(str).str.strip()
        == product_id
    ]

    if product_rows.empty:
        return None

    product = product_rows.iloc[0].to_dict()

    # --------------------------------------------------------
    # INVENTORY MOVEMENTS
    # --------------------------------------------------------

    if not movements.empty and "Product ID" in movements.columns:

        product_movements = movements[
            movements["Product ID"].astype(str).str.strip()
            == product_id
        ].copy()

    else:

        product_movements = pd.DataFrame()

    # --------------------------------------------------------
    # CALCULATED STOCK
    # --------------------------------------------------------

    calculated_stock = 0.0

    if not product_movements.empty:

        quantity_column = (
            "Quantity"
            if "Quantity" in product_movements.columns
            else None
        )

        type_column = (
            "Movement Type"
            if "Movement Type" in product_movements.columns
            else None
        )

        if quantity_column and type_column:

            product_movements["Quantity"] = pd.to_numeric(
                product_movements["Quantity"],
                errors="coerce"
            ).fillna(0)

            incoming = product_movements[
                product_movements[type_column].isin(
                    [
                        "Opening Stock",
                        "Stock Received",
                        "Stock Return",
                    ]
                )
            ]["Quantity"].sum()

            outgoing = product_movements[
                product_movements[type_column].isin(
                    [
                        "Stock Transfer",
                        "Stock Sold",
                        "Stock Damaged",
                    ]
                )
            ]["Quantity"].sum()

            calculated_stock = float(
                incoming - outgoing
            )

    else:

        calculated_stock = float(
            pd.to_numeric(
                product.get("Current Stock", 0),
                errors="coerce"
            ) or 0
        )

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    product_sales = pd.DataFrame()

    if not sale_items.empty:

        if "Product ID" in sale_items.columns:

            product_items = sale_items[
                sale_items["Product ID"].astype(str).str.strip()
                == product_id
            ].copy()

            if not product_items.empty:

                if (
                    not sales.empty
                    and "Sale ID" in product_items.columns
                    and "Sale ID" in sales.columns
                ):

                    product_sales = product_items.merge(
                        sales,
                        on="Sale ID",
                        how="left",
                        suffixes=(
                            "_Item",
                            "_Sale"
                        )
                    )

                else:

                    product_sales = product_items

    # --------------------------------------------------------
    # INVOICES
    # --------------------------------------------------------

    product_invoices = pd.DataFrame()

    if not product_sales.empty:

        if "Sale ID" in product_sales.columns:

            sale_ids = set(
                product_sales["Sale ID"]
                .astype(str)
                .tolist()
            )

            if (
                not invoices.empty
                and "Sale ID" in invoices.columns
            ):

                product_invoices = invoices[
                    invoices["Sale ID"]
                    .astype(str)
                    .isin(sale_ids)
                ].copy()

    # --------------------------------------------------------
    # RETURN PRODUCT PROFILE
    # --------------------------------------------------------

    return {
        "product": product,
        "movements": product_movements,
        "sales": product_sales,
        "invoices": product_invoices,
        "calculated_stock": calculated_stock,
    }