from pathlib import Path
from datetime import datetime
import pandas as pd

from .ids import generate_year_id
from .audit import record_audit


# ============================================================
# INVOICE ENGINE
# ============================================================

INVOICE_COLUMNS = [
    "Invoice ID",
    "Invoice Number",
    "Invoice Date",
    "Due Date",
    "Sale ID",
    "Customer ID",
    "Customer Name",
    "Subtotal",
    "Discount",
    "Tax",
    "Total Amount",
    "Amount Paid",
    "Balance Due",
    "Payment Status",
    "Invoice Status",
    "Created By"
]


PAYMENT_COLUMNS = [
    "Payment ID",
    "Payment Date",
    "Invoice ID",
    "Customer ID",
    "Customer Name",
    "Amount",
    "Payment Method",
    "Reference",
    "Received By",
    "Notes"
]


def load_table(file_path, columns):

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


def calculate_payment_status(
    total_amount,
    amount_paid
):

    total_amount = float(total_amount)
    amount_paid = float(amount_paid)

    if amount_paid <= 0:
        return "Outstanding"

    if amount_paid >= total_amount:
        return "Paid"

    return "Partially Paid"


def create_invoice_from_sale(
    sales_file,
    sale_items_file,
    invoices_file,
    audit_file,
    sale_id,
    created_by="Demo Administrator",
    payment_terms_days=30
):
    """
    Generate an invoice directly from a completed sale.

    Sale
       ↓
    Invoice
       ↓
    Customer account
    """

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    sales = pd.read_csv(
        sales_file
    )

    sale_items = pd.read_csv(
        sale_items_file
    )

    invoices = load_table(
        invoices_file,
        INVOICE_COLUMNS
    )

    # --------------------------------------------------------
    # FIND SALE
    # --------------------------------------------------------

    sale_rows = sales[
        sales["Sale ID"].astype(str)
        == str(sale_id)
    ]

    if sale_rows.empty:

        raise ValueError(
            f"Sale {sale_id} was not found."
        )

    sale = sale_rows.iloc[0]

    # --------------------------------------------------------
    # PREVENT DUPLICATE INVOICE
    # --------------------------------------------------------

    existing = invoices[
        invoices["Sale ID"].astype(str)
        == str(sale_id)
    ]

    if not existing.empty:

        raise ValueError(
            f"An invoice already exists for "
            f"sale {sale_id}."
        )

    # --------------------------------------------------------
    # SALE INFORMATION
    # --------------------------------------------------------

    customer_id = sale[
        "Customer ID"
    ]

    customer_name = sale[
        "Customer Name"
    ]

    subtotal = float(
        pd.to_numeric(
            sale["Subtotal"],
            errors="coerce"
        )
        or 0
    )

    discount = float(
        pd.to_numeric(
            sale["Discount"],
            errors="coerce"
        )
        or 0
    )

    tax = float(
        pd.to_numeric(
            sale["Tax"],
            errors="coerce"
        )
        or 0
    )

    total_amount = float(
        pd.to_numeric(
            sale["Total Amount"],
            errors="coerce"
        )
        or 0
    )

    # --------------------------------------------------------
    # GENERATE IDS
    # --------------------------------------------------------

    invoice_id = generate_year_id(
        "INV",
        invoices_file
    )

    invoice_number = invoice_id

    invoice_date = datetime.now()

    due_date = (
        invoice_date
        + pd.Timedelta(
            days=payment_terms_days
        )
    )

    # --------------------------------------------------------
    # CREATE INVOICE
    # --------------------------------------------------------

    new_invoice = pd.DataFrame(
        [
            {
                "Invoice ID": invoice_id,
                "Invoice Number": invoice_number,
                "Invoice Date": invoice_date.strftime(
                    "%Y-%m-%d"
                ),
                "Due Date": due_date.strftime(
                    "%Y-%m-%d"
                ),
                "Sale ID": sale_id,
                "Customer ID": customer_id,
                "Customer Name": customer_name,
                "Subtotal": subtotal,
                "Discount": discount,
                "Tax": tax,
                "Total Amount": total_amount,
                "Amount Paid": 0,
                "Balance Due": total_amount,
                "Payment Status": "Outstanding",
                "Invoice Status": "Issued",
                "Created By": created_by
            }
        ]
    )

    invoices = pd.concat(
        [
            invoices,
            new_invoice
        ],
        ignore_index=True
    )

    invoices.to_csv(
        invoices_file,
        index=False
    )

    # --------------------------------------------------------
    # AUDIT
    # --------------------------------------------------------

    record_audit(
        audit_file,
        created_by,
        "CREATE",
        "Invoice",
        invoice_id,
        (
            f"Invoice {invoice_number} generated "
            f"from sale {sale_id} for "
            f"{customer_name}. "
            f"Total: ₦{total_amount:,.2f}"
        )
    )

    return {
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        "sale_id": sale_id,
        "customer_id": customer_id,
        "customer_name": customer_name,
        "total_amount": total_amount,
        "amount_paid": 0,
        "balance_due": total_amount,
        "payment_status": "Outstanding",
        "invoice_status": "Issued"
    }


