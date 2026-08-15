from pathlib import Path
import pandas as pd


# ============================================================
# BISCUIT CRM / ERP
# REPORTS & ANALYTICS ENGINE
# ============================================================


# ============================================================
# GENERAL HELPERS
# ============================================================

def load_csv(file_path):

    path = Path(file_path)

    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(path)

    except Exception:
        return pd.DataFrame()


def numeric(series):

    return pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(0)


def find_column(df, candidates):

    for column in candidates:

        if column in df.columns:
            return column

    return None


# ============================================================
# SALES SUMMARY
# ============================================================

def sales_summary(sales_file):

    sales = load_csv(sales_file)

    if sales.empty:

        return {
            "total_sales": 0.0,
            "transaction_count": 0,
            "average_sale": 0.0
        }

    amount_column = find_column(
        sales,
        [
            "Total Amount",
            "Total",
            "Grand Total",
            "Amount"
        ]
    )

    if amount_column:

        total = numeric(
            sales[amount_column]
        ).sum()

    else:

        total = 0.0

    transaction_count = len(sales)

    if transaction_count > 0:

        average_sale = (
            total / transaction_count
        )

    else:

        average_sale = 0.0

    return {
        "total_sales": float(total),
        "transaction_count": transaction_count,
        "average_sale": float(average_sale)
    }


# ============================================================
# SALES BY DAY
# ============================================================

def sales_by_day(sales_file):

    sales = load_csv(
        sales_file
    )

    if sales.empty:
        return pd.DataFrame()

    date_column = find_column(
        sales,
        [
            "Sale Date",
            "Date",
            "Transaction Date"
        ]
    )

    amount_column = find_column(
        sales,
        [
            "Total Amount",
            "Total",
            "Grand Total",
            "Amount"
        ]
    )

    if not date_column or not amount_column:

        return pd.DataFrame()

    result = sales.copy()

    result["Date"] = pd.to_datetime(
        result[date_column],
        errors="coerce"
    )

    result["Amount"] = numeric(
        result[amount_column]
    )

    result = result.dropna(
        subset=["Date"]
    )

    if result.empty:
        return pd.DataFrame()

    result = (
        result
        .groupby(
            "Date",
            as_index=False
        )["Amount"]
        .sum()
        .sort_values(
            "Date"
        )
    )

    return result


# ============================================================
# SALES BY MONTH
# ============================================================

def sales_by_month(sales_file):

    daily = sales_by_day(
        sales_file
    )

    if daily.empty:
        return pd.DataFrame()

    daily["Month"] = (
        daily["Date"]
        .dt.to_period("M")
        .astype(str)
    )

    result = (
        daily
        .groupby(
            "Month",
            as_index=False
        )["Amount"]
        .sum()
    )

    return result


# ============================================================
# SALES BY PRODUCT
# ============================================================

def sales_by_product(sales_file, sale_items_file=None):

    # Product-level analysis belongs to sale_items, because sales.csv
    # contains transaction totals but not individual product names.
    if sale_items_file:
        items = load_csv(sale_items_file)
        if not items.empty:
            product_column = find_column(
                items,
                ["Product Name", "Product", "Product ID"]
            )
            amount_column = find_column(
                items,
                ["Line Total", "Total Amount", "Amount"]
            )
            if product_column and amount_column:
                result = items.copy()
                result["Amount"] = numeric(result[amount_column])
                return (
                    result.groupby(product_column, as_index=False)["Amount"]
                    .sum()
                    .sort_values("Amount", ascending=False)
                )

    # Backward-compatible fallback for older datasets.
    sales = load_csv(sales_file)
    if sales.empty:
        return pd.DataFrame()

    product_column = find_column(
        sales, ["Product Name", "Product", "Product ID"]
    )
    amount_column = find_column(
        sales, ["Total Amount", "Total", "Grand Total", "Amount"]
    )

    if not product_column or not amount_column:
        return pd.DataFrame()

    result = sales.copy()
    result["Amount"] = numeric(result[amount_column])
    return (
        result.groupby(product_column, as_index=False)["Amount"]
        .sum()
        .sort_values("Amount", ascending=False)
    )


# ============================================================
# SALES BY CUSTOMER
# ============================================================

