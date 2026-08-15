from pathlib import Path
from datetime import datetime
import pandas as pd

from .approvals import create_request
from .audit import record_audit


# ============================================================
# EXPENDITURE ENGINE
# ============================================================

EXPENDITURE_COLUMNS = [
    "Expenditure ID",
    "Request ID",
    "Date",
    "Department",
    "Requester",
    "Expense Category",
    "Description",
    "Amount Requested",
    "Amount Approved",
    "Amount Paid",
    "Payment Status",
    "Approval Status",
    "Approver",
    "Approval Date",
    "Payment Date",
    "Payment Method",
    "Payment Reference",
    "Supporting Document",
    "Notes"
]


def load_expenditures(file_path):

    path = Path(file_path)

    if path.exists():

        try:

            df = pd.read_csv(file_path)

            for column in EXPENDITURE_COLUMNS:

                if column not in df.columns:
                    df[column] = ""

            return df[EXPENDITURE_COLUMNS]

        except Exception:
            pass

    return pd.DataFrame(
        columns=EXPENDITURE_COLUMNS
    )


# ============================================================
# CREATE EXPENDITURE REQUEST
# ============================================================

def create_expenditure_request(
    approvals_file,
    expenditures_file,
    audit_file,
    requester,
    department,
    expense_category,
    description,
    amount,
    priority="Normal",
    supporting_document="",
    notes=""
):
    """
    Creates an expenditure request and sends it
    into the central approval workflow.
    """

    amount = float(amount)

    if amount <= 0:

        raise ValueError(
            "Expenditure amount must be greater than zero."
        )

    # --------------------------------------------------------
    # CREATE APPROVAL REQUEST
    # --------------------------------------------------------

    approval = create_request(
        approvals_file=approvals_file,
        audit_file=audit_file,
        request_type="Expenditure",
        requester=requester,
        department=department,
        description=description,
        amount=amount,
        quantity=0,
        priority=priority,
        status="Pending Approval"
    )

    request_id = approval[
        "request_id"
    ]

    # --------------------------------------------------------
    # LOAD EXPENDITURES
    # --------------------------------------------------------

    expenditures = load_expenditures(
        expenditures_file
    )

    # --------------------------------------------------------
    # GENERATE EXPENDITURE ID
    # --------------------------------------------------------

    expenditure_id = (
        f"EXP-{datetime.now().year}-"
        f"{len(expenditures) + 1:06d}"
    )

    # --------------------------------------------------------
    # CREATE EXPENDITURE RECORD
    # --------------------------------------------------------

    new_record = pd.DataFrame(
        [
            {
                "Expenditure ID": expenditure_id,
                "Request ID": request_id,
                "Date": datetime.now().strftime(
                    "%Y-%m-%d"
                ),
                "Department": department,
                "Requester": requester,
                "Expense Category": expense_category,
                "Description": description,
                "Amount Requested": amount,
                "Amount Approved": 0,
                "Amount Paid": 0,
                "Payment Status": "Unpaid",
                "Approval Status": "Pending Approval",
                "Approver": "",
                "Approval Date": "",
                "Payment Date": "",
                "Payment Method": "",
                "Payment Reference": "",
                "Supporting Document": supporting_document,
                "Notes": notes
            }
        ]
    )

    expenditures = pd.concat(
        [
            expenditures,
            new_record
        ],
        ignore_index=True
    )

    expenditures.to_csv(
        expenditures_file,
        index=False
    )

    record_audit(
        audit_file,
        requester,
        "CREATE",
        "Expenditure",
        expenditure_id,
        (
            f"Expenditure request created for "
            f"₦{amount:,.2f}. "
            f"Approval request: {request_id}"
        )
    )

    return {
        "expenditure_id": expenditure_id,
        "request_id": request_id,
        "amount_requested": amount,
        "status": "Pending Approval"
    }


# ============================================================
# APPROVE EXPENDITURE
# ============================================================

def approve_expenditure(
    approvals_file,
    expenditures_file,
    audit_file,
    request_id,
    approver,
    approved_amount=None,
    comment=""
):
    """
    Approves an expenditure request.

    Supports full or partial approval.
    """

    from .approvals import approve_request

    expenditures = load_expenditures(
        expenditures_file
    )

    matches = expenditures[
        expenditures["Request ID"].astype(str)
        == str(request_id)
    ]

    if matches.empty:

        raise ValueError(
            f"No expenditure exists for "
            f"request {request_id}."
        )

    index = matches.index[0]

    requested_amount = float(
        pd.to_numeric(
            expenditures.loc[
                index,
                "Amount Requested"
            ],
            errors="coerce"
        ) or 0
    )

    if approved_amount is None:

        approved_amount = requested_amount

    approved_amount = float(
        approved_amount
    )

    if approved_amount <= 0:

        raise ValueError(
            "Approved amount must be greater than zero."
        )

    if approved_amount > requested_amount:

        raise ValueError(
            "Approved amount cannot exceed "
            "the requested amount."
        )

    # --------------------------------------------------------
    # APPROVE CENTRAL REQUEST
    # --------------------------------------------------------

    result = approve_request(
        approvals_file=approvals_file,
        audit_file=audit_file,
        request_id=request_id,
        approver=approver,
        comment=comment
    )

    # --------------------------------------------------------
    # DETERMINE APPROVAL TYPE
    # --------------------------------------------------------

    if approved_amount < requested_amount:

        approval_status = "Partially Approved"

    else:

        approval_status = "Approved"

    # --------------------------------------------------------
    # UPDATE EXPENDITURE
    # --------------------------------------------------------

    expenditures.loc[
        index,
        "Amount Approved"
    ] = approved_amount

    expenditures.loc[
        index,
        "Approval Status"
    ] = approval_status

    expenditures.loc[
        index,
        "Approver"
    ] = approver

    expenditures.loc[
        index,
        "Approval Date"
    ] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    expenditures.to_csv(
        expenditures_file,
        index=False
    )

    record_audit(
        audit_file,
        approver,
        "APPROVE EXPENDITURE",
        "Expenditure",
        request_id,
        (
            f"Expenditure approved for "
            f"₦{approved_amount:,.2f} "
            f"out of ₦{requested_amount:,.2f} requested."
        )
    )

    return {
        "request_id": request_id,
        "amount_requested": requested_amount,
        "amount_approved": approved_amount,
        "status": approval_status
    }


