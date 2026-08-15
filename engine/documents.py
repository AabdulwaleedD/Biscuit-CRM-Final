from pathlib import Path
from datetime import datetime
import pandas as pd

from .audit import record_audit


# ============================================================
# DOCUMENT & RECORDS ARCHIVE ENGINE
# ============================================================

DOCUMENT_COLUMNS = [
    "Document ID",
    "Document Type",
    "Document Number",
    "Source Type",
    "Customer ID",
    "Customer Name",
    "Related Transaction",
    "Transaction Type",
    "Document Date",
    "Amount",
    "Uploaded By",
    "Upload Date",
    "File Name",
    "File Path",
    "Description",
    "Status"
]

ARCHIVE_COLUMNS = [
    "Record ID",
    "Record Type",
    "Record Number",
    "Source Type",
    "Record Date",
    "Customer ID",
    "Customer Name",
    "Related Transaction",
    "Description",
    "Imported By",
    "Import Date",
    "Status",
    "Notes"
]


# ============================================================
# GENERIC LOADER
# ============================================================

def load_table(file_path, columns):

    path = Path(file_path)

    if path.exists():

        try:

            df = pd.read_csv(file_path)

            for column in columns:

                if column not in df.columns:
                    df[column] = ""

            return df[columns]

        except Exception:
            pass

    return pd.DataFrame(columns=columns)


# ============================================================
# DOCUMENT ID
# ============================================================

def generate_document_id(documents):

    return (
        f"DOC-{datetime.now().year}-"
        f"{len(documents) + 1:06d}"
    )


# ============================================================
# RECORD ID
# ============================================================

def generate_record_id(records):

    return (
        f"REC-{datetime.now().year}-"
        f"{len(records) + 1:06d}"
    )


# ============================================================
# UPLOAD / REGISTER DOCUMENT
# ============================================================

def register_document(
    documents_file,
    audit_file,
    document_type,
    document_number,
    source_type,
    customer_id="",
    customer_name="",
    related_transaction="",
    transaction_type="",
    document_date="",
    amount=0,
    uploaded_by="Demo Administrator",
    file_name="",
    file_path="",
    description="",
    status="Active"
):

    documents = load_table(
        documents_file,
        DOCUMENT_COLUMNS
    )

    valid_sources = [
        "Created in CRM",
        "Imported",
        "Scanned Document",
        "Legacy / Historical"
    ]

    if source_type not in valid_sources:

        raise ValueError(
            "Invalid document source type."
        )

    document_id = generate_document_id(
        documents
    )

    # --------------------------------------------------------
    # DUPLICATE DOCUMENT CHECK
    # --------------------------------------------------------

    if document_number:

        duplicate = documents[
            documents["Document Number"]
            .astype(str)
            == str(document_number)
        ]

        if not duplicate.empty:

            raise ValueError(
                f"Document {document_number} "
                "already exists."
            )

    # --------------------------------------------------------
    # CREATE RECORD
    # --------------------------------------------------------

    new_document = pd.DataFrame(
        [
            {
                "Document ID": document_id,
                "Document Type": document_type,
                "Document Number": document_number,
                "Source Type": source_type,
                "Customer ID": customer_id,
                "Customer Name": customer_name,
                "Related Transaction":
                    related_transaction,
                "Transaction Type":
                    transaction_type,
                "Document Date": document_date,
                "Amount": float(amount),
                "Uploaded By": uploaded_by,
                "Upload Date":
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                "File Name": file_name,
                "File Path": file_path,
                "Description": description,
                "Status": status
            }
        ]
    )

    documents = pd.concat(
        [
            documents,
            new_document
        ],
        ignore_index=True
    )

    documents.to_csv(
        documents_file,
        index=False
    )

    record_audit(
        audit_file,
        uploaded_by,
        "UPLOAD DOCUMENT",
        "Document",
        document_id,
        (
            f"{document_type} registered. "
            f"Source: {source_type}. "
            f"Reference: {document_number}"
        )
    )

    return {
        "document_id": document_id,
        "document_number": document_number,
        "source_type": source_type,
        "status": status
    }


# ============================================================
# ARCHIVE HISTORICAL RECORD
# ============================================================

