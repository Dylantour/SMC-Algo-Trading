#!/usr/bin/env python3
"""
dashboard.py - Web dashboard for monitoring the ICT Trading Bot

This script provides a web interface to monitor the ICT Trading Bot's
activity, market structure, and trading performance.
"""

import os
import sys
import time
import datetime
import json
import logging
import threading
from flask import Flask, render_template, jsonify, request, send_from_directory

# Create necessary directories
os.makedirs('logs', exist_ok=True)
os.makedirs('charts', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/dashboard.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# Bot status dictionary
bot_status = {
    'is_running': False,
    'pairs': [],
    'total_value': 0,
    'total_trades': 0,
    'win_rate': 0,
    'active_positions': 0,
    'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

# Dictionary to store status for each trading pair
pair_status = {}

# Create the HTML template
template_path = os.path.join('templates', 'index.html')
with open(template_path, 'w') as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ICT Trading Bot Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            padding-top: 20px;
            background-color: #f8f9fa;
        }
        .card {
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .card-header {
            font-weight: bold;
            background-color: #f1f8ff;
        }
        .status-badge {
            font-size: 1rem;
        }
        .log-container {
            height: 300px;
            overflow-y: auto;
            background-color: #212529;
            color: #f8f9fa;
            padding: 10px;
            font-family: monospace;
            border-radius: 5px;
        }
        .log-entry {
            margin: 0;
            padding: 2px 0;
            border-bottom: 1px solid #343a40;
        }
        .chart-container {
            text-align: center;
            margin-bottom: 20px;
        }
        .chart-img {
            max-width: 100%;
            height: auto;
            border-radius: 5px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .pair-card {
            margin-bottom: 15px;
        }
        .pair-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .pair-title {
            margin: 0;
            font-size: 1.2rem;
        }
        .pair-badge {
            font-size: 0.9rem;
        }
        .refresh-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>ICT Trading Bot Dashboard</span>
                        <span id="bot-status" class="badge bg-secondary status-badge">Initializing...</span>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h5>Bot Information</h5>
                                <table class="table table-sm">
                                    <tbody>
                                        <tr>
                                            <td>Trading Pairs:</td>
                                            <td id="trading-pairs">-</td>
                                        </tr>
                                        <tr>
                                            <td>Total Portfolio Value:</td>
                                            <td id="total-value">-</td>
                                        </tr>
                                        <tr>
                                            <td>Active Positions:</td>
                                            <td id="active-positions">-</td>
                                        </tr>
                                        <tr>
                                            <td>Last Update:</td>
                                            <td id="last-update">-</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h5>Performance Metrics</h5>
                                <table class="table table-sm">
                                    <tbody>
                                        <tr>
                                            <td>Total Trades:</td>
                                            <td id="total-trades">-</td>
                                        </tr>
                                        <tr>
                                            <td>Win Rate:</td>
                                            <td id="win-rate">-</td>
                                        </tr>
                                        <tr>
                                            <td>Control:</td>
                                            <td>
                                                <button id="toggle-bot" class="btn btn-sm btn-primary">Start/Stop Bot</button>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        Trading Pairs
                    </div>
                    <div class="card-body">
                        <div id="pairs-container" class="row">
                            <!-- Pair cards will be dynamically added here -->
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>Live Logs</span>
                        <select id="log-selector" class="form-select form-select-sm" style="width: auto;">
                            <option value="multi_token_trader.log">Multi Token Trader</option>
                            <option value="dashboard.log">Dashboard</option>
                            <option value="trade.log">Trade</option>
                        </select>
                    </div>
                    <div class="card-body">
                        <div id="log-container" class="log-container">
                            <p class="log-entry">Loading logs...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <button id="refresh-data" class="btn btn-primary refresh-btn">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrow-clockwise" viewBox="0 0 16 16">
            <path fill-rule="evenodd" d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z"/>
            <path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z"/>
        </svg>
        Refresh
    </button>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Function to update the dashboard with bot status
        function updateDashboard() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // Update bot status badge
                    const statusBadge = document.getElementById('bot-status');
                    if (data.is_running) {
                        statusBadge.textContent = 'Running';
                        statusBadge.className = 'badge bg-success status-badge';
                    } else {
                        statusBadge.textContent = 'Stopped';
                        statusBadge.className = 'badge bg-danger status-badge';
                    }
                    
                    // Update bot information
                    document.getElementById('trading-pairs').textContent = data.pairs.join(', ');
                    document.getElementById('total-value').textContent = data.total_value.toFixed(2) + ' BUSD';
                    document.getElementById('active-positions').textContent = data.active_positions;
                    document.getElementById('last-update').textContent = data.last_update;
                    
                    // Update performance metrics
                    document.getElementById('total-trades').textContent = data.total_trades;
                    document.getElementById('win-rate').textContent = data.win_rate + '%';
                    
                    // Update pair cards
                    updatePairCards(data.pairs);
                })
                .catch(error => console.error('Error fetching bot status:', error));
        }
        
        // Function to update pair cards
        function updatePairCards(pairs) {
            const pairsContainer = document.getElementById('pairs-container');
            
            // Clear existing cards
            pairsContainer.innerHTML = '';
            
            // Fetch status for each pair
            fetch('/api/pair_status')
                .then(response => response.json())
                .then(pairData => {
                    // Create a card for each pair
                    pairs.forEach(pair => {
                        const pairInfo = pairData[pair] || {};
                        
                        const card = document.createElement('div');
                        card.className = 'col-md-4';
                        card.innerHTML = `
                            <div class="card pair-card">
                                <div class="card-header pair-header">
                                    <h5 class="pair-title">${pair}</h5>
                                    <span class="badge ${pairInfo.position_open ? 'bg-warning' : 'bg-info'} pair-badge">
                                        ${pairInfo.position_open ? 'Position Open' : 'No Position'}
                                    </span>
                                </div>
                                <div class="card-body">
                                    <table class="table table-sm">
                                        <tbody>
                                            <tr>
                                                <td>Current Price:</td>
                                                <td>${pairInfo.current_price ? pairInfo.current_price.toFixed(2) : '-'}</td>
                                            </tr>
                                            <tr>
                                                <td>Market Bias:</td>
                                                <td>${pairInfo.market_bias || 'Unknown'}</td>
                                            </tr>
                                            <tr>
                                                <td>Active FVGs:</td>
                                                <td>${pairInfo.active_fvgs || 0}</td>
                                            </tr>
                                            <tr>
                                                <td>Total Trades:</td>
                                                <td>${pairInfo.total_trades || 0}</td>
                                            </tr>
                                            <tr>
                                                <td>Win Rate:</td>
                                                <td>${pairInfo.win_rate ? pairInfo.win_rate + '%' : '0%'}</td>
                                            </tr>
                                            <tr>
                                                <td>Avg. Profit:</td>
                                                <td>${pairInfo.avg_profit ? pairInfo.avg_profit + '%' : '0%'}</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        `;
                        
                        pairsContainer.appendChild(card);
                    });
                })
                .catch(error => console.error('Error fetching pair status:', error));
        }
        
        // Function to update logs
        function updateLogs() {
            const logFile = document.getElementById('log-selector').value;
            fetch(`/api/logs?file=${logFile}`)
                .then(response => response.json())
                .then(data => {
                    const logContainer = document.getElementById('log-container');
                    logContainer.innerHTML = '';
                    
                    data.logs.forEach(log => {
                        const logEntry = document.createElement('p');
                        logEntry.className = 'log-entry';
                        logEntry.textContent = log;
                        logContainer.appendChild(logEntry);
                    });
                    
                    // Scroll to bottom
                    logContainer.scrollTop = logContainer.scrollHeight;
                })
                .catch(error => console.error('Error fetching logs:', error));
        }
        
        // Toggle bot status
        document.getElementById('toggle-bot').addEventListener('click', function() {
            fetch('/api/toggle')
                .then(response => response.json())
                .then(data => {
                    console.log('Bot status toggled:', data);
                    updateDashboard();
                })
                .catch(error => console.error('Error toggling bot status:', error));
        });
        
        // Refresh button
        document.getElementById('refresh-data').addEventListener('click', function() {
            updateDashboard();
            updateLogs();
        });
        
        // Log selector change
        document.getElementById('log-selector').addEventListener('change', updateLogs);
        
        // Initial update
        updateDashboard();
        updateLogs();
        
        // Set up periodic updates
        setInterval(updateDashboard, 5000);
        setInterval(updateLogs, 10000);
    </script>
