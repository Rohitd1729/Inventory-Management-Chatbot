"""
Inventory Management Chatbot - Streamlit UI
POC for AI-powered inventory assistant using Claude LLM
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import os
from anthropic import Anthropic

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

def chat_with_claude(user_message, conversation_history):
    """Send message to Claude API"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not api_key:
        return "⚠️ Please set ANTHROPIC_API_KEY environment variable to use AI features."
    
    try:
        client = Anthropic(api_key=api_key)
        
        # Load inventory context
        df = load_data()
        inventory_json = get_inventory_context(df)
        
        system_prompt = """You are an Inventory Management AI Assistant.

You have access to real-time inventory data in JSON format.

Your responsibilities:
1. Answer inventory questions clearly and concisely
2. Format data as clean markdown tables when showing results
3. Provide actionable insights after tables (2-3 sentences)
4. Flag critical issues: low stock, dead stock (30+ days), overstock (>5x min level)
5. Make reasonable forecasts based on movement patterns
6. Be direct - no preambles, just results

Respond ONLY to inventory-related questions. Politely decline off-topic requests."""

        enriched_message = f"""Current inventory data (first 100 items):
{inventory_json}

User question: {user_message}"""

        messages = conversation_history + [{"role": "user", "content": enriched_message}]
        
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            system=system_prompt,
            messages=messages
        )
        
        assistant_msg = response.content[0].text
        
        # Update history
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": assistant_msg})
        
        # Keep only last 10 turns
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        
        return assistant_msg
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

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
        st.subheader("Ask me anything about your inventory")
        
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
                    response = chat_with_claude(user_input, st.session_state.conversation)
                st.markdown(response)
            
            st.session_state.chat_history.append({"role": "assistant", "content": response})
    
    # Tab 2: Analytics
    with tab2:
        # Handle quick action queries
        if 'query_type' in st.session_state:
            query = st.session_state.query_type
            
            if query == "low_stock":
                st.subheader("⚠️ Low Stock Items")
                low_stock = get_low_stock_items(df)
                if not low_stock.empty:
                    st.dataframe(low_stock[['product_id', 'product_name', 'category', 
                                           'current_stock', 'min_stock_level', 'shortage', 
                                           'warehouse_name']], use_container_width=True)
                    st.info(f"📌 Found {len(low_stock)} items below minimum stock level. Consider reordering these items.")
                else:
                    st.success("✅ No low stock items!")
            
            elif query == "dead_stock":
                st.subheader("💤 Dead Stock Items (No movement in 30+ days)")
                dead_stock = get_dead_stock_items(df)
                if not dead_stock.empty:
                    st.dataframe(dead_stock[['product_id', 'product_name', 'category', 
                                            'current_stock', 'days_inactive', 'warehouse_name']], 
                               use_container_width=True)
                    st.warning(f"⚠️ {len(dead_stock)} items haven't moved in 30+ days. Consider promotions or clearance.")
                else:
                    st.success("✅ No dead stock!")
            
            elif query == "warehouse_summary":
                st.subheader("🏭 Stock Summary by Warehouse")
                summary = get_warehouse_summary(df)
                st.dataframe(summary, use_container_width=True)
                
                # Chart
                st.bar_chart(summary.set_index('Warehouse')['Total Stock'])
            
            elif query == "top_stock":
                st.subheader("📦 Top 5 Products by Stock")
                top_items = get_top_stock_items(df)
                st.dataframe(top_items, use_container_width=True)
            
            elif query == "overstock":
                st.subheader("📈 Overstock Items (>5× minimum level)")
                overstock = get_overstock_items(df)
                if not overstock.empty:
                    st.dataframe(overstock[['product_id', 'product_name', 'category', 
                                           'current_stock', 'min_stock_level', 'excess', 
                                           'warehouse_name']], use_container_width=True)
                    st.info(f"📌 {len(overstock)} items have excessive stock. Consider reducing orders.")
                else:
                    st.success("✅ No overstock items!")
            
            elif query == "category_analysis":
                st.subheader("📁 Stock by Category")
                cat_analysis = get_category_analysis(df)
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.dataframe(cat_analysis, use_container_width=True)
                with col2:
                    st.bar_chart(cat_analysis.set_index('category')['Total Stock'])
            
            # Clear query after showing
            del st.session_state.query_type
    
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
