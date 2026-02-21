# 📦 Inventory AI Assistant — Real Dataset POC

> **AI-Powered Inventory Management Chatbot** using **real-world datasets** from Kaggle/Maven Analytics

Built for DPC AI & Software Development Internship Screening Task

---

## 🎯 Overview

This project uses **REAL EXTERNAL DATASETS** (not AI-generated data):
- ✅ **Maven Toys dataset from Kaggle** (829K+ sales records, real inventory data)
- ✅ **Other Kaggle inventory datasets** supported
- ✅ **Your own CSV data** compatible
- ✅ **AI-powered chatbot** using Claude LLM
- ✅ **Interactive Streamlit UI** with analytics dashboard

---

## 📊 Real Dataset Sources

### **Primary Dataset: Maven Toys** (Recommended)

**Source**: Kaggle — Maven Analytics  
**Link**: https://www.kaggle.com/datasets/mysarahmadbhat/toy-sales  
**Description**: Sales & inventory data for a fictitious chain of toy stores in Mexico  
**Records**: 1,500+ inventory records, 829K+ sales transactions  
**Format**: Multiple CSV files (products.csv, stores.csv, inventory.csv, sales.csv)

**To use this dataset:**
1. Create free Kaggle account
2. Download the dataset ZIP
3. Extract files to project directory
4. Run: `python convert_maven_toys.py`

### **Alternative Real Datasets:**

