import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="Warehouse Pick Planner")

# --- 1. DATA LOADING ---
@st.cache_data(ttl=600) # Caches data for 10 minutes
def load_data():
    # Your Google Sheet converted to a direct CSV export link using your specific Document ID and GID
    stock_sheet_url = "https://docs.google.com/spreadsheets/d/1NiSNnc3bTqCshnivZZ6WMYhdCS0yLZHh_87LL3BS3hU/export?format=csv&gid=1304057791"
    
    # IMPORTANT: Replace this with the RAW GitHub URL of your master_blueprint.csv
    # Example: "https://raw.githubusercontent.com/YourUsername/YourRepo/main/master_blueprint.csv"
    blueprint_url = "master_blueprint.csv" 
    
    # Load both dataframes
    df_stock = pd.read_csv(stock_sheet_url)
    df_blueprint = pd.read_csv(blueprint_url)
    
    # Clean up column names to avoid trailing spaces just in case
    df_stock.columns = df_stock.columns.str.strip()
    df_blueprint.columns = df_blueprint.columns.str.strip()
    
    # Merge the coordinates onto the stock report based on the Bay name
    merged_df = pd.merge(
        df_stock, 
        df_blueprint, 
        left_on='Bay', 
        right_on='bay_name', 
        how='left'
    )
    
    return merged_df

# Attempt to load data, with a nice error message if the GitHub URL isn't set yet
try:
    df = load_data()
except Exception as e:
    st.error(f"Error loading data. Did you replace the GitHub Raw URL? Details: {e}")
    st.stop()

# --- 2. USER INTERFACE ---
st.title("📦 Warehouse Pick Sheet & Layout Planner")

# Assuming your column is strictly named 'Client' based on your headers
if 'Client' in df.columns:
    all_clients = df['Client'].dropna().unique()
    selected_clients = st.multiselect("Select Clients to Pick For:", all_clients)
else:
    st.error("Could not find the 'Client' column. Please check your Google Sheet headers.")
    selected_clients = []

if selected_clients:
    # Filter data for selected clients
    filtered_df = df[df['Client'].isin(selected_clients)]
    
    # --- 3. SHARED LOCATION LOGIC ---
    bay_client_counts = filtered_df.groupby('Bay')['Client'].nunique().reset_index()
    bay_client_counts.rename(columns={'Client': 'Unique_Clients_Count'}, inplace=True)
    
    display_df = pd.merge(filtered_df, bay_client_counts, on='Bay', how='left')
    
    def determine_status(row):
        if row['Unique_Clients_Count'] > 1:
            return "Shared (Multiple Clients)"
        else:
            return f"Single Client: {row['Client']}"
            
    display_df['Bay_Status'] = display_df.apply(determine_status, axis=1)

    # --- 4. VISUALIZATION (LAYOUT MAP) ---
    st.subheader("📍 Warehouse Layout Map")
    
    if 'grid_col' in display_df.columns and 'grid_row' in display_df.columns:
        plot_df = display_df.dropna(subset=['grid_col', 'grid_row'])
        
        # Determine colors: Red for shared, Blue for single
        color_discrete_map = {
            "Shared (Multiple Clients)": "#ff4b4b", # Streamlit red
        }
        # Add dynamic colors for single clients
        for client in selected_clients:
            color_discrete_map[f"Single Client: {client}"] = "#1f77b4" # Standard blue
        
        fig = px.scatter(
            plot_df, 
            x="grid_col", 
            y="grid_row", 
            color="Bay_Status",
            color_discrete_map=color_discrete_map,
            hover_data=["Bay", "Location_Full_Name", "Client", "SKU", "Items_In_Location"],
            symbol="Bay_Status",
            title="Bay Locations (Red = Shared Bay)",
            width=1200, 
            height=700
        )
        
        fig.update_traces(marker=dict(size=18, symbol='square'))
        fig.update_yaxes(autorange="reversed", scaleanchor="x", scaleratio=1) 
        
        st.plotly_chart(fig, use_container_width=True)
        
        missing_bays = display_df[display_df['grid_col'].isna()]['Bay'].dropna().unique()
        if len(missing_bays) > 0:
            st.warning(f"⚠️ The following bays have stock but are missing from the GitHub blueprint map: {', '.join(str(b) for b in missing_bays)}")
            
    else:
        st.error("Could not find 'grid_col' or 'grid_row'. Please check your GitHub master_blueprint file headers.")

    # --- 5. PICK SHEETS EXPORT ---
    st.subheader("📄 Generated Pick Sheets")
    
    # Select specific columns to show on the pick sheet
    pick_sheet_cols = ['Client', 'Bay', 'Location_Full_Name', 'SKU', 'Items_In_Location', 'Total_Weight', 'Bay_Status']
    pick_sheet_df = display_df[[c for c in pick_sheet_cols if c in display_df.columns]]
    
    st.dataframe(pick_sheet_df, use_container_width=True)
    
    # Download Button
    csv = pick_sheet_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download Pick Sheet (CSV)",
        data=csv,
        file_name='warehouse_pick_sheet.csv',
        mime='text/csv',
    )
    
else:
    st.info("👆 Please select one or more clients from the dropdown above to generate the layout and pick sheets.")
