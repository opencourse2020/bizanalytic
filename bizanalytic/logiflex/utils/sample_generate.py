import pandas as pd
from datetime import datetime, timedelta
import random

# Parameters
num_rows = 200
start_date = datetime(2025, 7, 1)

# Sample data pools
cities = ["Dallas, TX", "Houston, TX", "Austin, TX", "San Antonio, TX", "Tulsa, OK", "Oklahoma City, OK"]
drivers = ["John Doe", "Mike Lee", "Sara Kim", "Alex Ray", "Emma Stone", "Chris Park"]
carriers = ["ABC Carriers", "XYZ Freight", "DEF Logistics", "GHI Transport"]
statuses = ["Delivered", "Delayed", "In-Transit"]

# Generate data
data = []
for i in range(num_rows):
    shipment_id = f"SHP{str(i + 1).zfill(4)}"
    date = (start_date + timedelta(days=i % 30)).strftime("%Y-%m-%d")
    origin = random.choice(cities)
    destination = random.choice([c for c in cities if c != origin])
    distance = random.randint(200, 800)
    fuel_cost = round(distance * random.uniform(0.35, 0.45), 2)
    driver = random.choice(drivers)
    carrier = random.choice(carriers)
    load_weight = random.randint(15000, 25000)
    status = random.choice(statuses)
    delivery_time = round(distance / random.uniform(40, 55), 1)
    freight_cost = round(distance * random.uniform(1.8, 2.2), 2)

    data.append([shipment_id, date, origin, destination, distance, fuel_cost, driver, carrier, load_weight, status,
                 delivery_time, freight_cost])

# Create DataFrame and save
columns = ["ShipmentID", "Date", "OriginCity", "DestinationCity", "Distance_Miles", "FuelCost_USD", "DriverName",
           "CarrierName", "LoadWeight_lbs", "DeliveryStatus", "DeliveryTime_hrs", "FreightCost_USD"]
df = pd.DataFrame(data, columns=columns)
df.to_csv("freight_routes_sample_200.csv", index=False)
print("CSV file generated: freight_routes_sample_200.csv")
