from pathlib import Path
from datetime import datetime
import pandas as pd

from .ids import generate_year_id
from .audit import record_audit


# ============================================================
# APPROVAL ENGINE
# ============================================================

APPROVAL_COLUMNS = [
    "Approval ID",
    "Request ID",
    "Request Type",
    "Requester",
    "Department",
    "Request Date",
    "Description",
    "Amount",
    "Quantity",
    "Priority",
    "Status",
    "Approver",
    "Decision Date",
    "Decision",
    "Comment",
    "Product ID",
    "Product Name"
]


REQUEST_STATUSES = [
    "Draft",
    "Submitted",
    "Pending Approval",
    "Approved",
    "Partially Approved",
    "Rejected",
    "Request Revision",
    "Completed"
]


def load_approvals(file_path):
    """
    Load approval records or create an empty approval table.
    """

    path = Path(file_path)

    if path.exists():

        try:
            df = pd.read_csv(path)

            for column in APPROVAL_COLUMNS:
                if column not in df.columns:
                    df[column] = ""

            return df[APPROVAL_COLUMNS]

        except Exception:
            pass

    return pd.DataFrame(
        columns=APPROVAL_COLUMNS
    )


# ============================================================
# CREATE REQUEST
# ============================================================

def create_request(
    approvals_file,
    audit_file,
    request_type,
    requester,
    department,
    description,
    amount=0,
    quantity=0,
    priority="Normal",
    status="Pending Approval"
):
    """
    Create a new request requiring approval.

    Examples:

    Stock Request
    Expenditure Request
    Purchase Request
    """

    approvals = load_approvals(
        approvals_file
    )

    request_prefix = "REQ"

    if request_type.lower() == "expenditure":
        request_prefix = "EXP"

    request_id = generate_year_id(
        request_prefix,
        approvals_file
    )

    approval_id = (
        f"APR-{len(approvals) + 1:06d}"
    )

    request_date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    new_request = pd.DataFrame(
        [
            {
                "Approval ID": approval_id,
                "Request ID": request_id,
                "Request Type": request_type,
                "Requester": requester,
                "Department": department,
                "Request Date": request_date,
                "Description": description,
                "Amount": float(amount),
                "Quantity": float(quantity),
                "Priority": priority,
                "Status": status,
                "Approver": "",
                "Decision Date": "",
                "Decision": "",
                "Comment": ""
            }
        ]
    )

    approvals = pd.concat(
        [
            approvals,
            new_request
        ],
        ignore_index=True
    )

    approvals.to_csv(
        approvals_file,
        index=False
    )

    # --------------------------------------------------------
    # AUDIT
    # --------------------------------------------------------

    record_audit(
        audit_file,
        requester,
        "CREATE",
        request_type,
        request_id,
        (
            f"{request_type} submitted for approval. "
            f"Description: {description}"
        )
    )

    return {
        "approval_id": approval_id,
        "request_id": request_id,
        "request_type": request_type,
        "status": status
    }


# ============================================================
# APPROVE REQUEST
# ============================================================

def approve_request(
    approvals_file,
    audit_file,
    request_id,
    approver,
    comment=""
):
    """
    Approve a pending request.
    """

    approvals = load_approvals(
        approvals_file
    )

    matches = approvals[
        approvals["Request ID"].astype(str)
        == str(request_id)
    ]

    if matches.empty:

        raise ValueError(
            f"Request {request_id} was not found."
        )

    index = matches.index[0]

    current_status = str(
        approvals.loc[index, "Status"]
    )

    if current_status not in [
        "Submitted",
        "Pending Approval",
        "Request Revision"
    ]:

        raise ValueError(
            f"Request {request_id} cannot be approved "
            f"because its current status is "
            f"'{current_status}'."
        )

    decision_date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    approvals.loc[
        index,
        "Status"
    ] = "Approved"

    approvals.loc[
        index,
        "Approver"
    ] = approver

    approvals.loc[
        index,
        "Decision Date"
    ] = decision_date

    approvals.loc[
        index,
        "Decision"
    ] = "Approved"

    approvals.loc[
        index,
        "Comment"
    ] = comment

    approvals.to_csv(
        approvals_file,
        index=False
    )

    record_audit(
        audit_file,
        approver,
        "APPROVE",
        approvals.loc[
            index,
            "Request Type"
        ],
        request_id,
        (
            f"Request approved by {approver}. "
            f"Comment: {comment}"
        )
    )

    return {
        "request_id": request_id,
        "status": "Approved",
        "approver": approver,
        "decision_date": decision_date
    }


# ============================================================
# REJECT REQUEST
# ============================================================

