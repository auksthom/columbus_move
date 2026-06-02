import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Set page layout to wide for better map viewing
st.set_page_config(layout="wide", page_title="Warehouse Pick Planner")

# --- 1. DATA LOADING ---
@st.cache_data(ttl=600)
def load_data():
    # Live Google Sheet export link
    stock_sheet_url = "https://docs.google.com/spreadsheets/d/1NiSNnc3bTqCshnivZZ6WMYhdCS0yLZHh_87LL3BS3hU/export?format=csv&gid=1304057791"
    
    # Local blueprint file (must be in the same folder as this app.py file on GitHub)
    blueprint_url = "master_blueprint.csv" 
    
    try:
        df_stock = pd.read_csv(stock_sheet_url)
        df_blueprint = pd.read_csv(blueprint_url)
    except Exception as e:
        st.error(f"Error loading data files. Please check URLs and file paths. Error: {e}")
        st.stop()
    
    # Clean up column names to avoid trailing spaces
    df_stock.columns = df_stock.columns.str.strip()
    df_blueprint.columns = df_blueprint.columns.str.strip()
    
    return df_stock, df_blueprint

df_stock_raw, df_blueprint = load_data()

# --- 2. USER INTERFACE ---
st.title("📦 Warehouse Pick Sheet & Layout Planner")

if 'Client' in df_stock_raw.columns:
    all_clients = df_stock_raw['Client'].dropna().unique()
    selected_clients = st.multiselect("Select Clients to Pick For:", all_clients)
else:
    st.error("Could not find 'Client' column in stock report.")
    selected_clients = []

# If clients are selected, we process data and show map
if selected_clients:
    # --- 3. DATA PROCESSING ---
    
    # A. Filter stock for selected clients
    filtered_stock = df_stock_raw[df_stock_raw['Client'].isin(selected_clients)]
    
    # B. Identify Shared Bays among SELECTED clients
    bay_client_counts = filtered_stock.groupby('Bay')['Client'].nunique().reset_index()
    bay_client_counts.rename(columns={'Client': 'Selected_Client_Count'}, inplace=True)
    
    # C. Merge blueprint with the selected stock counts
    # Using 'left' merge keeps all layout bays visible even if they have no stock
    map_data = pd.merge(
        df
