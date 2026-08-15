from pathlib import Path
import pandas as pd


# ============================================================
# CUSTOMER RECEIVABLES / ACCOUNT ENGINE
# ============================================================

def load_csv(file_path):

    path = Path(file_path)

    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(path)

    except Exception:
        return pd.DataFrame()


# ============================================================
# SAFE NUMERIC CONVERSION
# ============================================================

def numeric(series):

    return pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(0)


# ============================================================
# CUSTOMER ACCOUNT SUMMARY
# ============================================================

def customer_account(
    customer_id,
    customers_file,
    sales_file,
    invoices_file,
    payments_file
):

    customers = load_csv(
        customers_file
    )

    sales = load_csv(
        sales_file
    )

    invoices = load_csv(
        invoices_file
    )

    payments = load_csv(
        payments_file
    )

    # --------------------------------------------------------
    # CUSTOMER
    # --------------------------------------------------------

    customer = pd.DataFrame()

    if not customers.empty and "Customer ID" in customers.columns:

        customer = customers[
            customers["Customer ID"]
            .astype(str)
            == str(customer_id)
        ]

    if customer.empty:

        return {
            "customer_id": customer_id,
            "customer_name": "Unknown Customer",
            "total_sales": 0.0,
            "total_invoiced": 0.0,
            "total_paid": 0.0,
            "outstanding": 0.0,
            "invoice_count": 0,
            "payment_count": 0,
            "last_purchase": "",
            "last_payment": "",
            "payment_status": "No Activity"
        }

    customer_row = customer.iloc[0]

    customer_name = customer_row.get(
        "Customer Name",
        ""
    )

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    customer_sales = pd.DataFrame()

    if (
        not sales.empty
        and "Customer ID" in sales.columns
    ):

        customer_sales = sales[
            sales["Customer ID"]
            .astype(str)
            == str(customer_id)
        ]

    total_sales = 0.0

    if not customer_sales.empty:

        if "Total Amount" in customer_sales.columns:

            total_sales = numeric(
                customer_sales["Total Amount"]
            ).sum()

        elif "Total" in customer_sales.columns:

            total_sales = numeric(
                customer_sales["Total"]
            ).sum()

        elif "Amount" in customer_sales.columns:

            total_sales = numeric(
                customer_sales["Amount"]
            ).sum()

    # --------------------------------------------------------
    # INVOICES
    # --------------------------------------------------------

    customer_invoices = pd.DataFrame()

    if (
        not invoices.empty
        and "Customer ID" in invoices.columns
    ):

        customer_invoices = invoices[
            invoices["Customer ID"]
            .astype(str)
            == str(customer_id)
        ]

    total_invoiced = 0.0

    if not customer_invoices.empty:

        if "Total Amount" in customer_invoices.columns:

            total_invoiced = numeric(
                customer_invoices["Total Amount"]
            ).sum()

        elif "Total" in customer_invoices.columns:

            total_invoiced = numeric(
                customer_invoices["Total"]
            ).sum()

        elif "Invoice Total" in customer_invoices.columns:

            total_invoiced = numeric(
                customer_invoices["Invoice Total"]
            ).sum()

        elif "Amount" in customer_invoices.columns:

            total_invoiced = numeric(
                customer_invoices["Amount"]
            ).sum()

    # --------------------------------------------------------
    # PAYMENTS
    # --------------------------------------------------------

    customer_payments = pd.DataFrame()

    if (
        not payments.empty
        and "Customer ID" in payments.columns
    ):

        customer_payments = payments[
            (
                payments["Customer ID"]
                .astype(str)
                == str(customer_id)
            )
            &
            (
                payments.get(
                    "Status",
                    pd.Series(
                        ["Completed"]
                        * len(payments)
                    )
                )
                .astype(str)
                == "Completed"
            )
        ]

    total_paid = 0.0

    if not customer_payments.empty:

        if "Amount" in customer_payments.columns:

            total_paid = numeric(
                customer_payments["Amount"]
            ).sum()

    # --------------------------------------------------------
    # OUTSTANDING BALANCE
    # --------------------------------------------------------

    outstanding = (
        total_invoiced
        - total_paid
    )

    if abs(outstanding) < 0.01:

        outstanding = 0.0

    outstanding = max(
        outstanding,
        0.0
    )

    # --------------------------------------------------------
    # LAST PURCHASE
    # --------------------------------------------------------

    last_purchase = ""

    if not customer_sales.empty:

        date_column = None

        for column in [
            "Sale Date",
            "Date",
            "Transaction Date"
        ]:

            if column in customer_sales.columns:

                date_column = column
                break

        if date_column:

            dates = pd.to_datetime(
                customer_sales[date_column],
                errors="coerce"
            ).dropna()

            if not dates.empty:

                last_purchase = (
                    dates.max()
                    .strftime("%Y-%m-%d")
                )

    # --------------------------------------------------------
    # LAST PAYMENT
    # --------------------------------------------------------

    last_payment = ""

    if not customer_payments.empty:

        date_column = None

        for column in [
            "Payment Date",
            "Date",
            "Transaction Date"
        ]:

            if column in customer_payments.columns:

                date_column = column
                break

        if date_column:

            dates = pd.to_datetime(
                customer_payments[date_column],
                errors="coerce"
            ).dropna()

            if not dates.empty:

                last_payment = (
                    dates.max()
                    .strftime("%Y-%m-%d")
                )

    # --------------------------------------------------------
    # PAYMENT STATUS
    # --------------------------------------------------------

    if total_invoiced <= 0:

        payment_status = "No Invoice"

    elif total_paid <= 0:

        payment_status = "Outstanding"

    elif total_paid >= total_invoiced:

        payment_status = "Paid"

    else:

        payment_status = "Partially Paid"

    # --------------------------------------------------------
    # RETURN ACCOUNT
    # --------------------------------------------------------

    return {

        "customer_id":
            customer_id,

        "customer_name":
            customer_name,

        "total_sales":
            float(total_sales),

        "total_invoiced":
            float(total_invoiced),

        "total_paid":
            float(total_paid),

        "outstanding":
            float(outstanding),

        "invoice_count":
            len(customer_invoices),

        "payment_count":
            len(customer_payments),

        "last_purchase":
            last_purchase,

        "last_payment":
            last_payment,

        "payment_status":
            payment_status
    }


