"# cherry-akshare-sse-skill" 
#!/usr/bin/env python3
"""
Cherry Studio API Module - Direct Integration
Provides REST API interface for Cherry Studio to call
"""

from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import logging
from sse_monitor import SSEMarketMonitor, CherryStudioAdapter
from db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize components
db = DatabaseManager()
monitor = SSEMarketMonitor(enable_validation=True, max_stocks=100)


@app.route('/api/v1/market/snapshot', methods=['GET'])
def get_market_snapshot():
    """Get current market snapshot"""
    try:
        if monitor.update():
            report = monitor.get_validation_report()
            return jsonify({
                'status': 'success',
                'data': {
                    'timestamp': report['timestamp'],
                    'total_stocks': report['total_stocks_monitored'],
                    'valid_stocks': report['valid_stocks'],
                    'validity_rate': report['validity_rate'],
                    'update_count': report['update_count']
                }
            })
        else:
            return jsonify({'status': 'error', 'message': 'Failed to fetch data'}), 500
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/v1/market/gainers', methods=['GET'])
def get_top_gainers():
    """Get top gaining stocks"""
    try:
        limit = request.args.get('limit', default=10, type=int)
        
        if not monitor.validated_stocks:
            monitor.update()
        
        gainers = monitor.get_top_gainers(limit)
        return jsonify({
            'status': 'success',
            'data': gainers.to_dict('records')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/v1/market/losers', methods=['GET'])
def get_top_losers():
    """Get top losing stocks"""
    try:
        limit = request.args.get('limit', default=10, type=int)
        
        if not monitor.validated_stocks:
            monitor.update()
        
        losers = monitor.get_top_losers(limit)
        return jsonify({
            'status': 'success',
            'data': losers.to_dict('records')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/v1/market/volume', methods=['GET'])
def get_high_volume():
    """Get high volume stocks"""
    try:
        limit = request.args.get('limit', default=10, type=int)
        
        if not monitor.validated_stocks:
            monitor.update()
        
        volume = monitor.get_high_volume_stocks(limit)
        return jsonify({
            'status': 'success',
            'data': volume.to_dict('records')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/v1/stock/<code>', methods=['GET'])
def get_stock_data(code):
    """Get specific stock data"""
    try:
        if not monitor.validated_stocks:
            monitor.update()
        
        stock = next((s for s in monitor.validated_stocks if s.code == code), None)
        if stock:
            return jsonify({
                'status': 'success',
                'data': stock.to_dict()
            })
        else:
            return jsonify({'status': 'error', 'message': f'Stock {code} not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/v1/database/stats', methods=['GET'])
def get_db_stats():
    """Get database statistics"""
    try:
        stats = db.get_database_stats()
        return jsonify({
            'status': 'success',
            'data': stats
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/v1/export/json', methods=['GET'])
def export_json():
    """Export data as JSON"""
    try:
        if not monitor.validated_stocks:
            monitor.update()
        
        adapter = CherryStudioAdapter(monitor)
        json_data = adapter.export_to_json()
        
        return jsonify({
            'status': 'success',
            'data': json_data
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/v1/export/csv', methods=['GET'])
def export_csv():
    """Export data as CSV"""
    try:
        if not monitor.validated_stocks:
            monitor.update()
        
        adapter = CherryStudioAdapter(monitor)
        filename = adapter.export_to_csv()
        
        return jsonify({
            'status': 'success',
            'data': {'filename': filename}
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("\n" + "="*80)
    print(" SSE Market Monitor - Cherry Studio API Server")
    print("="*80 + "\n")
    print("Starting API server on http://localhost:5000")
    print("\nAvailable Endpoints:")
    print("  GET /api/v1/market/snapshot      - Market overview")
    print("  GET /api/v1/market/gainers       - Top gainers")
    print("  GET /api/v1/market/losers        - Top losers")
    print("  GET /api/v1/market/volume        - High volume stocks")
    print("  GET /api/v1/stock/<code>         - Specific stock data")
    print("  GET /api/v1/database/stats       - Database statistics")
    print("  GET /api/v1/export/json          - Export as JSON")
    print("  GET /api/v1/export/csv           - Export as CSV")
    print("  GET /api/v1/health               - Health check")
    print("\n" + "="*80 + "\n")
    
    app.run(debug=False, host='0.0.0.0', port=5000)
