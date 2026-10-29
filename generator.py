"""
Synthetic E-Commerce Data Generator
Generates realistic initial (Batch 1) and incremental (Batch 2) data with SCD Type 2 changes.
"""
import random
import csv
from datetime import datetime, timedelta
from pathlib import Path
from faker import Faker

import sys
from pathlib import Path

# Add project root to sys.path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import RAW_BATCH_1_DIR, RAW_BATCH_2_DIR, logger

fake = Faker()
Faker.seed(42)
random.seed(42)

PRODUCT_CATALOG = [
    ("Electronics", "Smartphones", "Flagship Smartphone 5G", 450.00, 799.99),
    ("Electronics", "Laptops", "Ultra-thin Developer Laptop 16GB", 680.00, 1199.99),
    ("Electronics", "Audio", "Noise-Cancelling Wireless Headphones", 75.00, 149.99),
    ("Electronics", "Accessories", "Fast USB-C 65W GaN Charger", 12.00, 29.99),
    ("Electronics", "Wearables", "Fitness Tracker Smartwatch", 40.00, 89.99),
    ("Electronics", "Gaming", "Mechanical RGB Gaming Keyboard", 35.00, 79.99),
    ("Electronics", "Gaming", "Wireless Ergonomic Mouse", 18.00, 49.99),
    ("Electronics", "Monitors", "27-inch 4K IPS Display Monitor", 190.00, 349.99),
    ("Electronics", "Audio", "Bluetooth Waterproof Speaker", 22.00, 59.99),
    ("Electronics", "Storage", "1TB NVMe Portable SSD", 45.00, 99.99),
    ("Apparel", "Men", "Men's Classic Slim Fit Denim Jeans", 18.00, 49.99),
    ("Apparel", "Men", "Premium Oxford Button-Down Shirt", 15.00, 39.99),
    ("Apparel", "Women", "Breathable Athletic Yoga Leggings", 14.00, 44.99),
    ("Apparel", "Women", "Casual Floral Summer Dress", 16.00, 54.99),
    ("Apparel", "Outerwear", "All-Weather Hooded Rain Jacket", 32.00, 89.99),
    ("Apparel", "Footwear", "Lightweight Road Running Shoes", 30.00, 84.99),
    ("Apparel", "Footwear", "Classic White Leather Sneakers", 28.00, 74.99),
    ("Apparel", "Accessories", "Genuine Leather RFID Wallet", 10.00, 29.99),
    ("Home & Kitchen", "Cookware", "Cast Iron Pre-Seasoned Skillet", 16.00, 39.99),
    ("Home & Kitchen", "Appliances", "Digital Air Fryer 5.8 Qt", 42.00, 99.99),
    ("Home & Kitchen", "Coffee", "Precision Pour-Over Coffee Maker", 12.00, 34.99),
    ("Home & Kitchen", "Bedding", "100% Organic Bamboo Sheet Set", 25.00, 69.99),
    ("Home & Kitchen", "Cleaning", "Cordless Stick Vacuum Cleaner", 65.00, 159.99),
    ("Home & Kitchen", "Dining", "16-Piece Ceramic Dinnerware Set", 28.00, 64.99),
    ("Home & Kitchen", "Lighting", "Dimmable LED Smart Desk Lamp", 14.00, 39.99),
    ("Books", "Technology", "Designing Data-Intensive Applications", 18.00, 42.99),
    ("Books", "Technology", "The Data Warehouse Toolkit", 22.00, 49.99),
    ("Books", "Technology", "Python for Data Analysis", 16.00, 39.99),
    ("Books", "Business", "Atomic Habits: Building Systems", 8.00, 19.99),
    ("Books", "Business", "Zero to One: Notes on Startups", 7.50, 18.99),
    ("Health & Beauty", "Skincare", "Hydrating Hyaluronic Acid Serum", 8.00, 24.99),
    ("Health & Beauty", "Skincare", "Broad Spectrum SPF 50 Sunscreen", 6.50, 19.99),
    ("Health & Beauty", "Personal Care", "Sonic Electric Toothbrush", 20.00, 49.99),
    ("Health & Beauty", "Wellness", "Organic Ashwagandha Supplements", 7.00, 22.99),
    ("Health & Beauty", "Hair Care", "Moroccan Argan Hair Oil", 9.00, 26.99)
]