# ============================================================
# ALL CUSTOMER ACCOUNTS
# ============================================================

def customer_accounts(
    customers_file,
    sales_file,
    invoices_file,
    payments_file
):

    customers = load_csv(
        customers_file
    )

    if customers.empty:

        return pd.DataFrame()

    if "Customer ID" not in customers.columns:

        return pd.DataFrame()

    accounts = []

    for customer_id in customers[
        "Customer ID"
    ].dropna().unique():

        account = customer_account(
            customer_id,
            customers_file,
            sales_file,
            invoices_file,
            payments_file
        )

        accounts.append(
            account
        )

    return pd.DataFrame(
        accounts
    )


# ============================================================
# RECEIVABLES SUMMARY
# ============================================================

def receivables_summary(
    customers_file,
    sales_file,
    invoices_file,
    payments_file
):

    accounts = customer_accounts(
        customers_file,
        sales_file,
        invoices_file,
        payments_file
    )

    if accounts.empty:

        return {

            "customers": 0,

            "total_sales": 0.0,

            "total_invoiced": 0.0,

            "total_paid": 0.0,

            "total_outstanding": 0.0,

            "customers_with_balance": 0,

            "fully_paid": 0,

            "partially_paid": 0,

            "outstanding": 0
        }

    return {

        "customers":
            len(accounts),

        "total_sales":
            accounts[
                "total_sales"
            ].sum(),

        "total_invoiced":
            accounts[
                "total_invoiced"
            ].sum(),

        "total_paid":
            accounts[
                "total_paid"
            ].sum(),

        "total_outstanding":
            accounts[
                "outstanding"
            ].sum(),

        "customers_with_balance":
            int(
                (
                    accounts[
                        "outstanding"
                    ] > 0
                ).sum()
            ),

        "fully_paid":
            int(
                (
                    accounts[
                        "payment_status"
                    ]
                    == "Paid"
                ).sum()
            ),

        "partially_paid":
            int(
                (
                    accounts[
                        "payment_status"
                    ]
                    == "Partially Paid"
                ).sum()
            ),

        "outstanding":
            int(
                (
                    accounts[
                        "payment_status"
                    ]
                    == "Outstanding"
                ).sum()
            )
    }


