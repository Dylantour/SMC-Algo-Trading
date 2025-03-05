#!/usr/bin/env python3
"""
API Logger for Binance API Calls
This module provides a custom logger to capture and store Binance API calls.
"""

import logging
import datetime
import re
import threading
from collections import deque

class APILogHandler(logging.Handler):
    """Custom logging handler to capture API calls"""
    
    def __init__(self, max_logs=500):
        super().__init__()
        self.logs = deque(maxlen=max_logs)
        self.lock = threading.Lock()
        
        # Set up a formatter that extracts relevant information
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Regex patterns for extracting information from log messages
        self.url_pattern = re.compile(r'"(GET|POST|PUT|DELETE) ([^"]+) HTTP')
        self.status_pattern = re.compile(r'HTTP/\d\.\d" (\d+) (\d+)')
    
    def emit(self, record):
        """Process and store log records related to Binance API calls"""
        if 'api.binance.com' in record.getMessage():
            with self.lock:
                # Format the log message
                formatted_msg = self.formatter.format(record)
                
                # Extract HTTP method and endpoint
                url_match = self.url_pattern.search(record.getMessage())
                method = url_match.group(1) if url_match else "UNKNOWN"
                endpoint = url_match.group(2) if url_match else "UNKNOWN"
                
                # Extract status code and response size
                status_match = self.status_pattern.search(record.getMessage())
                status = status_match.group(1) if status_match else "UNKNOWN"
                size = status_match.group(2) if status_match else "UNKNOWN"
                
                # Parse endpoint to extract API category
                category = self._categorize_endpoint(endpoint)
                
                # Create a structured log entry
                log_entry = {
                    'timestamp': datetime.datetime.fromtimestamp(record.created),
                    'method': method,
                    'endpoint': endpoint,
                    'category': category,
                    'status': status,
                    'size': size,
                    'message': record.getMessage(),
                    'formatted': formatted_msg
                }
                
                # Add to the logs collection
                self.logs.append(log_entry)
    
    def _categorize_endpoint(self, endpoint):
        """Categorize the endpoint based on its path"""
        if '/api/v3/account' in endpoint:
            return "Account"
        elif '/api/v3/order' in endpoint:
            return "Order"
        elif '/api/v3/ticker' in endpoint:
            return "Market Data"
        elif '/api/v3/klines' in endpoint:
            return "Candlestick"
        elif '/api/v3/exchangeInfo' in endpoint:
            return "Exchange Info"
        elif '/api/v3/time' in endpoint:
            return "Server Time"
        else:
            return "Other"
    
    def get_logs(self, category=None, status=None, limit=100):
        """Get filtered logs"""
        with self.lock:
            filtered_logs = list(self.logs)
            
            if category:
                filtered_logs = [log for log in filtered_logs if log['category'] == category]
            
            if status:
                filtered_logs = [log for log in filtered_logs if log['status'] == status]
            
            # Return the most recent logs up to the limit
            return list(reversed(filtered_logs))[-limit:]
    
    def get_logs_by_time_range(self, start_time, end_time):
        """Get logs within a specific time range"""
        with self.lock:
            return [log for log in self.logs if start_time <= log['timestamp'] <= end_time]
    
    def get_request_rate(self, time_window_seconds=60):
        """Calculate the request rate over the specified time window"""
        with self.lock:
            now = datetime.datetime.now()
            cutoff_time = now - datetime.timedelta(seconds=time_window_seconds)
            
            # Count requests in the time window
            recent_requests = [log for log in self.logs if log['timestamp'] >= cutoff_time]
            return len(recent_requests)
    
    def get_category_distribution(self):
        """Get distribution of requests by category"""
        with self.lock:
            categories = {}
            for log in self.logs:
                category = log['category']
                if category in categories:
                    categories[category] += 1
                else:
                    categories[category] = 1
            return categories
    
    def get_status_distribution(self):
        """Get distribution of requests by status code"""
        with self.lock:
            statuses = {}
            for log in self.logs:
                status = log['status']
                if status in statuses:
                    statuses[status] += 1
                else:
                    statuses[status] = 1
            return statuses
    
    def clear(self):
        """Clear all stored logs"""
        with self.lock:
            self.logs.clear()

def setup_api_logger():
    """Set up and configure the API logger"""
    try:
        # Get the urllib3 logger that captures HTTP requests
        api_logger = logging.getLogger('urllib3')
        
        # Create our custom handler
        api_log_handler = APILogHandler()
        api_log_handler.setLevel(logging.DEBUG)
        
        # Add the handler to the logger
        api_logger.addHandler(api_log_handler)
        
        return api_log_handler
    except Exception as e:
        logging.error(f"Error setting up API logger: {str(e)}")
        
        # Create a fallback handler that doesn't rely on complex functionality
        class FallbackAPILogHandler:
            def __init__(self):
                self.logs = []
                
            def get_logs(self, category=None, status=None, limit=100):
                return []
                
            def get_request_rate(self, time_window_seconds=60):
                return 0
                
            def get_category_distribution(self):
                return {}
                
            def get_status_distribution(self):
                return {}
                
            def clear(self):
                pass
        
        return FallbackAPILogHandler() 