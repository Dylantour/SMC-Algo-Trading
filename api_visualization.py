#!/usr/bin/env python3
"""
API Visualization Components for Streamlit UI
This module provides visualization components for Binance API activity.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from collections import defaultdict

def render_api_activity_dashboard(api_log_handler):
    """Render the API activity dashboard in Streamlit"""
    st.subheader("API Activity Monitor")
    
    # Check if api_log_handler is None or doesn't have the expected methods
    if api_log_handler is None or not hasattr(api_log_handler, 'get_request_rate'):
        st.warning("API logger is not properly initialized. Some features may not be available.")
        
        # Show a button to restart the application
        if st.button("Restart Application"):
            st.experimental_rerun()
            
        return
    
    # Add API rate limit info
    col1, col2 = st.columns(2)
    with col1:
        # Count requests in the last minute
        try:
            requests_last_minute = api_log_handler.get_request_rate(60)
            
            # Binance has a limit of 1200 requests per minute for most API keys
            st.metric(
                "API Requests (Last Minute)", 
                f"{requests_last_minute}/1200", 
                delta=f"{requests_last_minute/12:.1f}%" if requests_last_minute > 0 else "0%",
                delta_color="inverse"  # Higher is worse for rate limits
            )
        except Exception as e:
            st.error(f"Error calculating request rate: {str(e)}")
            st.metric("API Requests (Last Minute)", "Error")
    
    with col2:
        try:
            # Get category distribution
            categories = api_log_handler.get_category_distribution()
            
            # Format for display
            category_str = ", ".join([f"{k}: {v}" for k, v in categories.items()])
            
            st.metric(
                "Request Distribution", 
                category_str if category_str else "No data yet"
            )
        except Exception as e:
            st.error(f"Error getting category distribution: {str(e)}")
            st.metric("Request Distribution", "Error")
    
    # Create a chart showing API activity over time
    try:
        if hasattr(api_log_handler, 'logs') and api_log_handler.logs:
            st.subheader("API Request Rate")
            
            # Create time-based request rate visualization
            fig = create_request_rate_chart(api_log_handler)
            st.plotly_chart(fig, use_container_width=True)
            
            # Create request distribution pie chart
            st.subheader("Request Distribution by Endpoint")
            fig2 = create_request_distribution_chart(api_log_handler)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No API activity data available yet. Start the bot to begin collecting data.")
            
            # Add a placeholder chart
            import numpy as np
            import pandas as pd
            
            # Create empty dataframe with placeholder data
            df = pd.DataFrame({
                'timestamp': [datetime.datetime.now() - datetime.timedelta(seconds=i) for i in range(5)],
                'count': [0, 0, 0, 0, 0]
            })
            
            fig = px.line(
                df, 
                x='timestamp', 
                y='count',
                title='API Requests Per Second (No Data Yet)',
                labels={'timestamp': 'Time', 'count': 'Requests'}
            )
            
            fig.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis_title="Time",
                yaxis_title="Requests per Second"
            )
            
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating charts: {str(e)}")
    
    # Add API request log table
    st.subheader("Recent API Requests")
    
    # Add filter options
    col1, col2 = st.columns(2)
    with col1:
        try:
            categories = ["All"]
            if hasattr(api_log_handler, 'get_category_distribution'):
                categories.extend(sorted(api_log_handler.get_category_distribution().keys()))
            
            category_filter = st.selectbox(
                "Filter by Category",
                options=categories,
                index=0
            )
        except Exception as e:
            st.error(f"Error getting categories: {str(e)}")
            category_filter = "All"
    
    with col2:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["All", "200 (Success)", "Error (4xx/5xx)"],
            index=0
        )
    
    # Display the filtered logs
    try:
        # Convert filter selections to actual filter values
        category = None if category_filter == "All" else category_filter
        status = None
        if status_filter == "200 (Success)":
            status = "200"
        elif status_filter == "Error (4xx/5xx)":
            status = "4"  # This is a prefix match in our filter logic
        
        # Get filtered logs
        if hasattr(api_log_handler, 'get_logs'):
            logs = api_log_handler.get_logs(category=category, status=status, limit=100)
        else:
            logs = []
        
        # Create a table of recent requests
        if logs:
            # Convert to dataframe for display
            df_logs = pd.DataFrame([{
                'Time': log['timestamp'].strftime('%H:%M:%S'),
                'Category': log['category'],
                'Method': log['method'],
                'Endpoint': log['endpoint'],
                'Status': log['status'],
                'Size (bytes)': log['size']
            } for log in logs])
            
            # Display as a table with pagination
            page_size = 10
            total_pages = len(df_logs) // page_size + (1 if len(df_logs) % page_size > 0 else 0)
            
            if 'api_log_page' not in st.session_state:
                st.session_state.api_log_page = 0
                
            # Add page navigation
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("← Previous", key="prev_api_log", 
                           disabled=st.session_state.api_log_page <= 0):
                    st.session_state.api_log_page -= 1
            
            with col2:
                st.write(f"Page {st.session_state.api_log_page + 1} of {max(1, total_pages)}")
                
            with col3:
                if st.button("Next →", key="next_api_log", 
                           disabled=st.session_state.api_log_page >= total_pages - 1):
                    st.session_state.api_log_page += 1
            
            # Show the current page
            start_idx = st.session_state.api_log_page * page_size
            end_idx = min(start_idx + page_size, len(df_logs))
            st.dataframe(df_logs.iloc[start_idx:end_idx], use_container_width=True)
        else:
            st.info("No API logs available yet. Start the bot to begin collecting logs.")
    except Exception as e:
        st.error(f"Error displaying logs: {str(e)}")
        st.info("No API logs available. There may be an issue with the logger.")
    
    # Add API request details
    with st.expander("API Reference Information"):
        st.markdown("""
        ### Common Endpoints
        - `/api/v3/account` - Gets account information
        - `/api/v3/ticker/bookTicker` - Gets best bid/ask prices
        - `/api/v3/klines` - Gets candlestick data
        
        ### Parameters
        - `recvWindow` - Specifies how long a request is valid for (in ms)
        - `timestamp` - Current timestamp
        - `signature` - API authentication signature
        
        ### Rate Limits
        - IP Limits: 1,200 requests per minute
        - Order Rate Limits: Vary by account tier
        
        ### Response Codes
        - 200: Success
        - 400: Bad request
        - 401: Unauthorized
        - 429: Rate limit exceeded
        - 418: IP banned for rate limit violation
        """)
        
    # Add a button to manually refresh the dashboard
    if st.button("Refresh Dashboard"):
        st.experimental_rerun()

def create_request_rate_chart(api_log_handler):
    """Create a time series chart of API request rate"""
    # Get all logs
    logs = list(api_log_handler.logs)
    
    if not logs:
        # Return empty figure if no logs
        return px.line(title="API Request Rate (No Data)")
    
    # Group logs by timestamp (rounded to the second)
    timestamps = {}
    for log in logs:
        # Round to the nearest second
        ts = log['timestamp'].replace(microsecond=0)
        if ts in timestamps:
            timestamps[ts] += 1
        else:
            timestamps[ts] = 1
    
    # Create dataframe for plotting
    df_time = pd.DataFrame({
        'timestamp': list(timestamps.keys()),
        'count': list(timestamps.values())
    }).sort_values('timestamp')
    
    # If we have very few data points, add some empty points for better visualization
    if len(df_time) < 5:
        # Add points before and after
        min_time = df_time['timestamp'].min()
        max_time = df_time['timestamp'].max()
        
        # Add points before
        for i in range(1, 3):
            new_time = min_time - datetime.timedelta(seconds=i)
            df_time = pd.concat([df_time, pd.DataFrame({'timestamp': [new_time], 'count': [0]})])
        
        # Add points after
        for i in range(1, 3):
            new_time = max_time + datetime.timedelta(seconds=i)
            df_time = pd.concat([df_time, pd.DataFrame({'timestamp': [new_time], 'count': [0]})])
        
        df_time = df_time.sort_values('timestamp')
    
    # Create time series chart
    fig = px.line(
        df_time, 
        x='timestamp', 
        y='count',
        title='API Requests Per Second',
        labels={'timestamp': 'Time', 'count': 'Requests'}
    )
    
    # Add a horizontal line for the rate limit warning (80% of 1200/60 = 16 requests per second)
    fig.add_shape(
        type="line",
        x0=df_time['timestamp'].min(),
        y0=16,
        x1=df_time['timestamp'].max(),
        y1=16,
        line=dict(color="orange", width=2, dash="dash"),
    )
    
    # Add annotation for the warning line
    fig.add_annotation(
        x=df_time['timestamp'].max(),
        y=16,
        text="Rate Limit Warning (80%)",
        showarrow=False,
        yshift=10,
        font=dict(color="orange")
    )
    
    # Improve layout
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified",
        xaxis_title="Time",
        yaxis_title="Requests per Second"
    )
    
    return fig

def create_request_distribution_chart(api_log_handler):
    """Create a pie chart of API request distribution by endpoint"""
    # Get category distribution
    categories = api_log_handler.get_category_distribution()
    
    if not categories:
        # Return empty figure if no data
        return px.pie(title="API Request Distribution (No Data)")
    
    # Create dataframe for plotting
    df_categories = pd.DataFrame({
        'category': list(categories.keys()),
        'count': list(categories.values())
    })
    
    # Create pie chart
    fig = px.pie(
        df_categories, 
        values='count', 
        names='category',
        title='API Request Distribution by Category',
        hole=0.4,  # Make it a donut chart
    )
    
    # Improve layout
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    
    # Improve trace appearance
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hoverinfo='label+percent+value'
    )
    
    return fig

def create_endpoint_timing_chart(api_log_handler):
    """Create a bar chart showing average response size by endpoint"""
    # Get all logs
    logs = list(api_log_handler.logs)
    
    if not logs:
        # Return empty figure if no logs
        return px.bar(title="API Response Size by Endpoint (No Data)")
    
    # Group logs by endpoint
    endpoint_sizes = defaultdict(list)
    for log in logs:
        # Extract base endpoint without parameters
        endpoint = log['endpoint'].split('?')[0]
        try:
            size = int(log['size'])
            endpoint_sizes[endpoint].append(size)
        except (ValueError, TypeError):
            continue
    
    # Calculate average size for each endpoint
    avg_sizes = {}
    for endpoint, sizes in endpoint_sizes.items():
        if sizes:
            avg_sizes[endpoint] = sum(sizes) / len(sizes)
    
    # Create dataframe for plotting
    df_sizes = pd.DataFrame({
        'endpoint': list(avg_sizes.keys()),
        'avg_size': list(avg_sizes.values())
    }).sort_values('avg_size', ascending=False)
    
    # Create bar chart
    fig = px.bar(
        df_sizes, 
        x='endpoint', 
        y='avg_size',
        title='Average Response Size by Endpoint',
        labels={'endpoint': 'Endpoint', 'avg_size': 'Avg Size (bytes)'}
    )
    
    # Improve layout
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="Endpoint",
        yaxis_title="Average Size (bytes)"
    )
    
    return fig 