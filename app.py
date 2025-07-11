import streamlit as st
import pandas as pd
import os
from datetime import datetime as dt


def get_latest_csv_file(directory_path) -> str | None:

    """
    Get the latest csv path from the target directory path

    args:
        directory_path: str, target directory
    return:
        latest_file: str, latest updated csv file in the repo
    """
    # list out all the csv files in the target path
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]
    
    # return None if there's no csv file
    if not csv_files:
        return None

    # define the latest file and updated time for comparison
    latest_file = None
    latest_time = 0

    # loop through all the csv file 
    for csv_file in csv_files:
        # get the target path to get the updated time
        file_path = os.path.join(directory_path, csv_file)
        file_time = os.path.getmtime(file_path)

        # compare the time for the latest file
        if file_time > latest_time:
            latest_time = file_time
            latest_file = csv_file

    return latest_file, latest_time


def main():
    # get the path for the latest csv file in the data folder
    path = 'public/data'
    latest_file, latest_time = get_latest_csv_file(path)
    data_path = os.path.join(path, latest_file)
    file_time = latest_file.split('_')[0]
    # read the data
    data = pd.read_csv(data_path)
    # simple display on the data
    st.title(f"VCP filtering")
    st.write(f'data updated at: {file_time}')
    st.write('Here is a result DataFrame:')
    st.dataframe(data)


if __name__ == "__main__":
    main()
