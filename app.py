# Python Code/stockfilter_streamlit/app.py
import os
import re
from datetime import datetime as dt
from typing import List, Optional, Tuple

import imageio
import numpy as np
import pandas as pd
import streamlit as st

# -------------------------
# Helper functions
# -------------------------


def get_latest_csv_file(directory_path: str) -> Tuple[Optional[str], Optional[float]]:
    """Return the latest CSV file (by modification time) in directory_path."""
    if not os.path.isdir(directory_path):
        return None, None
    csv_files = [f for f in os.listdir(directory_path) if f.lower().endswith(".csv")]
    if not csv_files:
        return None, None
    latest_file = None
    latest_time = 0.0
    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        try:
            file_time = os.path.getmtime(file_path)
        except Exception:
            continue
        if file_time > latest_time:
            latest_time = file_time
            latest_file = csv_file
    return latest_file, latest_time


def get_all_csv_files(directory_path: str) -> List[str]:
    """Return list of CSV filenames in directory_path (or empty list)."""
    if not os.path.isdir(directory_path):
        return []
    return [f for f in os.listdir(directory_path) if f.lower().endswith(".csv")]


def list_rrg_gifs_sorted(gif_dir: str) -> List[Tuple[str, Optional[dt]]]:
    """
    Return a list of GIF filenames in gif_dir sorted with:
      - files that contain YYYYMMDD in their name (parsed date) first, newest-first
      - then files without a parsable date sorted by file modification time (newest-first)

    Returns list of tuples: (filename, parsed_date_or_None)
    """
    if not os.path.isdir(gif_dir):
        return []

    gif_files = [f for f in os.listdir(gif_dir) if f.lower().endswith(".gif")]
    if not gif_files:
        return []

    date_pattern = re.compile(r"(\d{8})")
    with_date = []
    without_date = []

    for f in gif_files:
        m = date_pattern.search(f)
        if m:
            try:
                parsed = dt.strptime(m.group(1), "%Y%m%d")
                with_date.append((f, parsed))
            except Exception:
                without_date.append(f)
        else:
            without_date.append(f)

    # sort parsed-date files by date desc
    with_date.sort(key=lambda x: x[1], reverse=True)
    # sort undated files by mtime desc
    without_date.sort(
        key=lambda fn: os.path.getmtime(os.path.join(gif_dir, fn))
        if os.path.exists(os.path.join(gif_dir, fn))
        else 0,
        reverse=True,
    )

    out = [(f, d) for f, d in with_date] + [(f, None) for f in without_date]
    return out


def read_gif_frames(gif_path: str) -> List[np.ndarray]:
    """
    Read frames from a GIF using imageio and normalize to RGB uint8 numpy arrays.
    Returns a list of numpy arrays with shape (H, W, 3).
    """
    try:
        raw_frames = imageio.mimread(gif_path)
    except Exception:
        return []

    frames = []
    for fr in raw_frames:
        arr = np.asarray(fr)
        if arr.ndim == 2:
            # grayscale -> stack to RGB
            arr = np.stack([arr] * 3, axis=2)
        if arr.ndim == 3 and arr.shape[2] == 4:
            # drop alpha
            arr = arr[:, :, :3]
        # ensure uint8
        if arr.dtype != np.uint8:
            # try to normalize to 0-255
            try:
                arr = (255 * (arr.astype(float) / np.nanmax(arr))).astype(np.uint8)
            except Exception:
                arr = arr.astype(np.uint8)
        frames.append(arr)
    return frames


def build_sector_reference(symbols: List[str]) -> pd.DataFrame:
    sector_map = {
        "XLRE": "Real Estate",
        "XLF": "Financials",
        "XLV": "Health Care",
        "XLC": "Communication Services",
        "XLI": "Industrials",
        "XLY": "Consumer Discretionary",
        "XLP": "Consumer Staples",
        "XLB": "Materials",
        "XLK": "Information Technology",
        "XLU": "Utilities",
        "XLE": "Energy",
    }
    rows = [{"Symbol": s, "Sector": sector_map.get(s, "Unknown")} for s in symbols]
    return pd.DataFrame(rows)


# -------------------------
# Streamlit app
# -------------------------