</body>
</html>""")

def initialize_demo_data():
    """Initialize demo data for testing the dashboard"""
    global bot_status, pair_status
    
    # Set up demo bot status
    bot_status = {
        'is_running': True,
        'pairs': ['BTCBUSD', 'ETHBUSD', 'BNBBUSD'],
        'total_value': 1000.0,
        'total_trades': 15,
        'win_rate': 60.0,
        'active_positions': 1,
        'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Set up demo pair status
    pair_status = {
        'BTCBUSD': {
            'trading_pair': 'BTCBUSD',
            'base_balance': 500.0,
            'asset_balance': 0.01,
            'current_price': 30000.0,
            'market_bias': 'Bullish',
            'active_fvgs': 2,
            'position_open': True,
            'total_trades': 8,
            'win_rate': 62.5,
            'avg_profit': 1.8,
            'total_value': 800.0
        },
        'ETHBUSD': {
            'trading_pair': 'ETHBUSD',
            'base_balance': 200.0,
            'asset_balance': 0.0,
            'current_price': 1800.0,
            'market_bias': 'Bearish',
            'active_fvgs': 1,
            'position_open': False,
            'total_trades': 5,
            'win_rate': 60.0,
            'avg_profit': 1.5,
            'total_value': 200.0
        },
        'BNBBUSD': {
            'trading_pair': 'BNBBUSD',
            'base_balance': 0.0,
            'asset_balance': 0.0,
            'current_price': 300.0,
            'market_bias': 'Neutral',
            'active_fvgs': 0,
            'position_open': False,
            'total_trades': 2,
            'win_rate': 50.0,
            'avg_profit': 0.8,
            'total_value': 0.0
        }
    }

def update_bot_status(status_update):
    """Update the bot status with new information"""
    global bot_status
    bot_status.update(status_update)
    logger.info(f"Bot status updated: {bot_status['is_running']}, Pairs: {bot_status['pairs']}")

@app.route('/')
def index():
    """Render the dashboard page"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Return the current status of the bot"""
    return jsonify(bot_status)

