from pathlib import Path
from datetime import datetime
import pandas as pd

from .audit import record_audit


# ============================================================
# DISTRIBUTION ENGINE
# ============================================================

TRUCK_COLUMNS = [
    "Truck ID",
    "Registration Number",
    "Driver ID",
    "Driver Name",
    "Driver Phone",
    "Capacity",
    "Assigned Route",
    "Status"
]

DELIVERY_COLUMNS = [
    "Delivery ID",
    "Delivery Date",
    "Truck ID",
    "Registration Number",
    "Driver ID",
    "Driver Name",
    "Customer ID",
    "Customer Name",
    "Sale ID",
    "Invoice ID",
    "Delivery Address",
    "Route",
    "Status",
    "Dispatch Time",
    "Delivery Time",
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


# ============================================================
# TRUCK MANAGEMENT
# ============================================================

def add_truck(
    trucks_file,
    audit_file,
    registration_number,
    driver_id,
    driver_name,
    driver_phone,
    capacity,
    assigned_route,
    status="Available",
    created_by="Demo Administrator"
):

    trucks = load_table(
        trucks_file,
        TRUCK_COLUMNS
    )

    registration_number = str(
        registration_number
    ).strip().upper()

    if not registration_number:

        raise ValueError(
            "Truck registration number is required."
        )

    existing = trucks[
        trucks["Registration Number"]
        .astype(str)
        .str.upper()
        == registration_number
    ]

    if not existing.empty:

        raise ValueError(
            f"Truck {registration_number} already exists."
        )

    truck_id = (
        f"TRK-{len(trucks) + 1:06d}"
    )

    new_truck = pd.DataFrame(
        [
            {
                "Truck ID": truck_id,
                "Registration Number":
                    registration_number,
                "Driver ID": driver_id,
                "Driver Name": driver_name,
                "Driver Phone": driver_phone,
                "Capacity": capacity,
                "Assigned Route": assigned_route,
                "Status": status
            }
        ]
    )

    trucks = pd.concat(
        [
            trucks,
            new_truck
        ],
        ignore_index=True
    )

    trucks.to_csv(
        trucks_file,
        index=False
    )

    record_audit(
        audit_file,
        created_by,
        "CREATE",
        "Truck",
        truck_id,
        (
            f"Truck {registration_number} added. "
            f"Driver: {driver_name}"
        )
    )

    return {
        "truck_id": truck_id,
        "registration_number":
            registration_number,
        "status": status
    }


# ============================================================
# ASSIGN DRIVER
# ============================================================

def assign_driver(
    trucks_file,
    audit_file,
    truck_id,
    driver_id,
    driver_name,
    driver_phone,
    assigned_route,
    assigned_by="Demo Administrator"
):

    trucks = load_table(
        trucks_file,
        TRUCK_COLUMNS
    )

    matches = trucks[
        trucks["Truck ID"].astype(str)
        == str(truck_id)
    ]

    if matches.empty:

        raise ValueError(
            f"Truck {truck_id} was not found."
        )

    index = matches.index[0]

    trucks.loc[
        index,
        "Driver ID"
    ] = driver_id

    trucks.loc[
        index,
        "Driver Name"
    ] = driver_name

    trucks.loc[
        index,
        "Driver Phone"
    ] = driver_phone

    trucks.loc[
        index,
        "Assigned Route"
    ] = assigned_route

    trucks.loc[
        index,
        "Status"
    ] = "Assigned"

    trucks.to_csv(
        trucks_file,
        index=False
    )

    record_audit(
        audit_file,
        assigned_by,
        "ASSIGN DRIVER",
        "Truck",
        truck_id,
        (
            f"Driver {driver_name} assigned to "
            f"{truck_id} on route {assigned_route}."
        )
    )

    return {
        "truck_id": truck_id,
        "driver_id": driver_id,
        "driver_name": driver_name,
        "route": assigned_route,
        "status": "Assigned"
    }


# ============================================================
# CREATE DELIVERY
# ============================================================

def create_delivery(
    trucks_file,
    deliveries_file,
    audit_file,
    truck_id,
    customer_id,
    customer_name,
    sale_id,
    invoice_id,
    delivery_address,
    route,
    created_by="Demo Administrator",
    notes=""
):

    trucks = load_table(
        trucks_file,
        TRUCK_COLUMNS
    )

    deliveries = load_table(
        deliveries_file,
        DELIVERY_COLUMNS
    )

    # --------------------------------------------------------
    # FIND TRUCK
    # --------------------------------------------------------

    truck_rows = trucks[
        trucks["Truck ID"].astype(str)
        == str(truck_id)
    ]

    if truck_rows.empty:

        raise ValueError(
            f"Truck {truck_id} was not found."
        )

    truck = truck_rows.iloc[0]

    truck_status = str(
        truck["Status"]
    )

    if truck_status in [
        "Maintenance",
        "Inactive"
    ]:

        raise ValueError(
            f"Truck {truck_id} is currently "
            f"{truck_status.lower()}."
        )

    # --------------------------------------------------------
    # PREVENT DUPLICATE DELIVERY
    # --------------------------------------------------------

    existing = deliveries[
        (
            deliveries["Sale ID"].astype(str)
            == str(sale_id)
        )
        &
        (
            deliveries["Status"].astype(str)
            != "Cancelled"
        )
    ]

    if not existing.empty:

        raise ValueError(
            f"Sale {sale_id} already has a delivery."
        )

    # --------------------------------------------------------
    # GENERATE DELIVERY ID
    # --------------------------------------------------------

    delivery_id = (
        f"DEL-{datetime.now().year}-"
        f"{len(deliveries) + 1:06d}"
    )

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # --------------------------------------------------------
    # CREATE DELIVERY
    # --------------------------------------------------------

    new_delivery = pd.DataFrame(
        [
            {
                "Delivery ID": delivery_id,
                "Delivery Date":
                    datetime.now().strftime(
                        "%Y-%m-%d"
                    ),
                "Truck ID": truck_id,
                "Registration Number":
                    truck["Registration Number"],
                "Driver ID":
                    truck["Driver ID"],
                "Driver Name":
                    truck["Driver Name"],
                "Customer ID": customer_id,
                "Customer Name": customer_name,
                "Sale ID": sale_id,
                "Invoice ID": invoice_id,
                "Delivery Address":
                    delivery_address,
                "Route": route,
                "Status": "Dispatched",
                "Dispatch Time": now,
                "Delivery Time": "",
                "Notes": notes
            }
        ]
    )

    deliveries = pd.concat(
        [
            deliveries,
            new_delivery
        ],
        ignore_index=True
    )

    deliveries.to_csv(
        deliveries_file,
        index=False
    )

    # --------------------------------------------------------
    # UPDATE TRUCK
    # --------------------------------------------------------

    truck_index = truck_rows.index[0]

    trucks.loc[
        truck_index,
        "Status"
    ] = "On Delivery"

    trucks.to_csv(
        trucks_file,
        index=False
    )

    # --------------------------------------------------------
    # AUDIT
    # --------------------------------------------------------

    record_audit(
        audit_file,
        created_by,
        "CREATE DELIVERY",
        "Delivery",
        delivery_id,
        (
            f"Delivery dispatched from truck "
            f"{truck_id} to {customer_name}. "
            f"Sale: {sale_id}, "
            f"Invoice: {invoice_id}"
        )
    )

    return {
        "delivery_id": delivery_id,
        "truck_id": truck_id,
        "customer_id": customer_id,
        "sale_id": sale_id,
        "invoice_id": invoice_id,
        "status": "Dispatched"
    }


# ============================================================
# UPDATE DELIVERY STATUS
# ============================================================

def update_delivery_status(
    trucks_file,
    deliveries_file,
    audit_file,
    delivery_id,
    new_status,
    updated_by,
    notes=""
):

    deliveries = load_table(
        deliveries_file,
        DELIVERY_COLUMNS
    )

    trucks = load_table(
        trucks_file,
        TRUCK_COLUMNS
    )

    valid_statuses = [
        "Dispatched",
        "In Transit",
        "Delivered",
        "Failed",
        "Cancelled"
    ]

    if new_status not in valid_statuses:

        raise ValueError(
            f"Invalid delivery status: {new_status}"
        )

    matches = deliveries[
        deliveries["Delivery ID"].astype(str)
        == str(delivery_id)
    ]

    if matches.empty:

        raise ValueError(
            f"Delivery {delivery_id} was not found."
        )

    index = matches.index[0]

    truck_id = deliveries.loc[
        index,
        "Truck ID"
    ]

    deliveries.loc[
        index,
        "Status"
    ] = new_status

    if notes:

        deliveries.loc[
            index,
            "Notes"
        ] = notes

    if new_status == "Delivered":

        deliveries.loc[
            index,
            "Delivery Time"
        ] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        truck_matches = trucks[
            trucks["Truck ID"].astype(str)
            == str(truck_id)
        ]

        if not truck_matches.empty:

            truck_index = truck_matches.index[0]

            trucks.loc[
                truck_index,
                "Status"
            ] = "Available"

            trucks.to_csv(
                trucks_file,
                index=False
            )

    elif new_status in [
        "Cancelled",
        "Failed"
    ]:

        truck_matches = trucks[
            trucks["Truck ID"].astype(str)
            == str(truck_id)
        ]

        if not truck_matches.empty:

            truck_index = truck_matches.index[0]

            trucks.loc[
                truck_index,
                "Status"
            ] = "Available"

            trucks.to_csv(
                trucks_file,
                index=False
            )

    deliveries.to_csv(
        deliveries_file,
        index=False
    )

    record_audit(
        audit_file,
        updated_by,
        "UPDATE DELIVERY",
        "Delivery",
        delivery_id,
        (
            f"Delivery status changed to "
            f"{new_status}."
        )
    )

    return {
        "delivery_id": delivery_id,
        "status": new_status,
        "truck_id": truck_id
    }


# ============================================================
# DELIVERY SUMMARY
# ============================================================

def delivery_summary(
    deliveries_file
):

    deliveries = load_table(
        deliveries_file,
        DELIVERY_COLUMNS
    )

    if deliveries.empty:

        return {
            "total": 0,
            "dispatched": 0,
            "in_transit": 0,
            "delivered": 0,
            "failed": 0,
            "cancelled": 0
        }

    status = (
        deliveries["Status"]
        .astype(str)
    )

    return {
        "total": len(deliveries),

        "dispatched": int(
            (status == "Dispatched").sum()
        ),

        "in_transit": int(
            (status == "In Transit").sum()
        ),

        "delivered": int(
            (status == "Delivered").sum()
        ),

        "failed": int(
            (status == "Failed").sum()
        ),

        "cancelled": int(
            (status == "Cancelled").sum()
        )
    }