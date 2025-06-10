import streamlit as st
import pandas as pd
import numpy as np

# --- Page and Data Configuration ---
st.set_page_config(layout="wide")

# Custom colors for styling (if needed later, currently only used for table styling)
CUSTOM_COLORS = ["#2F76B9", "#3B9790", "#F5BA2E",
                 "#6A4C93", "#F77F00", "#B4BBBE", "#e6657b",
                 "#026df5", "#5aede2"]

# Load the data
ec = pd.read_csv("SOURCING & EARLY STAGE METRICS.csv")


# Proceed only if the data is loaded successfully
if ec is not None:
    # --- Data Pre-processing ---
    # Convert date columns to datetime
    ec['INVITATIONDT'] = pd.to_datetime(ec['INVITATIONDT'], errors='coerce')
    ec['ACTIVITY_CREATED_AT'] = pd.to_datetime(ec['ACTIVITY_CREATED_AT'], errors='coerce')
    ec['INSERTEDDATE'] = pd.to_datetime(ec['INSERTEDDATE'], errors='coerce')

    # Pre-process folder title columns for efficient string operations
    ec['FOLDER_LOWER'] = ec['FOLDER'].fillna('').str.strip().str.lower()
    ec['FOLDER_TO_TITLE_LOWER'] = ec['FOLDER_TO_TITLE'].fillna('').str.strip().str.lower()

    # --- Page Layout and Filters ---
    st.title("CANDIDATE PIPELINE CONVERSIONS")
    st.divider()

    st.subheader("Filters")

    # Ensure valid dates before showing the date filter
    valid_invitation_dates = ec['INVITATIONDT'].dropna()
    if valid_invitation_dates.empty:
        st.error("No valid INVITATIONDT values available in the data.")
        st.stop()

    min_date = valid_invitation_dates.min()
    max_date = valid_invitation_dates.max()

    if pd.isna(min_date) or pd.isna(max_date):
        st.error("Could not determine a valid date range from INVITATIONDT.")
        st.stop()

    # Compute default start as max_date - 60 days
    default_start_date = (max_date - pd.Timedelta(days=60)).date()

    start_date_val, end_date_val = st.date_input(
        "Select Date Range (based on Invitation Date)",
        value=[default_start_date, max_date.date()],
        min_value=min_date.date(),
        max_value=max_date.date()
    )
    start_datetime = pd.to_datetime(start_date_val)
    end_datetime = pd.to_datetime(end_date_val) + pd.Timedelta(days=1)

    with st.expander("Select Work Location(s)"):
        unique_worklocations = sorted(ec['CAMPAIGN_SITE'].dropna().unique())
        selected_worklocations = st.multiselect(
            "Work Location",
            options=unique_worklocations,
            default=[]
        )

    with st.expander("Select Campaign Title(s)"):
        unique_campaigns = sorted(ec['CAMPAIGNTITLE'].dropna().unique())
        selected_campaigns = st.multiselect(
            "Campaign Title",
            options=unique_campaigns,
            default=[]
        )
    st.divider()

    # --- Filter Data Based on Selections ---
    filtered_ec = ec.copy()

    # Apply date filter
    filtered_ec = filtered_ec[
        (filtered_ec['INVITATIONDT'] >= start_datetime) &
        (filtered_ec['INVITATIONDT'] < end_datetime)
    ]

    # Apply optional filters if selections were made
    if selected_worklocations:
        filtered_ec = filtered_ec[filtered_ec['CAMPAIGN_SITE'].isin(selected_worklocations)]

    if selected_campaigns:
        filtered_ec = filtered_ec[filtered_ec['CAMPAIGNTITLE'].isin(selected_campaigns)]

    # Stop if filters result in an empty DataFrame
    if filtered_ec.empty:
        st.warning("No data matches the current filter criteria.")
        st.stop()
        
    # --- Calculations on Filtered Data ---
    
    # Define system folders and convert to lowercase for matching
    SYSTEM_FOLDERS = [
        'inbox', 'unresponsive', 'completed', 'unresponsive talkscore', 'passed mq', 'failed mq',
        'talkscore retake', 'unresponsive talkscore retake', 'failed talkscore', 'cold leads',
        'cold leads talkscore', 'cold leads talkscore retake', 'on hold', 'rejected',
        'talent pool', 'shortlisted', 'hired'
    ]

    # Calculate 'Hired' counts using the cleaned 'FOLDER_LOWER' column
    hired_counts = filtered_ec[filtered_ec['FOLDER_LOWER'] == 'hired'].groupby(['SOURCE', 'TALKSCORE_CEFR'])['CAMPAIGNINVITATIONID'].nunique()
    hired_counts = hired_counts.reset_index().rename(columns={'CAMPAIGNINVITATIONID': 'Hired'})

    # Calculate 'Unique Endorsed' counts using the cleaned 'FOLDER_TO_TITLE_LOWER' column
    endorsed_counts = filtered_ec[~filtered_ec['FOLDER_TO_TITLE_LOWER'].isin(SYSTEM_FOLDERS)].groupby(['SOURCE', 'TALKSCORE_CEFR'])['CAMPAIGNINVITATIONID'].nunique()
    endorsed_counts = endorsed_counts.reset_index().rename(columns={'CAMPAIGNINVITATIONID': 'Unique Endorsed'})

    # Merge hired and endorsed dataframes
    merged_df = pd.merge(hired_counts, endorsed_counts, on=['SOURCE', 'TALKSCORE_CEFR'], how='outer')

    # Calculate 'Conversion Rate'
    merged_df['Conversion Rate'] = np.divide(merged_df['Hired'], merged_df['Unique Endorsed']) * 100
    
    # --- Pivot Table Creation and Formatting ---

    if merged_df.empty:
        st.warning("No Hired or Endorsed data to display for the current filter criteria.")
        st.stop()
        
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
    
    st.markdown("### SOURCING & EARLY STAGE METRICS")
    st.dataframe(display_table)