PAYMENT_METHODS = ["CREDIT_CARD", "PAYPAL", "DEBIT_CARD", "UPI", "NET_BANKING"]
ORDER_STATUSES = ["DELIVERED", "SHIPPED", "PROCESSING", "PENDING", "CANCELLED", "RETURNED"]
ORDER_STATUS_WEIGHTS = [0.65, 0.12, 0.08, 0.05, 0.05, 0.05]
RETURN_REASONS = ["DEFECTIVE", "WRONG_ITEM", "NOT_AS_DESCRIBED", "CHANGED_MIND"]
RETURN_STATUSES = ["APPROVED", "PROCESSED", "REJECTED"]


def generate_initial_dataset(num_customers=500, num_orders=1500, output_dir=RAW_BATCH_1_DIR):
    """Generates the initial Batch 1 baseline data."""
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Generating Batch 1 initial dataset in {output_dir}...")

    base_start_date = datetime(2025, 1, 1, 9, 0, 0)
    base_end_date = datetime(2025, 6, 30, 23, 59, 59)

    # 1. Customers
    customers = []
    for i in range(1, num_customers + 1):
        cust_created = base_start_date + timedelta(
            seconds=random.randint(0, int((datetime(2025, 4, 1) - base_start_date).total_seconds()))
        )
        customers.append({
            "customer_id": f"CUST_{i:04d}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email().lower(),
            "phone": fake.numerify("##########"),
            "street": fake.street_address().replace(",", " "),
            "city": fake.city(),
            "state": fake.state(),
            "postal_code": fake.postcode(),
            "country": "USA",
            "created_at": cust_created.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": cust_created.strftime("%Y-%m-%d %H:%M:%S")
        })

    # 2. Products
    products = []
    prod_id = 1
    for cat, subcat, name, cost, retail in PRODUCT_CATALOG:
        products.append({
            "product_id": f"PROD_{prod_id:03d}",
            "sku": f"SKU-{cat[:3].upper()}-{prod_id:03d}",
            "name": name,
            "category": cat,
            "subcategory": subcat,
            "cost_price": round(cost, 2),
            "retail_price": round(retail, 2),
            "stock_quantity": random.randint(50, 500),
            "supplier_id": f"SUPP_{random.randint(1, 10):02d}",
            "created_at": "2025-01-01 00:00:00",
            "updated_at": "2025-01-01 00:00:00"
        })
        prod_id += 1

    # 3. Orders & Order Items & Payments & Returns
    orders = []
    order_items = []
    payments = []
    returns = []

    item_id_counter = 1
    payment_id_counter = 1
    return_id_counter = 1

    for order_idx in range(1, num_orders + 1):
        customer = random.choice(customers)
        cust_created_dt = datetime.strptime(customer["created_at"], "%Y-%m-%d %H:%M:%S")
        
        # Order date must be on or after customer creation date
        earliest_order = max(cust_created_dt, base_start_date)
        time_diff = int((base_end_date - earliest_order).total_seconds())
        if time_diff <= 0:
            order_dt = earliest_order + timedelta(hours=random.randint(1, 24))
        else:
            order_dt = earliest_order + timedelta(seconds=random.randint(0, time_diff))

        status = random.choices(ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS)[0]
        shipping_fee = round(random.choice([0.00, 4.99, 9.99, 14.99]), 2)
        
        # Generate 1 to 4 items per order
        num_items = random.randint(1, 4)
        order_gross = 0.0
        order_discount = 0.0
        order_items_for_this_order = []

        chosen_prods = random.sample(products, min(num_items, len(products)))
        for prod in chosen_prods:
            qty = random.randint(1, 3)
            unit_price = prod["retail_price"]
            disc_rate = random.choice([0.0, 0.0, 0.05, 0.10, 0.15])
            disc_amount = round(qty * unit_price * disc_rate, 2)
            line_total = round((qty * unit_price) - disc_amount, 2)

            order_gross += (qty * unit_price)
            order_discount += disc_amount

            item_dict = {
                "order_item_id": f"ITEM_{item_id_counter:05d}",
                "order_id": f"ORD_{order_idx:05d}",
                "product_id": prod["product_id"],
                "quantity": qty,
                "unit_price": unit_price,
                "discount_amount": disc_amount,
                "line_total": line_total,
                "created_at": order_dt.strftime("%Y-%m-%d %H:%M:%S")
            }
            order_items.append(item_dict)
            order_items_for_this_order.append(item_dict)
            item_id_counter += 1

        tax_amount = round((order_gross - order_discount) * 0.08, 2)  # 8% tax
        total_amount = round(order_gross - order_discount + tax_amount + shipping_fee, 2)

        order_dict = {
            "order_id": f"ORD_{order_idx:05d}",
            "customer_id": customer["customer_id"],
            "order_date": order_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "shipping_fee": shipping_fee,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "shipping_address": f"{customer['street']}, {customer['city']}, {customer['state']} {customer['postal_code']}",
            "created_at": order_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": (order_dt + timedelta(days=random.randint(0, 5))).strftime("%Y-%m-%d %H:%M:%S")
        }
        orders.append(order_dict)

        # Payment record
        pay_status = "SUCCESS" if status not in ["CANCELLED"] else random.choice(["FAILED", "REFUNDED"])
        pay_dt = order_dt + timedelta(minutes=random.randint(1, 15))
        payments.append({
            "payment_id": f"PAY_{payment_id_counter:05d}",
            "order_id": f"ORD_{order_idx:05d}",
            "payment_date": pay_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "payment_method": random.choice(PAYMENT_METHODS),
            "payment_status": pay_status,
            "amount_paid": total_amount if pay_status == "SUCCESS" else 0.00,
            "transaction_reference": f"TXN_{fake.hexify(text='^^^^^^^^^^^^').upper()}"
        })
        payment_id_counter += 1

        # Return record if order was DELIVERED or RETURNED
        if status in ["DELIVERED", "RETURNED"] and random.random() < 0.08:
            returned_item = random.choice(order_items_for_this_order)
            return_dt = order_dt + timedelta(days=random.randint(2, 14))
            returns.append({
                "return_id": f"RET_{return_id_counter:04d}",
                "order_id": f"ORD_{order_idx:05d}",
                "order_item_id": returned_item["order_item_id"],
                "return_date": return_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "return_reason": random.choice(RETURN_REASONS),
                "refund_amount": returned_item["line_total"],
                "return_status": random.choice(RETURN_STATUSES)
            })
            return_id_counter += 1

    # Write CSV files
    _write_csv(output_dir / "customers.csv", customers)
    _write_csv(output_dir / "products.csv", products)
    _write_csv(output_dir / "orders.csv", orders)
    _write_csv(output_dir / "order_items.csv", order_items)
    _write_csv(output_dir / "payments.csv", payments)
    _write_csv(output_dir / "returns.csv", returns)

    logger.info(f"Batch 1 generated successfully: {len(customers)} customers, {len(products)} products, "
                f"{len(orders)} orders, {len(order_items)} items, {len(payments)} payments, {len(returns)} returns.")
    return {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
        "payments": payments,
        "returns": returns
    }


