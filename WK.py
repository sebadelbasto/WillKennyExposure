import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Add Adviser Name
st.write(f"### Will Keny - Canaccord Genuity Australia")
df = pd.read_excel('final_processed_exposure_data.xlsx')

# Ensure 'Maturity Date' is in datetime format
df['Maturity Date'] = pd.to_datetime(df['Maturity Date'], errors='coerce')

# Drop rows with invalid Maturity Dates
df = df.dropna(subset=['Maturity Date'])

# Set today's date
today = pd.to_datetime(datetime.today().date())

# Sidebar for interactive filters
st.sidebar.header("Filter Options")

# Clients selection with Select All/Deselect All option
clients = df['Full Name'].unique().tolist()

if st.sidebar.checkbox("Select All Clients", value=True):
    selected_clients = clients  # All clients selected
else:
    selected_clients = st.sidebar.multiselect("Select Clients", options=clients)

# Ensure selected_clients is a list
selected_clients = list(selected_clients)

# Check if any clients are selected
if len(selected_clients) == 0:
    st.warning("Please select at least one client.")
    st.stop()

# Stocks selection with Select All/Deselect All option
stocks = df['Name'].unique().tolist()

if st.sidebar.checkbox("Select All Stocks", value=True):
    selected_stocks = stocks  # All stocks selected
else:
    selected_stocks = st.sidebar.multiselect("Select Stocks", options=stocks)

# Ensure selected_stocks is a list
selected_stocks = list(selected_stocks)

# Check if any stocks are selected
if len(selected_stocks) == 0:
    st.warning("Please select at least one stock.")
    st.stop()

# Filter data based on user input
filtered_df = df[
    (df['Full Name'].isin(selected_clients)) & 
    (df['Name'].isin(selected_stocks))
].reset_index(drop=True)

# Date range input for selecting upcoming maturities
min_maturity_date = df['Maturity Date'].min().date()
max_maturity_date = df['Maturity Date'].max().date()
default_start_date = today.date()
default_end_date = (today + pd.Timedelta(days=14)).date()  # Default to next 2 weeks

selected_maturity_dates = st.sidebar.date_input(
    "Select Maturity Date Range for Upcoming Maturities",
    value=(default_start_date, default_end_date),
    min_value=min_maturity_date,
    max_value=max_maturity_date
)

# Get products maturing within the selected period
maturities_in_period = df[
    (df['Maturity Date'] >= pd.to_datetime(selected_maturity_dates[0])) &
    (df['Maturity Date'] <= pd.to_datetime(selected_maturity_dates[1]))
]

# Get unique products maturing within the period
products_maturing = maturities_in_period['Product'].unique()

# Allow the adviser to select which products to include
selected_products = st.sidebar.multiselect(
    "Select Maturities to Include",
    options=products_maturing,
    default=products_maturing
)

# Check if any products are selected
if len(selected_products) == 0:
    st.warning("Please select at least one maturity.")
    st.stop()

# Identify products that are maturing soon based on selected products
maturing_soon = filtered_df['Product'].isin(selected_products)

# --- Adjusted Exposure Calculations ---

# Current Exposure Amount per client and stock
current_exposure = filtered_df.groupby(['Full Name', 'Name'])['Exposure Amount'].sum().reset_index()
current_exposure.rename(columns={'Exposure Amount': 'Current Exposure Amount'}, inplace=True)

# Calculate total current portfolio per client
total_current_portfolio = current_exposure.groupby('Full Name')['Current Exposure Amount'].sum().reset_index()
total_current_portfolio.rename(columns={'Current Exposure Amount': 'Total Current Portfolio'}, inplace=True)

# Merge to get total current portfolio per client
current_exposure = pd.merge(current_exposure, total_current_portfolio, on='Full Name')

# Calculate Current Exposure %
current_exposure['Current Exposure %'] = (current_exposure['Current Exposure Amount'] / current_exposure['Total Current Portfolio']) * 100

# Calculate Future Exposure Amount per client and stock (excluding selected maturities)
future_filtered_df = filtered_df[~filtered_df['Product'].isin(selected_products)]