def reject_request(
    approvals_file,
    audit_file,
    request_id,
    approver,
    comment=""
):
    """
    Reject a pending request.
    """

    approvals = load_approvals(
        approvals_file
    )

    matches = approvals[
        approvals["Request ID"].astype(str)
        == str(request_id)
    ]

    if matches.empty:

        raise ValueError(
            f"Request {request_id} was not found."
        )

    index = matches.index[0]

    current_status = str(
        approvals.loc[index, "Status"]
    )

    if current_status not in [
        "Submitted",
        "Pending Approval",
        "Request Revision"
    ]:

        raise ValueError(
            f"Request {request_id} cannot be rejected "
            f"because its current status is "
            f"'{current_status}'."
        )

    decision_date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    approvals.loc[
        index,
        "Status"
    ] = "Rejected"

    approvals.loc[
        index,
        "Approver"
    ] = approver

    approvals.loc[
        index,
        "Decision Date"
    ] = decision_date

    approvals.loc[
        index,
        "Decision"
    ] = "Rejected"

    approvals.loc[
        index,
        "Comment"
    ] = comment

    approvals.to_csv(
        approvals_file,
        index=False
    )

    record_audit(
        audit_file,
        approver,
        "REJECT",
        approvals.loc[
            index,
            "Request Type"
        ],
        request_id,
        (
            f"Request rejected by {approver}. "
            f"Comment: {comment}"
        )
    )

    return {
        "request_id": request_id,
        "status": "Rejected",
        "approver": approver,
        "decision_date": decision_date
    }


# ============================================================
# REQUEST REVISION
# ============================================================

def request_revision(
    approvals_file,
    audit_file,
    request_id,
    approver,
    comment
):
    """
    Send a request back to the requester for revision.
    """

    if not comment.strip():

        raise ValueError(
            "A revision comment is required."
        )

    approvals = load_approvals(
        approvals_file
    )

    matches = approvals[
        approvals["Request ID"].astype(str)
        == str(request_id)
    ]

    if matches.empty:

        raise ValueError(
            f"Request {request_id} was not found."
        )

    index = matches.index[0]

    approvals.loc[
        index,
        "Status"
    ] = "Request Revision"

    approvals.loc[
        index,
        "Approver"
    ] = approver

    approvals.loc[
        index,
        "Decision Date"
    ] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    approvals.loc[
        index,
        "Decision"
    ] = "Request Revision"

    approvals.loc[
        index,
        "Comment"
    ] = comment

    approvals.to_csv(
        approvals_file,
        index=False
    )

    record_audit(
        audit_file,
        approver,
        "REVISION",
        approvals.loc[
            index,
            "Request Type"
        ],
        request_id,
        (
            f"Revision requested. "
            f"Comment: {comment}"
        )
    )

    return {
        "request_id": request_id,
        "status": "Request Revision",
        "approver": approver
    }


# ============================================================
# COMPLETE REQUEST
# ============================================================

def complete_request(
    approvals_file,
    audit_file,
    request_id,
    completed_by,
    comment=""
):
    """
    Mark an approved request as completed.
    """

    approvals = load_approvals(
        approvals_file
    )

    matches = approvals[
        approvals["Request ID"].astype(str)
        == str(request_id)
    ]

    if matches.empty:

        raise ValueError(
            f"Request {request_id} was not found."
        )

    index = matches.index[0]

    current_status = str(
        approvals.loc[index, "Status"]
    )

    if current_status != "Approved":

        raise ValueError(
            "Only approved requests can be completed."
        )

    approvals.loc[
        index,
        "Status"
    ] = "Completed"

    if comment:

        approvals.loc[
            index,
            "Comment"
        ] = comment

    approvals.to_csv(
        approvals_file,
        index=False
    )

    record_audit(
        audit_file,
        completed_by,
        "COMPLETE",
        approvals.loc[
            index,
            "Request Type"
        ],
        request_id,
        (
            f"Approved request completed."
            f" {comment}"
        )
    )

    return {
        "request_id": request_id,
        "status": "Completed"
    }


# ============================================================
# PENDING REQUESTS
# ============================================================

def get_pending_requests(
    approvals_file
):
    """
    Return requests currently waiting for approval.
    """

    approvals = load_approvals(
        approvals_file
    )

    if approvals.empty:
        return approvals

    return approvals[
        approvals["Status"].isin(
            [
                "Submitted",
                "Pending Approval",
                "Request Revision"
            ]
        )
    ].copy()


# ============================================================
# APPROVAL SUMMARY
# ============================================================

def get_approval_summary(
    approvals_file
):
    """
    Return counts by approval status.
    """

    approvals = load_approvals(
        approvals_file
    )

    if approvals.empty:

        return {
            "Total": 0,
            "Pending": 0,
            "Approved": 0,
            "Rejected": 0,
            "Revision": 0,
            "Completed": 0
        }

    status = (
        approvals["Status"]
        .astype(str)
    )

    return {
        "Total": len(approvals),

        "Pending": int(
            status.isin(
                [
                    "Submitted",
                    "Pending Approval"
                ]
            ).sum()
        ),

        "Approved": int(
            (status == "Approved").sum()
        ),

        "Rejected": int(
            (status == "Rejected").sum()
        ),

        "Revision": int(
            (status == "Request Revision").sum()
        ),

        "Completed": int(
            (status == "Completed").sum()
        )
    }