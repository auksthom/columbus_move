import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Warehouse Pick Planner")

# --- 1. DATA LOADING ---
@st.cache_data(ttl=600)
def load_data():
    stock_sheet_url = "https://docs.google.com/spreadsheets/d/1NiSNnc3bTqCshnivZZ6WMYhdCS0yLZHh_87LL3BS3hU/export?format=csv&gid=1304057791"
    
    # !!! REMINDER: Replace with your actual RAW GitHub URL !!!
    blueprint_url = "master_blueprint.csv" 
    
    try:
        df_stock = pd.read_csv(stock_sheet_url)
        df_blueprint = pd.read_csv(blueprint_url)
    except Exception as e:
        st.error(f"Error loading data files. Please check URLs. Error: {e}")
        st.stop()
    
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
    # We use a LEFT merge on blueprint to ensure EVERY bay exists in final map
    map_data = pd.merge(
        df_blueprint,
        bay_client_counts,
        left_on='bay_name',
        right_on='Bay',
        how='left'
    )
    
    # D. Define the status for coloring
    # Statuses: 0 (Gray), 1 (Blue), 2+ (Red)
    def determine_map_status(row):
        if pd.isna(row['Selected_Client_Count']) or row['Selected_Client_Count'] == 0:
            return 0 # No Selected Stock
        elif row['Selected_Client_Count'] == 1:
            return 1 # Single Client
        else:
            return 2 # Shared Location
            
    map_data['Map_Status_Id'] = map_data.apply(determine_map_status, axis=1)

    # We need text labels for the heatmap legend/hover
    status_map = {0: "No Selected Stock", 1: "Single Client", 2: "Shared (Multiple Clients)"}
    map_data['Bay_Status'] = map_data['Map_Status_Id'].map(status_map)

    # --- 4. VISUALIZATION (HEATMAP GRID) ---
    st.subheader("📍 Warehouse Layout Map")
    
    if 'grid_col' in map_data.columns and 'grid_row' in map_data.columns:
        
        # We need a matrix structure for the heatmap. 
        # Pivot the data: Rows are grid_row, Cols are grid_col, Values are status ID
        grid_pivot = map_data.pivot(index='grid_row', columns='grid_col', values='Map_Status_Id')
        
        # Pivot another one for the hover text (Bay Names)
        text_pivot = map_data.pivot(index='grid_row', columns='grid_col', values='bay_name')

        # Define custom discrete colorscale
        # 0 -> Light Gray, 1 -> Blue, 2 -> Red
        colorscale = [
            [0, '#e0e0e0'], # Light Gray (No stock)
            [0.5, '#1f77b4'], # Blue (Single)
            [1, '#ff4b4b']  # Red (Shared)
        ]

        # Create Heatmap using graph_objects for better control over gridlines
        fig = go.Figure(data=go.Heatmap(
            z=grid_pivot.values,
            x=grid_pivot.columns,
            y=grid_pivot.index,
            colorscale=colorscale,
            showscale=False, # Hide the colorbar, we will use a custom legend
            xgap=1, # REQUIRED: This creates the visible vertical grid lines
            ygap=1, # REQUIRED: This creates the visible horizontal grid lines
            hoverinfo='text',
            text=text_pivot.values # Show Bay Name on hover
        ))

       fig.update_layout(
            title="Warehouse Grid (Red = Shared, Gray = Empty/Other)",
            xaxis=dict(title="Column", tickmode='linear'),
            yaxis=dict(title="Row", tickmode='linear', autorange="reversed"), 
            width=1200,
            height=700,
            plot_bgcolor='black' # <-- Changed this to black
        )
        
        # Maintain square aspect ratio so it looks like a floor plan
        fig.update_yaxes(scaleanchor="x", scaleratio=1)

        # Custom Legend
        fig.add_annotation(xref="paper", yref="paper", x=1.02, y=0.9, text="<b>Legend:</b>", showarrow=False, font=dict(size=14))
        fig.add_annotation(xref="paper", yref="paper", x=1.02, y=0.85, text="▇ Shared", showarrow=False, font=dict(color="#ff4b4b"))
        fig.add_annotation(xref="paper", yref="paper", x=1.02, y=0.80, text="▇ Single Client", showarrow=False, font=dict(color="#1f77b4"))
        fig.add_annotation(xref="paper", yref="paper", x=1.02, y=0.75, text="▇ No Selected Stock", showarrow=False, font=dict(color="#bdbdbd"))

        st.plotly_chart(fig, use_container_width=True)
            
    else:
        st.error("Could not find grid coordinates in blueprint.")

    # --- 5. PICK SHEETS DATA TABLE ---
    st.subheader("📄 Generated Pick Data")
    # Join filtered stock back to status for the table
    table_df = pd.merge(filtered_stock, bay_client_counts, on='Bay', how='left')
    table_df['Bay_Status'] = table_df['Selected_Client_Count'].apply(lambda x: "Shared" if x > 1 else "Single")
    
    st.dataframe(table_df[['Client', 'Bay', 'Location_Full_Name', 'SKU', 'Items_In_Location', 'Bay_Status']], use_container_width=True)
    
else:
    st.info("👆 Please select clients to visualize the layout.")