future_exposure = future_filtered_df.groupby(['Full Name', 'Name'])['Exposure Amount'].sum().reset_index()
future_exposure.rename(columns={'Exposure Amount': 'Future Exposure Amount'}, inplace=True)

# Calculate total future portfolio per client
total_future_portfolio = future_exposure.groupby('Full Name')['Future Exposure Amount'].sum().reset_index()
total_future_portfolio.rename(columns={'Future Exposure Amount': 'Total Future Portfolio'}, inplace=True)

# Merge to get total future portfolio per client
future_exposure = pd.merge(future_exposure, total_future_portfolio, on='Full Name')

# Calculate Future Exposure %
future_exposure['Future Exposure %'] = (future_exposure['Future Exposure Amount'] / future_exposure['Total Future Portfolio']) * 100

# Merge current and future exposure data
exposure_df = pd.merge(current_exposure[['Full Name', 'Name', 'Current Exposure %']], 
                       future_exposure[['Full Name', 'Name', 'Future Exposure %']], 
                       on=['Full Name', 'Name'], 
                       how='outer')

# Fill NaN values with 0
exposure_df['Current Exposure %'] = exposure_df['Current Exposure %'].fillna(0)
exposure_df['Future Exposure %'] = exposure_df['Future Exposure %'].fillna(0)

# Round percentages
exposure_df['Current Exposure %'] = exposure_df['Current Exposure %'].round(2)
exposure_df['Future Exposure %'] = exposure_df['Future Exposure %'].round(2)

# Prepare a dynamic title based on selected clients
if len(selected_clients) == len(clients):
    client_names = "All Clients"
else:
    client_names = "; ".join(selected_clients)

# --- Function to Convert DataFrame to CSV for Download ---

@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv(index=False).encode('utf-8')

# Display the exposure table with dynamic title
st.write(f"### {client_names} Exposure after Upcoming Maturities ({selected_maturity_dates[0]} to {selected_maturity_dates[1]})")
st.dataframe(exposure_df[['Name', 'Current Exposure %', 'Future Exposure %']])

# Add download button for exposure data
csv_exposure = convert_df(exposure_df[['Name', 'Current Exposure %', 'Future Exposure %']])

st.download_button(
    label="Download Exposure Data as CSV",
    data=csv_exposure,
    file_name='exposure_data.csv',
    mime='text/csv',
)

# --- Adjusted Heatmaps ---

def create_heatmap(data):
    fig = px.imshow(
        data,
        labels=dict(x="Clients", y="Stocks", color="Exposure %"),
        x=data.columns,
        y=data.index,
        color_continuous_scale='Viridis',
        aspect='auto',
    )
    fig.update_layout(
        xaxis_tickangle=90,
        xaxis_title="",
        yaxis_title="",
        margin=dict(t=30),
        height=600,  # Increased height
        width=800,   # Adjusted width
    )
    fig.update_xaxes(tickfont_size=10)
    fig.update_yaxes(tickfont_size=10)
    return fig

# Prepare data for the current exposure heatmap
heatmap_data_current = exposure_df.pivot_table(
    index='Name',  # Stocks
    columns='Full Name',  # Clients
    values='Current Exposure %',
    aggfunc='first'
).fillna(0)

# Prepare data for the future exposure heatmap
heatmap_data_future = exposure_df.pivot_table(
    index='Name',
    columns='Full Name',
    values='Future Exposure %',
    aggfunc='first'
).fillna(0)

# Create heatmaps
fig_heatmap_current = create_heatmap(heatmap_data_current)
fig_heatmap_future = create_heatmap(heatmap_data_future)

# Display heatmaps side by side
col1, col2 = st.columns(2)

with col1:
    st.write("### Current Exposure Heatmap")
    st.plotly_chart(fig_heatmap_current, use_container_width=True)

with col2:
    st.write("### Future Exposure Heatmap")
    st.plotly_chart(fig_heatmap_future, use_container_width=True)

# --- Exposures Maturing Over Time Heatmap ---

st.write("### Exposures Maturing Over Time by Stock")

