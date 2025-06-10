import streamlit as st
import pandas as pd
import numpy as np

# --- Page and Data Configuration ---

# Set the title of the Streamlit page 
st.set_page_config(layout="wide")
st.title('Outcome of Endorsed Candidates')

# Function to load data from a CSV file
@st.cache_data
def load_data(file_path):
    """Loads a CSV file into a pandas DataFrame."""
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found.")
        st.info(f"Please make sure '{file_path}' is in the same directory as the script.")
        return None

# Load the dataset 
file_name = "SOURCING & EARLY STAGE METRICS.csv"
ec = load_data(file_name)

# Proceed only if the data is loaded successfully
if ec is not None:
    # Define the list of folders to be excluded for 'Unique Endorsed' calculation 
    SYSTEM_FOLDERS = [
        'Inbox', 'Unresponsive', 'Completed', 'Unresponsive Talkscore', 'Passed MQ', 'Failed MQ',
        'TalkScore Retake', 'Unresponsive Talkscore Retake', 'Failed TalkScore', 'Cold Leads',
        'Cold Leads Talkscore', 'Cold Leads Talkscore Retake', 'On hold', 'Rejected',
        'Talent Pool', 'Shortlisted', 'Hired'
    ]

    # --- Data Processing and Calculations ---

    # Calculate 'Hired' counts: Unique candidates per source and CEFR level where the folder is 'hired' 
    hired_counts = ec[ec['FOLDER'] == 'hired'].groupby(['SOURCE', 'TALKSCORE_CEFR'])['CAMPAIGNINVITATIONID'].nunique()
    hired_counts = hired_counts.reset_index().rename(columns={'CAMPAIGNINVITATIONID': 'Hired'})

    # Calculate 'Unique Endorsed' counts: Unique candidates not in any system folder 
    endorsed_counts = ec[~ec['FOLDER_TO_TITLE'].isin(SYSTEM_FOLDERS)].groupby(['SOURCE', 'TALKSCORE_CEFR'])['CAMPAIGNINVITATIONID'].nunique()
    endorsed_counts = endorsed_counts.reset_index().rename(columns={'CAMPAIGNINVITATIONID': 'Unique Endorsed'})

    # Merge hired and endorsed dataframes
    merged_df = pd.merge(hired_counts, endorsed_counts, on=['SOURCE', 'TALKSCORE_CEFR'], how='outer')

    # Calculate 'Conversion Rate' = (Hired / Unique Endorsed) * 100 
    # Note: The formula is corrected based on the sample data in the table.
    merged_df['Conversion Rate'] = np.divide(merged_df['Hired'], merged_df['Unique Endorsed']) * 100
    
    # --- Pivot Table Creation and Formatting ---

    # Create the pivot table with TALKSCORE_CEFR as the index and SOURCE as columns 
    pivot_table = merged_df.pivot_table(
        index='TALKSCORE_CEFR',
        columns='SOURCE',
        values=['Hired', 'Unique Endorsed', 'Conversion Rate']
    )

    # Swap column levels to group metrics under each source
    pivot_table = pivot_table.swaplevel(0, 1, axis=1)
    pivot_table.sort_index(axis=1, level=0, inplace=True)

    # Reorder the metric columns to the specified order: Hired, Unique Endorsed, Conversion Rate
    metric_order = ['Hired', 'Unique Endorsed', 'Conversion Rate']
    all_sources = pivot_table.columns.get_level_values(0).unique()
    pivot_table = pivot_table.reindex(columns=pd.MultiIndex.from_product([all_sources, metric_order]))

    # --- Final Display Formatting ---

    # Create a copy for display purposes to format numbers and percentages
    display_table = pivot_table.copy()

    # Format each column to match the desired output style 
    for source in all_sources:
        # Format Hired and Endorsed columns
        display_table[(source, 'Hired')] = display_table[(source, 'Hired')].fillna(0).astype(int)
        display_table[(source, 'Unique Endorsed')] = display_table[(source, 'Unique Endorsed')].fillna(0).astype(int)
        
        # Format Conversion Rate column as a percentage string
        display_table[(source, 'Conversion Rate')] = display_table[(source, 'Conversion Rate')].fillna(0).apply(lambda x: f'{x:.0f}%')

    # Replace zero values with empty strings for a cleaner look, matching the example
    display_table = display_table.astype(str).replace('0', '').replace('0%', '')
    
    st.markdown("### SOURCING & EARLY STAGE METRICS")
    
    # Display the final, formatted pivot table
    st.dataframe(display_table)
