import os
import re
from datetime import datetime as dt
from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st

# -------------------------
# Helper functions
# -------------------------


def get_latest_csv_file(directory_path: str) -> Tuple[Optional[str], Optional[float]]:
    """
    Get the latest csv path from the target directory path based on modification time.

    Returns:
        (latest_filename, modification_time) or (None, None) if no csv found.
    """
    if not os.path.isdir(directory_path):
        return None, None

    csv_files = [f for f in os.listdir(directory_path) if f.endswith(".csv")]
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
    """Return a list of CSV files in directory (or empty list)."""
    if not os.path.isdir(directory_path):
        return []
    return [f for f in os.listdir(directory_path) if f.endswith(".csv")]


def find_latest_rrg_gif_by_filename(gif_dir: str) -> Tuple[Optional[str], Optional[dt]]:
    """
    Search the gif_dir for RRG GIFs using filename date pattern and return the latest.

    Expected filename patterns (examples):
      SPY_rrg_all_sma_20251125.gif
      SPY_rrg_all_slope_20251125.gif

    The function will:
    - try to parse YYYYMMDD from filenames using a regex,
    - pick the entry with the newest parsed date,
    - fall back to latest modification time if no date-formatted names are found.

    Returns:
        (path_to_latest_gif, parsed_date_or_mtime_datetime) or (None, None)
    """
    if not os.path.isdir(gif_dir):
        return None, None

    gif_files = [f for f in os.listdir(gif_dir) if f.lower().endswith(".gif")]
    if not gif_files:
        return None, None

    pattern = re.compile(r".*_(\d{8})\.gif$")
    candidates = []
    for f in gif_files:
        m = pattern.search(f)
        if m:
            try:
                dt_val = dt.strptime(m.group(1), "%Y%m%d")
                candidates.append((f, dt_val))
            except Exception:
                # ignore parse errors
                pass

    if candidates:
        # pick the file with the newest parsed date
        candidates.sort(key=lambda x: x[1], reverse=True)
        chosen = candidates[0][0]
        return os.path.join(gif_dir, chosen), candidates[0][1]

    # fallback to modification time
    latest_file = None
    latest_mtime = 0.0
    for f in gif_files:
        fp = os.path.join(gif_dir, f)
        try:
            mtime = os.path.getmtime(fp)
        except Exception:
            continue
        if mtime > latest_mtime:
            latest_mtime = mtime
            latest_file = f
    if latest_file:
        return os.path.join(gif_dir, latest_file), dt.fromtimestamp(latest_mtime)
    return None, None


def build_sector_reference(symbols: List[str]) -> pd.DataFrame:
    """
    Return a DataFrame with Symbol and Sector columns for known SPDR sector ETF tickers.
    The mapping below covers the standard SPDR sector tickers provided.
    """
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
    rows = []
    for s in symbols:
        rows.append({"Symbol": s, "Sector": sector_map.get(s, "Unknown")})
    return pd.DataFrame(rows)


# -------------------------
# Main Streamlit app
# -------------------------


def main():
    st.set_page_config(layout="wide", page_title="Stockfilter Streamlit Dashboard")

    st.title("Stockfilter Dashboard")
    st.markdown(
        "This page shows the latest VCP CSV data and a visual RRG GIF (if available) with sector reference."
    )
    st.markdown("---")

    # --- CSV area (existing functionality) ---
    data_path = os.path.join("public", "data")
    all_files = get_all_csv_files(data_path)

    if not all_files:
        st.error(f"No CSV files found in the '{data_path}' directory.")
        # We will still allow RRG GIF display below if available, so do not stop.
        latest_file = None
        latest_time = None
        latest_data = pd.DataFrame()
        selected_data = None
    else:
        latest_file, latest_time = get_latest_csv_file(data_path)
        latest_data = (
            pd.read_csv(os.path.join(data_path, latest_file))
            if latest_file
            else pd.DataFrame()
        )

        # Side-by-side CSV display
        st.subheader("Latest VCP Data")
        file_time_str = (
            dt.fromtimestamp(latest_time).strftime("%Y-%m-%d %H:%M:%S")
            if latest_time
            else "N/A"
        )

        col_csv_left, col_csv_right = st.columns(2)

        with col_csv_left:
            if latest_file:
                st.write(
                    f"Latest file: **{latest_file}** (updated at: {file_time_str})"
                )
                st.dataframe(latest_data)
            else:
                st.info("No latest CSV available.")

        with col_csv_right:
            st.subheader("Comparison Data")
            comparison_files = [f for f in all_files if f != latest_file]
            if not comparison_files:
                st.info("No other files available for comparison.")
                selected_data = None
            else:
                selected_filename = st.selectbox(
                    "Select a file to compare with:", options=comparison_files
                )
                selected_data_path = os.path.join(data_path, selected_filename)
                try:
                    selected_data = pd.read_csv(selected_data_path)
                    st.dataframe(selected_data)
                except Exception as e:
                    st.error(f"Failed to load {selected_filename}: {e}")
                    selected_data = None

        # Common symbols area
        st.markdown("---")
        st.subheader("Symbols Present in Both Datasets")
        if selected_data is not None and not latest_data.empty:
            key_column = "symbol"
            if (
                key_column not in latest_data.columns
                or key_column not in selected_data.columns
            ):
                st.warning(
                    f"The key column '{key_column}' was not found in one or both of the files."
                )
            else:
                merged = pd.merge(
                    latest_data,
                    selected_data,
                    on=key_column,
                    how="inner",
                    suffixes=("_latest", "_selected"),
                )
                if merged.empty:
                    st.info("No common symbols found between the two selected files.")
                else:
                    st.write(f"Found {len(merged)} common symbols.")
                    st.dataframe(merged)
        else:
            st.info("Comparison disabled or not enough data for comparison.")

    # --- RRG GIF + Sector Reference section ---
    st.markdown("---")
    st.subheader("RRG GIF (latest) and Sector Reference")

    gif_dir = os.path.join("public", "data", "rrg_gif")
    gif_path, gif_date = find_latest_rrg_gif_by_filename(gif_dir)

    # Left (GIF) and Right (Sector table)
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.markdown("### Latest RRG Animation")
        if gif_path and os.path.exists(gif_path):
            # Display GIF
            try:
                # Show a caption with parsed date
                caption = f"File: {os.path.basename(gif_path)}"
                if isinstance(gif_date, dt):
                    caption += f" — date: {gif_date.strftime('%Y-%m-%d')}"
                st.image(gif_path, use_container_width=True, caption=caption)
            except Exception as e:
                st.error(f"Failed to display GIF: {e}")
        else:
            st.info(f"No RRG GIF found in: {gif_dir}")

    with right_col:
        st.markdown("### Sector Reference (SPDR Sector ETFs)")
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
