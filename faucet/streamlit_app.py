import streamlit as st
import requests
from datetime import datetime
import pandas as pd

# Configure API base URL
API_BASE_URL = "http://localhost:8000/api"  # Use full URL in Docker

def fund_tab():
    st.header("Request Sepolia ETH")
    wallet_address = st.text_input("Wallet Address", placeholder="0x...")
    
    if st.button("Request Funds"):
        if wallet_address:
            try:
                response = requests.post(
                    f"{API_BASE_URL}/fund",
                    json={"wallet_address": wallet_address}
                )
                if response.status_code == 200:
                    st.success(f"Transaction Hash: {response.json()['transaction_hash']}")
                else:
                    st.error(f"Error: {response.json().get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            st.warning("Please enter a wallet address")

def stats_tab():
    st.header("Faucet Statistics")
    if st.button("Refresh Stats"):
        try:
            response = requests.get(f"{API_BASE_URL}/stats")
            if response.status_code == 200:
                data = response.json()
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Transactions", data["total_transactions"])
                    st.metric("Last 24h Transactions", data["last_24h_transactions"])
                with col2:
                    st.metric("Successful Transactions", data["successful_transactions"])
                    st.metric("Failed Transactions", data["failed_transactions"])
            else:
                st.error("Failed to fetch statistics")
        except Exception as e:
            st.error(f"Error: {str(e)}")

def transactions_tab():
    st.header("Transaction History")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        from_date = st.date_input("From Date")
        from_time = st.time_input("From Time", value=datetime.min.time())
    with col2:
        to_date = st.date_input("To Date")
        to_time = st.time_input("To Time", value=datetime.max.time())
    with col3:
        wallet = st.text_input("Wallet Address (optional)", placeholder="0x...")
    
    if st.button("Search Transactions"):
        params = {}
        if from_date:
            from_datetime = datetime.combine(from_date, from_time)
            params["from_date"] = from_datetime.isoformat()
        if to_date:
            to_datetime = datetime.combine(to_date, to_time)
            params["to_date"] = to_datetime.isoformat()
        if wallet:
            params["wallet"] = wallet
            
        try:
            response = requests.get(f"{API_BASE_URL}/transactions", params=params)
            if response.status_code == 200:
                transactions = response.json()
                if transactions:
                    df = pd.DataFrame(transactions)
                    st.dataframe(df)
                else:
                    st.info("No transactions found")
            else:
                st.error(f"Error: {response.json().get('error', 'Unknown error')}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

def main():
    st.set_page_config(page_title="Sepolia Faucet", layout="wide")
    st.title("Sepolia Faucet")
    
    tab1, tab2, tab3 = st.tabs(["Request Funds", "Statistics", "Transactions"])
    
    with tab1:
        fund_tab()
    with tab2:
        stats_tab()
    with tab3:
        transactions_tab()

if __name__ == "__main__":
    main() 