def archive_record(
    archive_file,
    audit_file,
    record_type,
    record_number,
    source_type,
    record_date="",
    customer_id="",
    customer_name="",
    related_transaction="",
    description="",
    imported_by="Demo Administrator",
    status="Archived",
    notes=""
):

    records = load_table(
        archive_file,
        ARCHIVE_COLUMNS
    )

    valid_sources = [
        "Legacy / Historical",
        "Imported",
        "Scanned Document",
        "CRM Operational Archive"
    ]

    if source_type not in valid_sources:

        raise ValueError(
            "Archive records must come from "
            "a historical, imported or scanned source."
        )

    record_id = generate_record_id(
        records
    )

    # --------------------------------------------------------
    # DUPLICATE CHECK
    # --------------------------------------------------------

    if record_number:

        duplicate = records[
            records["Record Number"]
            .astype(str)
            == str(record_number)
        ]

        if not duplicate.empty:

            raise ValueError(
                f"Record {record_number} "
                "already exists in the archive."
            )

    new_record = pd.DataFrame(
        [
            {
                "Record ID": record_id,
                "Record Type": record_type,
                "Record Number": record_number,
                "Source Type": source_type,
                "Record Date": record_date,
                "Customer ID": customer_id,
                "Customer Name": customer_name,
                "Related Transaction":
                    related_transaction,
                "Description": description,
                "Imported By": imported_by,
                "Import Date":
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                "Status": status,
                "Notes": notes
            }
        ]
    )

    records = pd.concat(
        [
            records,
            new_record
        ],
        ignore_index=True
    )

    records.to_csv(
        archive_file,
        index=False
    )

    record_audit(
        audit_file,
        imported_by,
        "ARCHIVE RECORD",
        "Record Archive",
        record_id,
        (
            f"{record_type} {record_number} "
            f"archived as {source_type}."
        )
    )

    return {
        "record_id": record_id,
        "record_number": record_number,
        "status": status
    }


# ============================================================
# AUTOMATIC OPERATIONAL ARCHIVE
# ============================================================

def auto_archive_completed_records(
    archive_file,
    audit_file,
    sales_file=None,
    invoices_file=None,
    deliveries_file=None,
    expenditures_file=None,
    archived_by="Demo Administrator"
):
    """
    Automatically creates archive entries for completed/closed
    operational records while leaving the original records in
    their current operational tables.

    This keeps Records Archive useful for historical traceability
    without moving or deleting live transactions. Duplicate checks
    make the sync safe to run repeatedly on every Streamlit rerun.
    """
    records = load_table(archive_file, ARCHIVE_COLUMNS)
    existing_numbers = set(records["Record Number"].astype(str).str.strip())
    created = 0

    def add_from_table(file_path, record_type, number_col, date_col,
                       customer_id_col=None, customer_name_col=None,
                       related_col=None, description_builder=None,
                       status_values=None, source_notes=""):
        nonlocal records, existing_numbers, created
        if not file_path or not Path(file_path).exists():
            return
        try:
            df = pd.read_csv(file_path)
        except Exception:
            return
        if df.empty or number_col not in df.columns:
            return
        for _, row in df.iterrows():
            number = str(row.get(number_col, "")).strip()
            if not number or number in existing_numbers:
                continue
            current_status = str(row.get(status_values[0], "")).strip() if status_values else "Completed"
            if status_values and current_status not in status_values[1]:
                continue
            customer_id = str(row.get(customer_id_col, "")).strip() if customer_id_col else ""
            customer_name = str(row.get(customer_name_col, "")).strip() if customer_name_col else ""
            related = str(row.get(related_col, "")).strip() if related_col else ""
            description = description_builder(row) if description_builder else f"Automatically archived completed {record_type.lower()} {number}."
            new = {
                "Record ID": generate_record_id(records),
                "Record Type": record_type,
                "Record Number": number,
                "Source Type": "CRM Operational Archive",
                "Record Date": str(row.get(date_col, "")).strip() if date_col else "",
                "Customer ID": customer_id,
                "Customer Name": customer_name,
                "Related Transaction": related,
                "Description": description,
                "Imported By": archived_by,
                "Import Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Status": "Archived",
                "Notes": source_notes
            }
            records = pd.concat([records, pd.DataFrame([new])], ignore_index=True)
            existing_numbers.add(number)
            created += 1

    add_from_table(
        sales_file, "Completed Sale", "Sale ID", "Date",
        "Customer ID", "Customer Name", None,
        lambda r: f"Sale completed for {r.get('Customer Name', '')}. Total: {r.get('Total Amount', 0)}.",
        ("Status", {"Completed"}),
        "System-created archive entry; original sale remains in Sales."
    )
    add_from_table(
        invoices_file, "Issued Invoice", "Invoice Number", "Invoice Date",
        "Customer ID", "Customer Name", "Sale ID",
        lambda r: f"Invoice issued to {r.get('Customer Name', '')}. Total: {r.get('Total Amount', 0)}.",
        ("Invoice Status", {"Issued", "Paid", "Closed", "Completed"}),
        "System-created archive entry; original invoice remains in Invoices."
    )
    add_from_table(
        deliveries_file, "Completed Delivery", "Delivery ID", "Delivery Date",
        "Customer ID", "Customer Name", "Sale ID",
        lambda r: f"Delivery completed for {r.get('Customer Name', '')} via truck {r.get('Registration Number', '')}.",
        ("Status", {"Delivered", "Completed"}),
        "System-created archive entry; original delivery remains in Logistics."
    )
    add_from_table(
        expenditures_file, "Paid Expenditure", "Expenditure ID", "Date",
        None, None, "Request ID",
        lambda r: f"Expenditure paid for {r.get('Department', '')}: {r.get('Description', '')}.",
        ("Payment Status", {"Paid"}),
        "System-created archive entry; original expenditure remains in Expenditures."
    )

    if created:
        records.to_csv(archive_file, index=False)
        record_audit(
            audit_file, archived_by, "AUTO ARCHIVE", "Record Archive",
            f"AUTO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            f"Automatically archived {created} completed operational record(s)."
        )
    return {"created": created, "total": len(records)}