def sales_by_customer(sales_file):

    sales = load_csv(
        sales_file
    )

    if sales.empty:
        return pd.DataFrame()

    customer_column = find_column(
        sales,
        [
            "Customer Name",
            "Customer ID"
        ]
    )

    amount_column = find_column(
        sales,
        [
            "Total Amount",
            "Total",
            "Grand Total",
            "Amount"
        ]
    )

    if not customer_column or not amount_column:

        return pd.DataFrame()

    result = sales.copy()

    result["Amount"] = numeric(
        result[amount_column]
    )

    result = (
        result
        .groupby(
            customer_column,
            as_index=False
        )["Amount"]
        .sum()
        .sort_values(
            "Amount",
            ascending=False
        )
    )

    return result


# ============================================================
# INVENTORY SUMMARY
# ============================================================

def inventory_summary(
    products_file,
    movements_file
):

    products = load_csv(
        products_file
    )

    movements = load_csv(
        movements_file
    )

    if products.empty:

        return {
            "products": 0,
            "total_stock": 0,
            "low_stock": 0,
            "damaged_stock": 0,
            "stock_received": 0,
            "stock_issued": 0
        }

    # --------------------------------------------------------
    # REORDER LEVEL
    # --------------------------------------------------------

    if "Reorder Level" in products.columns:

        reorder = numeric(
            products["Reorder Level"]
        ).reset_index(
            drop=True
        )

    else:

        reorder = pd.Series(
            0,
            index=range(
                len(products)
            ),
            dtype="float64"
        )

    # --------------------------------------------------------
    # DEFAULT STOCK
    # --------------------------------------------------------

    calculated_stock = pd.Series(
        0,
        index=range(
            len(products)
        ),
        dtype="float64"
    )

    received = 0
    issued = 0
    damaged = 0

    # --------------------------------------------------------
    # CALCULATE FROM MOVEMENT LEDGER
    # --------------------------------------------------------

    if not movements.empty:

        quantity_column = find_column(
            movements,
            [
                "Quantity"
            ]
        )

        type_column = find_column(
            movements,
            [
                "Movement Type"
            ]
        )

        product_column = find_column(
            movements,
            [
                "Product ID"
            ]
        )

        if (
            quantity_column
            and type_column
            and product_column
        ):

            movements = movements.copy()

            movements["Quantity"] = numeric(
                movements[
                    quantity_column
                ]
            )

            movements[type_column] = (
                movements[type_column]
                .astype(str)
                .str.strip()
            )

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

            # ------------------------------------------------
            # TOTAL RECEIVED
            # ------------------------------------------------

            incoming = movements[
                movements[type_column].isin(
                    incoming_types
                )
            ]

            received = incoming[
                "Quantity"
            ].sum()

            # ------------------------------------------------
            # TOTAL ISSUED
            # ------------------------------------------------

            issued = movements[
                movements[type_column].isin(
                    [
                        "Stock Transfer",
                        "Stock Sold"
                    ]
                )
            ]["Quantity"].sum()

            # ------------------------------------------------
            # TOTAL DAMAGED
            # ------------------------------------------------

            damaged = movements[
                movements[type_column]
                == "Stock Damaged"
            ]["Quantity"].sum()

            # ------------------------------------------------
            # PRODUCT-BY-PRODUCT STOCK
            # ------------------------------------------------

            for position, (_, product) in enumerate(
                products.iterrows()
            ):

                product_id = str(
                    product.get(
                        "Product ID",
                        ""
                    )
                )

                product_movements = movements[
                    movements[
                        product_column
                    ]
                    .astype(str)
                    == product_id
                ]

                product_incoming = (
                    product_movements[
                        product_movements[
                            type_column
                        ].isin(
                            incoming_types
                        )
                    ]["Quantity"]
                    .sum()
                )

                product_outgoing = (
                    product_movements[
                        product_movements[
                            type_column
                        ].isin(
                            outgoing_types
                        )
                    ]["Quantity"]
                    .sum()
                )

                calculated_stock.iloc[
                    position
                ] = (
                    product_incoming
                    - product_outgoing
                )

        else:

            # ------------------------------------------------
            # FALLBACK
            # ------------------------------------------------

            if "Current Stock" in products.columns:

                calculated_stock = numeric(
                    products[
                        "Current Stock"
                    ]
                ).reset_index(
                    drop=True
                )

    else:

        # ----------------------------------------------------
        # NO MOVEMENT RECORDS
        # ----------------------------------------------------

        if "Current Stock" in products.columns:

            calculated_stock = numeric(
                products[
                    "Current Stock"
                ]
            ).reset_index(
                drop=True
            )

    # --------------------------------------------------------
    # TOTAL STOCK
    # --------------------------------------------------------

    total_stock = calculated_stock.sum()

    # --------------------------------------------------------
    # LOW STOCK
    # --------------------------------------------------------

    low_stock = int(
        (
            calculated_stock
            <= reorder
        ).sum()
    )

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return {

        "products":
            len(products),

        "total_stock":
            int(total_stock),

        "low_stock":
            low_stock,

        "damaged_stock":
            int(damaged),

        "stock_received":
            int(received),

        "stock_issued":
            int(issued)
    }


