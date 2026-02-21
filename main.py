from fastapi import FastAPI, HTTPException
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import os

app = FastAPI(
    title="Inventory AI Assistant API",
    description="Backend API for the Inventory Management POC using FastAPI.",
    version="1.0.0"
)

# ─── DATA LOADING ──────────────────────────────────────────

def load_data():
    """Load inventory data from CSV"""
    file_path = os.path.join(os.path.dirname(__file__), 'inventory.csv')
    if not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="inventory.csv not found.")
    return pd.read_csv(file_path, parse_dates=['last_movement_date'])

# ─── MODELS ──────────────────────────────────────────────

class ProductInfo(BaseModel):
    product_id: int
    product_name: str
    category: str
    current_stock: int
    min_stock_level: int
    last_movement_date: str
    warehouse_name: str

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

# ─── API ENDPOINTS ───────────────────────────────────────

@app.get("/")
def read_root():
    return {"message": "Welcome to the Inventory AI Assistant API!"}

@app.get("/api/inventory", response_model=List[ProductInfo])
def get_all_inventory():
    """Get all inventory items."""
    df = load_data()
    df['last_movement_date'] = df['last_movement_date'].dt.strftime('%Y-%m-%d')
    return df.to_dict(orient="records")

@app.get("/api/inventory/low-stock")
def get_low_stock():
    """Show items below minimum stock level."""
    df = load_data()
    low_stock = df[df['current_stock'] < df['min_stock_level']].copy()
    low_stock['shortage'] = low_stock['min_stock_level'] - low_stock['current_stock']
    low_stock['last_movement_date'] = low_stock['last_movement_date'].dt.strftime('%Y-%m-%d')
    
    return {
        "status": "success",
        "count": len(low_stock),
        "data": low_stock.sort_values('shortage', ascending=False).to_dict(orient="records")
    }

@app.get("/api/inventory/dead-stock")
def get_dead_stock(days: int = 30):
    """Show items with no movement in the specified days (default 30)."""
    df = load_data()
    cutoff = pd.Timestamp.now() - timedelta(days=days)
    dead_stock = df[df['last_movement_date'] < cutoff].copy()
    dead_stock['days_inactive'] = (pd.Timestamp.now() - dead_stock['last_movement_date']).dt.days
    dead_stock['last_movement_date'] = dead_stock['last_movement_date'].dt.strftime('%Y-%m-%d')
    
    return {
        "status": "success",
        "count": len(dead_stock),
        "data": dead_stock.sort_values('days_inactive', ascending=False).to_dict(orient="records")
    }

@app.get("/api/inventory/overstock")
def get_overstock(multiplier: int = 5):
    """Show items where stock is much higher than needed."""
    df = load_data()
    overstock = df[df['current_stock'] > df['min_stock_level'] * multiplier].copy()
    overstock['excess'] = overstock['current_stock'] - overstock['min_stock_level'] * multiplier
    overstock['last_movement_date'] = overstock['last_movement_date'].dt.strftime('%Y-%m-%d')
    
    return {
        "status": "success",
        "count": len(overstock),
        "data": overstock.sort_values('excess', ascending=False).to_dict(orient="records")
    }

@app.get("/api/inventory/warehouse-summary")
def get_warehouse_summary():
    """Get summarized stock data per warehouse."""
    df = load_data()
    summary = df.groupby('warehouse_name').agg({
        'product_id': 'count',
        'current_stock': 'sum',
        'product_name': lambda x: (df.loc[x.index, 'current_stock'] < df.loc[x.index, 'min_stock_level']).sum()
    }).reset_index()
    summary.columns = ['Warehouse', 'Total_Products', 'Total_Stock', 'Low_Stock_Items']
    
    return {
        "status": "success",
        "data": summary.to_dict(orient="records")
    }

@app.get("/api/inventory/top-stock")
def get_top_stock(n: int = 5):
    """Get the top N products by stock quantity."""
    df = load_data()
    top_items = df.nlargest(n, 'current_stock')
    top_items['last_movement_date'] = top_items['last_movement_date'].dt.strftime('%Y-%m-%d')
    
    return {
        "status": "success",
        "data": top_items.to_dict(orient="records")
    }