# ============================================================
# LINK DOCUMENT TO TRANSACTION
# ============================================================

def link_document(
    documents_file,
    audit_file,
    document_id,
    transaction_id,
    transaction_type,
    linked_by="Demo Administrator"
):

    documents = load_table(
        documents_file,
        DOCUMENT_COLUMNS
    )

    matches = documents[
        documents["Document ID"].astype(str)
        == str(document_id)
    ]

    if matches.empty:

        raise ValueError(
            f"Document {document_id} was not found."
        )

    index = matches.index[0]

    documents.loc[
        index,
        "Related Transaction"
    ] = transaction_id

    documents.loc[
        index,
        "Transaction Type"
    ] = transaction_type

    documents.to_csv(
        documents_file,
        index=False
    )

    record_audit(
        audit_file,
        linked_by,
        "LINK DOCUMENT",
        "Document",
        document_id,
        (
            f"Document linked to "
            f"{transaction_type} {transaction_id}."
        )
    )

    return {
        "document_id": document_id,
        "transaction_id": transaction_id,
        "transaction_type": transaction_type
    }


# ============================================================
# DOCUMENT SEARCH
# ============================================================

def search_documents(
    documents_file,
    search_term=""
):

    documents = load_table(
        documents_file,
        DOCUMENT_COLUMNS
    )

    if documents.empty:
        return documents

    if not search_term:
        return documents

    term = str(
        search_term
    ).lower()

    mask = documents.apply(
        lambda row:
            term in str(
                row.to_dict()
            ).lower(),
        axis=1
    )

    return documents[mask]


# ============================================================
# ARCHIVE SEARCH
# ============================================================

def search_archive(
    archive_file,
    search_term=""
):

    records = load_table(
        archive_file,
        ARCHIVE_COLUMNS
    )

    if records.empty:
        return records

    if not search_term:
        return records

    term = str(
        search_term
    ).lower()

    mask = records.apply(
        lambda row:
            term in str(
                row.to_dict()
            ).lower(),
        axis=1
    )

    return records[mask]


# ============================================================
# DOCUMENT SUMMARY
# ============================================================

def document_summary(
    documents_file
):

    documents = load_table(
        documents_file,
        DOCUMENT_COLUMNS
    )

    if documents.empty:

        return {
            "total": 0,
            "invoices": 0,
            "receipts": 0,
            "scanned": 0,
            "historical": 0,
            "imported": 0
        }

    source = (
        documents["Source Type"]
        .astype(str)
    )

    doc_type = (
        documents["Document Type"]
        .astype(str)
        .str.lower()
    )

    return {
        "total": len(documents),

        "invoices": int(
            doc_type.str.contains(
                "invoice"
            ).sum()
        ),

        "receipts": int(
            doc_type.str.contains(
                "receipt"
            ).sum()
        ),

        "scanned": int(
            (source == "Scanned Document").sum()
        ),

        "historical": int(
            (source == "Legacy / Historical").sum()
        ),

        "imported": int(
            (source == "Imported").sum()
        )
    }


# ============================================================
# ARCHIVE SUMMARY
# ============================================================

def archive_summary(
    archive_file
):

    records = load_table(
        archive_file,
        ARCHIVE_COLUMNS
    )

    if records.empty:

        return {
            "total": 0,
            "historical": 0,
            "imported": 0,
            "scanned": 0
        }

    source = (
        records["Source Type"]
        .astype(str)
    )

    return {
        "total": len(records),

        "historical": int(
            (source == "Legacy / Historical").sum()
        ),

        "imported": int(
            (source == "Imported").sum()
        ),

        "scanned": int(
            (source == "Scanned Document").sum()
        )
    }