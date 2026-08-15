
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import datetime
import io

# ============================================================
# BISCUIT CRM / ERP PROTOTYPE
# Integrated UI -> Engine Layer -> CSV Demo Database
# ============================================================

st.set_page_config(
    page_title="Biscuit CRM",
    page_icon="🍪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

CUSTOMERS_FILE = DATA_DIR / "customers.csv"
PRODUCTS_FILE = DATA_DIR / "products.csv"
SALES_FILE = DATA_DIR / "sales.csv"
SALE_ITEMS_FILE = DATA_DIR / "sale_items.csv"
MOVEMENTS_FILE = DATA_DIR / "inventory_movements.csv"
INVOICES_FILE = DATA_DIR / "invoices.csv"
PAYMENTS_FILE = DATA_DIR / "payments.csv"
APPROVALS_FILE = DATA_DIR / "approvals.csv"
EXPENDITURES_FILE = DATA_DIR / "expenditures.csv"
TRUCKS_FILE = DATA_DIR / "trucks.csv"
DELIVERIES_FILE = DATA_DIR / "deliveries.csv"
DOCUMENTS_FILE = DATA_DIR / "documents.csv"
ARCHIVE_FILE = DATA_DIR / "records_archive.csv"
AUDIT_FILE = DATA_DIR / "audit_log.csv"
INBOUND_FILE = DATA_DIR / "inbound_receipts.csv"

DEMO_USER = "Demo Administrator"

# ============================================================
# ENGINE IMPORTS
# ============================================================

from engine.sales import create_sale
from engine.invoices import create_invoice_from_sale, record_payment as invoice_payment
from engine.inventory import calculate_product_stock, get_stock_status
from engine.approvals import (
    create_request,
    approve_request,
    reject_request,
    request_revision,
    complete_request,
    get_pending_requests,
    get_approval_summary,
)
from engine.expenditure import (
    create_expenditure_request,
    approve_expenditure,
    reject_expenditure,
    pay_expenditure,
    expenditure_summary,
)
from engine.inbound_logistics import (
    create_inbound_receipt,
    update_inbound_status,
    receive_goods,
)
from engine.distribution import (
    add_truck,
    assign_driver,
    create_delivery,
    update_delivery_status,
    delivery_summary,
)
from engine.documents import (
    register_document,
    archive_record,
    link_document,
    search_documents,
    search_archive,
    document_summary,
    archive_summary,
    auto_archive_completed_records,
)
from engine.receivables import (
    customer_account,
    customer_accounts,
    receivables_summary,
    customer_transaction_history,
)
from engine.reports import (
    management_kpis,
    sales_by_day,
    sales_by_month,
    sales_by_product,
    sales_by_customer,
    top_products,
    top_customers,
    sales_vs_expenditure,
    stock_movement_summary,
    customer_performance,
    product_performance,
)

# Automatically synchronize completed operational records into the archive.
# Original records remain in their live modules; the archive is a traceable
# historical snapshot, and duplicate checks make this safe on Streamlit reruns.
try:
    auto_archive_completed_records(
        ARCHIVE_FILE,
        AUDIT_FILE,
        SALES_FILE,
        INVOICES_FILE,
        DELIVERIES_FILE,
        EXPENDITURES_FILE,
        DEMO_USER,
    )
except Exception:
    # Archive synchronization must never prevent the CRM from opening.
    pass

# ============================================================
# GENERAL HELPERS
# ============================================================

def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


ensure_data_dir()


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def write_csv(df, path):
    ensure_data_dir()
    df.to_csv(path, index=False)


def num(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)


def col(df, name, default=None):
    if name in df.columns:
        return df[name]
    if default is None:
        return pd.Series([""] * len(df), index=df.index)
    return pd.Series([default] * len(df), index=df.index)


def safe_rerun():
    st.rerun()


def flash_success(message):
    st.success(message)
    st.session_state["last_action"] = message


def format_naira(value):
    try:
        return f"₦{float(value):,.0f}"
    except Exception:
        return "₦0"


def kpi(label, value, note=""):
    st.markdown(
        f"""
        <div class="kpi-box">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-label">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(value):
    value = str(value)
    low = value.lower()
    if low in {"approved", "completed", "paid", "active", "delivered", "healthy"}:
        return f"🟢 {value}"
    if low in {"pending", "pending approval", "outstanding", "assigned", "on delivery", "submitted"}:
        return f"🟡 {value}"
    if low in {"rejected", "cancelled", "inactive", "maintenance", "damaged"}:
        return f"🔴 {value}"
    return f"🔵 {value}"


def select_id(df, id_col, name_col=None, label="Select record"):
    if df.empty or id_col not in df.columns:
        return None
    options = df[id_col].astype(str).tolist()
    if not options:
        return None
    if name_col and name_col in df.columns:
        display = [
            f"{row[id_col]} — {row[name_col]}"
            for _, row in df.iterrows()
        ]
        chosen = st.selectbox(label, display)
        return chosen.split(" — ", 1)[0]
    return st.selectbox(label, options)


def action_error(exc):
    st.error(str(exc))



# ============================================================
# VISUAL ASSETS / PAGE ICONS
# ============================================================

ASSETS_DIR = BASE_DIR / "assets"

NAV_ICONS = {
    "Dashboard": "dashboard.png",
    "Customers / Clients": "customers.png",
    "Products": "products.png",
    "Warehouse & Inventory": "warehouse.png",
    "Sales": "sales.png",
    "Invoices": "invoices.png",
    "Trucks / Distribution": "distribution.png",
    "Inbound Logistics": "distribution.png",
    "Product Scanner": "products.png",
    "Stock Requests": "stock_requests.png",
    "Expenditure": "expenditure.png",
    "Approval Center": "approvals.png",
    "Records Archive": "archive.png",
    "Documents": "documents.png",
    "Reports & Analytics": "reports.png",
    "Users & Roles": "users.png",
    "Settings": "settings.png",
}

PAGE_ICONS = {
    "Executive Dashboard": "dashboard.png",
    "Customers / Clients": "customers.png",
    "Products": "products.png",
    "Warehouse & Inventory": "warehouse.png",
    "Sales": "sales.png",
    "Invoices & Payments": "invoices.png",
    "Trucks / Distribution": "distribution.png",
    "Inbound Logistics": "distribution.png",
    "Product Scanner": "products.png",
    "Stock Requests": "stock_requests.png",
    "Expenditure": "expenditure.png",
    "Approval Center": "approvals.png",
    "Records Archive": "archive.png",
    "Documents / Scanned Invoices": "documents.png",
    "Reports & Analytics": "reports.png",
    "Users & Roles": "users.png",
    "Settings": "settings.png",
}

def asset_path(filename):
    path = ASSETS_DIR / filename
    return str(path) if path.exists() else None

def page_header(title, caption=""):
    icon = asset_path(PAGE_ICONS.get(title, "dashboard.png"))
    c1, c2 = st.columns([0.08, 0.92], vertical_alignment="center")
    with c1:
        if icon:
            st.image(icon, width=46)
    with c2:
        st.title(title)
        if caption:
            st.caption(caption)

def section_header(title, icon_name=None):
    icon = asset_path(icon_name) if icon_name else None
    c1, c2 = st.columns([0.06, 0.94], vertical_alignment="center")
    with c1:
        if icon:
            st.image(icon, width=30)
    with c2:
        st.subheader(title)

# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>
    .main { background-color: #f7f8fa; }

    [data-testid="stSidebar"] {
        background-color: #111827;
    }

    [data-testid="stSidebar"] * {
        color: white;
    }

    .kpi-box {
        background-color: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 18px;
        min-height: 105px;
    }

    .kpi-label {
        color: #6b7280;
        font-size: 13px;
    }

    .kpi-value {
        color: #111827;
        font-size: 25px;
        font-weight: 700;
        margin: 4px 0;
    }

    .section-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 18px;
    }

    .demo-banner {
        background: #fff7ed;
        border: 1px solid #fed7aa;
        color: #9a3412;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 15px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# SIDEBAR
# ============================================================

NAV_ITEMS = [
    "Dashboard",
    "Customers / Clients",
    "Products",
    "Warehouse & Inventory",
    "Sales",
    "Invoices",
    "Trucks / Distribution",
    "Inbound Logistics",
    "Product Scanner",
    "Stock Requests",
    "Expenditure",
    "Approval Center",
    "Records Archive",
    "Documents",
    "Reports & Analytics",
    "Users & Roles",
    "Settings",
]

if "menu" not in st.session_state:
    st.session_state["menu"] = "Dashboard"

with st.sidebar:
    st.markdown("# 🍪 Biscuit CRM")
    st.caption("Wholesale & Distribution")
    st.warning("PROTOTYPE / DEMO")
    st.divider()
    st.caption("MAIN MENU")

    for nav_item in NAV_ITEMS:
        icon_file = asset_path(NAV_ICONS.get(nav_item, "dashboard.png"))
        row_icon, row_button = st.columns([0.18, 0.82], vertical_alignment="center")
        with row_icon:
            if icon_file:
                st.image(icon_file, width=25)
        with row_button:
            if st.button(
                nav_item,
                key=f"nav_{nav_item}",
                use_container_width=True,
                type="primary" if st.session_state["menu"] == nav_item else "secondary",
            ):
                st.session_state["menu"] = nav_item
                st.rerun()

    st.divider()
    st.caption("CURRENT USER")
    st.write("👤 Demo Administrator")
    st.caption("Administrator")

menu = st.session_state["menu"]

# ============================================================
# DASHBOARD
# ============================================================

def dashboard():
    page_header("Executive Dashboard", "Central overview of the biscuit wholesale and distribution business.")
    st.markdown(
        '<div class="demo-banner">PROTOTYPE / DEMO — All displayed business records are fictional demonstration data.</div>',
        unsafe_allow_html=True,
    )

    try:
        k = management_kpis(
            CUSTOMERS_FILE,
            PRODUCTS_FILE,
            SALES_FILE,
            PAYMENTS_FILE,
            INVOICES_FILE,
            MOVEMENTS_FILE,
            EXPENDITURES_FILE,
        )
    except Exception:
        k = {
            "total_customers": len(read_csv(CUSTOMERS_FILE)),
            "total_sales": 0,
            "sales_transactions": 0,
            "average_sale": 0,
            "total_stock": 0,
            "low_stock": 0,
            "stock_received": 0,
            "stock_issued": 0,
            "damaged_stock": 0,
            "total_received": 0,
            "outstanding_invoices": 0,
            "total_expenditure": 0,
            "pending_expenditure": 0,
        }

    trucks = read_csv(TRUCKS_FILE)
    deliveries = read_csv(DELIVERIES_FILE)
    approvals = read_csv(APPROVALS_FILE)

    active_trucks = 0
    if not trucks.empty and "Status" in trucks.columns:
        active_trucks = int(
            trucks["Status"].astype(str).str.lower().isin(
                ["available", "assigned", "on delivery"]
            ).sum()
        )

    pending_approvals = 0
    if not approvals.empty and "Status" in approvals.columns:
        pending_approvals = int(
            approvals["Status"].astype(str).str.lower().isin(
                ["submitted", "pending approval"]
            ).sum()
        )

    active_deliveries = 0
    delivered_count = 0
    if not deliveries.empty and "Status" in deliveries.columns:
        delivery_status = deliveries["Status"].astype(str).str.lower()
        active_deliveries = int(delivery_status.isin(["dispatched", "in transit", "on delivery"]).sum())
        delivered_count = int((delivery_status == "delivered").sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Total Customers", f"{k['total_customers']:,}", "Demo customers")
    with c2:
        kpi("Total Sales", format_naira(k["total_sales"]), f"{k['sales_transactions']:,} transactions")
    with c3:
        kpi("Warehouse Stock", f"{k['total_stock']:,}", "Calculated from movement ledger")
    with c4:
        kpi("Low Stock Items", f"{k['low_stock']:,}", "Requires attention")

    st.write("")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Payments Received", format_naira(k["total_received"]), "Cash collected")
    with c2:
        kpi("Outstanding Invoices", format_naira(k["outstanding_invoices"]), "Receivables")
    with c3:
        kpi("Active Trucks", f"{active_trucks:,}", "Available / assigned / on delivery")
    with c4:
        kpi("Active Deliveries", f"{active_deliveries:,}", f"{delivered_count:,} delivered")

    st.divider()

    # Executive distribution snapshot
    st.subheader("Wholesale & Distribution Snapshot")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Sales Value", format_naira(k["total_sales"]))
    d2.metric("Stock Units", f"{k['total_stock']:,.0f}")
    d3.metric("Pending Approvals", f"{pending_approvals:,}")
    d4.metric("Expenditure", format_naira(k["total_expenditure"]))

    st.divider()

    sales_file = read_csv(SALES_FILE)
    left, right = st.columns(2)

    with left:
        section_header("Sales Performance", "sales.png")
        daily = sales_by_day(SALES_FILE)
        if not daily.empty:
            fig = px.line(daily, x="Date", y="Amount", markers=True)
            fig.update_layout(height=330, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sales chart will appear when sales records are available.")

    with right:
        section_header("Top Products", "products.png")
        tp = top_products(SALES_FILE, 10, SALE_ITEMS_FILE)
        if not tp.empty:
            product_col = [c for c in tp.columns if c != "Amount"][0]
            fig = px.bar(tp, x="Amount", y=product_col, orientation="h")
            fig.update_layout(height=330, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Top-product analysis will appear after sales are recorded.")

    section_header("Recent Activity", "reports.png")
    audit = read_csv(AUDIT_FILE)
    if not audit.empty:
        st.dataframe(audit.tail(10).iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("No audit activity yet.")

# ============================================================
# CUSTOMERS
# ============================================================

def customers_page():
    page_header("Customers / Clients", "Manage customer master records, accounts and relationships.")
    df = read_csv(CUSTOMERS_FILE)

    if df.empty:
        st.warning("customers.csv is empty or unavailable.")
    else:
        search = st.text_input("🔎 Search customers", placeholder="Name, business, phone or ID...")
        filtered = df.copy()
        if search:
            term = search.lower()
            filtered = filtered[
                filtered.apply(lambda r: term in str(r.to_dict()).lower(), axis=1)
            ]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Customers", len(df))
        with c2:
            active = int(
                col(df, "Account Status", "")
                .astype(str).str.lower().eq("active").sum()
            )
            st.metric("Active", active)
        with c3:
            outstanding = num(col(df, "Outstanding Balance", 0)).sum()
            st.metric("Outstanding", format_naira(outstanding))

        st.dataframe(filtered, use_container_width=True, hide_index=True, height=420)

    st.divider()
    with st.expander("➕ Add Demo Customer"):
        with st.form("add_customer_form"):
            name = st.text_input("Customer Name")
            business = st.text_input("Business Name")
            phone = st.text_input("Phone")
            email = st.text_input("Email")
            address = st.text_input("Address")
            customer_type = st.selectbox("Customer Type", ["Wholesale", "Distributor", "Retailer", "Corporate"])
            submitted = st.form_submit_button("Create Customer", type="primary")
            if submitted:
                if not name:
                    st.error("Customer name is required.")
                else:
                    try:
                        existing = read_csv(CUSTOMERS_FILE)
                        next_id = f"CUST-{len(existing)+1:06d}"
                        record = {
                            "Customer ID": next_id,
                            "Customer Name": name,
                            "Business Name": business,
                            "Phone": phone,
                            "Email": email,
                            "Address": address,
                            "Customer Type": customer_type,
                            "Registration Date": datetime.now().strftime("%Y-%m-%d"),
                            "Account Status": "Active",
                            "Credit Status": "Good",
                            "Total Purchases": 0,
                            "Outstanding Balance": 0,
                            "Last Purchase Date": "",
                        }
                        for c in existing.columns:
                            record.setdefault(c, "")
                        existing = pd.concat([existing, pd.DataFrame([record])], ignore_index=True)
                        write_csv(existing, CUSTOMERS_FILE)
                        flash_success(f"Customer {next_id} created successfully.")
                        safe_rerun()
                    except Exception as exc:
                        action_error(exc)

# ============================================================
# PRODUCTS
# ============================================================

def products_page():
    page_header("Products", "Product master database for the biscuit business.")
    df = read_csv(PRODUCTS_FILE)

    if df.empty:
        st.warning("products.csv is empty or unavailable.")
        return

    search = st.text_input("🔎 Search products", placeholder="Product, brand, category or ID...")
    category_values = ["All"]
    if "Category" in df.columns:
        category_values += sorted(df["Category"].dropna().astype(str).unique().tolist())
    category = st.selectbox("Category", category_values)

    filtered = df.copy()
    if search:
        term = search.lower()
        filtered = filtered[
            filtered.apply(lambda r: term in str(r.to_dict()).lower(), axis=1)
        ]
    if category != "All" and "Category" in filtered.columns:
        filtered = filtered[filtered["Category"] == category]

    stock = num(col(df, "Current Stock", 0))
    reorder = num(col(df, "Reorder Level", 0))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Products", len(df))
    c2.metric("Active", int(col(df, "Product Status", "").astype(str).str.lower().eq("active").sum()))
    c3.metric("Stock Units", f"{int(stock.sum()):,}")
    c4.metric("Low Stock", int((stock <= reorder).sum()))

    st.dataframe(filtered, use_container_width=True, hide_index=True, height=450)

    st.divider()
    with st.expander("➕ Add Demo Product"):
        with st.form("add_product_form"):
            pname = st.text_input("Product Name")
            brand = st.text_input("Brand")
            cat = st.text_input("Category", value="Biscuits")
            description = st.text_area("Description")
            unit = st.text_input("Unit Type", value="Carton")
            pack = st.text_input("Pack Size", value="24 packs")
            selling = st.number_input("Selling Price", min_value=0.0, step=100.0)
            cost = st.number_input("Cost Price", min_value=0.0, step=100.0)
            reorder_level = st.number_input("Reorder Level", min_value=0, step=10)
            submitted = st.form_submit_button("Create Product", type="primary")
            if submitted:
                if not pname:
                    st.error("Product name is required.")
                else:
                    existing = read_csv(PRODUCTS_FILE)
                    pid = f"PROD-{len(existing)+1:06d}"
                    record = {
                        "Product ID": pid,
                        "Product Name": pname,
                        "Brand": brand,
                        "Category": cat,
                        "Product Description": description,
                        "Unit Type": unit,
                        "Pack Size": pack,
                        "Selling Price": selling,
                        "Cost Price": cost,
                        "Reorder Level": reorder_level,
                        "Current Stock": 0,
                        "Product Status": "Active",
                    }
                    for c in existing.columns:
                        record.setdefault(c, "")
                    existing = pd.concat([existing, pd.DataFrame([record])], ignore_index=True)
                    write_csv(existing, PRODUCTS_FILE)
                    flash_success(f"Product {pid} created successfully.")
                    safe_rerun()

# ============================================================
# INVENTORY
# ============================================================

def inventory_page():
    page_header("Warehouse & Inventory", "Monitor stock levels, movements, requests and warehouse activity.")
    products = read_csv(PRODUCTS_FILE)
    movements = read_csv(MOVEMENTS_FILE)

    if products.empty:
        st.warning("Product database is empty.")
        return

    if movements.empty:
        products["Calculated Stock"] = num(col(products, "Current Stock", 0))
    else:
        products["Calculated Stock"] = products["Product ID"].apply(
            lambda pid: calculate_product_stock(movements, pid)
        )

    reorder = num(col(products, "Reorder Level", 0))
    calculated = num(products["Calculated Stock"])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Stock", f"{int(calculated.sum()):,}")
    c2.metric("Low Stock", int((calculated <= reorder).sum()))
    c3.metric("Received", int(
        num(col(movements, "Quantity", 0))[
            col(movements, "Movement Type", "").isin(
                ["Opening Stock", "Stock Received", "Stock Return"]
            )
        ].sum() if not movements.empty else 0
    ))
    c4.metric("Issued", int(
        num(col(movements, "Quantity", 0))[
            col(movements, "Movement Type", "").isin(
                ["Stock Transfer", "Stock Sold"]
            )
        ].sum() if not movements.empty else 0
    ))
    c5.metric("Damaged", int(
        num(col(movements, "Quantity", 0))[
            col(movements, "Movement Type", "").eq("Stock Damaged")
        ].sum() if not movements.empty else 0
    ))

    tab1, tab2, tab3 = st.tabs(["📦 Stock Overview", "🔄 Stock Movements", "➕ Record Movement"])

    with tab1:
        view = products.copy()
        view["Stock Status"] = [
            get_stock_status(s, r)
            for s, r in zip(calculated, reorder)
        ]
        st.dataframe(view, use_container_width=True, hide_index=True, height=450)

    with tab2:
        if movements.empty:
            st.info("No stock movements recorded.")
        else:
            st.dataframe(movements, use_container_width=True, hide_index=True, height=450)

    with tab3:
        product_choices = [
            f"{r['Product ID']} — {r.get('Product Name', '')}"
            for _, r in products.iterrows()
        ]
        with st.form("movement_form"):
            selected = st.selectbox("Product", product_choices)
            movement_type = st.selectbox(
                "Movement Type",
                ["Stock Received", "Stock Transfer", "Stock Return", "Stock Damaged"]
            )
            quantity = st.number_input("Quantity", min_value=1, value=10, step=1)
            reference = st.text_input("Reference")
            destination = st.text_input("Source / Destination")
            notes = st.text_area("Notes")
            submit = st.form_submit_button("Save Stock Movement", type="primary")

            if submit:
                pid = selected.split(" — ", 1)[0]
                pname = selected.split(" — ", 1)[1]
                current = read_csv(MOVEMENTS_FILE)
                movement_id = f"STOCK-{len(current)+1:06d}"
                record = {
                    "Movement ID": movement_id,
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Product ID": pid,
                    "Product Name": pname,
                    "Movement Type": movement_type,
                    "Quantity": quantity,
                    "Reference": reference,
                    "Source/Destination": destination,
                    "Recorded By": DEMO_USER,
                    "Notes": notes,
                }
                for c in current.columns:
                    record.setdefault(c, "")
                current = pd.concat([current, pd.DataFrame([record])], ignore_index=True)
                write_csv(current, MOVEMENTS_FILE)
                flash_success(f"Stock movement {movement_id} recorded.")
                safe_rerun()

# ============================================================
# SALES
# ============================================================

def sales_page():
    page_header("Sales", "Create and manage customer sales transactions.")
    customers = read_csv(CUSTOMERS_FILE)
    products = read_csv(PRODUCTS_FILE)
    sales = read_csv(SALES_FILE)

    c1, c2, c3 = st.columns(3)
    c1.metric("Sales Transactions", len(sales))
    c2.metric("Sales Value", format_naira(num(col(sales, "Total Amount", 0)).sum()))
    c3.metric("Average Sale", format_naira(
        num(col(sales, "Total Amount", 0)).mean() if not sales.empty else 0
    ))

    st.divider()
    tab1, tab2 = st.tabs(["➕ Create Sale", "📋 Sales History"])

    with tab1:
        if customers.empty or products.empty:
            st.warning("Customers and products are required before creating a sale.")
            return

        customer_id = select_id(customers, "Customer ID", "Customer Name", "Customer")
        customer = customers[customers["Customer ID"].astype(str) == str(customer_id)].iloc[0]

        product_options = [
            f"{r['Product ID']} — {r.get('Product Name','')}"
            for _, r in products.iterrows()
        ]

        if "sale_cart" not in st.session_state:
            st.session_state.sale_cart = []

        with st.form("add_sale_item"):
            selected_product = st.selectbox("Product", product_options)
            pid = selected_product.split(" — ", 1)[0]
            prow = products[products["Product ID"].astype(str) == pid].iloc[0]
            default_price = float(pd.to_numeric(prow.get("Selling Price", 0), errors="coerce") or 0)
            qty = st.number_input("Quantity", min_value=1.0, value=1.0, step=1.0)
            price = st.number_input("Unit Price", min_value=0.0, value=default_price, step=50.0)
            item_discount = st.number_input("Item Discount", min_value=0.0, value=0.0, step=50.0)
            add_item = st.form_submit_button("Add Item")
            if add_item:
                st.session_state.sale_cart.append({
                    "Product ID": pid,
                    "Quantity": qty,
                    "Unit Price": price,
                    "Discount": item_discount,
                })
                st.success("Item added to sale.")

        if st.session_state.sale_cart:
            st.subheader("Current Sale")
            cart_rows = []
            for item in st.session_state.sale_cart:
                prow = products[products["Product ID"].astype(str) == str(item["Product ID"])]
                pname = prow.iloc[0].get("Product Name", item["Product ID"]) if not prow.empty else item["Product ID"]
                line = item["Quantity"] * item["Unit Price"] - item.get("Discount", 0)
                cart_rows.append({
                    "Product ID": item["Product ID"],
                    "Product": pname,
                    "Quantity": item["Quantity"],
                    "Unit Price": item["Unit Price"],
                    "Discount": item.get("Discount", 0),
                    "Line Total": line,
                })
            cart_df = pd.DataFrame(cart_rows)
            st.dataframe(cart_df, use_container_width=True, hide_index=True)
            subtotal = float(cart_df["Line Total"].sum())

            with st.form("complete_sale"):
                c1, c2, c3 = st.columns(3)
                discount = c1.number_input("Sale Discount", min_value=0.0, value=0.0, step=100.0)
                tax = c2.number_input("Tax", min_value=0.0, value=0.0, step=100.0)
                salesperson = c3.text_input("Salesperson", value=DEMO_USER)
                payment_status = st.selectbox("Payment Status", ["Outstanding", "Paid", "Partially Paid"])
                delivery_status = st.selectbox("Delivery Status", ["Pending", "Ready for Delivery", "Delivered"])
                create = st.form_submit_button("🚀 Complete Sale", type="primary")

                if create:
                    try:
                        result = create_sale(
                            CUSTOMERS_FILE,
                            PRODUCTS_FILE,
                            MOVEMENTS_FILE,
                            SALES_FILE,
                            SALE_ITEMS_FILE,
                            AUDIT_FILE,
                            customer_id,
                            st.session_state.sale_cart,
                            salesperson=salesperson,
                            discount=discount,
                            tax=tax,
                            payment_status=payment_status,
                            delivery_status=delivery_status,
                            status="Completed",
                        )
                        st.session_state.sale_cart = []
                        try:
                            inv = create_invoice_from_sale(
                                SALES_FILE,
                                SALE_ITEMS_FILE,
                                INVOICES_FILE,
                                AUDIT_FILE,
                                result["sale_id"],
                                created_by=DEMO_USER,
                            )
                            flash_success(
                                f"Sale {result['sale_id']} completed and invoice {inv['invoice_number']} generated."
                            )
                        except Exception as invoice_exc:
                            flash_success(f"Sale {result['sale_id']} completed.")
                            st.warning(f"Invoice was not generated automatically: {invoice_exc}")
                        safe_rerun()
                    except Exception as exc:
                        action_error(exc)

            if st.button("🗑️ Clear Sale Cart"):
                st.session_state.sale_cart = []
                safe_rerun()
        else:
            st.info("Add one or more products to begin a sale.")

    with tab2:
        if sales.empty:
            st.info("No sales recorded yet.")
        else:
            st.dataframe(sales.sort_values("Date", ascending=False), use_container_width=True, hide_index=True, height=500)

# ============================================================
# INVOICES & PAYMENTS
# ============================================================

def invoices_page():
    """Invoices + Payments workflow."""

    page_header(
        "Invoices & Payments",
        "Generate invoices from completed sales and record customer payments against outstanding invoices."
    )

    invoices = read_csv(INVOICES_FILE)
    sales = read_csv(SALES_FILE)
    payments = read_csv(PAYMENTS_FILE)

    # ========================================================
    # KPI
    # ========================================================

    total_invoiced = num(col(invoices, "Total Amount", 0)).sum()
    total_paid = num(col(invoices, "Amount Paid", 0)).sum()
    total_due = num(col(invoices, "Balance Due", 0)).sum()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Invoices", f"{len(invoices):,}")
    c2.metric("Invoiced", format_naira(total_invoiced))
    c3.metric("Payments Received", format_naira(total_paid))
    c4.metric("Outstanding", format_naira(total_due))

    st.divider()

    # ========================================================
    # THREE VISIBLE WORKFLOW TABS
    # ========================================================

    tab1, tab2, tab3 = st.tabs(
        [
            "🧾 Invoice Register",
            "➕ Generate Invoice",
            "💳 Record Payment",
        ]
    )

    # ========================================================
    # INVOICE REGISTER
    # ========================================================

    with tab1:

        st.subheader("Invoice Register")

        if invoices.empty:

            st.info(
                "No invoices have been generated yet. "
                "Use the 'Generate Invoice' tab to create one "
                "from a completed sale."
            )

        else:

            status_options = ["All"] + sorted(
                col(invoices, "Payment Status", "")
                .astype(str)
                .unique()
                .tolist()
            )

            status = st.selectbox(
                "Invoice Status",
                status_options,
                key="invoice_status_filter",
            )

            view = invoices.copy()

            if status != "All":
                view = view[
                    col(view, "Payment Status", "").astype(str)
                    == status
                ]

            st.dataframe(
                view,
                use_container_width=True,
                hide_index=True,
                height=450,
            )

        st.subheader("Payment Ledger")

        if payments.empty:
            st.info("No payments have been recorded yet.")
        else:
            st.dataframe(
                payments,
                use_container_width=True,
                hide_index=True,
                height=300,
            )

    # ========================================================
    # GENERATE INVOICE
    # ========================================================

    with tab2:

        st.subheader("Generate Invoice from Completed Sale")

        st.info(
            "Select a completed sale that does not already have an invoice."
        )

        if sales.empty:

            st.warning(
                "No sales are available. Create a completed sale first."
            )

        else:

            invoiced_sales = set(
                col(invoices, "Sale ID", "")
                .astype(str)
                .str.strip()
                .tolist()
            )

            sale_ids = (
                sales["Sale ID"]
                .astype(str)
                .str.strip()
            )

            available_sales = sales[
                ~sale_ids.isin(invoiced_sales)
            ].copy()

            # Prefer completed sales where a Status column exists.
            if "Status" in available_sales.columns:

                completed = available_sales[
                    available_sales["Status"]
                    .astype(str)
                    .str.lower()
                    .isin(["completed", "complete", "closed"])
                ].copy()

                if not completed.empty:
                    available_sales = completed

            if available_sales.empty:

                st.success(
                    "All available completed sales already have invoices."
                )

            else:

                sale_id = select_id(
                    available_sales,
                    "Sale ID",
                    "Customer Name",
                    "Sale",
                )

                selected = available_sales[
                    available_sales["Sale ID"].astype(str)
                    == str(sale_id)
                ].iloc[0]

                st.write(
                    f"**Customer:** {selected.get('Customer Name', '')}"
                )
                st.write(
                    f"**Sale Total:** "
                    f"{format_naira(selected.get('Total Amount', 0))}"
                )
                st.write(
                    f"**Sale Date:** {selected.get('Date', '')}"
                )

                st.divider()

                if st.button(
                    "🧾 Generate Invoice",
                    type="primary",
                    use_container_width=True,
                    key="generate_invoice_button",
                ):

                    try:

                        result = create_invoice_from_sale(
                            SALES_FILE,
                            SALE_ITEMS_FILE,
                            INVOICES_FILE,
                            AUDIT_FILE,
                            str(sale_id),
                            DEMO_USER,
                        )

                        flash_success(
                            f"Invoice "
                            f"{result.get('invoice_number', result.get('invoice_id', 'created'))} "
                            f"generated successfully."
                        )

                        safe_rerun()

                    except Exception as exc:

                        action_error(exc)

    # ========================================================
    # RECORD PAYMENT
    # ========================================================

    with tab3:

        st.subheader("Record Customer Payment")

        st.info(
            "Select an outstanding invoice and record the payment received."
        )

        if invoices.empty:

            st.warning(
                "There are no invoices yet. "
                "Generate an invoice first."
            )

        else:

            outstanding = invoices[
                num(col(invoices, "Balance Due", 0)) > 0
            ].copy()

            if outstanding.empty:

                st.success(
                    "There are no outstanding invoice balances."
                )

            else:

                invoice_id = select_id(
                    outstanding,
                    "Invoice ID",
                    "Customer Name",
                    "Invoice",
                )

                inv = outstanding[
                    outstanding["Invoice ID"].astype(str)
                    == str(invoice_id)
                ].iloc[0]

                balance_value = pd.to_numeric(
                    inv.get("Balance Due", 0),
                    errors="coerce",
                )

                balance = (
                    float(balance_value)
                    if pd.notna(balance_value)
                    else 0.0
                )

                st.info(
                    f"Outstanding balance: "
                    f"{format_naira(balance)}"
                )

                st.write(
                    f"**Customer:** {inv.get('Customer Name', '')}"
                )
                st.write(
                    f"**Invoice:** {invoice_id}"
                )
                st.write(
                    f"**Sale:** {inv.get('Sale ID', '')}"
                )

                st.divider()

                with st.form("record_customer_payment"):

                    amount = st.number_input(
                        "Payment Amount",
                        min_value=0.01,
                        max_value=max(balance, 0.01),
                        value=max(balance, 0.01),
                        step=100.0,
                    )

                    method = st.selectbox(
                        "Payment Method",
                        [
                            "Bank Transfer",
                            "Cash",
                            "POS",
                            "Cheque",
                            "Other",
                        ],
                    )

                    reference = st.text_input(
                        "Payment Reference",
                        placeholder="PAY-REF-2026-000001",
                    )

                    notes = st.text_area("Notes")

                    submit = st.form_submit_button(
                        "💳 Record Payment",
                        type="primary",
                        use_container_width=True,
                    )

                    if submit:

                        if amount > balance:

                            st.error(
                                "Payment amount cannot be greater "
                                "than the outstanding invoice balance."
                            )

                        else:

                            try:

                                result = invoice_payment(
                                    INVOICES_FILE,
                                    PAYMENTS_FILE,
                                    AUDIT_FILE,
                                    str(invoice_id),
                                    amount,
                                    payment_method=method,
                                    reference=reference,
                                    received_by=DEMO_USER,
                                    notes=notes,
                                )

                                flash_success(
                                    f"Payment "
                                    f"{result.get('payment_id', 'created')} "
                                    f"recorded successfully. "
                                    f"Remaining balance: "
                                    f"{format_naira(result.get('balance_due', 0))}"
                                )

                                safe_rerun()

                            except Exception as exc:

                                action_error(exc)

# ============================================================
# TRUCKS / DISTRIBUTION
# ============================================================

def distribution_page():
    page_header("Trucks / Distribution", "Manage trucks, drivers, routes and customer deliveries.")
    trucks = read_csv(TRUCKS_FILE)
    deliveries = read_csv(DELIVERIES_FILE)
    customers = read_csv(CUSTOMERS_FILE)
    sales = read_csv(SALES_FILE)
    invoices = read_csv(INVOICES_FILE)

    c1, c2, c3 = st.columns(3)
    c1.metric("Trucks", len(trucks))
    c2.metric("Deliveries", len(deliveries))
    c3.metric("Active Deliveries", int(
        col(deliveries, "Status", "").astype(str).str.lower().isin(
            ["dispatched", "in transit", "on delivery"]
        ).sum()
    ))

    tab1, tab2, tab3 = st.tabs(["🚚 Fleet", "📍 Deliveries", "➕ Add / Assign"])

    with tab1:
        st.dataframe(trucks, use_container_width=True, hide_index=True, height=400)

    with tab2:
        if deliveries.empty:
            st.info("No deliveries recorded.")
        else:
            st.dataframe(deliveries, use_container_width=True, hide_index=True, height=400)
            delivery_id = select_id(deliveries, "Delivery ID", "Customer Name", "Delivery")
            new_status = st.selectbox("Update Delivery Status", ["Assigned", "Dispatched", "In Transit", "Delivered", "Failed"])
            if st.button("Update Delivery", type="primary"):
                try:
                    result = update_delivery_status(
                        TRUCKS_FILE,
                        DELIVERIES_FILE,
                        AUDIT_FILE,
                        delivery_id,
                        new_status,
                        DEMO_USER,
                    )
                    flash_success(f"Delivery {delivery_id} updated to {result.get('status', new_status)}.")
                    safe_rerun()
                except Exception as exc:
                    action_error(exc)

    with tab3:
        st.subheader("Add Truck")
        with st.form("truck_form"):
            reg = st.text_input("Registration Number")
            driver_id = st.text_input("Driver ID", value="DRV-000001")
            driver_name = st.text_input("Driver Name")
            driver_phone = st.text_input("Driver Phone")
            capacity = st.number_input("Capacity", min_value=0.0, value=500.0)
            route = st.text_input("Assigned Route")
            status = st.selectbox("Status", ["Available", "Assigned", "On Delivery", "Maintenance", "Inactive"])
            submit = st.form_submit_button("Add Truck", type="primary")
            if submit:
                try:
                    result = add_truck(
                        TRUCKS_FILE, AUDIT_FILE, reg, driver_id, driver_name,
                        driver_phone, capacity, route, status, DEMO_USER
                    )
                    flash_success(f"Truck {result.get('truck_id', 'created')} added.")
                    safe_rerun()
                except Exception as exc:
                    action_error(exc)

        if not trucks.empty:
            st.subheader("Create Delivery")
            truck_id = select_id(trucks, "Truck ID", "Registration Number", "Truck")
            customer_id = select_id(customers, "Customer ID", "Customer Name", "Customer") if not customers.empty else None
            sale_id = select_id(sales, "Sale ID", "Customer Name", "Sale") if not sales.empty else ""
            invoice_id = select_id(invoices, "Invoice ID", "Customer Name", "Invoice") if not invoices.empty else ""
            address = st.text_input("Delivery Address")
            route = st.text_input("Route")
            notes = st.text_area("Notes")
            if st.button("Create Delivery", type="primary"):
                try:
                    crow = customers[customers["Customer ID"].astype(str) == str(customer_id)].iloc[0]
                    result = create_delivery(
                        TRUCKS_FILE, DELIVERIES_FILE, AUDIT_FILE,
                        truck_id, customer_id, crow.get("Customer Name", ""),
                        sale_id, invoice_id, address, route, DEMO_USER, notes
                    )
                    flash_success(f"Delivery {result.get('delivery_id', 'created')} created.")
                    safe_rerun()
                except Exception as exc:
                    action_error(exc)


# ============================================================
# QR SCANNER HELPERS
# ============================================================

def decode_qr_camera(camera_image):
    """Decode a QR value from a Streamlit camera_input image."""
    if camera_image is None:
        return "", ""
    try:
        import cv2
        import numpy as np
        from PIL import Image
        image = Image.open(io.BytesIO(camera_image.getvalue())).convert("RGB")
        detector = cv2.QRCodeDetector()
        decoded, _, _ = detector.detectAndDecode(
            cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        )
        return (decoded or "").strip(), ""
    except Exception as exc:
        return "", str(exc)


def product_id_from_qr(decoded):
    decoded = (decoded or "").strip()
    if not decoded:
        return ""
    parts = decoded.split("|")
    return parts[-1].strip() if parts else decoded


# ============================================================
# INBOUND LOGISTICS
# ============================================================

def inbound_logistics_page():
    page_header("Inbound Logistics", "Track expected supplier loads, arriving trucks and goods received into the warehouse.")
    inbound = read_csv(INBOUND_FILE)
    trucks = read_csv(TRUCKS_FILE)
    products = read_csv(PRODUCTS_FILE)

    status_series = col(inbound, "Status", "").astype(str)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Expected Loads", int((status_series == "Expected").sum()))
    c2.metric("In Transit", int((status_series == "In Transit").sum()))
    c3.metric("Arrived / Receiving", int(status_series.isin(["Arrived", "Receiving"]).sum()))
    c4.metric("Received", int(status_series.isin(["Received", "Short Received"]).sum()))

    tab1, tab2, tab3 = st.tabs(["🚛 Incoming Loads", "➕ Schedule Inbound", "📷 Receive & Scan Goods"])

    with tab1:
        if inbound.empty:
            st.info("No inbound shipments are scheduled.")
        else:
            display = inbound.copy()
            st.dataframe(display, use_container_width=True, hide_index=True, height=360)
            receipt_id = select_id(display, "Receipt ID", "Product Name", "Select inbound load")
            if receipt_id:
                row = display[display["Receipt ID"].astype(str) == str(receipt_id)].iloc[0]
                st.info(
                    f"Truck {row.get('Truck ID','—')} ({row.get('Registration Number','—')}) • "
                    f"Expected {float(pd.to_numeric(row.get('Expected Quantity',0), errors='coerce') or 0):,.0f} {row.get('Unit','units')} • "
                    f"Status: {row.get('Status','—')}"
                )
                new_status = st.selectbox("Update inbound status", ["Expected", "In Transit", "Arrived", "Receiving", "Cancelled"], key=f"inbound_status_{receipt_id}")
                if st.button("Update Inbound Status", type="primary"):
                    try:
                        update_inbound_status(INBOUND_FILE, AUDIT_FILE, receipt_id, new_status, DEMO_USER)
                        flash_success(f"{receipt_id} updated to {new_status}.")
                        safe_rerun()
                    except Exception as exc:
                        action_error(exc)

    with tab2:
        if products.empty or trucks.empty:
            st.warning("Products and trucks are required before scheduling an inbound load.")
        else:
            product_id = select_id(products, "Product ID", "Product Name", "Product")
            truck_id = select_id(trucks, "Truck ID", "Registration Number", "Expected Truck")
            prow = products[products["Product ID"].astype(str) == str(product_id)].iloc[0]
            trow = trucks[trucks["Truck ID"].astype(str) == str(truck_id)].iloc[0]
            with st.form("inbound_form"):
                supplier = st.text_input("Supplier", value="Demo Biscuit Supplier Ltd")
                expected_date = st.date_input("Expected Arrival Date")
                expected_qty = st.number_input("Expected Quantity", min_value=1.0, value=500.0, step=10.0)
                unit = st.selectbox("Unit", ["cartons", "cases", "packs", "units"])
                notes = st.text_area("Notes", value="Wholesale replenishment load")
                submit = st.form_submit_button("Schedule Inbound Load", type="primary")
                if submit:
                    try:
                        result = create_inbound_receipt(
                            INBOUND_FILE, AUDIT_FILE, supplier, truck_id,
                            trow.get("Registration Number", ""), trow.get("Driver ID", ""),
                            trow.get("Driver Name", ""), product_id, prow.get("Product Name", ""),
                            str(expected_date), expected_qty, unit, notes, DEMO_USER
                        )
                        flash_success(f"Inbound load {result['Receipt ID']} scheduled.")
                        safe_rerun()
                    except Exception as exc:
                        action_error(exc)

    with tab3:
        receivable = inbound[inbound["Status"].astype(str).isin(["Arrived", "Receiving", "In Transit"])] if not inbound.empty else pd.DataFrame()
        if receivable.empty:
            st.info("No inbound loads are ready for receiving.")
        else:
            receipt_id = select_id(receivable, "Receipt ID", "Product Name", "Goods receipt")
            row = receivable[receivable["Receipt ID"].astype(str) == str(receipt_id)].iloc[0]
            expected = float(pd.to_numeric(row.get("Expected Quantity", 0), errors="coerce") or 0)
            expected_product = str(row.get("Product ID", ""))
            expected_name = str(row.get("Product Name", ""))
            st.info(f"**Truck:** {row.get('Truck ID','—')} • **Supplier:** {row.get('Supplier','—')} • **Expected:** {expected:,.0f} {row.get('Unit','units')} • **Product:** {expected_name} ({expected_product})")

            st.subheader("1. Scan the incoming product")
            camera_image = st.camera_input("Scan the product QR on the incoming goods", key=f"inbound_camera_{receipt_id}")
            manual = st.text_input("Or paste the QR value", placeholder="BISCUIT|PRODUCT|PROD-000001", key=f"inbound_manual_{receipt_id}")
            decoded, scan_error = decode_qr_camera(camera_image)
            decoded = (decoded or manual).strip()
            scanned_product_id = product_id_from_qr(decoded)

            if scan_error and camera_image is not None:
                st.warning(f"Camera QR decoding is unavailable: {scan_error}")
            scan_ok = False
            if scanned_product_id:
                if scanned_product_id == expected_product:
                    scan_ok = True
                    st.success(f"✓ Correct product scanned: {expected_name} ({expected_product})")
                else:
                    st.error(f"Wrong product scanned. Expected {expected_product}, but received {scanned_product_id}.")
            else:
                st.caption("Scan the physical QR label before confirming receipt.")

            st.subheader("2. Confirm actual quantity received")
            received_qty = st.number_input("Actual Quantity Received", min_value=1.0, value=expected if expected > 0 else 1.0, step=10.0, key=f"inbound_qty_{receipt_id}")
            if st.button("Confirm Scanned Goods Received", type="primary", disabled=not scan_ok, key=f"receive_{receipt_id}"):
                try:
                    result = receive_goods(INBOUND_FILE, MOVEMENTS_FILE, AUDIT_FILE, receipt_id, received_qty, DEMO_USER)
                    variance = float(result.get("Variance", 0) or 0)
                    if variance == 0:
                        flash_success(f"{receipt_id}: goods received in full. Warehouse stock updated.")
                    elif variance < 0:
                        st.warning(f"{receipt_id}: short receipt of {abs(variance):,.0f} {result.get('Unit','units')}. Stock updated with actual quantity received.")
                    else:
                        st.success(f"{receipt_id}: over-receipt of {variance:,.0f} {result.get('Unit','units')}. Stock updated with actual quantity received.")
                    safe_rerun()
                except Exception as exc:
                    action_error(exc)

# ============================================================
# PRODUCT SCANNER / QR
# ============================================================

def product_scanner_page():
    page_header("Product Scanner", "Use the camera to scan physical product QR labels, identify products and check live warehouse stock.")
    products = read_csv(PRODUCTS_FILE)

    if products.empty:
        st.warning("Products are required for scanning.")
        return

    st.info("📷 Scan a physical QR label. The Product Scanner is a lookup/activity tool; stock changes only through a confirmed Sale, Warehouse Release or Goods Receipt.")
    tab1, tab2 = st.tabs(["📷 Live Camera Scanner", "🔳 Product QR Cards"])

    with tab1:
        st.subheader("Scan a physical product")
        st.caption("Point the camera at one of the printed QR labels. After scanning, the CRM identifies the product and shows its current stock.")
        camera_image = st.camera_input("📷 Open Camera and Scan QR", key="product_scanner_camera")
        manual = st.text_input("Or paste a QR value", placeholder="BISCUIT|PRODUCT|PROD-000001", key="product_scanner_manual")
        decoded, scan_error = decode_qr_camera(camera_image)
        decoded = (decoded or manual).strip()
        product_id = product_id_from_qr(decoded)

        if scan_error and camera_image is not None:
            st.warning(f"Camera QR decoding is unavailable in this environment: {scan_error}. You can paste the QR value instead.")

        if product_id:
            match = products[products["Product ID"].astype(str).str.strip() == product_id]
            if match.empty:
                st.error(f"Product QR not recognised: {decoded}")
            else:
                row = match.iloc[0]
                stock = calculate_product_stock(read_csv(MOVEMENTS_FILE), product_id)
                try:
                    from engine.audit import record_audit
                    record_audit(AUDIT_FILE, DEMO_USER, "SCAN PRODUCT QR", "Product", product_id, f"Product QR scanned: {row.get('Product Name','')}")
                except Exception as exc:
                    st.warning(f"Scan identified the product, but the activity log could not be updated: {exc}")
                st.success(f"✓ Product identified: {row.get('Product Name','')} ({product_id})")
                a, b, c = st.columns(3)
                a.metric("Current Stock", f"{stock:,.0f}")
                b.metric("Product", str(row.get("Product Name", "")))
                c.metric("Status", str(row.get("Status", "Active")))
                st.caption("Scan activity recorded. No stock was deducted by this lookup scan.")

    with tab2:
        st.caption("Generate printable/displayable QR values for demonstration. Each code identifies one product.")
        import qrcode
        sample = products.head(12).copy()
        for start in range(0, len(sample), 4):
            cols = st.columns(4)
            for idx, (_, row) in enumerate(sample.iloc[start:start+4].iterrows()):
                payload = f"BISCUIT|PRODUCT|{row.get('Product ID','')}"
                qr = qrcode.make(payload)
                with cols[idx]:
                    qr_buffer = io.BytesIO()
                    qr.save(qr_buffer, format="PNG")
                    st.image(qr_buffer.getvalue(), width=120)
                    st.caption(f"{row.get('Product ID','')}\n{row.get('Product Name','')}")

# ============================================================
# STOCK REQUESTS
# ============================================================

def stock_requests_page():
    page_header("Stock Requests", "Sales/distribution requests move through approval before warehouse release.")
    approvals = read_csv(APPROVALS_FILE)
    products = read_csv(PRODUCTS_FILE)

    stock_requests = approvals[
        col(approvals, "Request Type", "").astype(str).str.lower().eq("stock request")
    ].copy() if not approvals.empty else pd.DataFrame()

    st.dataframe(stock_requests, use_container_width=True, hide_index=True, height=350)

    tab1, tab2 = st.tabs(["➕ New Request", "📦 Warehouse Release"])

    with tab1:
        if products.empty:
            st.warning("Products are required.")
        else:
            product_id = select_id(products, "Product ID", "Product Name", "Product")
            prow = products[products["Product ID"].astype(str) == str(product_id)].iloc[0]
            with st.form("stock_request_form"):
                requester = st.text_input("Requester", value=DEMO_USER)
                department = st.text_input("Department", value="Sales / Distribution")
                quantity = st.number_input("Quantity Requested", min_value=1.0, value=10.0)
                priority = st.selectbox("Priority", ["Normal", "High", "Urgent"])
                reason = st.text_area("Reason")
                submit = st.form_submit_button("Submit Stock Request", type="primary")
                if submit:
                    try:
                        result = create_request(
                            APPROVALS_FILE, AUDIT_FILE,
                            "Stock Request", requester, department,
                            f"{prow.get('Product Name','')} — {reason}",
                            amount=0, quantity=quantity, priority=priority
                        )
                        # The warehouse release engine requires product identifiers.
                        approval_df = read_csv(APPROVALS_FILE)
                        idx = approval_df.index[
                            approval_df["Approval ID"].astype(str) == str(result["approval_id"])
                        ] if "Approval ID" in approval_df.columns else approval_df.index[
                            approval_df["Request ID"].astype(str) == str(result["request_id"])
                        ]
                        if len(idx):
                            i = idx[0]
                            approval_df.loc[i, "Product ID"] = product_id
                            approval_df.loc[i, "Product Name"] = prow.get("Product Name", "")
                            write_csv(approval_df, APPROVALS_FILE)
                        flash_success(f"Stock request {result['request_id']} submitted for approval.")
                        safe_rerun()
                    except Exception as exc:
                        action_error(exc)

    with tab2:
        approved = stock_requests[
            col(stock_requests, "Status", "").astype(str).eq("Approved")
        ] if not stock_requests.empty else pd.DataFrame()

        if approved.empty:
            st.info("No approved stock requests are waiting for warehouse release.")
        else:
            if "Approval ID" in approved.columns:
                approval_options = [
                    f"{row['Approval ID']} — {row.get('Request ID','')} — {row.get('Product Name','')}"
                    for _, row in approved.iterrows()
                ]
                chosen_approval = st.selectbox("Approved Request", approval_options)
                approval_id = chosen_approval.split(" — ", 1)[0]
                request = approved[
                    approved["Approval ID"].astype(str) == str(approval_id)
                ].iloc[0]
            else:
                request_id = select_id(approved, "Request ID", "Product Name", "Approved Request")
                request = approved[approved["Request ID"].astype(str) == str(request_id)].iloc[0]
            request_id = str(request.get("Request ID", ""))
            product_id = str(request.get("Product ID", ""))
            if product_id:
                try:
                    current_stock = calculate_product_stock(
                        read_csv(MOVEMENTS_FILE), product_id
                    )
                    st.info(
                        f"Warehouse availability: {current_stock:,.0f} units"
                    )
                except Exception:
                    pass

            st.subheader("1. Scan the approved product")
            release_camera = st.camera_input("📷 Scan the product QR before warehouse release", key=f"release_camera_{request_id}")
            release_manual = st.text_input("Or paste a QR value", placeholder="BISCUIT|PRODUCT|PROD-000001", key=f"release_manual_{request_id}")
            release_decoded, release_scan_error = decode_qr_camera(release_camera)
            release_decoded = (release_decoded or release_manual).strip()
            scanned_release_product = product_id_from_qr(release_decoded)
            release_scan_ok = False
            if release_scan_error and release_camera is not None:
                st.warning(f"Camera QR decoding is unavailable: {release_scan_error}")
            if scanned_release_product:
                if scanned_release_product == product_id:
                    release_scan_ok = True
                    st.success(f"✓ Correct product scanned: {request.get('Product Name','')} ({product_id})")
                else:
                    st.error(f"Wrong product scanned. This request is for {product_id}, but the scan returned {scanned_release_product}.")
            else:
                st.caption("The warehouse release button remains locked until the correct product QR is scanned.")

            approved_qty = st.number_input(
                "Approved Quantity to Release",
                min_value=0.01,
                max_value=float(pd.to_numeric(request.get("Quantity", 0), errors="coerce") or 0),
                value=float(pd.to_numeric(request.get("Quantity", 0), errors="coerce") or 1),
                key=f"release_qty_{request_id}",
            )
            destination = st.text_input("Destination", value="Sales / Distribution", key=f"release_dest_{request_id}")
            if st.button("Release Scanned Warehouse Stock", type="primary", disabled=not release_scan_ok, key=f"release_btn_{request_id}"):
                try:
                    from engine.warehouse_release import release_stock
                    result = release_stock(
                        APPROVALS_FILE, PRODUCTS_FILE, MOVEMENTS_FILE,
                        AUDIT_FILE, request_id, DEMO_USER,
                        approved_quantity=approved_qty,
                        destination=destination,
                        notes=f"Released after QR verification of {product_id}."
                    )
                    flash_success(
                        f"{result['quantity_released']:,.0f} units released. Remaining stock: {result['remaining_stock']:,.0f}"
                    )
                    safe_rerun()
                except Exception as exc:
                    action_error(exc)

# ============================================================
# EXPENDITURE
# ============================================================

def expenditure_page():
    page_header("Expenditure", "Manage expenditure requests, approvals and payments.")
    exp = read_csv(EXPENDITURES_FILE)

    summary = expenditure_summary(EXPENDITURES_FILE)
    c1, c2, c3 = st.columns(3)
    c1.metric("Requested", format_naira(summary.get("total_requested", 0)))
    c2.metric("Approved", format_naira(summary.get("total_approved", 0)))
    c3.metric("Pending", format_naira(summary.get("pending_amount", 0)))

    tab1, tab2 = st.tabs(["➕ New Expenditure", "💰 Payment"])

    with tab1:
        with st.form("expenditure_form"):
            requester = st.text_input("Requester", value=DEMO_USER)
            department = st.selectbox("Department", ["Administration", "Warehouse", "Sales", "Distribution", "Finance"])
            category = st.selectbox("Expense Category", [
                "Fuel", "Vehicle Maintenance", "Warehouse Expenses", "Transportation",
                "Office Expenses", "Repairs", "Utilities", "Staff-related Expenses", "Other"
            ])
            description = st.text_area("Description")
            amount = st.number_input("Amount Requested", min_value=0.01, value=10000.0, step=1000.0)
            priority = st.selectbox("Priority", ["Normal", "High", "Urgent"])
            supporting = st.text_input("Supporting Document / Reference")
            notes = st.text_area("Notes")
            submit = st.form_submit_button("Submit Expenditure", type="primary")
            if submit:
                try:
                    result = create_expenditure_request(
                        APPROVALS_FILE, EXPENDITURES_FILE, AUDIT_FILE,
                        requester, department, category, description,
                        amount, priority, supporting, notes
                    )
                    flash_success(f"Expenditure {result.get('expenditure_id')} submitted for approval.")
                    safe_rerun()
                except Exception as exc:
                    action_error(exc)

        st.dataframe(exp, use_container_width=True, hide_index=True, height=350)

    with tab2:
        unpaid = exp[
            num(col(exp, "Amount Approved", 0)) > num(col(exp, "Amount Paid", 0))
        ] if not exp.empty else pd.DataFrame()
        if unpaid.empty:
            st.info("No approved expenditure is waiting for payment.")
        else:
            eid = select_id(unpaid, "Expenditure ID", "Description", "Expenditure")
            row = unpaid[unpaid["Expenditure ID"].astype(str) == str(eid)].iloc[0]
            max_amount = float(pd.to_numeric(row.get("Amount Approved", 0), errors="coerce") or 0) - float(pd.to_numeric(row.get("Amount Paid", 0), errors="coerce") or 0)
            amount = st.number_input("Amount to Pay", min_value=0.01, max_value=max(max_amount, 0.01), value=max(max_amount, 0.01))
            method = st.selectbox("Payment Method", ["Bank Transfer", "Cash", "POS", "Cheque"])
            reference = st.text_input("Payment Reference")
            if st.button("Pay Expenditure", type="primary"):
                try:
                    result = pay_expenditure(
                        EXPENDITURES_FILE, AUDIT_FILE, eid,
                        method, reference, DEMO_USER, amount
                    )
                    flash_success(f"Expenditure payment recorded for {eid}.")
                    safe_rerun()
                except Exception as exc:
                    action_error(exc)

# ============================================================
# APPROVAL CENTER
# ============================================================

def approvals_page():
    page_header(
        "Approval Center",
        "Central management authorization for stock and expenditure requests."
    )

    approvals = read_csv(APPROVALS_FILE)

    if approvals.empty:
        st.info("No approval requests recorded.")
        return

    status_series = col(approvals, "Status", "").astype(str).str.strip()
    pending = approvals[
        status_series.str.lower().isin(["submitted", "pending approval"])
    ].copy()

    approved = approvals[
        status_series.str.lower().eq("approved")
    ].copy()

    rejected = approvals[
        status_series.str.lower().eq("rejected")
    ].copy()

    completed = approvals[
        status_series.str.lower().eq("completed")
    ].copy()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pending Approval", len(pending))
    c2.metric("Approved", len(approved))
    c3.metric("Rejected", len(rejected))
    c4.metric("Completed", len(completed))

    st.divider()
    section_header("Approval Register", "approvals.png")
    display = approvals.sort_values("Request Date", ascending=False).copy()
    if "Status" in display.columns:
        display["Status"] = display["Status"].apply(status_badge)
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        height=380
    )

    if pending.empty:
        st.success("No requests are currently waiting for management approval.")
        return

    st.divider()
    section_header("Pending Approval", "approvals.png")

    # Use Approval ID as the selection key so duplicate/legacy Request IDs
    # cannot cause the wrong row to be approved.
    if "Approval ID" in pending.columns:
        options = [
            f"{row['Approval ID']} — {row.get('Request ID','')} — {row.get('Request Type','')}"
            for _, row in pending.iterrows()
        ]
        chosen = st.selectbox("Pending Request", options)
        approval_id = chosen.split(" — ", 1)[0]
        selected_rows = pending[
            pending["Approval ID"].astype(str) == str(approval_id)
        ]
    else:
        request_id = select_id(pending, "Request ID", "Request Type", "Pending Request")
        selected_rows = pending[
            pending["Request ID"].astype(str) == str(request_id)
        ]

    if selected_rows.empty:
        st.error("The selected approval record could not be found.")
        return

    row = selected_rows.iloc[0]
    request_id = str(row.get("Request ID", ""))
    current_status = str(row.get("Status", "")).strip()

    if current_status.lower() not in ["submitted", "pending approval"]:
        st.warning(
            f"This request is no longer pending. Current status: {current_status}."
        )
        return

    st.info(
        f"Requester: {row.get('Requester','')} | "
        f"Type: {row.get('Request Type','')} | "
        f"Amount: {format_naira(row.get('Amount',0))} | "
        f"Quantity: {row.get('Quantity',0)}"
    )

    if row.get("Product Name", ""):
        st.caption(
            f"Product: {row.get('Product Name','')} "
            f"({row.get('Product ID','')})"
        )

    comment = st.text_area("Decision Comment", key=f"decision_comment_{approval_id if 'approval_id' in locals() else request_id}")

    a, b, c = st.columns(3)

    if a.button("✅ Approve", type="primary", use_container_width=True):
        try:
            # Re-read immediately before mutation to prevent stale UI state.
            latest = read_csv(APPROVALS_FILE)
            latest_rows = latest[
                latest["Approval ID"].astype(str) == str(approval_id)
            ] if "Approval ID" in latest.columns else latest[
                latest["Request ID"].astype(str) == request_id
            ]

            if latest_rows.empty:
                raise ValueError(f"Approval record {approval_id} was not found.")

            latest_status = str(latest_rows.iloc[0].get("Status", "")).strip()
            if latest_status.lower() not in ["submitted", "pending approval"]:
                raise ValueError(
                    f"Request {request_id} cannot be approved because its current status is '{latest_status}'."
                )

            if str(row.get("Request Type", "")).lower() == "expenditure":
                result = approve_expenditure(
                    APPROVALS_FILE,
                    EXPENDITURES_FILE,
                    AUDIT_FILE,
                    request_id,
                    DEMO_USER,
                    comment=comment
                )
            else:
                result = approve_request(
                    APPROVALS_FILE,
                    AUDIT_FILE,
                    request_id,
                    DEMO_USER,
                    comment
                )

            flash_success(f"Request {request_id} approved successfully.")
            safe_rerun()
        except Exception as exc:
            action_error(exc)

    if b.button("❌ Reject", use_container_width=True):
        try:
            if str(row.get("Request Type", "")).lower() == "expenditure":
                reject_expenditure(
                    APPROVALS_FILE, EXPENDITURES_FILE, AUDIT_FILE,
                    request_id, DEMO_USER, comment
                )
            else:
                reject_request(
                    APPROVALS_FILE, AUDIT_FILE, request_id, DEMO_USER, comment
                )
            flash_success(f"Request {request_id} rejected.")
            safe_rerun()
        except Exception as exc:
            action_error(exc)

    if c.button("↩️ Request Revision", use_container_width=True):
        try:
            request_revision(
                APPROVALS_FILE, AUDIT_FILE, request_id, DEMO_USER, comment
            )
            flash_success(f"Revision requested for {request_id}.")
            safe_rerun()
        except Exception as exc:
            action_error(exc)

# ============================================================
# RECORDS ARCHIVE
# ============================================================

def archive_page():
    page_header("Records Archive", "Access historical and legacy records without mixing them with current operations.")
    archive = read_csv(ARCHIVE_FILE)

    if not archive.empty:
        st.dataframe(archive, use_container_width=True, hide_index=True, height=400)
    else:
        st.info("No archived records yet.")

    with st.expander("🗄️ Archive a Demo Record"):
        with st.form("archive_form"):
            record_type = st.selectbox("Record Type", ["Historical Invoice", "Legacy Customer Record", "Imported Sale", "Historical Receipt", "Other"])
            record_number = st.text_input("Record Number")
            source_type = st.selectbox("Source Type", ["Legacy / Historical", "Imported", "Scanned Document"])
            record_date = st.date_input("Record Date")
            customer_id = st.text_input("Customer ID")
            customer_name = st.text_input("Customer Name")
            related = st.text_input("Related Transaction")
            description = st.text_area("Description")
            notes = st.text_area("Notes")
            submit = st.form_submit_button("Archive Record", type="primary")
            if submit:
                try:
                    result = archive_record(
                        ARCHIVE_FILE, AUDIT_FILE, record_type, record_number,
                        source_type, str(record_date), customer_id, customer_name,
                        related, description, DEMO_USER, "Archived", notes
                    )
                    flash_success(f"Record {result.get('record_id')} archived.")
                    safe_rerun()
                except Exception as exc:
                    action_error(exc)

# ============================================================
# DOCUMENTS
# ============================================================

def documents_page():
    page_header("Documents / Scanned Invoices", "Register and manage invoices, receipts and supporting documents.")
    docs = read_csv(DOCUMENTS_FILE)

    if not docs.empty:
        search = st.text_input("🔎 Search documents")
        view = docs.copy()
        if search:
            view = view[view.apply(lambda r: search.lower() in str(r.to_dict()).lower(), axis=1)]
        st.dataframe(view, use_container_width=True, hide_index=True, height=400)
    else:
        st.info("No documents registered.")

    with st.expander("📄 Register Document"):
        with st.form("document_form"):
            doc_type = st.selectbox("Document Type", ["Invoice", "Receipt", "Delivery Document", "Purchase Document", "Expenditure Receipt", "Other"])
            doc_number = st.text_input("Document Number")
            source = st.selectbox("Source Type", ["Scanned Document", "Digitally Generated", "Legacy / Historical", "Imported"])
            customer_id = st.text_input("Customer ID")
            customer_name = st.text_input("Customer Name")
            related = st.text_input("Related Transaction")
            transaction_type = st.selectbox("Transaction Type", ["", "Sale", "Invoice", "Payment", "Expenditure", "Delivery"])
            document_date = st.date_input("Document Date")
            amount = st.number_input("Amount", min_value=0.0, step=100.0)
            file_name = st.text_input("File Name")
            file_path = st.text_input("File Path / Placeholder")
            description = st.text_area("Description")
            submit = st.form_submit_button("Register Document", type="primary")
            if submit:
                try:
                    result = register_document(
                        DOCUMENTS_FILE, AUDIT_FILE,
                        doc_type, doc_number, source,
                        customer_id, customer_name, related,
                        transaction_type, str(document_date), amount,
                        DEMO_USER, file_name, file_path, description
                    )
                    flash_success(f"Document {result.get('document_id')} registered.")
                    safe_rerun()
                except Exception as exc:
                    action_error(exc)

# ============================================================
# REPORTS & ANALYTICS
# ============================================================

def reports_page():
    page_header("Reports & Analytics", "Management reporting powered by the reports engine.")

    try:
        k = management_kpis(
            CUSTOMERS_FILE, PRODUCTS_FILE, SALES_FILE, PAYMENTS_FILE,
            INVOICES_FILE, MOVEMENTS_FILE, EXPENDITURES_FILE
        )
    except Exception as exc:
        st.error(f"Report engine error: {exc}")
        k = {}

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sales", format_naira(k.get("total_sales", 0)))
    c2.metric("Payments", format_naira(k.get("total_received", 0)))
    c3.metric("Receivables", format_naira(k.get("outstanding_invoices", 0)))
    c4.metric("Expenditure", format_naira(k.get("total_expenditure", 0)))

    tab1, tab2, tab3, tab4 = st.tabs(["📈 Sales", "📦 Inventory", "💰 Finance", "👥 Customers"])

    with tab1:
        daily = sales_by_day(SALES_FILE)
        monthly = sales_by_month(SALES_FILE)
        if not daily.empty:
            st.subheader("Sales by Day")
            st.plotly_chart(px.line(daily, x="Date", y="Amount", markers=True), use_container_width=True)
        if not monthly.empty:
            st.subheader("Sales by Month")
            st.plotly_chart(px.bar(monthly, x="Month", y="Amount"), use_container_width=True)
        tp = top_products(SALES_FILE, 10, SALE_ITEMS_FILE)
        if not tp.empty:
            st.subheader("Top Products")
            pc = [c for c in tp.columns if c != "Amount"][0]
            st.plotly_chart(px.bar(tp, x="Amount", y=pc, orientation="h"), use_container_width=True)

    with tab2:
        sm = stock_movement_summary(MOVEMENTS_FILE)
        if not sm.empty:
            st.dataframe(sm, use_container_width=True, hide_index=True)
        else:
            st.info("No stock movement report available.")

    with tab3:
        sv = sales_vs_expenditure(SALES_FILE, EXPENDITURES_FILE)
        if not sv.empty:
            st.dataframe(sv, use_container_width=True, hide_index=True)
        else:
            st.info("No sales-vs-expenditure report available.")

    with tab4:
        cp = customer_performance(SALES_FILE, 20)
        if not cp.empty:
            st.dataframe(cp, use_container_width=True, hide_index=True)
        else:
            st.info("No customer performance data available.")

    st.divider()
    st.download_button(
        "⬇️ Export Current Sales Report",
        data=read_csv(SALES_FILE).to_csv(index=False),
        file_name="sales_report_demo.csv",
        mime="text/csv",
    )

# ============================================================
# USERS & ROLES
# ============================================================

def users_page():
    page_header("Users & Roles", "Manage system users, roles and permissions.")

    roles = pd.DataFrame({
        "Role": [
            "Administrator", "Management", "Sales Officer",
            "Warehouse Officer", "Finance Officer", "Driver / Distribution"
        ],
        "Access": [
            "Full system access",
            "Dashboard, reports, approvals, sales, inventory and finance",
            "Customers, sales, invoices and assigned transactions",
            "Inventory, stock requests and warehouse release",
            "Invoices, payments, expenditure and financial records",
            "Assigned deliveries and delivery status",
        ]
    })

    st.dataframe(roles, use_container_width=True, hide_index=True)

    st.info(
        "Production implementation will enforce these permissions through authenticated users "
        "and backend authorization. This prototype demonstrates the intended structure."
    )

# ============================================================
# SETTINGS
# ============================================================

def settings_page():
    page_header("Settings", "System configuration and prototype controls.")

    st.subheader("System")
    st.write("Application: Biscuit CRM / ERP")
    st.write("Environment: PROTOTYPE / DEMO")
    st.write("Data layer: CSV demonstration database")
    st.write("Future database: MySQL / PostgreSQL / SQL Server")

    st.subheader("Data Locations")
    st.code(str(DATA_DIR))

    if st.button("🔄 Reload Application Data"):
        st.cache_data.clear()
        safe_rerun()

# ============================================================
# ROUTING
# ============================================================

if menu == "Dashboard":
    dashboard()
elif menu == "Customers / Clients":
    customers_page()
elif menu == "Products":
    products_page()
elif menu == "Warehouse & Inventory":
    inventory_page()
elif menu == "Sales":
    sales_page()
elif menu == "Invoices":
    invoices_page()
elif menu == "Trucks / Distribution":
    distribution_page()
elif menu == "Inbound Logistics":
    inbound_logistics_page()
elif menu == "Product Scanner":
    product_scanner_page()
elif menu == "Stock Requests":
    stock_requests_page()
elif menu == "Expenditure":
    expenditure_page()
elif menu == "Approval Center":
    approvals_page()
elif menu == "Records Archive":
    archive_page()
elif menu == "Documents":
    documents_page()
elif menu == "Reports & Analytics":
    reports_page()
elif menu == "Users & Roles":
    users_page()
elif menu == "Settings":
    settings_page()

# ============================================================
# FOOTER
# ============================================================

st.divider()
st.caption(
    "🍪 Biscuit Wholesale & Distribution CRM/ERP • PROTOTYPE / DEMO • "
    "Fictional demonstration data"
)