def generate_incremental_dataset(batch_1_data, output_dir=RAW_BATCH_2_DIR):
    """
    Generates the incremental Batch 2 dataset.
    Features:
    - New customers
    - Existing customers with address/phone changes (SCD Type 2 triggers!)
    - New products and updated product prices
    - New orders placed in July - August 2025
    - Existing orders with status updates (e.g. PROCESSING -> DELIVERED)
    - Additional order items, payments, returns
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Generating Batch 2 incremental dataset in {output_dir}...")

    inc_start_date = datetime(2025, 7, 1, 0, 0, 0)
    inc_end_date = datetime(2025, 8, 31, 23, 59, 59)

    existing_customers = batch_1_data["customers"]
    existing_products = batch_1_data["products"]
    existing_orders = batch_1_data["orders"]

    # 1. Customers:
    # A) 50 existing customers update their addresses/phones (SCD Type 2 test cases!)
    scd2_customers_updated = []
    scd_candidates = random.sample(existing_customers, 50)
    for cust in scd_candidates:
        update_time = inc_start_date + timedelta(days=random.randint(1, 15))
        updated_cust = cust.copy()
        updated_cust["street"] = fake.street_address().replace(",", " ")
        updated_cust["city"] = fake.city()
        updated_cust["state"] = fake.state()
        updated_cust["postal_code"] = fake.postcode()
        updated_cust["phone"] = fake.numerify("##########")
        updated_cust["updated_at"] = update_time.strftime("%Y-%m-%d %H:%M:%S")
        scd2_customers_updated.append(updated_cust)

    # B) 100 brand new customers
    new_customers = []
    last_cust_num = len(existing_customers)
    for i in range(1, 101):
        cust_id_num = last_cust_num + i
        created_dt = inc_start_date + timedelta(days=random.randint(0, 30))
        new_customers.append({
            "customer_id": f"CUST_{cust_id_num:04d}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email().lower(),
            "phone": fake.numerify("##########"),
            "street": fake.street_address().replace(",", " "),
            "city": fake.city(),
            "state": fake.state(),
            "postal_code": fake.postcode(),
            "country": "USA",
            "created_at": created_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": created_dt.strftime("%Y-%m-%d %H:%M:%S")
        })

    customers_delta = scd2_customers_updated + new_customers

    # 2. Products Delta: 5 new products, 10 updated prices
    products_delta = []
    # 5 new products
    last_prod_num = len(existing_products)
    new_prod_specs = [
        ("Electronics", "Gaming", "VR Headset 128GB All-In-One", 220.00, 399.99),
        ("Home & Kitchen", "Appliances", "Espresso Coffee Machine Deluxe", 120.00, 249.99),
        ("Apparel", "Outerwear", "Ultra-Light Packable Down Vest", 25.00, 69.99),
        ("Books", "Technology", "Building Real-Time Data Pipelines", 20.00, 44.99),
        ("Health & Beauty", "Skincare", "Vitamin C Brightening Facial Oil", 11.00, 32.99)
    ]
    for idx, (cat, subcat, name, cost, retail) in enumerate(new_prod_specs, 1):
        products_delta.append({
            "product_id": f"PROD_{last_prod_num + idx:03d}",
            "sku": f"SKU-{cat[:3].upper()}-{last_prod_num + idx:03d}",
            "name": name,
            "category": cat,
            "subcategory": subcat,
            "cost_price": round(cost, 2),
            "retail_price": round(retail, 2),
            "stock_quantity": random.randint(40, 300),
            "supplier_id": f"SUPP_{random.randint(1, 10):02d}",
            "created_at": "2025-07-01 00:00:00",
            "updated_at": "2025-07-01 00:00:00"
        })

    # 10 updated products (price changes)
    price_change_prods = random.sample(existing_products, 10)
    for prod in price_change_prods:
        p_upd = prod.copy()
        new_retail = round(float(p_upd["retail_price"]) * random.choice([1.05, 1.10, 0.90]), 2)
        p_upd["retail_price"] = new_retail
        p_upd["updated_at"] = "2025-07-05 12:00:00"
        products_delta.append(p_upd)

    # 3. Orders Delta:
    # A) 40 existing orders transition status (e.g. PROCESSING -> DELIVERED)
    orders_delta = []
    eligible_orders = [o for o in existing_orders if o["status"] in ["PROCESSING", "SHIPPED", "PENDING"]]
    for o in eligible_orders[:40]:
        o_upd = o.copy()
        o_upd["status"] = "DELIVERED"
        o_upd["updated_at"] = "2025-07-02 10:00:00"
        orders_delta.append(o_upd)

    # B) 400 new orders in July - August 2025
    all_active_customers = existing_customers + new_customers
    all_active_products = existing_products + products_delta[:5]

    last_order_num = len(existing_orders)
    last_item_num = len(batch_1_data["order_items"])
    last_pay_num = len(batch_1_data["payments"])
    last_ret_num = len(batch_1_data["returns"])

    order_items_delta = []
    payments_delta = []
    returns_delta = []

    for idx in range(1, 401):
        order_num = last_order_num + idx
        customer = random.choice(all_active_customers)
        order_dt = inc_start_date + timedelta(seconds=random.randint(0, int((inc_end_date - inc_start_date).total_seconds())))

        status = random.choices(ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS)[0]
        shipping_fee = round(random.choice([0.00, 4.99, 9.99]), 2)

        num_items = random.randint(1, 3)
        order_gross = 0.0
        order_discount = 0.0
        items_for_this_order = []

        chosen_prods = random.sample(all_active_products, min(num_items, len(all_active_products)))
        for prod in chosen_prods:
            last_item_num += 1
            qty = random.randint(1, 3)
            unit_price = float(prod["retail_price"])
            disc_rate = random.choice([0.0, 0.05, 0.10])
            disc_amount = round(qty * unit_price * disc_rate, 2)
            line_total = round((qty * unit_price) - disc_amount, 2)

            order_gross += (qty * unit_price)
            order_discount += disc_amount

            item_dict = {
                "order_item_id": f"ITEM_{last_item_num:05d}",
                "order_id": f"ORD_{order_num:05d}",
                "product_id": prod["product_id"],
                "quantity": qty,
                "unit_price": unit_price,
                "discount_amount": disc_amount,
                "line_total": line_total,
                "created_at": order_dt.strftime("%Y-%m-%d %H:%M:%S")
            }
            order_items_delta.append(item_dict)
            items_for_this_order.append(item_dict)

        tax_amount = round((order_gross - order_discount) * 0.08, 2)
        total_amount = round(order_gross - order_discount + tax_amount + shipping_fee, 2)

        order_dict = {
            "order_id": f"ORD_{order_num:05d}",
            "customer_id": customer["customer_id"],
            "order_date": order_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "shipping_fee": shipping_fee,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "shipping_address": f"{customer['street']}, {customer['city']}, {customer['state']} {customer['postal_code']}",
            "created_at": order_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": order_dt.strftime("%Y-%m-%d %H:%M:%S")
        }
        orders_delta.append(order_dict)

        # Payment
        last_pay_num += 1
        pay_status = "SUCCESS" if status not in ["CANCELLED"] else "FAILED"
        payments_delta.append({
            "payment_id": f"PAY_{last_pay_num:05d}",
            "order_id": f"ORD_{order_num:05d}",
            "payment_date": order_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "payment_method": random.choice(PAYMENT_METHODS),
            "payment_status": pay_status,
            "amount_paid": total_amount if pay_status == "SUCCESS" else 0.00,
            "transaction_reference": f"TXN_{fake.hexify(text='^^^^^^^^^^^^').upper()}"
        })

        # Return
        if status in ["DELIVERED", "RETURNED"] and random.random() < 0.09:
            last_ret_num += 1
            ret_item = random.choice(items_for_this_order)
            returns_delta.append({
                "return_id": f"RET_{last_ret_num:04d}",
                "order_id": f"ORD_{order_num:05d}",
                "order_item_id": ret_item["order_item_id"],
                "return_date": (order_dt + timedelta(days=random.randint(3, 10))).strftime("%Y-%m-%d %H:%M:%S"),
                "return_reason": random.choice(RETURN_REASONS),
                "refund_amount": ret_item["line_total"],
                "return_status": random.choice(RETURN_STATUSES)
            })

    # Write Batch 2 files
    _write_csv(output_dir / "customers_delta.csv", customers_delta)
    _write_csv(output_dir / "products_delta.csv", products_delta)
    _write_csv(output_dir / "orders_delta.csv", orders_delta)
    _write_csv(output_dir / "order_items_delta.csv", order_items_delta)
    _write_csv(output_dir / "payments_delta.csv", payments_delta)
    _write_csv(output_dir / "returns_delta.csv", returns_delta)

    logger.info(f"Batch 2 generated successfully: {len(customers_delta)} customer updates/inserts, "
                f"{len(products_delta)} product updates/inserts, {len(orders_delta)} orders, "
                f"{len(order_items_delta)} items, {len(payments_delta)} payments, {len(returns_delta)} returns.")


def _write_csv(file_path: Path, data: list):
    """Helper to write a list of dictionaries to CSV."""
    if not data:
        return
    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


def generate_all_datasets():
    """Generates both initial and incremental batches."""
    batch_1 = generate_initial_dataset(num_customers=500, num_orders=1500)
    generate_incremental_dataset(batch_1)
    logger.info("All datasets generated successfully!")


if __name__ == "__main__":
    generate_all_datasets()
