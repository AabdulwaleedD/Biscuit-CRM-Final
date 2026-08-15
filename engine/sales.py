from pathlib import Path
from datetime import datetime
import pandas as pd

from .ids import generate_year_id
from .inventory import (
    calculate_product_stock,
    check_stock_available
)
from .audit import record_audit


# ============================================================
# SALES ENGINE
# ============================================================

SALE_COLUMNS = [
    "Sale ID",
    "Date",
    "Customer ID",
    "Customer Name",
    "Salesperson",
    "Subtotal",
    "Discount",
    "Tax",
    "Total Amount",
    "Payment Status",
    "Delivery Status",
    "Status"
]


SALE_ITEM_COLUMNS = [
    "Sale Item ID",
    "Sale ID",
    "Product ID",
    "Product Name",
    "Quantity",
    "Unit Price",
    "Discount",
    "Line Total"
]


def load_table(file_path, columns):
    """
    Load a CSV table or create an empty table
    with the correct structure.
    """

    path = Path(file_path)

    if path.exists():

        try:
            df = pd.read_csv(path)

            for column in columns:

                if column not in df.columns:
                    df[column] = ""

            return df[columns]

        except Exception:
            pass

    return pd.DataFrame(columns=columns)


def calculate_line_total(
    quantity,
    unit_price,
    discount=0
):
    """
    Calculate:

    Quantity × Unit Price − Discount
    """

    quantity = float(quantity)
    unit_price = float(unit_price)
    discount = float(discount)

    return (
        quantity * unit_price
    ) - discount


def calculate_sale_total(items):
    """
    Calculate subtotal from sale items.

    items should contain:
    Quantity
    Unit Price
    Discount
    """

    subtotal = 0

    for item in items:

        subtotal += calculate_line_total(
            item["Quantity"],
            item["Unit Price"],
            item.get("Discount", 0)
        )

    return subtotal