# Set the time granularity (e.g., weekly)
filtered_df['Week'] = filtered_df['Maturity Date'].dt.to_period('W').dt.start_time

# Aggregate the total exposure amount maturing per stock per week
heatmap_data = filtered_df.groupby(['Name', 'Week'])['Exposure Amount'].sum().reset_index()

# Create a pivot table for the heatmap
heatmap_pivot = heatmap_data.pivot_table(
    index='Name',  # Stocks
    columns='Week',  # Weeks
    values='Exposure Amount',
    fill_value=0
)

# Reindex to include all stocks and all weeks
all_stocks = df['Name'].unique()
all_weeks = pd.date_range(start=filtered_df['Week'].min(), end=filtered_df['Week'].max(), freq='W-MON')

heatmap_pivot = heatmap_pivot.reindex(index=all_stocks, columns=all_weeks, fill_value=0)

# Create the heatmap
fig_heatmap_timeline = px.imshow(
    heatmap_pivot,
    labels=dict(x="Week", y="Stock", color="Maturing Exposure Amount"),
    x=heatmap_pivot.columns.strftime('%Y-%m-%d'),
    y=heatmap_pivot.index,
    aspect='auto',
    color_continuous_scale='Viridis'
)

fig_heatmap_timeline.update_layout(
    xaxis_tickangle=45,
    height=600,
    width=800,
    margin=dict(t=30)
)

st.plotly_chart(fig_heatmap_timeline)

st.write(f"### {client_names} Exposures per Stock and Maturity Timeline")

# Create a DataFrame with all combinations of clients, stocks, and maturity dates
all_maturity_dates = pd.to_datetime(filtered_df['Maturity Date'].unique())
all_combinations = pd.MultiIndex.from_product(
    [selected_clients, selected_stocks, all_maturity_dates],
    names=['Full Name', 'Name', 'Maturity Date']
).to_frame(index=False)

# Merge with the existing data to get exposure information
chart_df = pd.merge(
    all_combinations,
    filtered_df[['Full Name', 'Name', 'Maturity Date', 'Exposure Amount']],
    on=['Full Name', 'Name', 'Maturity Date'],
    how='left'
)

# Fill NaN values for exposures with 0
chart_df['Exposure Amount'] = chart_df['Exposure Amount'].fillna(0)

# Merge exposure percentages into chart_df
chart_df = chart_df.merge(
    exposure_df[['Full Name', 'Name', 'Current Exposure %', 'Future Exposure %']],
    on=['Full Name', 'Name'],
    how='left'
)

# Replace NaN values in percentages with 0
chart_df['Current Exposure %'] = chart_df['Current Exposure %'].fillna(0)
chart_df['Future Exposure %'] = chart_df['Future Exposure %'].fillna(0)

# Create the scatter plot for exposures
fig = px.scatter(
    chart_df,
    x='Maturity Date',
    y='Name',
    size='Exposure Amount',
    color='Full Name',
    symbol='Full Name',
    size_max=20,
    opacity=0.7,
    title='Clients Exposures per Stock and Maturity Timeline',
    custom_data=['Full Name', 'Exposure Amount', 'Current Exposure %', 'Future Exposure %']
)

# Define custom hover template
fig.update_traces(
    hovertemplate=
    'Full Name: %{customdata[0]}<br>' +
    'Maturity Date: %{x|%Y-%m-%d}<br>' +
    'Stock: %{y}<br>' +
    'Exposure Amount: %{customdata[1]:,.2f}<br>' +
    'Current Exposure %: %{customdata[2]:.2f}%<br>' +
    'Future Exposure %: %{customdata[3]:.2f}%<br>' +
    '<extra></extra>'
)

# Adjust markers to improve visibility
fig.update_traces(
    marker=dict(
        line_width=0.5,
        line_color='DarkSlateGrey'
    )
)

st.plotly_chart(fig)

# Add credits
st.markdown(
    """
    <div style='text-align: right; font-size: 10px; color: #898a8c;'>
        Built by Sebastian del Basto
    </div>
    """,
    unsafe_allow_html=True
)
