#!/usr/bin/env python3
"""
UPS Server Dashboard - Streamlit interface for monitoring and configuration
streamlit run dashboard.py
"""

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# Configuration
DB_PATH = 'ups_clients.db'

def get_db_connection():
    """Create a database connection."""
    return sqlite3.connect(DB_PATH)

def load_client_connections():
    """Load all client connections from the database."""
    try:
        conn = get_db_connection()
        query = """
            SELECT hostname, ip_address, port, last_connection_time, seconds_to_shutdown
            FROM client_connections
            ORDER BY last_connection_time DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading client connections: {e}")
        return pd.DataFrame()

def load_configuration():
    """Load all configuration values from the database."""
    try:
        conn = get_db_connection()
        query = "SELECT key, value FROM configuration ORDER BY key"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        return pd.DataFrame()

def update_config_value(key: str, value: str):
    """Update a configuration value in the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO configuration (key, value)
            VALUES (?, ?)
        ''', (key, value))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error updating configuration: {e}")
        return False

def delete_config_value(key: str):
    """Delete a configuration value from the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM configuration WHERE key = ?', (key,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error deleting configuration: {e}")
        return False

def update_client_shutdown_time(hostname: str, seconds: int):
    """Update the seconds_to_shutdown for a client."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE client_connections
            SET seconds_to_shutdown = ?
            WHERE hostname = ?
        ''', (seconds, hostname))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error updating shutdown time: {e}")
        return False

def main():
    st.set_page_config(
        page_title="UPS Server Dashboard",
        page_icon="🔌",
        layout="wide"
    )
    
    st.title("🔌 UPS Server Dashboard")
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        st.error(f"Database not found: {DB_PATH}")
        st.info("Please start the UPS server first to initialize the database.")
        return
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Client Connections", "Configuration", "Add Configuration"])
    
    # Add refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()
    
    if page == "Client Connections":
        st.header("📡 Client Connections")
        
        clients_df = load_client_connections()
        
        if clients_df.empty:
            st.info("No client connections recorded yet.")
        else:
            st.subheader(f"Total Clients: {len(clients_df)}")
            
            # Display client connections table
            st.dataframe(
                clients_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Edit shutdown times
            st.subheader("⚙️ Edit Client Shutdown Times")
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                selected_hostname = st.selectbox(
                    "Select Client",
                    options=clients_df['hostname'].tolist()
                )
            
            with col2:
                current_seconds = clients_df[clients_df['hostname'] == selected_hostname]['seconds_to_shutdown'].iloc[0]
                new_seconds = st.number_input(
                    "Seconds to Shutdown",
                    min_value=0,
                    max_value=3600,
                    value=int(current_seconds),
                    step=10
                )
            
            with col3:
                st.write("")  # Spacer
                st.write("")  # Spacer
                if st.button("Update"):
                    if update_client_shutdown_time(selected_hostname, new_seconds):
                        st.success(f"Updated {selected_hostname} shutdown time to {new_seconds} seconds")
                        st.rerun()
    
    elif page == "Configuration":
        st.header("⚙️ Server Configuration")
        
        config_df = load_configuration()
        
        if config_df.empty:
            st.info("No configuration values found.")
        else:
            st.subheader(f"Configuration Values: {len(config_df)}")
            
            # Display configuration in an editable format
            for idx, row in config_df.iterrows():
                key = row['key']
                value = row['value']
                
                with st.expander(f"🔑 {key}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        new_value = st.text_input(
                            "Value",
                            value=value,
                            key=f"input_{key}"
                        )
                    
                    with col2:
                        st.write("")  # Spacer
                        st.write("")  # Spacer
                        update_col, delete_col = st.columns(2)
                        
                        with update_col:
                            if st.button("💾", key=f"update_{key}", help="Update"):
                                if update_config_value(key, new_value):
                                    st.success(f"Updated {key}")
                                    st.rerun()
                        
                        with delete_col:
                            if st.button("🗑️", key=f"delete_{key}", help="Delete"):
                                if st.checkbox(f"Confirm delete {key}?", key=f"confirm_{key}"):
                                    if delete_config_value(key):
                                        st.success(f"Deleted {key}")
                                        st.rerun()
    
    elif page == "Add Configuration":
        st.header("➕ Add Configuration Value")
        
        with st.form("add_config_form"):
            new_key = st.text_input("Configuration Key", placeholder="e.g., UPS_CHECK_INTERVAL")
            new_value = st.text_input("Configuration Value", placeholder="e.g., 60")
            
            submitted = st.form_submit_button("Add Configuration")
            
            if submitted:
                if not new_key or not new_value:
                    st.error("Please provide both key and value")
                else:
                    if update_config_value(new_key, new_value):
                        st.success(f"Added configuration: {new_key} = {new_value}")
                        st.balloons()
                    else:
                        st.error("Failed to add configuration")
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info(f"Database: {DB_PATH}")

if __name__ == "__main__":
    main()