def create_sale(
    customers_file,
    products_file,
    movements_file,
    sales_file,
    sale_items_file,
    audit_file,
    customer_id,
    items,
    salesperson="Demo Administrator",
    discount=0,
    tax=0,
    payment_status="Outstanding",
    delivery_status="Pending",
    status="Completed"
):
    """
    Create a complete sales transaction.

    Workflow:

    Customer
       ↓
    Sale
       ↓
    Sale Items
       ↓
    Inventory Validation
       ↓
    Stock Movement
       ↓
    Audit Log
    """

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    customers = pd.read_csv(customers_file)

    products = pd.read_csv(products_file)

    movements = pd.read_csv(movements_file)

    sales = load_table(
        sales_file,
        SALE_COLUMNS
    )

    sale_items = load_table(
        sale_items_file,
        SALE_ITEM_COLUMNS
    )

    # --------------------------------------------------------
    # FIND CUSTOMER
    # --------------------------------------------------------

    customer_rows = customers[
        customers["Customer ID"].astype(str)
        == str(customer_id)
    ]

    if customer_rows.empty:

        raise ValueError(
            f"Customer {customer_id} was not found."
        )

    customer = customer_rows.iloc[0]

    customer_name = customer.get(
        "Customer Name",
        "Unknown Customer"
    )

    # --------------------------------------------------------
    # VALIDATE PRODUCTS AND STOCK
    # --------------------------------------------------------

    validated_items = []

    for item in items:

        product_id = item["Product ID"]

        product_rows = products[
            products["Product ID"].astype(str)
            == str(product_id)
        ]

        if product_rows.empty:

            raise ValueError(
                f"Product {product_id} was not found."
            )

        product = product_rows.iloc[0]

        product_name = product.get(
            "Product Name",
            "Unknown Product"
        )

        quantity = float(
            item["Quantity"]
        )

        if quantity <= 0:

            raise ValueError(
                f"Quantity for {product_name} "
                "must be greater than zero."
            )

        # ----------------------------------------------------
        # CHECK STOCK
        # ----------------------------------------------------

        available_stock = calculate_product_stock(
            movements,
            product_id
        )

        if available_stock < quantity:

            raise ValueError(
                f"Insufficient stock for "
                f"{product_name}. "
                f"Available: {available_stock:,.0f}, "
                f"Requested: {quantity:,.0f}"
            )

        unit_price = item.get(
            "Unit Price",
            product.get("Selling Price", 0)
        )

        discount_amount = item.get(
            "Discount",
            0
        )

        line_total = calculate_line_total(
            quantity,
            unit_price,
            discount_amount
        )

        validated_items.append(
            {
                "Product ID": product_id,
                "Product Name": product_name,
                "Quantity": quantity,
                "Unit Price": float(unit_price),
                "Discount": float(discount_amount),
                "Line Total": line_total
            }
        )

    # --------------------------------------------------------
    # CALCULATE TOTAL
    # --------------------------------------------------------

    subtotal = calculate_sale_total(
        validated_items
    )

    total_amount = (
        subtotal
        - float(discount)
        + float(tax)
    )

    # --------------------------------------------------------
    # GENERATE SALE ID
    # --------------------------------------------------------

    sale_id = generate_year_id(
        "SALE",
        sales_file
    )

    sale_date = datetime.now().strftime(
        "%Y-%m-%d"
    )

    # --------------------------------------------------------
    # CREATE SALE RECORD
    # --------------------------------------------------------

    new_sale = pd.DataFrame(
        [
            {
                "Sale ID": sale_id,
                "Date": sale_date,
                "Customer ID": customer_id,
                "Customer Name": customer_name,
                "Salesperson": salesperson,
                "Subtotal": subtotal,
                "Discount": discount,
                "Tax": tax,
                "Total Amount": total_amount,
                "Payment Status": payment_status,
                "Delivery Status": delivery_status,
                "Status": status
            }
        ]
    )

    sales = pd.concat(
        [
            sales,
            new_sale
        ],
        ignore_index=True
    )

    sales.to_csv(
        sales_file,
        index=False
    )

    # --------------------------------------------------------
    # CREATE SALE ITEMS
    # --------------------------------------------------------

    for index, item in enumerate(
        validated_items,
        start=1
    ):

        sale_item_id = (
            f"SLITEM-{len(sale_items) + 1:06d}"
        )

        new_item = pd.DataFrame(
            [
                {
                    "Sale Item ID": sale_item_id,
                    "Sale ID": sale_id,
                    "Product ID": item["Product ID"],
                    "Product Name": item["Product Name"],
                    "Quantity": item["Quantity"],
                    "Unit Price": item["Unit Price"],
                    "Discount": item["Discount"],
                    "Line Total": item["Line Total"]
                }
            ]
        )

        sale_items = pd.concat(
            [
                sale_items,
                new_item
            ],
            ignore_index=True
        )

    sale_items.to_csv(
        sale_items_file,
        index=False
    )

    # --------------------------------------------------------
    # CREATE INVENTORY MOVEMENTS
    # --------------------------------------------------------

    for item in validated_items:

        movement_id = (
            f"STOCK-{len(movements) + 1:06d}"
        )

        movement = pd.DataFrame(
            [
                {
                    "Movement ID": movement_id,
                    "Date": sale_date,
                    "Product ID": item["Product ID"],
                    "Product Name": item["Product Name"],
                    "Movement Type": "Stock Sold",
                    "Quantity": item["Quantity"],
                    "Reference": sale_id,
                    "Source/Destination": customer_name,
                    "Recorded By": salesperson,
                    "Notes": (
                        f"Stock issued against "
                        f"sale {sale_id}"
                    )
                }
            ]
        )

        movements = pd.concat(
            [
                movements,
                movement
            ],
            ignore_index=True
        )

    movements.to_csv(
        movements_file,
        index=False
    )

    # --------------------------------------------------------
    # AUDIT LOG
    # --------------------------------------------------------

    record_audit(
        audit_file,
        salesperson,
        "CREATE",
        "Sale",
        sale_id,
        (
            f"Sale created for {customer_name} "
            f"with total value "
            f"₦{total_amount:,.2f}"
        )
    )

    # --------------------------------------------------------
    # RETURN TRANSACTION
    # --------------------------------------------------------

    return {
        "sale_id": sale_id,
        "customer_id": customer_id,
        "customer_name": customer_name,
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": total_amount,
        "items": validated_items,
        "payment_status": payment_status,
        "delivery_status": delivery_status,
        "status": status
    }