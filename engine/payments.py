from pathlib import Path
from datetime import datetime
import pandas as pd

from .audit import record_audit


# ============================================================
# PAYMENT ENGINE
# ============================================================

PAYMENT_COLUMNS = [
    "Payment ID",
    "Payment Date",
    "Customer ID",
    "Customer Name",
    "Invoice ID",
    "Sale ID",
    "Payment Method",
    "Amount",
    "Reference",
    "Status",
    "Received By",
    "Notes"
]


# ============================================================
# LOAD PAYMENT TABLE
# ============================================================

def load_payments(payments_file):

    path = Path(payments_file)

    if path.exists():

        try:

            df = pd.read_csv(path)

            for column in PAYMENT_COLUMNS:

                if column not in df.columns:
                    df[column] = ""

            return df[PAYMENT_COLUMNS]

        except Exception:
            pass

    return pd.DataFrame(
        columns=PAYMENT_COLUMNS
    )


# ============================================================
# GENERATE PAYMENT ID
# ============================================================

def generate_payment_id(payments):

    return (
        f"PAY-{datetime.now().year}-"
        f"{len(payments) + 1:06d}"
    )


# ============================================================
# RECORD PAYMENT
# ============================================================

def record_payment(
    payments_file,
    audit_file,
    customer_id,
    customer_name,
    invoice_id,
    sale_id,
    amount,
    payment_method,
    reference="",
    received_by="Demo Administrator",
    notes=""
):

    payments = load_payments(
        payments_file
    )

    # --------------------------------------------------------
    # VALIDATE AMOUNT
    # --------------------------------------------------------

    try:
        amount = float(amount)

    except (TypeError, ValueError):

        raise ValueError(
            "Payment amount must be numeric."
        )

    if amount <= 0:

        raise ValueError(
            "Payment amount must be greater than zero."
        )

    # --------------------------------------------------------
    # VALIDATE METHOD
    # --------------------------------------------------------

    valid_methods = [
        "Cash",
        "Bank Transfer",
        "POS",
        "Cheque",
        "Other"
    ]

    if payment_method not in valid_methods:

        raise ValueError(
            f"Invalid payment method: {payment_method}"
        )

    # --------------------------------------------------------
    # GENERATE ID
    # --------------------------------------------------------

    payment_id = generate_payment_id(
        payments
    )

    # --------------------------------------------------------
    # CREATE PAYMENT
    # --------------------------------------------------------

    new_payment = pd.DataFrame(
        [
            {
                "Payment ID": payment_id,

                "Payment Date":
                    datetime.now().strftime(
                        "%Y-%m-%d"
                    ),

                "Customer ID":
                    customer_id,

                "Customer Name":
                    customer_name,

                "Invoice ID":
                    invoice_id,

                "Sale ID":
                    sale_id,

                "Payment Method":
                    payment_method,

                "Amount":
                    amount,

                "Reference":
                    reference,

                "Status":
                    "Completed",

                "Received By":
                    received_by,

                "Notes":
                    notes
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
    # AUDIT
    # --------------------------------------------------------

    record_audit(
        audit_file,
        received_by,
        "RECORD PAYMENT",
        "Payment",
        payment_id,
        (
            f"Payment of ₦{amount:,.2f} "
            f"received for invoice {invoice_id} "
            f"from {customer_name}."
        )
    )

    return {
        "payment_id": payment_id,
        "invoice_id": invoice_id,
        "amount": amount,
        "status": "Completed"
    }


# ============================================================
# GET INVOICE PAYMENTS
# ============================================================

def get_invoice_payments(
    payments_file,
    invoice_id
):

    payments = load_payments(
        payments_file
    )

    if payments.empty:
        return payments

    return payments[
        (
            payments["Invoice ID"]
            .astype(str)
            == str(invoice_id)
        )
        &
        (
            payments["Status"]
            .astype(str)
            == "Completed"
        )
    ]


# ============================================================
# CALCULATE TOTAL PAID
# ============================================================

def calculate_invoice_paid(
    payments_file,
    invoice_id
):

    payments = get_invoice_payments(
        payments_file,
        invoice_id
    )

    if payments.empty:
        return 0.0

    return pd.to_numeric(
        payments["Amount"],
        errors="coerce"
    ).fillna(0).sum()


# ============================================================
# CALCULATE INVOICE BALANCE
# ============================================================

def calculate_invoice_balance(
    payments_file,
    invoice_id,
    invoice_total
):

    try:

        invoice_total = float(
            invoice_total
        )

    except (TypeError, ValueError):

        invoice_total = 0.0

    paid = calculate_invoice_paid(
        payments_file,
        invoice_id
    )

    balance = invoice_total - paid

    # Prevent tiny floating point errors
    if abs(balance) < 0.01:
        balance = 0.0

    return {
        "invoice_total": invoice_total,
        "paid": paid,
        "balance": max(balance, 0.0)
    }


# ============================================================
# INVOICE PAYMENT STATUS
# ============================================================

def get_invoice_payment_status(
    payments_file,
    invoice_id,
    invoice_total
):

    result = calculate_invoice_balance(
        payments_file,
        invoice_id,
        invoice_total
    )

    total = result["invoice_total"]
    paid = result["paid"]

    if paid <= 0:

        return "Outstanding"

    if paid >= total:

        return "Paid"

    return "Partially Paid"


# ============================================================
# CUSTOMER PAYMENT SUMMARY
# ============================================================

def customer_payment_summary(
    payments_file,
    customer_id
):

    payments = load_payments(
        payments_file
    )

    if payments.empty:

        return {
            "customer_id": customer_id,
            "total_paid": 0.0,
            "payment_count": 0
        }

    customer_payments = payments[
        (
            payments["Customer ID"]
            .astype(str)
            == str(customer_id)
        )
        &
        (
            payments["Status"]
            .astype(str)
            == "Completed"
        )
    ]

    total_paid = pd.to_numeric(
        customer_payments["Amount"],
        errors="coerce"
    ).fillna(0).sum()

    return {
        "customer_id": customer_id,
        "total_paid": float(total_paid),
        "payment_count": len(
            customer_payments
        )
    }


# ============================================================
# PAYMENT SUMMARY
# ============================================================

def payment_summary(
    payments_file
):

    payments = load_payments(
        payments_file
    )

    if payments.empty:

        return {
            "total_payments": 0,
            "total_received": 0.0,
            "cash": 0.0,
            "bank_transfer": 0.0,
            "pos": 0.0,
            "cheque": 0.0,
            "other": 0.0
        }

    completed = payments[
        payments["Status"]
        .astype(str)
        == "Completed"
    ].copy()

    completed["Amount"] = pd.to_numeric(
        completed["Amount"],
        errors="coerce"
    ).fillna(0)

    method = (
        completed["Payment Method"]
        .astype(str)
    )

    return {
        "total_payments": len(completed),

        "total_received":
            float(
                completed["Amount"].sum()
            ),

        "cash":
            float(
                completed.loc[
                    method == "Cash",
                    "Amount"
                ].sum()
            ),

        "bank_transfer":
            float(
                completed.loc[
                    method == "Bank Transfer",
                    "Amount"
                ].sum()
            ),

        "pos":
            float(
                completed.loc[
                    method == "POS",
                    "Amount"
                ].sum()
            ),

        "cheque":
            float(
                completed.loc[
                    method == "Cheque",
                    "Amount"
                ].sum()
            ),

        "other":
            float(
                completed.loc[
                    method == "Other",
                    "Amount"
                ].sum()
            )
    }


# ============================================================
# CANCEL PAYMENT
# ============================================================

def cancel_payment(
    payments_file,
    audit_file,
    payment_id,
    cancelled_by,
    reason=""
):

    payments = load_payments(
        payments_file
    )

    matches = payments[
        payments["Payment ID"]
        .astype(str)
        == str(payment_id)
    ]

    if matches.empty:

        raise ValueError(
            f"Payment {payment_id} was not found."
        )

    index = matches.index[0]

    current_status = str(
        payments.loc[
            index,
            "Status"
        ]
    )

    if current_status == "Cancelled":

        raise ValueError(
            f"Payment {payment_id} "
            "is already cancelled."
        )

    payments.loc[
        index,
        "Status"
    ] = "Cancelled"

    if reason:

        payments.loc[
            index,
            "Notes"
        ] = reason

    payments.to_csv(
        payments_file,
        index=False
    )

    record_audit(
        audit_file,
        cancelled_by,
        "CANCEL PAYMENT",
        "Payment",
        payment_id,
        (
            f"Payment cancelled. "
            f"Reason: {reason}"
        )
    )

    return {
        "payment_id": payment_id,
        "status": "Cancelled"
    }