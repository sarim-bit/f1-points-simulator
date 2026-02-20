import pandas as pd
import os
import streamlit as st

def load_processed_season(year):
    """Purely reads from the local Parquet database."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, '..', 'data', 'processed', f'season_{year}.parquet')
    
    if os.path.exists(file_path):
        return pd.read_parquet(file_path)
    else:
        st.error(f"Database error: Season {year} not found. Please run builder.py.")
        return pd.DataFrame()