def main():
    st.set_page_config(layout="wide", page_title="RRG GIF Viewer")
    st.title("Stock Analysis Viewer")

    # Directory where GIFs are stored (relative to app root)
    gif_dir = os.path.join("public", "data", "rrg_gif")

    # Gather sorted gif list
    gif_items = list_rrg_gifs_sorted(gif_dir)  # list of (filename, parsed_date_or_none)
    gif_filenames = [fname for fname, _ in gif_items]

    # Define the data path (VCP CSV area restored)
    path = "public/data"

    # Data Loading
    all_files = get_all_csv_files(path)
    if not all_files:
        st.error(f"No CSV files found in the '{path}' directory.")
        st.stop()

    latest_file, latest_time = get_latest_csv_file(path)
    latest_data_path = os.path.join(path, latest_file)
    file_time_str = dt.fromtimestamp(latest_time).strftime("%Y-%m-%d %H:%M:%S")

    # Read the latest data
    latest_data = pd.read_csv(latest_data_path)

    # Main display (VCP section)
    st.markdown("---")
    st.header("VCP Filtering with Benchmark Comparison")

    # --- Top Two DataFrames (Side-by-Side) ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(
            f"Latest Data - from **{latest_file}** (updated at: {file_time_str})"
        )
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
                "Select a file to compare with:", options=comparison_files
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
        key_column = "symbol"

        if (
            key_column not in latest_data.columns
            or key_column not in selected_data.columns
        ):
            st.warning(
                f"The key column '{key_column}' was not found in one or both of the files."
            )
        else:
            # Find common symbols
            common_symbols = pd.merge(
                latest_data, selected_data, on=key_column, how="inner"
            )

            if common_symbols.empty:
                st.info("No common symbols found between the two selected files.")
            else:
                # Display the merged dataframe with data from both files for the common symbols
                st.write(f"Found {len(common_symbols)} common symbols.")
                # The suffixes help distinguish columns from the left (_latest) and right (_selected) files
                st.dataframe(
                    pd.merge(
                        latest_data,
                        selected_data,
                        on=key_column,
                        how="inner",
                        suffixes=("_latest", "_selected"),
                    )
                )

    st.markdown("---")

    # Dropdown on top (above the two components)
    st.header("RRG analysis")
    if not gif_filenames:
        st.info(f"No GIFs found in: {gif_dir}")
        selected_name = None
    else:
        # show filenames in dropdown, most-recent (by parsed date or mtime) first
        selected_name = st.selectbox(
            "Select GIF (most recent first):", options=gif_filenames, index=0
        )

    st.markdown("---")

    # Layout: left = paused GIF with slider, right = sector reference table
    left_col, right_col = st.columns([2, 1])

    # Left: paused GIF + slider
    with left_col:
        if selected_name:
            gif_path = os.path.join(gif_dir, selected_name)
            if not os.path.exists(gif_path):
                st.error("Selected GIF file not found.")
            else:
                # Read normalized frames
                frames = read_gif_frames(gif_path)
                if not frames:
                    st.error(
                        "Could not read frames from the GIF or GIF contains no frames."
                    )
                else:
                    n = len(frames)
                    # Default to last frame (most recent)
                    default_idx = n - 1
                    frame_idx = st.slider(
                        "Frame",
                        min_value=0,
                        max_value=n - 1,
                        value=default_idx,
                        key="frame_slider",
                    )
                    # Show metadata line
                    # attempt to parse date from filename
                    m = re.search(r"(\d{8})", selected_name)
                    parsed_date = None
                    if m:
                        try:
                            parsed_date = dt.strptime(m.group(1), "%Y%m%d")
                        except Exception:
                            parsed_date = None
                    meta_text = f"File: {selected_name}"
                    if parsed_date:
                        meta_text += f" — date: {parsed_date.strftime('%Y-%m-%d')}"
                    else:
                        meta_text += f" — frames: {n}"
                    st.caption(meta_text)

                    # display the chosen frame
                    try:
                        st.image(frames[frame_idx])
                        st.caption(f"Frame {frame_idx + 1} / {n}")
                    except Exception as e:
                        st.error(f"Failed to render frame: {e}")
        else:
            st.info("No GIF selected.")

    # Right: sector table
    with right_col:
        st.markdown("### Reference")
        symbols = [
            "XLRE",
            "XLF",
            "XLV",
            "XLC",
            "XLI",
            "XLY",
            "XLP",
            "XLB",
            "XLK",
            "XLU",
            "XLE",
        ]
        sector_df = build_sector_reference(symbols)
        st.table(sector_df)

    st.markdown("---")
    st.write("Disclaimer: These analyses are for self-taught & self-reference only.")


if __name__ == "__main__":
    main()