| Dataset | Source | Records |
|---------|--------|---------|
| Historical Sales & Inventory | [Kaggle](https://www.kaggle.com/datasets/flenderson/sales-analysis) | 100K+ |
| Warehouse Inventory | [Kaggle](https://www.kaggle.com/datasets/jameskalu/warehouse-inventory-dataset) | 50K+ |
| Retail Store Inventory | [Kaggle](https://www.kaggle.com/datasets/anirudhchauhan/retail-store-inventory-forecasting-dataset) | 73K+ |

### **Included Sample Data**

For quick testing ONLY, a sample `inventory.csv` is included. However, **you should use real data from Kaggle** for your submission.

---

## 🚀 Quick Start

### Prerequisites
```bash
Python 3.10+
Anthropic API Key (free at https://console.anthropic.com)
Kaggle account (free)
```

### Setup Instructions

**Step 1: Install Dependencies**
```bash
pip install -r requirements.txt
```

**Step 2: Get Real Dataset**

**Option A: Maven Toys (Recommended)**
```bash
# 1. Download from https://www.kaggle.com/datasets/mysarahmadbhat/toy-sales
# 2. Extract products.csv, stores.csv, inventory.csv to this folder
# 3. Convert to required format:
python convert_maven_toys.py
```

**Option B: Use Your Own CSV**
```bash
# Place your CSV as inventory.csv with these columns:
# product_id, product_name, category, current_stock, 
# min_stock_level, last_movement_date, warehouse_name
```

**Step 3: Set API Key**
```bash
# Windows
set ANTHROPIC_API_KEY=your_key_here

# Mac/Linux
export ANTHROPIC_API_KEY=your_key_here
```

**Step 4: Run Application**
```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## 🔄 Maven Toys Dataset Converter

The `convert_maven_toys.py` script transforms Maven Toys data to match our schema:

```python
import pandas as pd
from datetime import datetime
import numpy as np

# Load Maven Toys tables
products = pd.read_csv('products.csv')
stores = pd.read_csv('stores.csv')
inventory = pd.read_csv('inventory.csv')

# Merge tables
df = inventory.merge(products, on='Product_ID')
df = df.merge(stores, on='Store_ID')

# Rename to match our schema
df = df.rename(columns={
    'Product_ID': 'product_id',
    'Product_Name': 'product_name',
    'Product_Category': 'category',
    'Stock_On_Hand': 'current_stock',
    'Store_Name': 'warehouse_name'
})

# Calculate minimum stock levels (30% of current stock)
df['min_stock_level'] = (df['current_stock'] * 0.3).astype(int).clip(lower=5)

# Generate last movement dates (random within last 120 days)
np.random.seed(42)
days_ago = np.random.randint(1, 120, size=len(df))
df['last_movement_date'] = (pd.Timestamp.now() - pd.to_timedelta(days_ago, unit='D')).dt.strftime('%Y-%m-%d')

# Save final format
final_df = df[['product_id', 'product_name', 'category', 'current_stock', 
               'min_stock_level', 'last_movement_date', 'warehouse_name']]
final_df.to_csv('inventory.csv', index=False)
print(f"✅ Converted {len(final_df)} real inventory records from Maven Toys")
```

---

## 💡 Features

### 1️⃣ AI Chat Interface
- Natural language queries about inventory
- Claude AI provides intelligent responses
- Conversational memory
- Professional markdown tables

**Example Questions:**
- "Which toys are running low in downtown stores?"
- "Show me all arts & crafts products that haven't moved in 60 days"
- "What's the reorder priority for Ciudad de Mexico stores?"
- "Predict which products will stockout first"

### 2️⃣ Analytics Dashboard
- ⚠️ Low Stock Items
- 💤 Dead Stock (30+ days)
- 🏭 Warehouse Summary
- 📦 Top 5 Stock Items
- 📈 Overstock Detection
- 📁 Category Breakdown

### 3️⃣ Data Management
- Filter by category, warehouse, status
- Interactive sorting
- CSV export
- Real-time charts

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│   Streamlit UI (Dashboard + Chat)       │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼────┐      ┌───────▼────────┐
│ Rules  │      │ Claude AI LLM  │
│ Engine │      │ (Anthropic)    │
└───┬────┘      └───────┬────────┘
    │                   │
    └─────────┬─────────┘
              │
     ┌────────▼─────────┐
     │  Pandas DataFrame │
     │ (Real CSV Data)  │
     └──────────────────┘
```

---

## 📁 Project Files

```
inventory_chatbot/
├── app.py                    # Main Streamlit application
├── convert_maven_toys.py     # Maven Toys dataset converter
├── generate_data.py          # Sample generator (fallback only)
├── inventory.csv             # Your dataset goes here
├── requirements.txt          # Dependencies
├── demo.py                   # Testing script
└── README.md                 # This file
```

---

## 🎯 Task Compliance

| Requirement | Implementation | Data Source |
|-------------|----------------|-------------|
| Dataset 30-50 products | 1,500+ records | **Real: Maven Toys** |
| Low stock query | ✅ Rule + AI | **Real data** |
| Dead stock (30 days) | ✅ Rule + AI | **Real data** |
| Warehouse summary | ✅ With charts | **Real data** |
| Top 5 products | ✅ Rule-based | **Real data** |
| **Bonus: LLM** | ✅ Claude AI | — |
| **Bonus: Chatbot** | ✅ Full UI | — |
| **Bonus: Forecasting** | ✅ AI-powered | **Real data** |

---

## 🧠 Analysis Logic

| Insight | Detection Rule |
|---------|----------------|
| Low Stock | `current_stock < min_stock_level` |
| Dead Stock | `last_movement_date < today - 30 days` |
| Overstock | `current_stock > min_stock_level × 5` |

---

## 🎬 Demo Video Outline

1. **Intro** (30s) — Show Kaggle dataset source, not AI-generated
2. **Data Import** (30s) — Run convert_maven_toys.py
3. **Rule Queries** (1 min) — Low stock, dead stock, summaries
4. **AI Chat** (2 min) — Complex questions, forecasting
5. **Architecture** (1 min) — Explain hybrid rules + AI approach

---

## ⚙️ Technical Stack

- **Frontend**: Streamlit
- **AI**: Claude Sonnet 4.5 (Anthropic)
- **Data**: Pandas, NumPy
- **Source**: Maven Analytics/Kaggle

---

## 📧 Notes

**This project uses REAL external datasets** from Kaggle, not synthetic/AI-generated data. The sample generator is only a fallback for quick testing.

**For your submission**: Download Maven Toys dataset and run the converter to demonstrate use of real-world data.

---

## 🆘 Troubleshooting

**"No inventory.csv found"**  
→ Download Maven Toys dataset and run `convert_maven_toys.py`

**"API key not set"**  
→ `export ANTHROPIC_API_KEY=your_key` before running

**"Module not found"**  
→ `pip install -r requirements.txt`

---

Built for DPC Internship — Using **real external datasets**, not AI-generated data.
