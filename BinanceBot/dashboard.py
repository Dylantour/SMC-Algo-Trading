#!/usr/bin/env python3
"""
dashboard.py - Web dashboard for monitoring the Trading Bot

This script provides a web interface to monitor the Trading Bot's
activity, market structure, and trading performance. It supports
multiple strategies (Original and ICT) and multi-token trading.
"""

import os
import sys
import time
import datetime
import json
import logging
import threading
from flask import Flask, render_template, jsonify, request, send_from_directory, render_template_string

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
    'strategy': 'Original',  # Default strategy
    'pairs': [],
    'total_value': 0,
    'total_trades': 0,
    'win_rate': 0,
    'active_positions': 0,
    'daily_bias': 'bullish',  # Add daily bias
    'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

# Dictionary to store status for each trading pair
pair_status = {}

# Create the HTML template
template_path = os.path.join('templates', 'index.html')
with open(template_path, 'w') as f:
    f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Bot Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { padding: 20px; background-color: #f8f9fa; }
        .card { margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .status-badge { font-size: 1rem; }
        .log-container { height: 300px; overflow-y: auto; background-color: #212529; color: #f8f9fa; padding: 10px; font-family: monospace; border-radius: 5px; }
        .log-entry { margin: 0; padding: 2px 0; border-bottom: 1px solid #343a40; }
        .pair-card { cursor: pointer; transition: all 0.3s; }
        .pair-card:hover { transform: translateY(-5px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); }
        
        /* Bias indicator styles */
        .bias-bullish { background-color: #28a745; color: white; padding: 3px 8px; border-radius: 4px; }
        .bias-bearish { background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 4px; }
        .bias-neutral { background-color: #6c757d; color: white; padding: 3px 8px; border-radius: 4px; }
        
        /* Position card styles */
        .position-info {
            background-color: rgba(0,0,0,0.02);
            border-radius: 5px;
            padding: 10px;
        }
        
        /* Stats card styles */
        .stats-card {
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            text-align: center;
        }
        
        .stats-card h3 {
            margin-bottom: 0;
            font-weight: bold;
        }
        
        /* Execution feed styles */
        .execution-item {
            background-color: #f8f9fa;
            border-radius: 5px;
            transition: all 0.3s;
            margin-bottom: 10px;
            padding: 10px;
        }
        
        .execution-item:hover {
            background-color: #e9ecef;
        }
        
        /* Table styles */
        .table {
            font-size: 0.9rem;
        }
        
        /* Badge styles */
        .badge {
            padding: 0.35em 0.65em;
        }
        
        /* Chart container */
        canvas {
            max-height: 200px;
        }
        
        .execution-feed {
            max-height: 300px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mb-4">Trading Bot Dashboard</h1>
        
        <div class="row">
            <!-- Bot Status Card -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="card-title mb-0">Bot Status</h5>
                    </div>
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="mb-0">Status:</h6>
                            <span id="bot-status" class="badge bg-success status-badge">Running</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="mb-0">Strategy:</h6>
                            <div class="d-flex align-items-center">
                                <select id="strategy-selector" class="form-select form-select-sm me-2">
                                    <option value="Original">Original</option>
                                    <option value="ICT">ICT</option>
                                    <option value="Enhanced">Enhanced ICT</option>
                                </select>
                                <button id="change-strategy" class="btn btn-sm btn-outline-primary">Apply</button>
                            </div>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="mb-0">Daily Bias:</h6>
                            <span id="daily-bias" class="bias-bullish">BULLISH</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="mb-0">Total Value:</h6>
                            <span id="total-value">$1000.00</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="mb-0">Total Trades:</h6>
                            <span id="total-trades">0</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="mb-0">Win Rate:</h6>
                            <span id="win-rate">0%</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="mb-0">Active Positions:</h6>
                            <span id="active-positions">0</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="mb-0">Last Update:</h6>
                            <span id="last-update">-</span>
                        </div>
                        <div class="mt-3">
                            <button id="toggle-bot" class="btn btn-danger w-100">Stop Bot</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Trading Pairs Card -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0">Trading Pairs</h5>
                        <button id="add-pair-btn" class="btn btn-sm btn-light">Add Pair</button>
                    </div>
                    <div class="card-body">
                        <div id="pairs-container" class="row">
                            <!-- Trading pairs will be added here dynamically -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Trade History Section -->
        <div class="row mt-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0">Trade History</h5>
                        <div>
                            <select id="trade-filter" class="form-select form-select-sm">
                                <option value="all">All Pairs</option>
                                <!-- Will be populated dynamically with trading pairs -->
                            </select>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>Trade ID</th>
                                        <th>Pair</th>
                                        <th>Type</th>
                                        <th>Entry Time</th>
                                        <th>Exit Time</th>
                                        <th>Duration</th>
                                        <th>Entry Price</th>
                                        <th>Exit Price</th>
                                        <th>Size</th>
                                        <th>PnL %</th>
                                        <th>PnL $</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody id="trade-history">
                                    <!-- Trade history will be populated here -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Execution Feed and Stats Section -->
        <div class="row mt-4">
            <div class="col-12 col-md-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="card-title mb-0">Recent Executions</h5>
                    </div>
                    <div class="card-body">
                        <div class="execution-feed" id="execution-feed">
                            <!-- Executions will be populated here -->
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Trade Stats Section -->
            <div class="col-12 col-md-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="card-title mb-0">Trade Statistics</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-6">
                                <div class="stats-card mb-3">
                                    <h6>Win Rate</h6>
                                    <h3 id="stats-win-rate">0%</h3>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="stats-card mb-3">
                                    <h6>Avg. Profit</h6>
                                    <h3 id="stats-avg-profit">0%</h3>
                                </div>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-6">
                                <div class="stats-card mb-3">
                                    <h6>Avg. Duration</h6>
                                    <h3 id="stats-avg-duration">0m</h3>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="stats-card mb-3">
                                    <h6>Total PnL</h6>
                                    <h3 id="stats-total-pnl">$0.00</h3>
                                </div>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-12">
                                <canvas id="monthly-pnl-chart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Logs Card -->
        <div class="row mt-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0">Logs</h5>
                        <div class="d-flex">
                            <select id="log-selector" class="form-select form-select-sm me-2">
                                <option value="all">All Logs</option>
                                <option value="trades">Trades Only</option>
                                <option value="errors">Errors Only</option>
                            </select>
                            <button id="refresh-data" class="btn btn-sm btn-light">Refresh</button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div id="log-container" class="log-container">
                            <!-- Logs will be added here dynamically -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Add Pair Modal -->
        <div class="modal fade" id="addPairModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Add Trading Pair</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label for="pair-input" class="form-label">Trading Pair</label>
                            <input type="text" class="form-control" id="pair-input" placeholder="e.g. BTCBUSD">
                            <div class="form-text">Enter the trading pair in the format SYMBOLBUSD</div>
                        </div>
                        <div class="mb-3">
                            <label for="htf-interval" class="form-label">Higher Timeframe</label>
                            <select class="form-select" id="htf-interval" required>
                                <option value="15m">15 Minutes</option>
                                <option value="30m">30 Minutes</option>
                                <option value="1h" selected>1 Hour</option>
                                <option value="4h">4 Hours</option>
                                <option value="1d">1 Day</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="ltf-interval" class="form-label">Lower Timeframe</label>
                            <select class="form-select" id="ltf-interval" required>
                                <option value="1m">1 Minute</option>
                                <option value="3m">3 Minutes</option>
                                <option value="5m" selected>5 Minutes</option>
                                <option value="15m">15 Minutes</option>
                                <option value="30m">30 Minutes</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="risk-percentage" class="form-label">Risk Percentage</label>
                            <input type="number" class="form-control" id="risk-percentage" value="1" min="0.1" max="10" step="0.1" required>
                            <div class="form-text">Risk per trade as a percentage (0.1 - 10)</div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="confirm-add-pair">Add</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Trade Details Modal -->
        <div class="modal fade" id="tradeDetailsModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Trade Details</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Trade Information</h6>
                                <table class="table table-sm">
                                    <tbody>
                                        <tr>
                                            <td>Trade ID:</td>
                                            <td id="detail-trade-id"></td>
                                        </tr>
                                        <tr>
                                            <td>Pair:</td>
                                            <td id="detail-pair"></td>
                                        </tr>
                                        <tr>
                                            <td>Type:</td>
                                            <td id="detail-type"></td>
                                        </tr>
                                        <tr>
                                            <td>Entry Time:</td>
                                            <td id="detail-entry-time"></td>
                                        </tr>
                                        <tr>
                                            <td>Exit Time:</td>
                                            <td id="detail-exit-time"></td>
                                        </tr>
                                        <tr>
                                            <td>Duration:</td>
                                            <td id="detail-duration"></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h6>Performance</h6>
                                <table class="table table-sm">
                                    <tbody>
                                        <tr>
                                            <td>Entry Price:</td>
                                            <td id="detail-entry-price"></td>
                                        </tr>
                                        <tr>
                                            <td>Exit Price:</td>
                                            <td id="detail-exit-price"></td>
                                        </tr>
                                        <tr>
                                            <td>Size:</td>
                                            <td id="detail-size"></td>
                                        </tr>
                                        <tr>
                                            <td>PnL %:</td>
                                            <td id="detail-pnl-percent"></td>
                                        </tr>
                                        <tr>
                                            <td>PnL $:</td>
                                            <td id="detail-pnl-absolute"></td>
                                        </tr>
                                        <tr>
                                            <td>Status:</td>
                                            <td id="detail-status"></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="row mt-3">
                            <div class="col-12">
                                <h6>Related Executions</h6>
                                <div class="table-responsive">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>Time</th>
                                                <th>Side</th>
                                                <th>Price</th>
                                                <th>Quantity</th>
                                                <th>Reason</th>
                                            </tr>
                                        </thead>
                                        <tbody id="detail-executions">
                                            <!-- Executions will be populated here -->
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-3">
                            <div class="col-12">
                                <h6>Trade Notes</h6>
                                <div class="mb-2" id="detail-notes-content">
                                    <!-- Notes will be populated here -->
                                </div>
                                <div class="d-flex">
                                    <textarea class="form-control" id="detail-notes-input" rows="2" placeholder="Add a note to this trade..."></textarea>
                                    <button class="btn btn-primary ms-2" id="detail-notes-save">Save</button>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Initialize Bootstrap components
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize modals
            window.addPairModal = new bootstrap.Modal(document.getElementById('addPairModal'));
            window.tradeDetailsModal = new bootstrap.Modal(document.getElementById('tradeDetailsModal'));
            
            // Trade history data structure
            let tradeHistory = [];
            let executionFeed = [];
            
            // Update dashboard with latest data
            function updateDashboard() {
                // Fetch bot status
                fetch('/api/status')
                    .then(response => response.json())
                    .then(data => {
                        // Update bot status elements
                        const botStatusEl = document.getElementById('bot-status');
                        botStatusEl.textContent = data.is_running ? 'Running' : 'Stopped';
                        botStatusEl.className = data.is_running ? 'badge bg-success status-badge' : 'badge bg-danger status-badge';
                        
                        const toggleBotBtn = document.getElementById('toggle-bot');
                        toggleBotBtn.textContent = data.is_running ? 'Stop Bot' : 'Start Bot';
                        toggleBotBtn.className = data.is_running ? 'btn btn-danger w-100' : 'btn btn-success w-100';
                        
                        document.getElementById('strategy-selector').value = data.strategy;
                        document.getElementById('total-value').textContent = '$' + data.total_value.toFixed(2);
                        document.getElementById('total-trades').textContent = data.total_trades;
                        document.getElementById('win-rate').textContent = data.win_rate.toFixed(1) + '%';
                        document.getElementById('active-positions').textContent = data.active_positions;
                        document.getElementById('last-update').textContent = data.last_update;
                        
                        // Update daily bias
                        const dailyBiasEl = document.getElementById('daily-bias');
                        if (data.daily_bias) {
                            dailyBiasEl.textContent = data.daily_bias.toUpperCase();
                            dailyBiasEl.className = 'bias-' + data.daily_bias.toLowerCase();
                        }
                    });
                
                // Fetch pair status
                fetch('/api/pair_status')
                    .then(response => response.json())
                    .then(data => {
                        // Clear existing pairs
                        const pairsContainer = document.getElementById('pairs-container');
                        pairsContainer.innerHTML = '';
                        
                        // Add each pair
                        Object.values(data).forEach(pair => {
                            const pairCard = document.createElement('div');
                            pairCard.className = 'col-md-6 mb-3';
                            
                            // Check if we have a position for enhanced display
                            const hasPosition = pair.position !== undefined && pair.position !== null && pair.position !== '';
                            
                            pairCard.innerHTML = `
                                <div class="card pair-card ${hasPosition ? 'border-' + (pair.position === 'long' ? 'success' : 'danger') : ''}">
                                    <div class="card-header d-flex justify-content-between align-items-center">
                                        <h5 class="card-title mb-0">${pair.trading_pair}</h5>
                                        <span class="bias-${pair.daily_bias || 'neutral'}">${pair.daily_bias ? pair.daily_bias.toUpperCase() : 'NEUTRAL'}</span>
                                    </div>
                                    <div class="card-body">
                                        <div class="position-info ${hasPosition ? '' : 'd-none'}">
                                            <div class="alert alert-${pair.position === 'long' ? 'success' : 'danger'} mb-2">
                                                <strong>OPEN ${pair.position ? pair.position.toUpperCase() : ''} POSITION</strong>
                                            </div>
                                            <div class="row">
                                                <div class="col-6">
                                                    <small class="text-muted">Entry Price:</small>
                                                    <p class="mb-1">$${pair.entry_price ? pair.entry_price.toFixed(2) : '-'}</p>
                                                </div>
                                                <div class="col-6">
                                                    <small class="text-muted">Entry Time:</small>
                                                    <p class="mb-1">${pair.entry_time || 'N/A'}</p>
                                                </div>
                                            </div>
                                            <div class="row">
                                                <div class="col-6">
                                                    <small class="text-muted">Current Price:</small>
                                                    <p class="mb-1">$${pair.current_price ? pair.current_price.toFixed(2) : '-'}</p>
                                                </div>
                                                <div class="col-6">
                                                    <small class="text-muted">Position Size:</small>
                                                    <p class="mb-1">${pair.position_size || 'N/A'}</p>
                                                </div>
                                            </div>
                                            <div class="row">
                                                <div class="col-6">
                                                    <small class="text-muted">Stop Loss:</small>
                                                    <p class="mb-1">$${pair.stop_loss ? pair.stop_loss.toFixed(2) : 'N/A'}</p>
                                                </div>
                                                <div class="col-6">
                                                    <small class="text-muted">Take Profit:</small>
                                                    <p class="mb-1">$${pair.take_profit ? pair.take_profit.toFixed(2) : 'N/A'}</p>
                                                </div>
                                            </div>
                                            <div class="row">
                                                <div class="col-6">
                                                    <small class="text-muted">PnL %:</small>
                                                    <p class="mb-1 ${pair.pnl > 0 ? 'text-success' : pair.pnl < 0 ? 'text-danger' : ''}">${pair.pnl ? (pair.pnl > 0 ? '+' : '') + pair.pnl.toFixed(2) + '%' : 'N/A'}</p>
                                                </div>
                                                <div class="col-6">
                                                    <small class="text-muted">PnL $:</small>
                                                    <p class="mb-1 ${pair.pnl_absolute > 0 ? 'text-success' : pair.pnl_absolute < 0 ? 'text-danger' : ''}">${pair.pnl_absolute ? (pair.pnl_absolute > 0 ? '+$' : '-$') + Math.abs(pair.pnl_absolute).toFixed(2) : 'N/A'}</p>
                                                </div>
                                            </div>
                                            <div class="row">
                                                <div class="col-12">
                                                    <small class="text-muted">Duration:</small>
                                                    <p class="mb-1">${pair.position_duration || 'N/A'}</p>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="no-position-info ${hasPosition ? 'd-none' : ''}">
                                            <div class="alert alert-secondary mb-2">NO OPEN POSITION</div>
                                            <div class="d-flex justify-content-between mb-2">
                                                <span>Current Price:</span>
                                                <span>$${pair.current_price ? pair.current_price.toFixed(2) : '-'}</span>
                                            </div>
                                            <div class="d-flex justify-content-between mb-2">
                                                <span>Last Trade:</span>
                                                <span>${pair.last_trade_time || 'None'}</span>
                                            </div>
                                        </div>
                                        <div class="mt-3 d-flex justify-content-between">
                                            <button class="btn btn-sm btn-primary view-trades-btn" data-pair="${pair.trading_pair}">View Trades</button>
                                            <button class="btn btn-sm btn-outline-danger remove-pair" data-pair="${pair.trading_pair}">Remove</button>
                                        </div>
                                    </div>
                                </div>
                            `;
                            
                            pairsContainer.appendChild(pairCard);
                        });
                        
                        // Add event listeners for remove pair buttons and trade view buttons
                        document.querySelectorAll('.remove-pair').forEach(button => {
                            button.addEventListener('click', function(e) {
                                e.stopPropagation();
                                const pair = this.getAttribute('data-pair');
                                removePair(pair);
                            });
                        });
                        
                        document.querySelectorAll('.view-trades-btn').forEach(button => {
                            button.addEventListener('click', function(e) {
                                e.stopPropagation();
                                const pair = this.getAttribute('data-pair');
                                document.getElementById('trade-filter').value = pair;
                                displayFilteredTrades();
                            });
                        });
                    });
            }
            
            // Function to update trade history
            function updateTradeHistory() {
                fetch('/api/trade_history')
                    .then(response => response.json())
                    .then(data => {
                        tradeHistory = data.trades;
                        
                        // Update trade filter dropdown
                        const tradeFilter = document.getElementById('trade-filter');
                        const pairs = [...new Set(tradeHistory.map(trade => trade.pair))];
                        pairs.forEach(pair => {
                            const option = document.createElement('option');
                            option.value = pair;
                            option.textContent = pair;
                            tradeFilter.appendChild(option);
                        });
                    });
            }
            
            // Function to display filtered trades
            function displayFilteredTrades() {
                const selectedPair = document.getElementById('trade-filter').value;
                const filteredTrades = tradeHistory.filter(trade => trade.pair === selectedPair);
                
                // Clear existing trade history
                const tradeHistoryTable = document.getElementById('trade-history');
                tradeHistoryTable.innerHTML = '';
                
                // Populate trade history table
                filteredTrades.forEach(trade => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${trade.id}</td>
                        <td>${trade.pair}</td>
                        <td>${trade.type}</td>
                        <td>${trade.entry_time}</td>
                        <td>${trade.exit_time}</td>
                        <td>${trade.duration}</td>
                        <td>${trade.entry_price.toFixed(2)}</td>
                        <td>${trade.exit_price.toFixed(2)}</td>
                        <td>${trade.size.toFixed(8)}</td>
                        <td>${trade.pnl_percent.toFixed(2)}%</td>
                        <td>${trade.pnl_absolute.toFixed(2)}</td>
                        <td>${trade.status}</td>
                    `;
                    tradeHistoryTable.appendChild(row);
                });
            }
            
            // Toggle bot status
            function toggleBot() {
                fetch('/api/toggle')
                    .then(response => response.json())
                    .then(data => {
                        updateDashboard();
                    });
            }
            
            // Change strategy
            function changeStrategy() {
                const strategy = document.getElementById('strategy-selector').value;
                
                fetch('/api/change_strategy', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ strategy })
                })
                .then(response => response.json())
                .then(data => {
                    updateDashboard();
                });
            }
            
            // Add new trading pair
            function addPair() {
                const pair = document.getElementById('pair-input').value.trim().toUpperCase();
                const htf = document.getElementById('htf-interval').value;
                const ltf = document.getElementById('ltf-interval').value;
                const risk = document.getElementById('risk-percentage').value / 100;
                
                fetch('/api/add_pair', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        pair: pair,
                        htf: htf,
                        ltf: ltf,
                        risk: risk
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        addPairModal.hide();
                        updateDashboard();
                    } else {
                        alert('Error: ' + data.error);
                    }
                });
            }
            
            // Remove trading pair
            function removePair(pair) {
                if (!confirm(`Are you sure you want to remove ${pair}?`)) {
                    return;
                }
                
                fetch('/api/remove_pair', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ pair })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateDashboard();
                    } else {
                        alert('Error: ' + data.error);
                    }
                });
            }
            
            // Event listeners
            document.getElementById('toggle-bot').addEventListener('click', toggleBot);
            document.getElementById('change-strategy').addEventListener('click', changeStrategy);
            document.getElementById('add-pair-btn').addEventListener('click', function() {
                addPairModal.show();
            });
            document.getElementById('confirm-add-pair').addEventListener('click', addPair);
            
            // Refresh button
            document.getElementById('refresh-data').addEventListener('click', function() {
                updateDashboard();
                updateTradeHistory();
            });
            
            // Trade filter change
            document.getElementById('trade-filter').addEventListener('change', displayFilteredTrades);
            
            // Initial update
            updateDashboard();
            updateTradeHistory();
        });
    </script>
</body>
</html>''')

def initialize_demo_data():
    """Initialize demo data for testing the dashboard"""
    global bot_status, pair_status
    
    # Set up demo bot status
    bot_status = {
        'is_running': True,
        'strategy': 'Original',
        'pairs': ['BTCBUSD', 'ETHBUSD', 'BNBBUSD'],
        'total_value': 1000.0,
        'total_trades': 15,
        'win_rate': 60.0,
        'active_positions': 1,
        'daily_bias': 'bullish',  # Add daily bias
        'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Set up demo pair status
    pair_status = {
        'BTCBUSD': {
            'trading_pair': 'BTCBUSD',
            'position': 'long',
            'entry_price': 28500.0,
            'current_price': 28650.0,
            'pnl': 0.53,
            'daily_bias': 'bullish',  # Add daily bias for each pair
            'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        'ETHBUSD': {
            'trading_pair': 'ETHBUSD',
            'base_balance': 200.0,
            'asset_balance': 0.0,
            'current_price': 3800.0,
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
            'current_price': 600.0,
            'market_bias': 'Neutral',
            'active_fvgs': 0,
            'position_open': False,
            'total_trades': 2,
            'win_rate': 50.0,
            'avg_profit': 0.8,
            'total_value': 0.0
        }
    }

# Sample trades data for demonstration
trades_data = {
    'trades': [
        {
            'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'pair': 'BTCBUSD',
            'type': 'BUY',
            'price': 89500.0,
            'quantity': 0.01,
            'profit': 0.0
        },
        {
            'time': (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'pair': 'ETHBUSD',
            'type': 'SELL',
            'price': 3750.0,
            'quantity': 0.05,
            'profit': 1.2
        },
        {
            'time': (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
            'pair': 'ETHBUSD',
            'type': 'BUY',
            'price': 3700.0,
            'quantity': 0.05,
            'profit': 0.0
        }
    ]
}

def update_bot_status(status_update):
    """Update the bot status with new information"""
    global bot_status
    bot_status.update(status_update)
    logger.info(f"Bot status updated: {bot_status['is_running']}, Strategy: {bot_status['strategy']}, Pairs: {bot_status['pairs']}")

def update_pair_status(pair, status_update):
    """Update the status of a specific trading pair"""
    global pair_status
    if pair in pair_status:
        pair_status[pair].update(status_update)
    else:
        pair_status[pair] = status_update
    logger.info(f"Pair status updated: {pair}")

def add_trade(trade_data):
    """Add a new trade to the trades log"""
    global trades_data
    trades_data['trades'].insert(0, trade_data)
    # Keep only the most recent 50 trades
    if len(trades_data['trades']) > 50:
        trades_data['trades'] = trades_data['trades'][:50]
    logger.info(f"Trade added: {trade_data['pair']} {trade_data['type']} at {trade_data['price']}")

@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    """Return the current status of the bot"""
    return jsonify(bot_status)

@app.route('/api/pair_status')
def get_pair_status():
    """Return the status of all trading pairs"""
    return jsonify(pair_status)

@app.route('/api/trades')
def get_trades():
    """Return the recent trades data"""
    return jsonify(trades_data)

@app.route('/api/toggle', methods=['GET'])
def toggle_bot():
    """Toggle the bot's running status"""
    global bot_status
    bot_status['is_running'] = not bot_status['is_running']
    logger.info(f"Bot status toggled to: {'running' if bot_status['is_running'] else 'stopped'}")
    return jsonify({'success': True, 'is_running': bot_status['is_running']})

@app.route('/api/change_strategy', methods=['POST'])
def change_strategy():
    """Change the active trading strategy"""
    global bot_status
    data = request.get_json()
    
    if 'strategy' not in data:
        return jsonify({'success': False, 'error': 'Strategy not specified'})
    
    strategy = data['strategy']
    if strategy not in ['ICT', 'Original', 'Enhanced']:
        return jsonify({'success': False, 'error': 'Invalid strategy'})
    
    bot_status['strategy'] = strategy
    logger.info(f"Strategy changed to: {strategy}")
    
    return jsonify({'success': True, 'strategy': strategy})

@app.route('/api/add_pair', methods=['POST'])
def add_pair():
    """Add a new trading pair to the bot"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['pair', 'htf', 'ltf', 'risk']
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing required field: {field}'})
    
    # Extract parameters
    pair = data['pair']
    htf = data['htf']
    ltf = data['ltf']
    risk = data['risk']
    
    # Check if pair already exists
    if pair in bot_status['pairs']:
        return jsonify({'success': False, 'error': f'Pair {pair} already added'})
    
    # Add pair to bot status
    bot_status['pairs'].append(pair)
    
    # Initialize pair status
    update_pair_status(pair, {
        'trading_pair': pair,
        'base_balance': 0.0,
        'asset_balance': 0.0,
        'current_price': 0.0,
        'market_bias': 'Unknown',
        'active_fvgs': 0,
        'position_open': False,
        'total_trades': 0,
        'win_rate': 0.0,
        'avg_profit': 0.0,
        'total_value': 0.0
    })
    
    logger.info(f"Added trading pair: {pair} with HTF: {htf}, LTF: {ltf}, Risk: {risk}")
    
    return jsonify({'success': True, 'pair': pair})

@app.route('/api/remove_pair', methods=['POST'])
def remove_pair():
    """Remove a trading pair from the bot"""
    data = request.get_json()
    
    if 'pair' not in data:
        return jsonify({'success': False, 'error': 'Pair not specified'})
    
    pair = data['pair']
    
    # Check if pair exists
    if pair not in bot_status['pairs']:
        return jsonify({'success': False, 'error': f'Pair {pair} not found'})
    
    # Remove pair from bot status
    bot_status['pairs'].remove(pair)
    
    # Remove pair from pair status
    if pair in pair_status:
        del pair_status[pair]
    
    logger.info(f"Removed trading pair: {pair}")
    
    return jsonify({'success': True, 'pair': pair})

@app.route('/api/logs')
def get_logs():
    """Return logs for the dashboard"""
    log_type = request.args.get('type', 'all')
    
    # Filter logs based on type
    if log_type == 'all':
        filtered_logs = logs
    elif log_type == 'trades':
        filtered_logs = [log for log in logs if 'trade' in log['message'].lower()]
    elif log_type == 'errors':
        filtered_logs = [log for log in logs if log['level'] == 'ERROR']
    else:
        filtered_logs = logs
    
    return jsonify(filtered_logs)

@app.route('/api/trade_history')
def get_trade_history():
    """Return complete trade history with matching entries/exits"""
    # This is sample data - you'll need to implement this based on your actual trade storage
    trades = [
        {
            'id': 'T1001',
            'pair': 'BTCBUSD',
            'type': 'LONG',
            'entry_time': '2023-06-01 09:30:45',
            'exit_time': '2023-06-01 14:15:22',
            'entry_price': 28500.50,
            'exit_price': 29100.25,
            'size': 0.05,
            'pnl_percent': 2.1,
            'pnl_absolute': 29.98,
            'status': 'CLOSED'
        },
        {
            'id': 'T1002',
            'pair': 'ETHBUSD',
            'type': 'SHORT',
            'entry_time': '2023-06-02 11:20:15',
            'exit_time': '2023-06-02 16:45:30',
            'entry_price': 1850.75,
            'exit_price': 1820.25,
            'size': 0.2,
            'pnl_percent': 1.65,
            'pnl_absolute': 6.10,
            'status': 'CLOSED'
        },
        {
            'id': 'T1003',
            'pair': 'BTCBUSD',
            'type': 'LONG',
            'entry_time': '2023-06-03 08:15:33',
            'entry_price': 28750.00,
            'size': 0.05,
            'pnl_percent': -0.35,
            'pnl_absolute': -5.03,
            'status': 'OPEN'
        }
        # Add more sample trades as needed
    ]
    
    return jsonify({'trades': trades})

@app.route('/api/executions')
def get_executions():
    """Return recent trade executions"""
    # This is sample data - implement based on your actual execution storage
    executions = [
        {
            'trade_id': 'T1001',
            'pair': 'BTCBUSD',
            'side': 'BUY',
            'price': 28500.50,
            'quantity': 0.05,
            'time': '2023-06-01 09:30:45',
            'reason': 'Bullish FVG retest at 28475.25'
        },
        {
            'trade_id': 'T1001',
            'pair': 'BTCBUSD',
            'side': 'SELL',
            'price': 29100.25,
            'quantity': 0.05,
            'time': '2023-06-01 14:15:22',
            'reason': 'Take profit reached'
        },
        {
            'trade_id': 'T1002',
            'pair': 'ETHBUSD',
            'side': 'SELL',
            'price': 1850.75,
            'quantity': 0.2,
            'time': '2023-06-02 11:20:15',
            'reason': 'Bearish FVG retest at 1855.50'
        },
        {
            'trade_id': 'T1002',
            'pair': 'ETHBUSD',
            'side': 'BUY',
            'price': 1820.25,
            'quantity': 0.2,
            'time': '2023-06-02 16:45:30',
            'reason': 'Take profit reached'
        },
        {
            'trade_id': 'T1003',
            'pair': 'BTCBUSD',
            'side': 'BUY',
            'price': 28750.00,
            'quantity': 0.05,
            'time': '2023-06-03 08:15:33',
            'reason': 'Bullish liquidity sweep at 28725.00'
        }
        # Add more sample executions as needed
    ]
    
    return jsonify({'executions': executions})

@app.route('/charts/<path:filename>')
def serve_chart(filename):
    """Serve chart images"""
    return send_from_directory('charts', filename)

# Initialize demo data for testing
initialize_demo_data()

if __name__ == '__main__':
    # Run the dashboard
    app.run(host='0.0.0.0', port=8080, debug=True) 