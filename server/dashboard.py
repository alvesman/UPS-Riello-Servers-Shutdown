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
    page = st.sidebar.radio("Go to", ["Client Connections", "Configuration"])
    
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
                width='stretch',
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
            st.subheader(f"All Configuration Values: {len(config_df)}")
            
            # Display configuration table
            st.dataframe(
                config_df,
                width='stretch',
                hide_index=True
            )
            
            # Edit configuration values
            st.subheader("✏️ Edit Configuration")
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                selected_key = st.selectbox(
                    "Select Configuration Key",
                    options=config_df['key'].tolist(),
                    key="selected_config_key"
                )
            
            current_value = config_df[config_df['key'] == selected_key]['value'].iloc[0]
            
            with col2:
                new_value = st.text_input(
                    "New Value",
                    value=current_value,
                    key=f"edit_value_{selected_key}"
                )
            
            with col3:
                st.write("")  # Spacer
                st.write("")  # Spacer
                if st.button("💾 Update", key="update_btn"):
                    if update_config_value(selected_key, new_value):
                        st.success(f"Updated {selected_key}")
                        st.rerun()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info(f"Database: {DB_PATH}")

if __name__ == "__main__":
    main()