@app.post("/api/chat", response_model=ChatResponse)
def offline_chat(request: ChatRequest):
    """
    Offline Rule-Based Chatbot Endpoint.
    Responds to queries using local data analysis functions.
    """
    msg = request.message.lower()
    df = load_data()
    
    response = ""
    
    # 1. Low Stock Query
    if "low" in msg or "shortage" in msg or "reorder" in msg:
        items = df[df['current_stock'] < df['min_stock_level']].head(5)
        if items.empty:
            response = "✅ Good news! There are no items below minimum stock levels right now."
        else:
            table = items[['product_name', 'current_stock', 'min_stock_level', 'warehouse_name']].to_markdown(index=False)
            response = f"⚠️ **Low Stock Alert**\n\nHere are the top items needing reorder:\n\n{table}\n\nRunning low on stock can lead to lost sales. I recommend creating a purchase order for these items immediately."

    # 2. Dead Stock Query
    elif "dead" in msg or "inactive" in msg or "stuck" in msg:
        cutoff = pd.Timestamp.now() - timedelta(days=30)
        items = df[df['last_movement_date'] < cutoff].head(5).copy()
        if items.empty:
            response = "✅ No dead stock found! All inventory is moving within the last 30 days."
        else:
            items['days_inactive'] = (pd.Timestamp.now() - items['last_movement_date']).dt.days
            table = items[['product_name', 'days_inactive', 'current_stock', 'warehouse_name']].to_markdown(index=False)
            response = f"💤 **Dead Stock Detected**\n\nThese items haven't moved in 30+ days:\n\n{table}\n\nConsider running a promotion or simple discount to clear this inventory."

    # 3. Warehouse/Summary Query
    elif "warehouse" in msg or "summary" in msg or "total" in msg:
        summary = app.state.get_warehouse_summary_internal(df) if hasattr(app.state, 'get_warehouse_summary_internal') else None
        
        summ = df.groupby('warehouse_name').agg({
            'product_id': 'count',
            'current_stock': 'sum'
        }).reset_index()
        summ.columns = ['Warehouse', 'Total Products', 'Total Stock']
        table = summ.to_markdown(index=False)
        response = f"🏭 **Warehouse Summary**\n\nHere is the current status across your locations:\n\n{table}"

    # 4. Overstock Query
    elif "over" in msg or "excess" in msg or "too much" in msg:
        items = df[df['current_stock'] > df['min_stock_level'] * 5].head(5)
        if items.empty:
            response = "✅ Inventory levels look healthy. No significant overstock detected."
        else:
            table = items[['product_name', 'current_stock', 'min_stock_level', 'warehouse_name']].to_markdown(index=False)
            response = f"📈 **Overstock Alert**\n\nThese items have >5x required stock:\n\n{table}\n\nConsider pausing orders for these products to free up capital and storage space."

    # 5. Product Search (Simple match)
    else:
        found = False
        for product in df['product_name'].unique():
            if product.lower() in msg:
                item_info = df[df['product_name'] == product].iloc[0]
                response = f"📦 **Product Info: {product}**\n\n" \
                           f"- **Category:** {item_info['category']}\n" \
                           f"- **Current Stock:** {item_info['current_stock']}\n" \
                           f"- **Location:** {item_info['warehouse_name']}\n" \
                           f"- **Last Moved:** {item_info['last_movement_date'].strftime('%Y-%m-%d')}"
                found = True
                break
        
        if not found:
            response = "🤖 **Offline Mode (FastAPI)**\n\nI'm operating purely using analytical logic. \n\nI can answer questions about:\n- ⚠️ Low Stock\n- 💤 Dead Stock\n- 🏭 Warehouse Summaries\n- 📈 Overstock\n- 📦 Specific Product Info\n\nTry asking: *'Show me low stock items'* or *'Which warehouse has the most items?'*"

    return ChatResponse(response=response)
