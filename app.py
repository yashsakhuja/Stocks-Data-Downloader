import appdirs as ad
ad.user_cache_dir = lambda *args: "/tmp"

import streamlit as st
from datetime import date
from dateutil.relativedelta import relativedelta
import yfinance as yf
import pandas as pd
from google.oauth2 import service_account
import gspread
from gspread_pandas import Spread,Client

# Streamlit page configuration
st.set_page_config(layout="wide")

st.title("💵 💹 Stocks Data Downloader")
st.caption('Using Yahoo Finance API')

# Initialize or reset session state
def initialize_session_state():
    st.session_state.step = 1
    st.session_state.tickers = []
    st.session_state.dates = None
    st.session_state.final_data = None

# Check if session state is already initialized, if not initialize it
if 'step' not in st.session_state:
    initialize_session_state()

# Step 1: User inputs for tickers and dates
if st.session_state.step == 1:
    # Input for comma-separated stock tickers
    tickers_input = st.text_area("Enter Comma Separated Stock Tickers", value="LICI.NS, INFY.NS, HDFCBANK.NS, WIPRO.NS, TATAMOTORS.NS, BHARTIARTL.BO, TCS.NS")

    # Input for end date, defaulting to today
    end_date = st.date_input("Enter Latest Date", value=date.today())

    # Slider for number of years
    nyears = st.slider("Number of Years", 1, 15)

    # Calculate the default start date as n years before the end date
    default_date_ly = end_date - relativedelta(years=nyears)

    # Input for custom start date, defaulting to the calculated start date
    start_date = st.date_input("Or Enter Custom Start Date", value=default_date_ly)

    # Submit button for step 1
    if st.button('Submit'):
        st.session_state.tickers = [ticker.strip() for ticker in tickers_input.split(",")]
        st.session_state.dates = pd.DataFrame({
            'Ticker': st.session_state.tickers,
            'Start Date': [start_date] * len(st.session_state.tickers),
            'End Date': [end_date] * len(st.session_state.tickers)
        })
        st.session_state.step = 2

# Step 2: Display the DataFrame for user adjustments
if st.session_state.step == 2:
    st.write("Modify the tickers or customise start and end dates using the editable dataframe below if needed, then submit again to prepare data.")
    edited_dates = st.data_editor(st.session_state.dates, num_rows="dynamic")

    # Final submit button
    if st.button('Prepare Data'):
        # Store edited dates back to session state
        st.session_state.dates = edited_dates

        tickers_list = edited_dates['Ticker'].tolist()
        start_dates = edited_dates['Start Date'].tolist()
        end_dates = edited_dates['End Date'].tolist()

        # Initialize empty DataFrame to store combined data
        final_data = pd.DataFrame()

        # Download data for each ticker
        for ticker, start, end in zip(tickers_list, start_dates, end_dates):
            data = yf.download(ticker, start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'), progress=False)
            data['Ticker'] = ticker
            data.reset_index(inplace=True)
            final_data = pd.concat([final_data, data])

        # Extract the 'Close' prices
        final_data = final_data[['Date', 'Ticker', 'Close']]

        # Convert Timestamp to string to avoid JSON serialization issues
        final_data['Date'] = final_data['Date'].astype(str)

        # Display the transformed data
        st.dataframe(final_data)

        st.session_state.final_data = final_data
        st.session_state.step = 3

# Step 3: Provide options to download data or update Google Sheets
if st.session_state.step == 3:
    # CSV Conversion of dataframe
    data_as_csv = st.session_state.final_data.to_csv(index=False).encode("utf-8")

    # Download CSV
    st.download_button("Download Data", data_as_csv, "yfinance_data.csv", "text/csv", key='download-csv')

    if st.button('Update the Google Sheets', key="gsheets_button"):
        # Create the Google Sheets authentication scope
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

        credentials=service_account.Credentials.from_service_account_info(st.secrets,scopes=scope)

        client= Client(scope=scope,creds=credentials)

        spreadsheetname="YFinance Data"
        spread=Spread(spreadsheetname,client=client)

        st.write(spread.url)

        #Call our spreadsheet
        sh=client.open(spreadsheetname)

        # Select the "Live Match" worksheet
        worksheet = sh.worksheet('Data')

        # Clear the worksheet
        worksheet.clear()

        # Update the worksheet with new data
        worksheet.update([st.session_state.final_data.columns.values.tolist()] + st.session_state.final_data.values.tolist())

        st.balloons()

    # Button to reset the session state
    if st.button("Start Over"):
        initialize_session_state()
        st.experimental_rerun()
