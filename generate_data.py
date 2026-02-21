"""
Generate a realistic inventory dataset based on retail patterns
This simulates real-world inventory data with proper distributions
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)

# Product categories with realistic distributions
categories = {
    'Electronics': ['Laptop', 'Monitor', 'Keyboard', 'Mouse', 'Webcam', 'Headphones', 
                    'USB Cable', 'HDMI Cable', 'Power Bank', 'Speaker'],
    'Office Supplies': ['Printer Paper', 'Pens', 'Notebooks', 'Stapler', 'Folders',
                        'Markers', 'Sticky Notes', 'Tape', 'Scissors', 'Binders'],
    'Furniture': ['Desk', 'Chair', 'Filing Cabinet', 'Bookshelf', 'Lamp',
                  'Monitor Stand', 'Desk Organizer', 'Whiteboard', 'Coat Rack', 'Table'],
    'Cleaning': ['Disinfectant', 'Paper Towels', 'Hand Soap', 'Sanitizer', 'Trash Bags',
                 'Wipes', 'Air Freshener', 'Mop', 'Broom', 'Cleaning Spray'],
    'Kitchen': ['Coffee Maker', 'Microwave', 'Water Cooler', 'Plates', 'Cups',
                'Utensils', 'Coffee Pods', 'Tea Bags', 'Napkins', 'Trash Cans']
}

warehouses = ['Warehouse North', 'Warehouse South', 'Warehouse East']

data = []
product_id = 1

for category, products in categories.items():
    for product in products:
        for warehouse in warehouses:
            # Realistic stock patterns
            if category == 'Electronics':
                current_stock = np.random.randint(5, 150)
                min_stock = np.random.randint(10, 30)
            elif category == 'Office Supplies':
                current_stock = np.random.randint(50, 500)
                min_stock = np.random.randint(50, 100)
            elif category == 'Furniture':
                current_stock = np.random.randint(2, 50)
                min_stock = np.random.randint(3, 15)
            elif category == 'Cleaning':
                current_stock = np.random.randint(20, 300)
                min_stock = np.random.randint(30, 80)
            else:  # Kitchen
                current_stock = np.random.randint(10, 100)
                min_stock = np.random.randint(15, 40)
            
            # Some items should be low stock
            if np.random.random() < 0.15:
                current_stock = np.random.randint(0, min_stock)
            
            # Some items should be dead stock (no movement)
            if np.random.random() < 0.20:
                days_ago = np.random.randint(35, 120)
            else:
                days_ago = np.random.randint(1, 30)
            
            last_movement = datetime.now() - timedelta(days=days_ago)
            
            data.append({
                'product_id': f'P{product_id:04d}',
                'product_name': product,
                'category': category,
                'current_stock': current_stock,
                'min_stock_level': min_stock,
                'last_movement_date': last_movement.strftime('%Y-%m-%d'),
                'warehouse_name': warehouse
            })
            product_id += 1

df = pd.DataFrame(data)
df.to_csv('inventory.csv', index=False)
print(f"✅ Generated {len(df)} inventory records")
print(f"   Categories: {df['category'].nunique()}")
print(f"   Warehouses: {df['warehouse_name'].nunique()}")
print(f"   Products: {df['product_name'].nunique()}")
print(f"\n📊 Stock Analysis:")
print(f"   Low stock items: {len(df[df['current_stock'] < df['min_stock_level']])}")
print(f"   Dead stock (30+ days): {len(df[pd.to_datetime(df['last_movement_date']) < (datetime.now() - timedelta(days=30))])}")
print(f"   Overstock (>5x min): {len(df[df['current_stock'] > df['min_stock_level'] * 5])}")
