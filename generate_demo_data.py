import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# BISCUIT CRM / ERP
# DEMO DATA GENERATOR
# ============================================================

random.seed(2026)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(exist_ok=True)

# ============================================================
# CUSTOMER DATA
# ============================================================

first_names = [
    "Muhammad", "Abubakar", "Ibrahim", "Musa", "Ahmed",
    "Usman", "Sani", "Yusuf", "Abdullahi", "Hassan",
    "Hussaini", "Umar", "Aliyu", "Mustapha", "Bello",
    "Aisha", "Fatima", "Zainab", "Maryam", "Hauwa",
    "Khadija", "Asma'u", "Safiya", "Rukayya", "Hadiza"
]

last_names = [
    "Abdullahi", "Musa", "Bello", "Sani", "Ibrahim",
    "Umar", "Mohammed", "Yusuf", "Hassan", "Garba",
    "Usman", "Shehu", "Aliyu", "Danjuma", "Lawal",
    "Abubakar", "Ahmad", "Suleiman", "Tanko", "Kabiru"
]

business_prefixes = [
    "Northern Star",
    "Prime Choice",
    "Golden Basket",
    "Royal Foods",
    "Central Market",
    "Trusted Choice",
    "Sunrise",
    "Diamond",
    "Excellent",
    "Premium",
    "Unity",
    "Evergreen",
    "Victory",
    "Standard",
    "Success"
]

business_suffixes = [
    "Wholesale Centre",
    "Trading Enterprise",
    "Distribution Hub",
    "General Suppliers",
    "Foods & Beverages",
    "Wholesale Depot",
    "Food Distributors",
    "Trading Company",
    "Wholesale Stores",
    "Distribution Centre"
]

customer_types = [
    "Wholesale",
    "Distributor",
    "Retailer"
]

credit_statuses = [
    "Good",
    "Good",
    "Good",
    "Review",
    "Restricted"
]

account_statuses = [
    "Active",
    "Active",
    "Active",
    "Active",
    "Inactive"
]

customers = []

for i in range(1, 526):

    first = random.choice(first_names)
    last = random.choice(last_names)

    customer_name = f"{first} {last}"

    business_name = (
        f"{random.choice(business_prefixes)} "
        f"{random.choice(business_suffixes)}"
    )

    customer_type = random.choice(customer_types)

    total_purchases = random.randint(
        250_000,
        8_500_000
    )

    if random.random() < 0.55:
        outstanding = 0
    else:
        outstanding = random.randint(
            20_000,
            min(750_000, total_purchases)
        )

    last_purchase = (
        datetime.now()
        - timedelta(
            days=random.randint(1, 60)
        )
    ).strftime("%d %b %Y")

    customers.append({
        "Customer ID":
            f"CUST-{i:06d}",

        "Customer Name":
            customer_name,

        "Business Name":
            business_name,

        "Phone":
            f"080{random.randint(10000000, 99999999)}",

        "Email":
            f"customer{i}@demo-biscuit.com",

        "Address":
            f"Demo Business District, "
            f"Area {random.randint(1, 25)}",

        "Customer Type":
            customer_type,

        "Registration Date":
            (
                datetime.now()
                - timedelta(
                    days=random.randint(
                        30,
                        1000
                    )
                )
            ).strftime("%Y-%m-%d"),

        "Account Status":
            random.choice(account_statuses),

        "Credit Status":
            random.choice(credit_statuses),

        "Total Purchases":
            total_purchases,

        "Outstanding Balance":
            outstanding,

        "Last Purchase":
            last_purchase
    })


customers_df = pd.DataFrame(customers)

customers_df.to_csv(
    DATA_DIR / "customers.csv",
    index=False
)

print(
    f"✓ Created {len(customers_df)} customers"
)


# ============================================================
# PRODUCT DATA
# ============================================================

brands = [
    "Golden Bite",
    "Crispy Crown",
    "Royal Treat",
    "Sweet Valley",
    "Happy Crunch",
    "Premium Choice",
    "Biscuit House",
    "Daily Delight",
    "Crunchy Gold",
    "Family Treat"
]

categories = [
    "Cream Biscuits",
    "Chocolate Biscuits",
    "Plain Biscuits",
    "Wafer Biscuits",
    "Crackers",
    "Sandwich Biscuits",
    "Kids Biscuits",
    "Assorted Biscuits"
]

product_names = [
    "Classic Cream",
    "Chocolate Delight",
    "Golden Crunch",
    "Vanilla Cream",
    "Milk Crunch",
    "Cocoa Sandwich",
    "Honey Crunch",
    "Rich Chocolate",
    "Butter Delight",
    "Family Pack",
    "Strawberry Cream",
    "Coconut Crunch",
    "Premium Wafer",
    "Caramel Cream",
    "Classic Crackers"
]

descriptions = [
    "Crispy golden biscuits with a smooth cream filling, designed for everyday retail and wholesale distribution.",
    
    "Premium crunchy biscuits with a rich chocolate flavour and satisfying texture, suitable for family consumption.",
    
    "Light and crispy biscuits carefully produced for convenient retail display and high-volume distribution.",
    
    "Delicious vanilla-flavoured cream biscuits combining a crunchy outer texture with a smooth centre.",
    
    "Rich chocolate biscuits with a balanced sweetness and crisp texture, ideal for supermarkets and wholesale outlets.",
    
    "Classic family-friendly biscuits packaged for convenient storage, transportation and retail distribution.",
    
    "Crunchy snack biscuits offering a satisfying bite and distinctive flavour, suitable for everyday consumption.",
    
    "Premium-quality wafer biscuits featuring delicate crispy layers and smooth flavoured cream.",
    
    "Golden baked biscuits with a rich buttery flavour, suitable for retailers, distributors and wholesale customers.",
    
    "Assorted biscuit selection combining popular flavours in a convenient commercial pack."
]

unit_types = [
    "Carton",
    "Box",
    "Pack"
]

products = []

for i in range(1, 526):

    brand = random.choice(brands)
    category = random.choice(categories)
    product_name = random.choice(product_names)

    pack_size = random.choice([
        "12 x 100g",
        "24 x 50g",
        "24 x 75g",
        "12 x 150g",
        "48 x 25g",
        "20 x 100g",
        "10 x 200g"
    ])

    cost_price = random.randint(
        2500,
        15000
    )

    selling_price = round(
        cost_price * random.uniform(
            1.15,
            1.40
        ),
        -2
    )

    reorder_level = random.randint(
        50,
        300
    )

    current_stock = random.randint(
        20,
        1500
    )

    products.append({
        "Product ID":
            f"PROD-{i:06d}",

        "Product Name":
            product_name,

        "Brand":
            brand,

        "Category":
            category,

        "Description":
            random.choice(descriptions),

        "Unit Type":
            random.choice(unit_types),

        "Pack Size":
            pack_size,

        "Cost Price":
            cost_price,

        "Selling Price":
            selling_price,

        "Reorder Level":
            reorder_level,

        "Current Stock":
            current_stock,

        "Product Status":
            "Active"
            if random.random() > 0.08
            else "Inactive"
    })


products_df = pd.DataFrame(products)

products_df.to_csv(
    DATA_DIR / "products.csv",
    index=False
)

print(
    f"✓ Created {len(products_df)} products"
)

print()
print("============================================")
print("DEMO DATA GENERATION COMPLETED")
print("============================================")
print(f"Data location: {DATA_DIR}")
print("Customers : 525")
print("Products  : 525")
print("============================================")