# ============================================================
# PAYMENT ENGINE
# ============================================================

def record_payment(
    invoices_file,
    payments_file,
    audit_file,
    invoice_id,
    amount,
    payment_method="Bank Transfer",
    reference="",
    received_by="Demo Administrator",
    notes=""
):
    """
    Record a payment against an invoice.

    Automatically updates:

    Amount Paid
    Balance Due
    Payment Status
    """

    invoices = pd.read_csv(
        invoices_file
    )

    payments = load_table(
        payments_file,
        PAYMENT_COLUMNS
    )

    # --------------------------------------------------------
    # FIND INVOICE
    # --------------------------------------------------------

    invoice_rows = invoices[
        invoices["Invoice ID"].astype(str)
        == str(invoice_id)
    ]

    if invoice_rows.empty:

        raise ValueError(
            f"Invoice {invoice_id} was not found."
        )

    index = invoice_rows.index[0]

    invoice = invoices.loc[index]

    # --------------------------------------------------------
    # PAYMENT AMOUNT
    # --------------------------------------------------------

    amount = float(amount)

    if amount <= 0:

        raise ValueError(
            "Payment amount must be greater than zero."
        )

    total_amount = float(
        pd.to_numeric(
            invoice["Total Amount"],
            errors="coerce"
        )
        or 0
    )

    existing_paid = float(
        pd.to_numeric(
            invoice["Amount Paid"],
            errors="coerce"
        )
        or 0
    )

    remaining = (
        total_amount
        - existing_paid
    )

    if amount > remaining:

        raise ValueError(
            f"Payment exceeds the outstanding "
            f"balance of ₦{remaining:,.2f}."
        )

    # --------------------------------------------------------
    # GENERATE PAYMENT ID
    # --------------------------------------------------------

    payment_id = (
        f"PAY-{len(payments) + 1:06d}"
    )

    payment_date = datetime.now().strftime(
        "%Y-%m-%d"
    )

    # --------------------------------------------------------
    # CREATE PAYMENT
    # --------------------------------------------------------

    new_payment = pd.DataFrame(
        [
            {
                "Payment ID": payment_id,
                "Payment Date": payment_date,
                "Invoice ID": invoice_id,
                "Customer ID": invoice["Customer ID"],
                "Customer Name": invoice["Customer Name"],
                "Amount": amount,
                "Payment Method": payment_method,
                "Reference": reference,
                "Received By": received_by,
                "Notes": notes
            }
        ]
    )

    payments = pd.concat(
        [
            payments,
            new_payment
        ],
        ignore_index=True
    )

    payments.to_csv(
        payments_file,
        index=False
    )

    # --------------------------------------------------------
    # UPDATE INVOICE
    # --------------------------------------------------------

    new_total_paid = (
        existing_paid
        + amount
    )

    new_balance = (
        total_amount
        - new_total_paid
    )

    status = calculate_payment_status(
        total_amount,
        new_total_paid
    )

    invoices.loc[
        index,
        "Amount Paid"
    ] = new_total_paid

    invoices.loc[
        index,
        "Balance Due"
    ] = new_balance

    invoices.loc[
        index,
        "Payment Status"
    ] = status

    invoices.to_csv(
        invoices_file,
        index=False
    )

    # --------------------------------------------------------
    # AUDIT
    # --------------------------------------------------------

    record_audit(
        audit_file,
        received_by,
        "PAYMENT",
        "Invoice",
        invoice_id,
        (
            f"Payment of ₦{amount:,.2f} "
            f"received for invoice "
            f"{invoice_id}. "
            f"Remaining balance: "
            f"₦{new_balance:,.2f}"
        )
    )

    return {
        "payment_id": payment_id,
        "invoice_id": invoice_id,
        "amount_paid": amount,
        "total_paid": new_total_paid,
        "balance_due": new_balance,
        "payment_status": status
    }