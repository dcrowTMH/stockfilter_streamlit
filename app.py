import streamlit as st
import pandas as pd
import os
from datetime import datetime as dt

# --- Helper Functions (No changes needed here, but kept for context) ---


def get_latest_csv_file(directory_path: str) -> tuple[str | None, float | None]:
    """
    Get the latest csv path from the target directory path.

    Args:
        directory_path (str): The target directory.

    Returns:
        tuple[str | None, float | None]: A tuple containing the latest filename and its modification time, or (None, None).
    """
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]
    if not csv_files:
        return None, None

    latest_file = None
    latest_time = 0

    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        file_time = os.path.getmtime(file_path)
        if file_time > latest_time:
            latest_time = file_time
            latest_file = csv_file

    return latest_file, latest_time


def get_all_csv_files(directory_path: str) -> list:
    """Gets a list of all CSV files in a directory."""
    return [f for f in os.listdir(directory_path) if f.endswith('.csv')]

# --- Main Application ---


def main():
    st.set_page_config(layout="wide")  # Use a wide layout for more space

    # Define the data path
    path = 'public/data'

    # Data Loading
    all_files = get_all_csv_files(path)
    if not all_files:
        st.error(f"No CSV files found in the '{path}' directory.")
        st.stop()

    latest_file, latest_time = get_latest_csv_file(path)
    latest_data_path = os.path.join(path, latest_file)
    file_time_str = dt.fromtimestamp(latest_time).strftime('%Y-%m-%d %H:%M:%S')

    # Read the latest data
    latest_data = pd.read_csv(latest_data_path)

    # Main display
    st.title("VCP Filtering with Benchmark Comparison")
    st.markdown("---")

    # --- Top Two DataFrames (Side-by-Side) ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Latest Data - from **{latest_file}** (updated at: {file_time_str})")
        st.dataframe(latest_data)

    with col2:
        st.subheader("Comparison Data")

        # Create a list of other files for the dropdown, excluding the latest one
        comparison_files = [f for f in all_files if f != latest_file]

        if not comparison_files:
            st.info("No other files available for comparison.")
            selected_data = None  # Ensure selected_data is defined
        else:
            # Create the dropdown
            selected_filename = st.selectbox(
                "Select a file to compare with:",
                options=comparison_files
            )

            # Load and display the data from the selected file
            selected_data_path = os.path.join(path, selected_filename)
            selected_data = pd.read_csv(selected_data_path)
            st.dataframe(selected_data)

    # Common Symbols in both dataframes
    st.markdown("---")
    st.subheader("Symbols Present in Both Datasets")

    # Check if both dataframes are loaded before trying to find duplicates
    if selected_data is not None and not latest_data.empty:
        # Assuming the column to join on is 'symbol'. Change if necessary.
        key_column = 'symbol'

        if key_column not in latest_data.columns or key_column not in selected_data.columns:
            st.warning(
                f"The key column '{key_column}' was not found in one or both of the files.")
        else:
            # Find common symbols
            common_symbols = pd.merge(
                latest_data, selected_data, on=key_column, how='inner')

            if common_symbols.empty:
                st.info("No common symbols found between the two selected files.")
            else:
                # Display the merged dataframe with data from both files for the common symbols
                st.write(f"Found {len(common_symbols)} common symbols.")
                # The suffixes help distinguish columns from the left (_latest) and right (_selected) files
                st.dataframe(pd.merge(
                    latest_data,
                    selected_data,
                    on=key_column,
                    how='inner',
                    suffixes=('_latest', '_selected')
                ))
    
    st.markdown("---")
    # Footer
    st.write('Disclaimer: These analyses are for self-taught & self-reference only.')


if __name__ == "__main__":
    main()
