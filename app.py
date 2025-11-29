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
    """Return the latest CSV file (by mtime) in directory_path."""
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


def list_rrg_gifs(gif_dir: str) -> List[Tuple[str, Optional[dt]]]:
    """
    List GIF files in gif_dir and attempt to parse YYYYMMDD from their filenames.
    Returns list of tuples: (filename, parsed_date_or_None).
    """
    out = []
    if not os.path.isdir(gif_dir):
        return out
    gif_files = [f for f in os.listdir(gif_dir) if f.lower().endswith(".gif")]
    date_pattern = re.compile(r"(\d{8})")
    for f in gif_files:
        parsed_date = None
        m = date_pattern.search(f)
        if m:
            try:
                parsed_date = dt.strptime(m.group(1), "%Y%m%d")
            except Exception:
                parsed_date = None
        out.append((f, parsed_date))

    # sort by parsed_date desc then by mtime desc as fallback
    def sort_key(item):
        fname, pdx = item
        if pdx:
            return (0, pdx)  # parsed dates first
        # fallback: mtime
        try:
            mtime = os.path.getmtime(os.path.join(gif_dir, fname))
        except Exception:
            mtime = 0
        return (1, dt.fromtimestamp(mtime))

    out_sorted = sorted(out, key=sort_key, reverse=True)
    return out_sorted


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


def read_gif_frames(gif_path: str) -> List[np.ndarray]:
    """
    Read frames from a GIF using imageio.
    Returns list of numpy arrays (H,W,3) for frames (RGB).
    """
    try:
        frames = imageio.mimread(gif_path)
        # imageio sometimes returns rgba; normalize to rgb uint8 arrays
        norm_frames = []
        for fr in frames:
            arr = np.asarray(fr)
            if arr.ndim == 3 and arr.shape[2] == 4:
                arr = arr[:, :, :3]
            elif arr.ndim == 2:
                arr = np.stack([arr] * 3, axis=2)
            # ensure dtype uint8
            if arr.dtype != np.uint8:
                arr = (
                    (255 * (arr.astype(float) / arr.max())).astype(np.uint8)
                    if arr.max()
                    else arr.astype(np.uint8)
                )
            norm_frames.append(arr)
        return norm_frames
    except Exception:
        return []


# -------------------------
# Streamlit app
# -------------------------
def main():
    st.set_page_config(layout="wide", page_title="Stockfilter Streamlit Dashboard")
    st.title("Stockfilter Dashboard")

    st.markdown(
        "This page shows the latest VCP CSV data and a visual RRG GIF (if available) with sector reference."
    )
    st.markdown("---")

    # -------------------------
    # CSV area (left top)
    # -------------------------
    data_dir = os.path.join("public", "data")
    all_csvs = get_all_csv_files(data_dir)
    latest_csv_file, latest_csv_time = get_latest_csv_file(data_dir)

    if latest_csv_file:
        try:
            latest_csv = pd.read_csv(os.path.join(data_dir, latest_csv_file))
        except Exception as e:
            latest_csv = pd.DataFrame()
            st.error(f"Failed to load latest CSV ({latest_csv_file}): {e}")
    else:
        latest_csv = pd.DataFrame()

    col_csv_left, col_csv_right = st.columns(2)

    with col_csv_left:
        st.subheader("Latest VCP CSV")
        if latest_csv_file:
            ts = (
                dt.fromtimestamp(latest_csv_time).strftime("%Y-%m-%d %H:%M:%S")
                if latest_csv_time
                else "N/A"
            )
            st.write(f"Latest file: **{latest_csv_file}** (updated: {ts})")
            st.dataframe(latest_csv)
        else:
            st.info(f"No CSV files found in {data_dir}")

    with col_csv_right:
        st.subheader("Comparison CSV")
        comparison_files = [f for f in all_csvs if f != latest_csv_file]
        if comparison_files:
            sel = st.selectbox("Select a CSV to compare", options=comparison_files)
            try:
                df_sel = pd.read_csv(os.path.join(data_dir, sel))
                st.dataframe(df_sel)
            except Exception as e:
                st.error(f"Failed to load {sel}: {e}")
        else:
            st.info("No other CSVs available for comparison")

    st.markdown("---")

    # -------------------------
    # RRG GIF area
    # -------------------------
    st.subheader("RRG Animation and Sector Reference")

    gif_dir = os.path.join("public", "data", "rrg_gif")
    # Controls: Refresh button, GIF selectbox, Pause checkbox, Frame slider when paused
    control_col, display_col = st.columns([1, 3])

    # Refresh button: force re-scan of files (we call st.experimental_rerun to refresh UI)
    with control_col:
        if st.button("Refresh GIF list"):
            # Force a rerun so list_rrg_gifs updates
            st.experimental_rerun()

    # Gather GIF files (sorted)
    gif_items = list_rrg_gifs(gif_dir)  # list of (filename, parsed_date)
    gif_filenames = [f for f, _ in gif_items]

    if not gif_filenames:
        st.info(f"No GIF files found in {gif_dir}")
        # still show sector table on the right in the layout below
        selected_gif = None
    else:
        # Provide dropdown for selecting older gifs. Default is first item (most recent).
        selected = st.selectbox(
            "Choose GIF (most recent first)", options=gif_filenames, index=0
        )
        selected_gif = os.path.join(gif_dir, selected)

    # Playback controls
    pause_checkbox = st.checkbox(
        "Pause animation (show static frame & manual frame slider)", value=False
    )
    auto_refresh_checkbox = st.checkbox(
        "Auto-refresh GIF on page reload (no-op for now)",
        value=False,
        help="When checked the app will still need a manual refresh trigger to rescan files; this checkbox is here for UX parity.",
    )

    # Display area
    with display_col:
        if selected_gif and os.path.exists(selected_gif):
            st.markdown(f"**Selected GIF:** `{os.path.basename(selected_gif)}`")
            if pause_checkbox:
                # Read frames and show first frame + slider to navigate
                frames = read_gif_frames(selected_gif)
                if not frames:
                    st.error("Failed to read frames from the GIF.")
                else:
                    n_frames = len(frames)
                    # choose a default start frame (last frame to represent latest)
                    default_idx = n_frames - 1
                    frame_idx = st.slider(
                        "Frame", min_value=0, max_value=n_frames - 1, value=default_idx
                    )
                    # show the selected static frame
                    try:
                        st.image(frames[frame_idx], use_column_width=True)
                        st.caption(f"Frame {frame_idx + 1} / {n_frames}")
                    except Exception as e:
                        st.error(f"Failed to render frame: {e}")
            else:
                # show the animated gif directly
                try:
                    st.image(selected_gif, use_container_width=True)
                    st.caption("Playing animation (GIF)")
                except Exception as e:
                    st.error(f"Failed to display GIF: {e}")
        else:
            st.info("No GIF selected or file not found.")

    # Right column: Sector reference (fixed list)
    right_wrapper = st.container()
    with right_wrapper:
        st.markdown("### Sector reference (SPDR Sector ETFs)")
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