# ============================================================
# PAYMENT SUMMARY
# ============================================================

def payment_summary(payments_file):

    payments = load_csv(
        payments_file
    )

    if payments.empty:

        return {
            "total_received": 0.0,
            "payment_count": 0,
            "average_payment": 0.0
        }

    amount_column = find_column(
        payments,
        [
            "Amount",
            "Payment Amount"
        ]
    )

    if not amount_column:

        return {
            "total_received": 0.0,
            "payment_count": 0,
            "average_payment": 0.0
        }

    valid = payments.copy()

    if "Status" in valid.columns:

        valid = valid[
            valid["Status"]
            .astype(str)
            .str.strip()
            .str.lower()
            == "completed"
        ]

    valid["Amount"] = numeric(
        valid[amount_column]
    )

    total = valid[
        "Amount"
    ].sum()

    count = len(valid)

    if count > 0:

        average = (
            total / count
        )

    else:

        average = 0.0

    return {

        "total_received":
            float(total),

        "payment_count":
            count,

        "average_payment":
            float(average)
    }


# ============================================================
# EXPENDITURE SUMMARY
# ============================================================

def expenditure_summary(
    expenditure_file
):

    expenditure = load_csv(
        expenditure_file
    )

    if expenditure.empty:

        return {
            "total_requested": 0.0,
            "total_approved": 0.0,
            "pending_amount": 0.0,
            "request_count": 0
        }

    amount_column = find_column(
        expenditure,
        [
            "Amount Requested",
            "Requested Amount",
            "Amount"
        ]
    )

    if not amount_column:

        return {
            "total_requested": 0.0,
            "total_approved": 0.0,
            "pending_amount": 0.0,
            "request_count": len(
                expenditure
            )
        }

    expenditure = expenditure.copy()

    expenditure["Amount"] = numeric(
        expenditure[
            amount_column
        ]
    )

    total_requested = (
        expenditure[
            "Amount"
        ].sum()
    )

    total_approved = 0.0

    pending_amount = 0.0

    if "Status" in expenditure.columns:

        status = (
            expenditure[
                "Status"
            ]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        approved = expenditure[
            status.isin(
                [
                    "approved",
                    "completed",
                    "paid"
                ]
            )
        ]

        pending = expenditure[
            status.isin(
                [
                    "submitted",
                    "pending",
                    "pending approval"
                ]
            )
        ]

        total_approved = (
            approved[
                "Amount"
            ].sum()
        )

        pending_amount = (
            pending[
                "Amount"
            ].sum()
        )

    return {

        "total_requested":
            float(total_requested),

        "total_approved":
            float(total_approved),

        "pending_amount":
            float(pending_amount),

        "request_count":
            len(expenditure)
    }


# ============================================================
# INVOICE SUMMARY
# ============================================================

def invoice_summary(
    invoices_file,
    payments_file
):

    invoices = load_csv(
        invoices_file
    )

    payments = payment_summary(
        payments_file
    )

    if invoices.empty:

        return {
            "invoice_count": 0,
            "total_invoiced": 0.0,
            "total_paid": payments[
                "total_received"
            ],
            "outstanding": 0.0
        }

    total_column = find_column(
        invoices,
        [
            "Total Amount",
            "Invoice Total",
            "Total",
            "Grand Total",
            "Amount"
        ]
    )

    if not total_column:

        total_invoiced = 0.0

    else:

        total_invoiced = numeric(
            invoices[
                total_column
            ]
        ).sum()

    total_paid = payments[
        "total_received"
    ]

    outstanding = max(
        total_invoiced
        - total_paid,
        0
    )

    return {

        "invoice_count":
            len(invoices),

        "total_invoiced":
            float(total_invoiced),

        "total_paid":
            float(total_paid),

        "outstanding":
            float(outstanding)
    }


# ============================================================
# MANAGEMENT KPIs
# ============================================================

def management_kpis(
    customers_file,
    products_file,
    sales_file,
    payments_file,
    invoices_file,
    movements_file,
    expenditure_file
):

    customers = load_csv(
        customers_file
    )

    sales = sales_summary(
        sales_file
    )

    inventory = inventory_summary(
        products_file,
        movements_file
    )

    payments = payment_summary(
        payments_file
    )

    invoices = invoice_summary(
        invoices_file,
        payments_file
    )

    expenditure = expenditure_summary(
        expenditure_file
    )

    return {

        "total_customers":
            len(customers),

        "total_sales":
            sales[
                "total_sales"
            ],

        "sales_transactions":
            sales[
                "transaction_count"
            ],

        "average_sale":
            sales[
                "average_sale"
            ],

        "total_stock":
            inventory[
                "total_stock"
            ],

        "low_stock":
            inventory[
                "low_stock"
            ],

        "stock_received":
            inventory[
                "stock_received"
            ],

        "stock_issued":
            inventory[
                "stock_issued"
            ],

        "damaged_stock":
            inventory[
                "damaged_stock"
            ],

        "total_received":
            payments[
                "total_received"
            ],

        "outstanding_invoices":
            invoices[
                "outstanding"
            ],

        "total_invoiced":
            invoices[
                "total_invoiced"
            ],

        "invoice_count":
            invoices[
                "invoice_count"
            ],

        "total_expenditure":
            expenditure[
                "total_approved"
            ],

        "pending_expenditure":
            expenditure[
                "pending_amount"
            ]
    }


# ============================================================
# TOP PRODUCTS
# ============================================================

def top_products(
    sales_file,
    limit=10,
    sale_items_file=None
):

    result = sales_by_product(
        sales_file,
        sale_items_file
    )

    if result.empty:

        return pd.DataFrame()

    return result.head(
        limit
    )


# ============================================================
# TOP CUSTOMERS
# ============================================================

def top_customers(
    sales_file,
    limit=10
):

    result = sales_by_customer(
        sales_file
    )

    if result.empty:

        return pd.DataFrame()

    return result.head(
        limit
    )


# ============================================================
# SALES VS EXPENDITURE
# ============================================================

def sales_vs_expenditure(
    sales_file,
    expenditure_file
):

    sales = sales_summary(
        sales_file
    )

    expenditure = expenditure_summary(
        expenditure_file
    )

    return pd.DataFrame(
        [
            {
                "Category": "Sales",
                "Amount":
                    sales[
                        "total_sales"
                    ]
            },
            {
                "Category": "Approved Expenditure",
                "Amount":
                    expenditure[
                        "total_approved"
                    ]
            }
        ]
    )


# ============================================================
# STOCK MOVEMENT SUMMARY
# ============================================================

def stock_movement_summary(
    movements_file
):

    movements = load_csv(
        movements_file
    )

    if movements.empty:

        return pd.DataFrame(
            columns=[
                "Movement Type",
                "Quantity"
            ]
        )

    type_column = find_column(
        movements,
        [
            "Movement Type"
        ]
    )

    quantity_column = find_column(
        movements,
        [
            "Quantity"
        ]
    )

    if not type_column or not quantity_column:

        return pd.DataFrame(
            columns=[
                "Movement Type",
                "Quantity"
            ]
        )

    movements = movements.copy()

    movements["Quantity"] = numeric(
        movements[
            quantity_column
        ]
    )

    result = (
        movements
        .groupby(
            type_column,
            as_index=False
        )[
            "Quantity"
        ]
        .sum()
        .sort_values(
            "Quantity",
            ascending=False
        )
    )

    return result


# ============================================================
# CUSTOMER PERFORMANCE
# ============================================================

def customer_performance(
    sales_file,
    limit=20
):

    result = sales_by_customer(
        sales_file
    )

    if result.empty:

        return pd.DataFrame()

    result = result.rename(
        columns={
            result.columns[0]:
                "Customer"
        }
    )

    return result.head(
        limit
    )


# ============================================================
# PRODUCT PERFORMANCE
# ============================================================

def product_performance(
    sales_file,
    limit=20
):

    result = sales_by_product(
        sales_file
    )

    if result.empty:

        return pd.DataFrame()

    result = result.rename(
        columns={
            result.columns[0]:
                "Product"
        }
    )

    return result.head(
        limit
    )