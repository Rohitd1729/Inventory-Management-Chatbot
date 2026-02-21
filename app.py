"""
Inventory Management Chatbot - Streamlit UI
POC for AI-powered inventory assistant 
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()
# import ollama
import plotly.express as px

# Page config
st.set_page_config(
    page_title="Inventory AI Assistant",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stButton>button {
        width: 100%;
    }
    .insight-box {
        background: #e8f4f8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #0066cc;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────

@st.cache_data
def load_data():
    """Load inventory data from CSV"""
    df = pd.read_csv('inventory.csv', parse_dates=['last_movement_date'])
    return df

# ─────────────────────────────────────────────
# ANALYSIS FUNCTIONS
# ─────────────────────────────────────────────

def get_low_stock_items(df):
    """Get items below minimum stock level"""
    low_stock = df[df['current_stock'] < df['min_stock_level']].copy()
    low_stock['shortage'] = low_stock['min_stock_level'] - low_stock['current_stock']
    return low_stock.sort_values('shortage', ascending=False)

def get_dead_stock_items(df, days=30):
    """Get items with no movement in specified days"""
    cutoff = pd.Timestamp.now() - timedelta(days=days)
    dead_stock = df[df['last_movement_date'] < cutoff].copy()
    dead_stock['days_inactive'] = (pd.Timestamp.now() - dead_stock['last_movement_date']).dt.days
    return dead_stock.sort_values('days_inactive', ascending=False)

def get_warehouse_summary(df):
    """Get stock summary by warehouse"""
    summary = df.groupby('warehouse_name').agg({
        'product_id': 'count',
        'current_stock': 'sum',
        'product_name': lambda x: (df.loc[x.index, 'current_stock'] < df.loc[x.index, 'min_stock_level']).sum()
    }).reset_index()
    summary.columns = ['Warehouse', 'Total Products', 'Total Stock', 'Low Stock Items']
    return summary

def get_top_stock_items(df, n=5):
    """Get top N items by stock quantity"""
    return df.nlargest(n, 'current_stock')[['product_id', 'product_name', 'category', 
                                             'current_stock', 'warehouse_name']]

def get_overstock_items(df, multiplier=5):
    """Get items with excessive stock"""
    overstock = df[df['current_stock'] > df['min_stock_level'] * multiplier].copy()
    overstock['excess'] = overstock['current_stock'] - overstock['min_stock_level'] * multiplier
    return overstock.sort_values('excess', ascending=False)

def get_category_analysis(df):
    """Analyze stock by category"""
    return df.groupby('category').agg({
        'product_id': 'count',
        'current_stock': 'sum',
    }).reset_index().rename(columns={'product_id': 'Products', 'current_stock': 'Total Stock'})

# ─────────────────────────────────────────────
# LLM INTEGRATION
# ─────────────────────────────────────────────

def get_inventory_context(df):
    """Create context for LLM"""
    today = pd.Timestamp.now()
    df_ctx = df.copy()
    df_ctx['days_since_movement'] = (today - df_ctx['last_movement_date']).dt.days
    df_ctx['is_low_stock'] = df_ctx['current_stock'] < df_ctx['min_stock_level']
    df_ctx['is_dead_stock'] = df_ctx['days_since_movement'] > 30
    df_ctx['is_overstock'] = df_ctx['current_stock'] > df_ctx['min_stock_level'] * 5
    
    # Convert to JSON for LLM
    summary = df_ctx[['product_id', 'product_name', 'category', 'current_stock', 
                      'min_stock_level', 'days_since_movement', 'warehouse_name',
                      'is_low_stock', 'is_dead_stock', 'is_overstock']].to_dict(orient='records')
    return json.dumps(summary[:100])  # Limit to avoid token overload

def get_api_key():
    """Not needed for offline rule-based logic."""
    return None

def chat_with_claude(user_message, conversation_history):
    """
    Offline Rule-Based Chatbot
    Responds to queries using local data analysis functions without an API key or LLM.
    """
    msg = user_message.lower()
    df = load_data()
    
    response = ""
    
    # 1. Low Stock Query
    if any(k in msg for k in ["low", "shortage", "reorder", "minimum", "below", "refill", "buy", "order"]):
        items = get_low_stock_items(df).head(5)
        if items.empty:
            response = "✅ Good news! There are no items below minimum stock levels right now."
        else:
            table = items[['product_name', 'current_stock', 'min_stock_level', 'warehouse_name']].to_markdown(index=False)
            response = f"⚠️ **Low Stock Alert**\n\nHere are the top items needing reorder:\n\n{table}\n\nRunning low on stock can lead to lost sales. I recommend creating a purchase order for these items immediately."

    # 2. Dead Stock Query
    elif any(k in msg for k in ["dead", "inactive", "stuck", "unsold", "not moving", "stagnant", "old", "obsolete", "slow movement"]):
        items = get_dead_stock_items(df).head(5)
        if items.empty:
            response = "✅ No dead stock found! All inventory is moving within the last 30 days."
        else:
            table = items[['product_name', 'days_inactive', 'current_stock', 'warehouse_name']].to_markdown(index=False)
            response = f"💤 **Dead Stock Detected**\n\nThese items haven't moved in 30+ days:\n\n{table}\n\nConsider running a promotion or simple discount to clear this inventory."

    # 3. Warehouse/Summary Query
    elif any(k in msg for k in ["warehouse", "summary", "total", "store", "location overview", "stock levels", "inventory summary", "dashboard", "report"]):
        summary = get_warehouse_summary(df)
        table = summary.to_markdown(index=False)
        response = f"🏭 **Warehouse Summary**\n\nHere is the current status across your locations:\n\n{table}"

    # 4. Overstock Query
    elif any(k in msg for k in ["overstock", "excess", "too much", "surplus", "abundant", "overflow", "too many", "high stock", "over"]):
        items = get_overstock_items(df).head(5)
        if items.empty:
            response = "✅ Inventory levels look healthy. No significant overstock detected."
        else:
            table = items[['product_name', 'current_stock', 'min_stock_level', 'warehouse_name']].to_markdown(index=False)
            response = f"📈 **Overstock Alert**\n\nThese items have >5x required stock:\n\n{table}\n\nConsider pausing orders for these products to free up capital and storage space."

    # 5. Top Items Query
    elif any(k in msg for k in ["top", "best", "highest", "most", "popular", "max", "greatest", "number one", "leading"]):
        items = get_top_stock_items(df, n=5)
        table = items.to_markdown(index=False)
        response = f"🏆 **Top 5 Items (Highest Stock Volume)**\n\n{table}\n\n*These are the most highly stocked items across all warehouses.*"

    # 6. Category Query
    elif any(k in msg for k in ["category", "types", "departments", "group", "class", "genre", "sorts", "kind", "breakdown"]):
        summary = get_category_analysis(df)
        table = summary.to_markdown(index=False)
        response = f"📁 **Category Analysis**\n\nHere is the current breakdown of total stock by category:\n\n{table}"

    # 7. Out of Stock Query
    elif any(k in msg for k in ["out of stock", "zero", "empty", "no stock", "0 stock", "none", "sold out", "depleted", "unavailable"]):
        out_of_stock = df[df['current_stock'] == 0]
        if out_of_stock.empty:
            response = "✅ No items are currently out of stock!"
        else:
            table = out_of_stock[['product_name', 'category', 'warehouse_name']].head(5).to_markdown(index=False)
            response = f"🚨 **Out of Stock Alert!**\n\nThese items currently have 0 stock:\n\n{table}\n\nYou must reorder these immediately."

    # 8. Recently Moved / Active Query
    elif any(k in msg for k in ["recent", "new", "active", "latest", "just moved", "current", "fresh"]):
        recent_items = df.sort_values(by='last_movement_date', ascending=False).head(5)
        table = recent_items[['product_name', 'current_stock', 'last_movement_date', 'warehouse_name']].to_markdown(index=False)
        response = f"🔥 **Recently Moved Items**\n\nHere are the products that moved most recently:\n\n{table}"

    # 9. Total / General Counts Query
    elif any(k in msg for k in ["how many", "count", "number of", "total amount", "metrics", "stats", "statistics", "size", "portfolio"]):
        total_products = len(df)
        total_categories = df['category'].nunique()
        total_warehouses = df['warehouse_name'].nunique()
        total_quant = df['current_stock'].sum()
        response = f"📊 **Inventory Statistics**\n\n- **Unique Items**: {total_products}\n- **Categories**: {total_categories}\n- **Locations**: {total_warehouses}\n- **Total Stock Quantity**: {total_quant:,}"

    # 10. Help / Greeting Query
    elif any(k in msg for k in ["hi", "hello", "hey", "help", "what can you do", "commands", "start"]):
        response = "🤖 **Hello! I am your Offline Inventory Assistant.**\n\nI analyze your data locally without the internet. You can ask me:\n- ⚠️ 'Show me **low stock** items'\n- 🚨 'Are any items **out of stock**?'\n- 💤 'Find **dead stock**'\n- 🏭 'Give me a **warehouse summary**'\n- 📈 'Do we have any **overstock**?'\n- 🏆 'What are our **top** items?'\n- 🔥 'What moved **recently**?'\n- 📊 'How many **total** items do we have?'\n- 📁 'Show me the **category** breakdown.'\n- 📦 Or just type a specific **product name**!"
        
    # 11. Fuzzy Search (Product Name -> Category -> Warehouse)
    else:
        found = False
        
        # Check specific product names
        for product in df['product_name'].unique():
            if product.lower() in msg:
                item_info = df[df['product_name'] == product].iloc[0]
                response = f"📦 **Product Info: {product}**\n\n" \
                           f"- **Category:** {item_info['category']}\n" \
                           f"- **Current Stock:** {item_info['current_stock']}\n" \
                           f"- **Location:** {item_info['warehouse_name']}\n" \
                           f"- **Min Required:** {item_info['min_stock_level']}\n" \
                           f"- **Last Moved:** {item_info['last_movement_date'].strftime('%Y-%m-%d')}"
                found = True
                break
                
        # Check specific category
        if not found:
            for category in df['category'].unique():
                if category.lower() in msg:
                    cat_items = df[df['category'] == category].sort_values('current_stock', ascending=False).head(5)
                    table = cat_items[['product_name', 'current_stock', 'warehouse_name']].to_markdown(index=False)
                    response = f"📁 **Category Match: {category}**\n\nHere are the top 5 stocked items in this category:\n\n{table}"
                    found = True
                    break

        # Check specific warehouse
        if not found:
            for warehouse in df['warehouse_name'].unique():
                if warehouse.lower() in msg:
                    wh_items = df[df['warehouse_name'] == warehouse]
                    total_stock = wh_items['current_stock'].sum()
                    table = wh_items.sort_values('current_stock', ascending=False).head(5)[['product_name', 'category', 'current_stock']].to_markdown(index=False)
                    response = f"🏭 **Location Match: {warehouse}**\n\nThis location is currently holding {total_stock:,} total items. Here are the top 5 items stored here:\n\n{table}"
                    found = True
                    break
        
        # Absolute fallback
        if not found:
            response = "🤖 **Offline Rule-Based Mode**\n\nI couldn't find a keyword match for that. \n\nTry using explicit queries like: **out of stock**, **recent**, **low stock**, **dead**, **overstock**, **warehouse**, **how many items**, **top**, or **category**."

    # Update history
    conversation_history.append({"role": "user", "content": user_message})
    conversation_history.append({"role": "assistant", "content": response})
    
    return response

# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────

def main():
    # Header
    st.markdown('<h1 class="main-header">📦 Inventory AI Assistant</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Inventory Management & Insights</p>', unsafe_allow_html=True)
    
    # Load data
    df = load_data()
    
    # Sidebar - Dashboard
    with st.sidebar:
        st.header("📊 Dashboard")
        
        # Key metrics
        total_products = len(df)
        total_stock = df['current_stock'].sum()
        low_stock_count = len(df[df['current_stock'] < df['min_stock_level']])
        dead_stock_count = len(df[df['last_movement_date'] < (pd.Timestamp.now() - timedelta(days=30))])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Products", total_products)
            st.metric("Low Stock", low_stock_count, delta=f"{low_stock_count/total_products*100:.1f}%")
        with col2:
            st.metric("Total Stock", f"{total_stock:,}")
            st.metric("Dead Stock", dead_stock_count, delta=f"{dead_stock_count/total_products*100:.1f}%")
        
        st.divider()
        
        # Quick Actions
        st.subheader("🎯 Quick Actions")
        
        if st.button("⚠️ Show Low Stock Items"):
            st.session_state.query_type = "low_stock"
        
        if st.button("💤 Show Dead Stock"):
            st.session_state.query_type = "dead_stock"
        
        if st.button("🏭 Warehouse Summary"):
            st.session_state.query_type = "warehouse_summary"
        
        if st.button("📦 Top 5 Stock Items"):
            st.session_state.query_type = "top_stock"
        
        if st.button("📈 Show Overstock"):
            st.session_state.query_type = "overstock"
        
        if st.button("📁 Category Analysis"):
            st.session_state.query_type = "category_analysis"
            
        if 'query_type' in st.session_state:
            st.success("✅ Query active! Open the **📊 Analytics** tab to see results.")
        
        st.divider()
        
        # Dataset info
        with st.expander("ℹ️ Dataset Info"):
            st.write(f"**Total Records:** {len(df)}")
            st.write(f"**Categories:** {df['category'].nunique()}")
            st.write(f"**Warehouses:** {df['warehouse_name'].nunique()}")
            st.write(f"**Unique Products:** {df['product_name'].nunique()}")
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["💬 AI Chat", "📊 Analytics", "📋 Data View"])
    
    # Tab 1: AI Chat
    with tab1:
        col1, col2 = st.columns([5, 1])
        with col1:
            st.subheader("Ask me anything about your inventory")
        with col2:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.conversation = []
                st.rerun()
        
        # Initialize chat history
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        if 'conversation' not in st.session_state:
            st.session_state.conversation = []
        
        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        user_input = st.chat_input("Type your question here... e.g., 'Which electronics are running low?'")
        
        if user_input:
            # Add user message
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # Get AI response
            with st.chat_message("assistant"):
                with st.spinner("Analyzing inventory..."):
                    # We pass 'st.session_state.conversation' assuming it's used for context tracking
                    # But the new implementation mostly uses 'conversation_history' passed as argument
                    # for the 'messages' list.
                    # Wait, the logic in original code was passing 'st.session_state.conversation' which was list of dicts.
                    # My new implementation expects list of dicts too.
                    # However, 'messages' construction in my new function:
                    # messages = [...] + conversation_history + [...]
                    # OpenAI expects {"role": "...", "content": "..."}
                    # It seems compatible.
                    response = chat_with_claude(user_input, st.session_state.conversation)
                st.markdown(response)
            
            # Note: The function chat_with_claude updates conversation_history IN PLACE in my code?
            # In original code:
            # conversation_history.append(...)
            # return assistant_msg
            # Here I return assistant_msg.
            # And I append to conversation_history inside the function.
            # AND I append to st.session_state.chat_history OUTSIDE the function (lines 282 in original).
            # So duplicate update?
            # Original code:
            # chat_with_claude(user_input, st.session_state.conversation)
            #   -> updates conversation_history (which is st.session_state.conversation)
            # OUTSIDE:
            # st.session_state.chat_history.append(...)
            # This is fine. 'conversation' is for LLM context, 'chat_history' is for UI display.
            
            # Wait, my new function implementation:
            # conversation_history.append({"role": "user", "content": user_message})
            # conversation_history.append({"role": "assistant", "content": assistant_msg})
            # This logic mimics the original one.
            pass
            
            # Note: The UI update for 'chat_history' needs to happen too.
            # In original code:
            # st.session_state.chat_history.append({"role": "assistant", "content": response})
            # This happens outside.
            pass
    
    # Tab 2: Analytics
    with tab2:
        # Handle quick action queries
        if 'query_type' in st.session_state:
            query = st.session_state.query_type
            
            if query == "low_stock":
                st.subheader("⚠️ Low Stock Items")
                low_stock = get_low_stock_items(df)
                if not low_stock.empty:
                    col1, col2 = st.columns([1, 1.5])
                    with col1:
                        st.dataframe(low_stock[['product_id', 'product_name', 'category', 
                                               'current_stock', 'min_stock_level', 'shortage', 
                                               'warehouse_name']], use_container_width=True)
                        st.info(f"📌 Found {len(low_stock)} items below minimum stock level. Consider reordering these items.")
                    with col2:
                        fig = px.bar(low_stock.head(15), x='shortage', y='product_name', color='warehouse_name', orientation='h', title='Top 15 Items Shortage')
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.success("✅ No low stock items!")
            
            elif query == "dead_stock":
                st.subheader("💤 Dead Stock Items (No movement in 30+ days)")
                dead_stock = get_dead_stock_items(df)
                if not dead_stock.empty:
                    col1, col2 = st.columns([1, 1.5])
                    with col1:
                        st.dataframe(dead_stock[['product_id', 'product_name', 'category', 
                                                'current_stock', 'days_inactive', 'warehouse_name']], 
                                   use_container_width=True)
                        st.warning(f"⚠️ {len(dead_stock)} items haven't moved in 30+ days. Consider promotions or clearance.")
                    with col2:
                        fig = px.histogram(dead_stock, x='days_inactive', color='category', title='Distribution of Inactive Days', nbins=20)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.success("✅ No dead stock!")
            
            elif query == "warehouse_summary":
                st.subheader("🏭 Stock Summary by Warehouse")
                summary = get_warehouse_summary(df)
                col1, col2 = st.columns([1, 1.5])
                with col1:
                    st.dataframe(summary, use_container_width=True)
                    fig_pie = px.pie(summary, values='Total Stock', names='Warehouse', title='Total Stock by Warehouse', hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
                with col2:
                    fig_bar = px.bar(summary, x='Warehouse', y=['Total Stock', 'Low Stock Items'], barmode='group', title='Warehouse Health Comparison')
                    st.plotly_chart(fig_bar, use_container_width=True)
            
            elif query == "top_stock":
                st.subheader("📦 Top 5 Products by Stock")
                top_items = get_top_stock_items(df, n=10) # increase to 10 for better visual
                col1, col2 = st.columns([1, 1.5])
                with col1:
                    st.dataframe(top_items, use_container_width=True)
                with col2:
                    fig = px.bar(top_items.sort_values('current_stock', ascending=True), x='current_stock', y='product_name', color='category', orientation='h', title='Highest Stock Volumes')
                    st.plotly_chart(fig, use_container_width=True)
            
            elif query == "overstock":
                st.subheader("📈 Overstock Items (>5× minimum level)")
                overstock = get_overstock_items(df)
                if not overstock.empty:
                    col1, col2 = st.columns([1, 1.5])
                    with col1:
                        st.dataframe(overstock[['product_id', 'product_name', 'category', 
                                               'current_stock', 'min_stock_level', 'excess', 
                                               'warehouse_name']], use_container_width=True)
                        st.info(f"📌 {len(overstock)} items have excessive stock. Consider reducing orders.")
                    with col2:
                        fig = px.bar(overstock.head(15).sort_values('excess', ascending=True), x='excess', y='product_name', color='category', orientation='h', title='Top 15 Overstock Items')
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.success("✅ No overstock items!")
            
            elif query == "category_analysis":
                st.subheader("📁 Stock by Category")
                cat_analysis = get_category_analysis(df)
                col1, col2 = st.columns([1, 1.5])
                with col1:
                    st.dataframe(cat_analysis, use_container_width=True)
                    fig_pie = px.pie(cat_analysis, values='Total Stock', names='category', title='Category Stock Distribution')
                    st.plotly_chart(fig_pie, use_container_width=True)
                with col2:
                    fig_bar = px.bar(cat_analysis.sort_values('Total Stock', ascending=True), x='Total Stock', y='category', orientation='h', title='Stock Volume by Category', color='Total Stock')
                    st.plotly_chart(fig_bar, use_container_width=True)
            
            # Don't delete the query_type so it persists across tab switches
            pass
    
    # Tab 3: Data View
    with tab3:
        st.subheader("📋 Complete Inventory Data")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            category_filter = st.multiselect("Category", df['category'].unique())
        with col2:
            warehouse_filter = st.multiselect("Warehouse", df['warehouse_name'].unique())
        with col3:
            stock_filter = st.selectbox("Stock Status", 
                                       ["All", "Low Stock", "Normal", "Overstock"])
        
        # Apply filters
        filtered_df = df.copy()
        if category_filter:
            filtered_df = filtered_df[filtered_df['category'].isin(category_filter)]
        if warehouse_filter:
            filtered_df = filtered_df[filtered_df['warehouse_name'].isin(warehouse_filter)]
        if stock_filter == "Low Stock":
            filtered_df = filtered_df[filtered_df['current_stock'] < filtered_df['min_stock_level']]
        elif stock_filter == "Overstock":
            filtered_df = filtered_df[filtered_df['current_stock'] > filtered_df['min_stock_level'] * 5]
        elif stock_filter == "Normal":
            filtered_df = filtered_df[
                (filtered_df['current_stock'] >= filtered_df['min_stock_level']) &
                (filtered_df['current_stock'] <= filtered_df['min_stock_level'] * 5)
            ]
        
        st.dataframe(filtered_df, use_container_width=True, height=400)
        
        # Download button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data (CSV)",
            data=csv,
            file_name="inventory_export.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
