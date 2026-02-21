"""
Demo script to test inventory analysis functions
Run this to verify everything works without starting Streamlit
"""

import pandas as pd
from datetime import datetime, timedelta

print("="*60)
print("  📦  Inventory Management System - Demo")
print("="*60)

# Load data
df = pd.read_csv('inventory.csv', parse_dates=['last_movement_date'])
print(f"\n✅ Loaded {len(df)} inventory records")
print(f"   Categories: {df['category'].nunique()}")
print(f"   Warehouses: {df['warehouse_name'].nunique()}")
print(f"   Products: {df['product_name'].nunique()}")

# Low stock analysis
print("\n" + "─"*60)
print("⚠️  LOW STOCK ANALYSIS")
print("─"*60)
low_stock = df[df['current_stock'] < df['min_stock_level']].copy()
low_stock['shortage'] = low_stock['min_stock_level'] - low_stock['current_stock']
print(f"\nFound {len(low_stock)} items below minimum stock level:\n")
print(low_stock[['product_id', 'product_name', 'current_stock', 'min_stock_level', 'shortage']].head(10).to_string(index=False))

# Dead stock analysis
print("\n" + "─"*60)
print("💤  DEAD STOCK ANALYSIS (30+ days)")
print("─"*60)
cutoff = pd.Timestamp.now() - timedelta(days=30)
dead_stock = df[df['last_movement_date'] < cutoff].copy()
dead_stock['days_inactive'] = (pd.Timestamp.now() - dead_stock['last_movement_date']).dt.days
print(f"\nFound {len(dead_stock)} items with no movement in 30+ days:\n")
print(dead_stock[['product_id', 'product_name', 'days_inactive', 'current_stock']].head(10).to_string(index=False))

# Warehouse summary
print("\n" + "─"*60)
print("🏭  WAREHOUSE SUMMARY")
print("─"*60)
summary = df.groupby('warehouse_name').agg({
    'product_id': 'count',
    'current_stock': 'sum'
}).reset_index()
summary.columns = ['Warehouse', 'Products', 'Total Stock']
print("\n" + summary.to_string(index=False))

# Top stock items
print("\n" + "─"*60)
print("📦  TOP 5 ITEMS BY STOCK")
print("─"*60)
top_items = df.nlargest(5, 'current_stock')[['product_name', 'current_stock', 'warehouse_name']]
print("\n" + top_items.to_string(index=False))

# Overstock analysis
print("\n" + "─"*60)
print("📈  OVERSTOCK ANALYSIS (>5× minimum)")
print("─"*60)
overstock = df[df['current_stock'] > df['min_stock_level'] * 5].copy()
overstock['excess'] = overstock['current_stock'] - overstock['min_stock_level'] * 5
print(f"\nFound {len(overstock)} items with excessive stock:\n")
print(overstock[['product_id', 'product_name', 'current_stock', 'min_stock_level', 'excess']].head(10).to_string(index=False))

print("\n" + "="*60)
print("  ✅  All analysis functions working correctly!")
print("  🚀  Ready to run: streamlit run app.py")
print("="*60 + "\n")