@app.route('/api/pair_status')
def get_pair_status():
    """Return the status of all trading pairs"""
    return jsonify(pair_status)

@app.route('/api/toggle', methods=['GET'])
def toggle_bot():
    """Toggle the bot's running status"""
    global bot_status
    bot_status['is_running'] = not bot_status['is_running']
    logger.info(f"Bot status toggled to: {'running' if bot_status['is_running'] else 'stopped'}")
    return jsonify({'success': True, 'is_running': bot_status['is_running']})

@app.route('/api/logs')
def get_logs():
    """Return the most recent logs"""
    log_file = request.args.get('file', 'multi_token_trader.log')
    log_path = os.path.join('logs', log_file)
    
    logs = []
    try:
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                # Get the last 100 lines
                logs = f.readlines()[-100:]
                logs = [log.strip() for log in logs]
        else:
            logs = [f"Log file {log_file} not found"]
    except Exception as e:
        logs = [f"Error reading logs: {str(e)}"]
    
    return jsonify({'logs': logs})

@app.route('/charts/<path:filename>')
def serve_chart(filename):
    """Serve chart images"""
    return send_from_directory('charts', filename)

# Initialize demo data for testing
initialize_demo_data()

if __name__ == '__main__':
    # Run the dashboard
    app.run(host='0.0.0.0', port=5000, debug=True) 