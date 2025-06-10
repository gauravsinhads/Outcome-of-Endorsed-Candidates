import streamlit as st
import pandas as pd
import numpy as np

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Outcome of Endorsed Candidates"
)

# --- Global Constants ---
# Define system folders that are not considered 'endorsements'.
# Using a set of lowercase strings provides faster lookups.
SYSTEM_FOLDERS = {
    'inbox', 'unresponsive', 'completed', 'unresponsive talkscore', 'passed mq', 'failed mq',
    'talkscore retake', 'unresponsive talkscore retake', 'failed talkscore', 'cold leads',
    'cold leads talkscore', 'cold leads talkscore retake', 'on hold', 'rejected',
    'talent pool', 'shortlisted', 'hired'
}

# --- Data Loading and Caching ---
@st.cache_data
def load_and_process_data(file_path):
    """
    Loads data from a CSV file, performs initial cleaning and type conversion,
    and returns a DataFrame. Caching this function improves app performance.
    """
    try:
        df = pd.read_csv(file_path)
        # Convert date columns to datetime, coercing errors to NaT (Not a Time)
        df['INVITATIONDT'] = pd.to_datetime(df['INVITATIONDT'], errors='coerce')
        df['ACTIVITY_CREATED_AT'] = pd.to_datetime(df['ACTIVITY_CREATED_AT'], errors='coerce')
        df['INSERTEDDATE'] = pd.to_datetime(df['INSERTEDDATE'], errors='coerce')

        # Pre-process folder title columns for efficient and reliable string matching
        df['FOLDER_LOWER'] = df['FOLDER'].fillna('').str.strip().str.lower()
        df['FOLDER_TO_TITLE_LOWER'] = df['FOLDER_TO_TITLE'].fillna('').str.strip().str.lower()
        return df
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found.")
        st.info("Please ensure the data file is in the same directory as the script.")
        return None

# Load the dataset
ec = load_and_process_data("SOURCING & EARLY STAGE METRICS.csv")

# --- Main Application ---
if ec is not None:
    st.title("Outcome of Endorsed Candidates")
    st.divider()

    # --- Sidebar Filters ---
    st.sidebar.header("Filters")

    # Ensure valid dates are available before showing the date filter
    valid_invitation_dates = ec['INVITATIONDT'].dropna()
    if not valid_invitation_dates.empty:
        min_date = valid_invitation_dates.min().date()
        max_date = valid_invitation_dates.max().date()
        default_start_date = max_date - pd.Timedelta(days=60)

        start_date_val, end_date_val = st.sidebar.date_input(
            "Select Date Range (Invitation Date)",
            value=[default_start_date, max_date],
            min_value=min_date,
            max_value=max_date
        )
        start_datetime = pd.to_datetime(start_date_val)
        end_datetime = pd.to_datetime(end_date_val) + pd.Timedelta(days=1)
    else:
        st.sidebar.error("No valid invitation dates found in the data.")
        st.stop()

    with st.sidebar.expander("Filter by Work Location"):
        unique_worklocations = sorted(ec['CAMPAIGN_SITE'].dropna().unique())
        selected_worklocations = st.multiselect("Work Location(s)", options=unique_worklocations, default=[])

    with st.sidebar.expander("Filter by Campaign Title"):
        unique_campaigns = sorted(ec['CAMPAIGNTITLE'].dropna().unique())
        selected_campaigns = st.multiselect("Campaign Title(s)", options=unique_campaigns, default=[])
    
    # --- Data Filtering Logic ---
    filtered_ec = ec[
        (ec['INVITATIONDT'] >= start_datetime) &
        (ec['INVITATIONDT'] < end_datetime)
    ]

    if selected_worklocations:
        filtered_ec = filtered_ec[filtered_ec['CAMPAIGN_SITE'].isin(selected_worklocations)]
    if selected_campaigns:
        filtered_ec = filtered_ec[filtered_ec['CAMPAIGNTITLE'].isin(selected_campaigns)]

    # --- Main Panel Display ---
    if filtered_ec.empty:
        st.warning("No data matches the current filter criteria.")
    else:
        # --- Calculations on Filtered Data ---
        hired_counts = filtered_ec[filtered_ec['FOLDER_LOWER'] == 'hired'].groupby(['SOURCE', 'TALKSCORE_CEFR'])['CAMPAIGNINVITATIONID'].nunique()
        hired_counts = hired_counts.reset_index().rename(columns={'CAMPAIGNINVITATIONID': 'Hired'})

        endorsed_counts = filtered_ec[~filtered_ec['FOLDER_TO_TITLE_LOWER'].isin(SYSTEM_FOLDERS)].groupby(['SOURCE', 'TALKSCORE_CEFR'])['CAMPAIGNINVITATIONID'].nunique()
        endorsed_counts = endorsed_counts.reset_index().rename(columns={'CAMPAIGNINVITATIONID': 'Unique Endorsed'})

        if hired_counts.empty and endorsed_counts.empty:
            st.info("No Hired or Endorsed data to display for the current filter criteria.")
        else:
            merged_df = pd.merge(hired_counts, endorsed_counts, on=['SOURCE', 'TALKSCORE_CEFR'], how='outer')
            merged_df['Conversion Rate'] = (merged_df['Hired'] / merged_df['Unique Endorsed']) * 100
            
            # --- Pivot Table Creation and Formatting ---
            pivot_table = merged_df.pivot_table(
                index='TALKSCORE_CEFR',
                columns='SOURCE',
                values=['Hired', 'Unique Endorsed', 'Conversion Rate']
            )
            
            pivot_table = pivot_table.swaplevel(0, 1, axis=1).sort_index(axis=1, level=0)
            
            metric_order = ['Hired', 'Unique Endorsed', 'Conversion Rate']
            all_sources = pivot_table.columns.get_level_values(0).unique()
            pivot_table = pivot_table.reindex(columns=pd.MultiIndex.from_product([all_sources, metric_order]))

            display_table = pivot_table.copy()
            for source in all_sources:
                display_table[(source, 'Hired')] = display_table[(source, 'Hired')].fillna(0).astype(int)
                display_table[(source, 'Unique Endorsed')] = display_table[(source, 'Unique Endorsed')].fillna(0).astype(int)
                display_table[(source, 'Conversion Rate')] = display_table[(source, 'Conversion Rate')].fillna(0).apply(lambda x: f'{x:.0f}%')

            display_table = display_table.astype(str).replace('0', '').replace('0%', '')
            
            st.markdown("### Endorsement & Hiring Metrics by Source and CEFR Score")
            st.dataframe(display_table, use_container_width=True)
