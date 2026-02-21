"""
Maven Toys Dataset Converter
Converts Maven Toys Kaggle dataset to inventory management format

Download the Maven Toys dataset from:
https://www.kaggle.com/datasets/mysarahmadbhat/toy-sales

Required files: products.csv, stores.csv, inventory.csv
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

def convert_maven_toys():
    """Convert Maven Toys dataset to inventory format"""
    
    # Check if files exist
    required_files = ['products.csv', 'stores.csv', 'inventory.csv']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print("❌ Missing files:", ", ".join(missing_files))
        print("\n📥 Please download Maven Toys dataset from:")
        print("   https://www.kaggle.com/datasets/mysarahmadbhat/toy-sales")
        print("\nExtract these files to the current directory:")
        for f in required_files:
            print(f"   - {f}")
        return False
    
    print("📦 Loading Maven Toys dataset...")
    
    # Load tables
    products = pd.read_csv('products.csv')
    stores = pd.read_csv('stores.csv')
    inventory_data = pd.read_csv('inventory.csv')
    
    print(f"   Products: {len(products)} records")
    print(f"   Stores: {len(stores)} records")
    print(f"   Inventory: {len(inventory_data)} records")
    
    # Merge tables
    print("\n🔗 Merging tables...")
    df = inventory_data.merge(products, on='Product_ID', how='left')
    df = df.merge(stores, on='Store_ID', how='left')
    
    # Rename columns to match our schema
    print("🔄 Transforming to inventory format...")
    df = df.rename(columns={
        'Product_ID': 'product_id',
        'Product_Name': 'product_name',
        'Product_Category': 'category',
        'Stock_On_Hand': 'current_stock',
        'Store_Name': 'warehouse_name'
    })
    
    # Calculate minimum stock levels
    # Rule: min stock = 30% of current stock, minimum 5 units
    df['min_stock_level'] = (df['current_stock'] * 0.3).astype(int).clip(lower=5)
    
    # Generate realistic last movement dates
    # Random dates within last 120 days, weighted toward recent dates
    np.random.seed(42)
    
    # 70% of items moved in last 30 days (active)
    # 20% moved 31-60 days ago (slow moving)
    # 10% moved 61-120 days ago (dead stock)
    probabilities = [0.7, 0.2, 0.1]
    date_ranges = [(1, 30), (31, 60), (61, 120)]
    
    days_ago = []
    for _ in range(len(df)):
        range_idx = np.random.choice(len(date_ranges), p=probabilities)
        min_days, max_days = date_ranges[range_idx]
        days_ago.append(np.random.randint(min_days, max_days + 1))
    
    df['last_movement_date'] = pd.to_datetime('today') - pd.to_timedelta(days_ago, unit='D')
    df['last_movement_date'] = df['last_movement_date'].dt.strftime('%Y-%m-%d')
    
    # Select final columns
    final_df = df[['product_id', 'product_name', 'category', 'current_stock', 
                   'min_stock_level', 'last_movement_date', 'warehouse_name']].copy()
    
    # Remove any rows with missing data
    final_df = final_df.dropna()
    
    # Save to inventory.csv
    final_df.to_csv('inventory.csv', index=False)
    
    print(f"\n✅ Successfully converted {len(final_df)} inventory records!")
    print(f"\n📊 Dataset Statistics:")
    print(f"   Total Records: {len(final_df)}")
    print(f"   Unique Products: {final_df['product_name'].nunique()}")
    print(f"   Categories: {final_df['category'].nunique()}")
    print(f"   Warehouses: {final_df['warehouse_name'].nunique()}")
    
    # Analysis
    low_stock = len(final_df[final_df['current_stock'] < final_df['min_stock_level']])
    cutoff = pd.to_datetime('today') - pd.Timedelta(days=30)
    dead_stock = len(final_df[pd.to_datetime(final_df['last_movement_date']) < cutoff])
    overstock = len(final_df[final_df['current_stock'] > final_df['min_stock_level'] * 5])
    
    print(f"\n🔍 Insights:")
    print(f"   Low stock items: {low_stock}")
    print(f"   Dead stock (30+ days): {dead_stock}")
    print(f"   Overstock items: {overstock}")
    
    print(f"\n💾 Saved to: inventory.csv")
    print(f"🚀 Ready to run: streamlit run app.py")
    
    return True


if __name__ == "__main__":
    print("="*60)
    print("  Maven Toys Dataset Converter")
    print("  Convert Kaggle dataset to inventory format")
    print("="*60 + "\n")
    
    convert_maven_toys()