# ============================================================
# REJECT EXPENDITURE
# ============================================================

def reject_expenditure(
    approvals_file,
    expenditures_file,
    audit_file,
    request_id,
    approver,
    comment
):
    """
    Reject an expenditure request.
    """

    from .approvals import reject_request

    expenditures = load_expenditures(
        expenditures_file
    )

    matches = expenditures[
        expenditures["Request ID"].astype(str)
        == str(request_id)
    ]

    if matches.empty:

        raise ValueError(
            f"No expenditure exists for "
            f"request {request_id}."
        )

    result = reject_request(
        approvals_file=approvals_file,
        audit_file=audit_file,
        request_id=request_id,
        approver=approver,
        comment=comment
    )

    index = matches.index[0]

    expenditures.loc[
        index,
        "Approval Status"
    ] = "Rejected"

    expenditures.loc[
        index,
        "Approver"
    ] = approver

    expenditures.loc[
        index,
        "Approval Date"
    ] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    expenditures.to_csv(
        expenditures_file,
        index=False
    )

    return result


# ============================================================
# PAY EXPENDITURE
# ============================================================

def pay_expenditure(
    expenditures_file,
    audit_file,
    expenditure_id,
    payment_method,
    payment_reference,
    paid_by,
    amount=None,
    notes=""
):
    """
    Record payment for an approved expenditure.
    """

    expenditures = load_expenditures(
        expenditures_file
    )

    matches = expenditures[
        expenditures["Expenditure ID"].astype(str)
        == str(expenditure_id)
    ]

    if matches.empty:

        raise ValueError(
            f"Expenditure {expenditure_id} "
            "was not found."
        )

    index = matches.index[0]

    approval_status = str(
        expenditures.loc[
            index,
            "Approval Status"
        ]
    )

    if approval_status not in [
        "Approved",
        "Partially Approved"
    ]:

        raise ValueError(
            "Only approved expenditures can be paid."
        )

    approved_amount = float(
        pd.to_numeric(
            expenditures.loc[
                index,
                "Amount Approved"
            ],
            errors="coerce"
        ) or 0
    )

    existing_paid = float(
        pd.to_numeric(
            expenditures.loc[
                index,
                "Amount Paid"
            ],
            errors="coerce"
        ) or 0
    )

    remaining = (
        approved_amount
        - existing_paid
    )

    if amount is None:
        amount = remaining

    amount = float(amount)

    if amount <= 0:

        raise ValueError(
            "Payment amount must be greater than zero."
        )

    if amount > remaining:

        raise ValueError(
            f"Payment exceeds remaining approved "
            f"balance of ₦{remaining:,.2f}."
        )

    new_paid = (
        existing_paid
        + amount
    )

    new_balance = (
        approved_amount
        - new_paid
    )

    if new_balance <= 0:

        payment_status = "Paid"

    else:

        payment_status = "Partially Paid"

    # --------------------------------------------------------
    # UPDATE RECORD
    # --------------------------------------------------------

    expenditures.loc[
        index,
        "Amount Paid"
    ] = new_paid

    expenditures.loc[
        index,
        "Payment Status"
    ] = payment_status

    expenditures.loc[
        index,
        "Payment Date"
    ] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    expenditures.loc[
        index,
        "Payment Method"
    ] = payment_method

    expenditures.loc[
        index,
        "Payment Reference"
    ] = payment_reference

    if notes:

        expenditures.loc[
            index,
            "Notes"
        ] = notes

    expenditures.to_csv(
        expenditures_file,
        index=False
    )

    # --------------------------------------------------------
    # AUDIT
    # --------------------------------------------------------

    record_audit(
        audit_file,
        paid_by,
        "PAY EXPENDITURE",
        "Expenditure",
        expenditure_id,
        (
            f"Payment of ₦{amount:,.2f} recorded. "
            f"Remaining balance: "
            f"₦{new_balance:,.2f}"
        )
    )

    return {
        "expenditure_id": expenditure_id,
        "amount_paid": amount,
        "total_paid": new_paid,
        "remaining_balance": new_balance,
        "payment_status": payment_status
    }


# ============================================================
# EXPENDITURE SUMMARY
# ============================================================

def expenditure_summary(
    expenditures_file
):
    """
    Return management-level expenditure statistics.
    """

    df = load_expenditures(
        expenditures_file
    )

    if df.empty:

        return {
            "total_requested": 0,
            "total_approved": 0,
            "total_paid": 0,
            "outstanding": 0,
            "pending": 0
        }

    requested = pd.to_numeric(
        df["Amount Requested"],
        errors="coerce"
    ).fillna(0).sum()

    approved = pd.to_numeric(
        df["Amount Approved"],
        errors="coerce"
    ).fillna(0).sum()

    paid = pd.to_numeric(
        df["Amount Paid"],
        errors="coerce"
    ).fillna(0).sum()

    pending = int(
        (
            df["Approval Status"]
            == "Pending Approval"
        ).sum()
    )

    return {
        "total_requested": requested,
        "total_approved": approved,
        "total_paid": paid,
        "outstanding": approved - paid,
        "pending": pending
    }