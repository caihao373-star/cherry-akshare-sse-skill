#!/usr/bin/env python3
"""
Database Manager - Handles data persistence and retrieval
Supports SQLite for local development and extensible for other backends
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manage database operations for market data storage"""
    
    def __init__(self, db_path: str = 'market_data.db'):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database tables if they don't exist"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            cursor = self.connection.cursor()
            
            # Create stocks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create stock_snapshots table for historical data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    price REAL NOT NULL,
                    change_percent REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (stock_code) REFERENCES stocks(code)
                )
            ''')
            
            # Create indexes for better query performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_stock_code ON stocks(code)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_snapshot_time ON stock_snapshots(snapshot_time)
            ''')
            
            self.connection.commit()
            logger.info(f"Database initialized at {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def save_stock(self, code: str, name: str) -> bool:
        """
        Save or update stock record
        
        Args:
            code: Stock code (e.g., 'sh600000')
            name: Stock name
            
        Returns:
            bool: True if successful
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO stocks (code, name, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (code, name))
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error saving stock {code}: {e}")
            return False
    
    def save_stock_snapshot(self, code: str, price: float, change_percent: float, volume: int) -> bool:
        """
        Save stock price snapshot
        
        Args:
            code: Stock code
            price: Current price
            change_percent: Change percentage
            volume: Trading volume
            
        Returns:
            bool: True if successful
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO stock_snapshots (stock_code, price, change_percent, volume)
                VALUES (?, ?, ?, ?)
            ''', (code, price, change_percent, volume))
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error saving snapshot for {code}: {e}")
            return False
    
    def save_stocks_batch(self, stocks: List[Dict]) -> bool:
        """
        Save multiple stocks in a transaction
        
        Args:
            stocks: List of stock dictionaries
            
        Returns:
            bool: True if successful
        """
        try:
            cursor = self.connection.cursor()
            
            for stock in stocks:
                cursor.execute('''
                    INSERT OR REPLACE INTO stocks (code, name, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (stock['code'], stock['name']))
                
                cursor.execute('''
                    INSERT INTO stock_snapshots (stock_code, price, change_percent, volume)
                    VALUES (?, ?, ?, ?)
                ''', (stock['code'], stock['price'], stock['change_percent'], stock['volume']))
            
            self.connection.commit()
            logger.info(f"Saved {len(stocks)} stocks to database")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error saving batch stocks: {e}")
            self.connection.rollback()
            return False
    
    def get_stock(self, code: str) -> Optional[Dict]:
        """
        Get stock information
        
        Args:
            code: Stock code
            
        Returns:
            dict: Stock data or None
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM stocks WHERE code = ?', (code,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error retrieving stock {code}: {e}")
            return None
    
    def get_all_stocks(self) -> List[Dict]:
        """
        Get all stocks
        
        Returns:
            list: List of stock data
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM stocks ORDER BY code')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving all stocks: {e}")
            return []
    
    def get_latest_snapshot(self, code: str) -> Optional[Dict]:
        """
        Get latest price snapshot for a stock
        
        Args:
            code: Stock code
            
        Returns:
            dict: Latest snapshot data or None
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT * FROM stock_snapshots 
                WHERE stock_code = ? 
                ORDER BY snapshot_time DESC 
                LIMIT 1
            ''', (code,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error retrieving snapshot for {code}: {e}")
            return None
    
    def get_snapshots_range(self, code: str, start_time: str, end_time: str) -> List[Dict]:
        """
        Get snapshots within time range
        
        Args:
            code: Stock code
            start_time: Start timestamp (ISO format)
            end_time: End timestamp (ISO format)
            
        Returns:
            list: List of snapshots
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT * FROM stock_snapshots 
                WHERE stock_code = ? AND snapshot_time BETWEEN ? AND ?
                ORDER BY snapshot_time DESC
            ''', (code, start_time, end_time))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving snapshots: {e}")
            return []
    
    def get_database_stats(self) -> Dict:
        """
        Get database statistics
        
        Returns:
            dict: Statistics including record counts and file size
        """
        try:
            cursor = self.connection.cursor()
            
            # Count stocks
            cursor.execute('SELECT COUNT(*) as count FROM stocks')
            stock_count = cursor.fetchone()['count']
            
            # Count snapshots
            cursor.execute('SELECT COUNT(*) as count FROM stock_snapshots')
            snapshot_count = cursor.fetchone()['count']
            
            # Get database file size
            db_file = Path(self.db_path)
            file_size = db_file.stat().st_size if db_file.exists() else 0
            
            # Get oldest and latest snapshot times
            cursor.execute('''
                SELECT MIN(snapshot_time) as oldest, MAX(snapshot_time) as latest 
                FROM stock_snapshots
            ''')
            time_row = cursor.fetchone()
            
            return {
                'total_stocks': stock_count,
                'total_snapshots': snapshot_count,
                'database_file_size': file_size,
                'oldest_snapshot': time_row['oldest'] if time_row['oldest'] else None,
                'latest_snapshot': time_row['latest'] if time_row['latest'] else None,
                'timestamp': datetime.now().isoformat()
            }
            
        except sqlite3.Error as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def clear_old_snapshots(self, days: int = 30) -> int:
        """
        Delete snapshots older than specified days
        
        Args:
            days: Number of days to retain
            
        Returns:
            int: Number of deleted records
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                DELETE FROM stock_snapshots 
                WHERE snapshot_time < datetime('now', '-' || ? || ' days')
            ''', (days,))
            self.connection.commit()
            deleted = cursor.rowcount
            logger.info(f"Deleted {deleted} old snapshots")
            return deleted
        except sqlite3.Error as e:
            logger.error(f"Error clearing old snapshots: {e}")
            return 0
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def __del__(self):
        """Ensure database connection is closed on cleanup"""
        self.close()
