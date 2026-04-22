import pandas as pd
from sqlalchemy import create_engine
import random
from datetime import datetime, timedelta

print("🔌 Booting up Power Choice Supply Chain Simulation...")

# 1. Connect to your Docker MySQL Database
engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/retail")

# 2. Define the Power Choice SKUs with Deep Supply Chain Metrics
products = [
    {
        "Product_ID": "WIRE-22AWG", 
        "Category": "Wire & Cabling", 
        "Unit_Cost": 4.50,          # Cost to manufacture/buy
        "Base_Price": 12.50,        # Selling price
        "Lead_Time_Days": 14,       # Takes 2 weeks to arrive from supplier
        "Safety_Stock": 1500,       # Absolute minimum allowed before production stops
        "Starting_Stock": 8000,     # Max warehouse capacity
        "Daily_Demand": (50, 150)   # Realistic random daily usage range
    },
    {
        "Product_ID": "WIRE-18AWG", 
        "Category": "Wire & Cabling", 
        "Unit_Cost": 6.00, 
        "Base_Price": 18.00, 
        "Lead_Time_Days": 14, 
        "Safety_Stock": 1000, 
        "Starting_Stock": 5000, 
        "Daily_Demand": (30, 100)
    },
    {
        "Product_ID": "CRIMP-4MM", 
        "Category": "Terminals & Connectors", 
        "Unit_Cost": 0.15, 
        "Base_Price": 0.45, 
        "Lead_Time_Days": 7, 
        "Safety_Stock": 5000, 
        "Starting_Stock": 20000, 
        "Daily_Demand": (200, 600)
    },
    {
        "Product_ID": "CONN-SPLICE", 
        "Category": "Terminals & Connectors", 
        "Unit_Cost": 0.40, 
        "Base_Price": 1.20, 
        "Lead_Time_Days": 10, 
        "Safety_Stock": 3000, 
        "Starting_Stock": 10000, 
        "Daily_Demand": (100, 400)
    },
    {
        "Product_ID": "PEI-RESIN-KG", 
        "Category": "Plastics & Resins", 
        "Unit_Cost": 20.00, 
        "Base_Price": 45.00, 
        "Lead_Time_Days": 21, 
        "Safety_Stock": 500, 
        "Starting_Stock": 3000, 
        "Daily_Demand": (10, 40)
    },
    {
        "Product_ID": "PEEK-RESIN-KG", 
        "Category": "Plastics & Resins", 
        "Unit_Cost": 45.00, 
        "Base_Price": 85.00, 
        "Lead_Time_Days": 30, 
        "Safety_Stock": 200, 
        "Starting_Stock": 1500, 
        "Daily_Demand": (5, 20)
    }
]

store_id = "BM-01"

# 3. Generate exactly 120 days (Jan 1, 2026 to Apr 30, 2026)
start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 4, 30)

data = []

# Dictionaries to track running inventory and simulated purchase orders
current_inventory = {p["Product_ID"]: p["Starting_Stock"] for p in products}
scheduled_deliveries = {p["Product_ID"]: [] for p in products} 

for single_date in pd.date_range(start_date, end_date):
    for p in products:
        pid = p["Product_ID"]
        
        # --- A. Process Incoming Shipments (Lead Time complete) ---
        arrived_today = [d['qty'] for d in scheduled_deliveries[pid] if d['date'].date() == single_date.date()]
        if arrived_today:
            current_inventory[pid] += sum(arrived_today)
            
        # Clear out arrived shipments from the queue
        scheduled_deliveries[pid] = [d for d in scheduled_deliveries[pid] if d['date'].date() != single_date.date()]

        # --- B. Daily Production Demand (Sales/Usage) ---
        units_sold = random.randint(p["Daily_Demand"][0], p["Daily_Demand"][1])
        units_sold = min(units_sold, current_inventory[pid]) # Cannot sell what we don't have
        current_inventory[pid] -= units_sold
        
        # --- C. Intelligent Restock Trigger (Reorder Point Math) ---
        # ROP = Safety Stock + (Average Daily Demand * Lead Time)
        avg_daily_demand = sum(p["Daily_Demand"]) / 2
        reorder_point = p["Safety_Stock"] + (avg_daily_demand * p["Lead_Time_Days"])
        
        # Are we expecting any deliveries?
        pending_qty = sum(d['qty'] for d in scheduled_deliveries[pid])
        
        # If our current stock + incoming stock is below the ROP, trigger an order!
        if (current_inventory[pid] + pending_qty) < reorder_point:
            # Order enough to get back to warehouse capacity
            order_qty = p["Starting_Stock"] - current_inventory[pid]
            delivery_date = single_date + timedelta(days=p["Lead_Time_Days"])
            scheduled_deliveries[pid].append({'date': delivery_date, 'qty': order_qty})

        # --- D. Occasional Bulk Discounts ---
        discount = random.choice([0, 0, 0, 0, 5, 10]) 

        # --- E. Record the Day's Data ---
        data.append({
            "Date": single_date.strftime("%Y-%m-%d"),
            "Product_ID": pid,
            "Category": p["Category"],
            "Store_ID": store_id,
            "Unit_Cost": p["Unit_Cost"],
            "Price": p["Base_Price"],
            "Discount": discount,
            "Units_Sold": units_sold,
            "Inventory_Level": current_inventory[pid],
            "Safety_Stock": p["Safety_Stock"],
            "Lead_Time_Days": p["Lead_Time_Days"]
        })

# 4. Convert to DataFrame and push to MySQL
df = pd.DataFrame(data)

# This will drop the old table and replace it with our new simulation
df.to_sql("inventory", con=engine, if_exists="replace", index=False)

print(f"✅ Successfully seeded {len(df)} rows of intelligent Supply Chain data into MySQL!")
print(f"🗓️ Date Range: {start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}")