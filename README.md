# Cherry Studio - EASTMONEY SSE Market Monitor

## Overview

This project provides a REST API interface to fetch Shanghai Stock Exchange (SSE) market data from EASTMONEY with **anti-crawler mechanisms** built-in.

## Anti-Crawler Solution

**Problem Solved:** PUSH2.EASTMONEY.com was blocking Python `requests` library connections.

**Solution Implemented:**
1. **Browser-like User-Agent Headers** - Mimics Chrome browser to avoid detection
2. **Complete HTTP Headers** - Includes Referer, Accept-Language, DNT, and other browser headers
3. **Session Management** - Uses connection pooling and persistent sessions
4. **Retry Mechanism** - Automatic retries with exponential backoff for failed requests
5. **Proper Timeout Handling** - Prevents hanging connections

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python app.py
```

Server runs on `http://localhost:5000`

## API Endpoints

### 1. Market Snapshot
```
GET /api/v1/market/snapshot
```
Returns overall market statistics and validity report.

**Response:**
```json
{
  "status": "success",
  "data": {
    "timestamp": "2024-01-15T10:30:00",
    "total_stocks": 100,
    "valid_stocks": 98,
    "validity_rate": 98.0,
    "update_count": 5
  }
}
```

### 2. Top Gainers
```
GET /api/v1/market/gainers?limit=10
```
Get top gaining stocks.

**Parameters:**
- `limit` (optional, default: 10) - Number of results

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "code": "sh600000",
      "name": "浦发银行",
      "price": 12.34,
      "change_percent": 2.50,
      "volume": 50000000
    }
  ]
}
```

### 3. Top Losers
```
GET /api/v1/market/losers?limit=10
```
Get top losing stocks.

### 4. High Volume Stocks
```
GET /api/v1/market/volume?limit=10
```
Get stocks with highest trading volume.

### 5. Specific Stock Data
```
GET /api/v1/stock/<code>
```
Get detailed data for a specific stock.

**Example:** `GET /api/v1/stock/sh600000`

### 6. Database Statistics
```
GET /api/v1/database/stats
```
Get database storage statistics.

**Response:**
```json
{
  "status": "success",
  "data": {
    "total_stocks": 250,
    "total_snapshots": 5000,
    "database_file_size": 512000,
    "oldest_snapshot": "2024-01-10T10:00:00",
    "latest_snapshot": "2024-01-15T10:30:00"
  }
}
```

### 7. Export as JSON
```
GET /api/v1/export/json
```
Export all current stock data as JSON.

### 8. Export as CSV
```
GET /api/v1/export/csv
```
Export all current stock data as CSV file.

### 9. Health Check
```
GET /api/v1/health
```
Check server health status.

## File Structure

- `app.py` - Main Flask API server
- `sse_monitor.py` - Market data monitor with anti-crawler headers
- `db_manager.py` - Database management for data persistence
- `requirements.txt` - Python dependencies
- `README.md` - This file

## Key Components

### SSEMarketMonitor
Handles fetching data from EASTMONEY with:
- Proper HTTP headers (User-Agent, Referer, etc.)
- Session management with connection pooling
- Automatic retry mechanism
- Data validation

### StockData
Represents individual stock information with validation methods.

### CherryStudioAdapter
Adapts market monitor data for Cherry Studio integration.

### DatabaseManager
Persistent storage using SQLite with:
- Stock information storage
- Historical price snapshots
- Database statistics and cleanup utilities

## Features

✅ Anti-crawler mechanisms for EASTMONEY  
✅ Automatic retry with exponential backoff  
✅ Data validation and reporting  
✅ Persistent database storage  
✅ CSV/JSON export capabilities  
✅ RESTful API interface  
✅ Comprehensive error handling  
✅ Logging and monitoring  

## Configuration

Edit `sse_monitor.py` to customize:
- Maximum stocks to fetch (default: 100)
- Request timeout (default: 10 seconds)
- Retry strategy
- HTTP headers

## Dependencies

- Flask 2.3.3 - Web framework
- requests 2.31.0 - HTTP library with anti-crawler support
- pandas 2.0.3 - Data analysis
- urllib3 2.0.4 - Connection pooling

## Troubleshooting

### Connection Refused
- Ensure EASTMONEY server is accessible
- Check internet connection
- Verify firewall settings

### Timeout Errors
- Increase timeout in `SSEMarketMonitor.__init__(timeout=15)`
- Check network latency to EASTMONEY servers

### Import Errors
- Run `pip install -r requirements.txt`
- Verify Python 3.7+

## License

Open source - Use freely for educational and commercial purposes.

## Support

For issues or improvements, please open an issue or pull request.