# ============================================================
# CUSTOMER TRANSACTION HISTORY
# ============================================================

def customer_transaction_history(
    customer_id,
    sales_file,
    invoices_file,
    payments_file
):

    sales = load_csv(
        sales_file
    )

    invoices = load_csv(
        invoices_file
    )

    payments = load_csv(
        payments_file
    )

    transactions = []

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    if (
        not sales.empty
        and "Customer ID" in sales.columns
    ):

        customer_sales = sales[
            sales["Customer ID"]
            .astype(str)
            == str(customer_id)
        ]

        for _, row in customer_sales.iterrows():

            amount = 0

            for column in [
                "Total Amount",
                "Total",
                "Amount"
            ]:

                if column in row.index:

                    try:
                        amount = float(
                            row[column]
                        )

                    except:
                        amount = 0

                    break

            transactions.append(
                {
                    "Date":
                        row.get(
                            "Sale Date",
                            row.get(
                                "Date",
                                ""
                            )
                        ),

                    "Type":
                        "Sale",

                    "Reference":
                        row.get(
                            "Sale ID",
                            ""
                        ),

                    "Amount":
                        amount,

                    "Status":
                        row.get(
                            "Status",
                            "Recorded"
                        )
                }
            )

    # --------------------------------------------------------
    # INVOICES
    # --------------------------------------------------------

    if (
        not invoices.empty
        and "Customer ID" in invoices.columns
    ):

        customer_invoices = invoices[
            invoices["Customer ID"]
            .astype(str)
            == str(customer_id)
        ]

        for _, row in customer_invoices.iterrows():

            amount = 0

            for column in [
                "Total Amount",
                "Total",
                "Invoice Total",
                "Amount"
            ]:

                if column in row.index:

                    try:
                        amount = float(
                            row[column]
                        )

                    except:
                        amount = 0

                    break

            transactions.append(
                {
                    "Date":
                        row.get(
                            "Invoice Date",
                            row.get(
                                "Date",
                                ""
                            )
                        ),

                    "Type":
                        "Invoice",

                    "Reference":
                        row.get(
                            "Invoice ID",
                            row.get(
                                "Invoice Number",
                                ""
                            )
                        ),

                    "Amount":
                        amount,

                    "Status":
                        row.get(
                            "Payment Status",
                            "Outstanding"
                        )
                }
            )

    # --------------------------------------------------------
    # PAYMENTS
    # --------------------------------------------------------

    if (
        not payments.empty
        and "Customer ID" in payments.columns
    ):

        customer_payments = payments[
            payments["Customer ID"]
            .astype(str)
            == str(customer_id)
        ]

        for _, row in customer_payments.iterrows():

            if str(
                row.get(
                    "Status",
                    "Completed"
                )
            ) != "Completed":

                continue

            amount = 0

            try:

                amount = float(
                    row.get(
                        "Amount",
                        0
                    )
                )

            except:

                amount = 0

            transactions.append(
                {
                    "Date":
                        row.get(
                            "Payment Date",
                            ""
                        ),

                    "Type":
                        "Payment",

                    "Reference":
                        row.get(
                            "Payment ID",
                            ""
                        ),

                    "Amount":
                        amount,

                    "Status":
                        "Completed"
                }
            )

    history = pd.DataFrame(
        transactions
    )

    if not history.empty:

        history["Date"] = pd.to_datetime(
            history["Date"],
            errors="coerce"
        )

        history = history.sort_values(
            "Date",
            ascending=False
        )

        history["Date"] = history[
            "Date"
        ].dt.strftime(
            "%Y-%m-%d"
        )

    return history.reset_index(
        drop=True
    )