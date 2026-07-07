#!/usr/bin/env python3
"""
SSE Market Monitor - Shanghai Stock Exchange Monitor
Handles data collection from Sina/Tencent APIs (no anti-crawler issues)
"""

import requests
import pandas as pd
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SSEMarketMonitor:
    """Monitor Shanghai Stock Exchange market data from Sina API"""
    
    # Sina API - No anti-crawler protection
    SINA_API_URL = 'https://vip.stock.finance.sina.com.cn/q_gab=sh,sz'
    
    def __init__(self, enable_validation: bool = True, max_stocks: int = 100, timeout: int = 10):
        """
        Initialize SSE Market Monitor
        
        Args:
            enable_validation: Enable data validation
            max_stocks: Maximum stocks to fetch
            timeout: Request timeout in seconds
        """
        self.enable_validation = enable_validation
        self.max_stocks = max_stocks
        self.timeout = timeout
        self.validated_stocks = []
        self.update_count = 0
        self.session = requests.Session()
        
    def update(self) -> bool:
        """
        Fetch and update market data from Sina API
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Fetching SSE market data from Sina API...")
            
            # Fetch Shanghai stocks
            sh_stocks = self._fetch_sina_stocks('sh')
            
            # Fetch Shenzhen stocks
            sz_stocks = self._fetch_sina_stocks('sz')
            
            # Combine both
            all_stocks = sh_stocks + sz_stocks
            
            if not all_stocks:
                logger.warning("No stock data received from Sina")
                return False
            
            # Limit to max_stocks
            self.validated_stocks = all_stocks[:self.max_stocks]
            self.update_count += 1
            
            logger.info(f"Successfully fetched {len(self.validated_stocks)} stocks (Update #{self.update_count})")
            return True
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return False
    
    def _fetch_sina_stocks(self, exchange: str) -> List['StockData']:
        """
        Fetch stocks from Sina for specific exchange
        
        Args:
            exchange: 'sh' for Shanghai, 'sz' for Shenzhen
            
        Returns:
            List of StockData objects
        """
        try:
            url = f'https://vip.stock.finance.sina.com.cn/q_gab={exchange}'
            response = self.session.get(url, timeout=self.timeout)
            response.encoding = 'gb2312'
            
            stocks = []
            # Parse response format: var hq_str_sh600000="浦发银行,12.34,1.23,2.5,..."
            pattern = r'var hq_str_(\w+)="([^"]+)"'
            
            for match in re.finditer(pattern, response.text):
                code = match.group(1)
                data_str = match.group(2)
                parts = data_str.split(',')
                
                if len(parts) >= 5:
                    try:
                        stock = StockData(
                            code=code,
                            name=parts[0],
                            price=float(parts[3]),
                            change_percent=float(parts[4]) if parts[4] else 0,
                            volume=int(float(parts[8]) * 100) if len(parts) > 8 else 0
                        )
                        if stock.is_valid():
                            stocks.append(stock)
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Failed to parse stock {code}: {e}")
                        continue
            
            logger.info(f"Fetched {len(stocks)} stocks from {exchange}")
            return stocks
            
        except Exception as e:
            logger.error(f"Error fetching {exchange} stocks from Sina: {e}")
            return []
    
    def get_validation_report(self) -> Dict:
        """Get validation report of current data"""
        total = len(self.validated_stocks)
        valid = sum(1 for s in self.validated_stocks if s.is_valid())
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_stocks_monitored': total,
            'valid_stocks': valid,
            'validity_rate': (valid / total * 100) if total > 0 else 0,
            'update_count': self.update_count
        }
    
    def get_top_gainers(self, limit: int = 10) -> pd.DataFrame:
        """Get top gaining stocks"""
        if not self.validated_stocks:
            return pd.DataFrame()
        
        df = pd.DataFrame([s.to_dict() for s in self.validated_stocks])
        if df.empty or 'change_percent' not in df.columns:
            return pd.DataFrame()
        
        return df.nlargest(limit, 'change_percent')[['code', 'name', 'price', 'change_percent', 'volume']]
    
    def get_top_losers(self, limit: int = 10) -> pd.DataFrame:
        """Get top losing stocks"""
        if not self.validated_stocks:
            return pd.DataFrame()
        
        df = pd.DataFrame([s.to_dict() for s in self.validated_stocks])
        if df.empty or 'change_percent' not in df.columns:
            return pd.DataFrame()
        
        return df.nsmallest(limit, 'change_percent')[['code', 'name', 'price', 'change_percent', 'volume']]
    
    def get_high_volume_stocks(self, limit: int = 10) -> pd.DataFrame:
        """Get high volume stocks"""
        if not self.validated_stocks:
            return pd.DataFrame()
        
        df = pd.DataFrame([s.to_dict() for s in self.validated_stocks])
        if df.empty or 'volume' not in df.columns:
            return pd.DataFrame()
        
        return df.nlargest(limit, 'volume')[['code', 'name', 'price', 'volume', 'change_percent']]


class StockData:
    """Represents individual stock data"""
    
    def __init__(self, code: str, name: str, price: float, change_percent: float, volume: int):
        self.code = code
        self.name = name
        self.price = price
        self.change_percent = change_percent
        self.volume = volume
    
    def is_valid(self) -> bool:
        """Check if stock data is valid"""
        return bool(self.code and self.name and self.price > 0)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'code': self.code,
            'name': self.name,
            'price': round(self.price, 2),
            'change_percent': round(self.change_percent, 2),
            'volume': self.volume
        }


class CherryStudioAdapter:
    """Adapter for Cherry Studio integration"""
    
    def __init__(self, monitor: SSEMarketMonitor):
        self.monitor = monitor
    
    def export_to_json(self) -> Dict:
        """Export data to JSON format"""
        return {
            'timestamp': datetime.now().isoformat(),
            'total_stocks': len(self.monitor.validated_stocks),
            'stocks': [s.to_dict() for s in self.monitor.validated_stocks],
            'metadata': self.monitor.get_validation_report()
        }
    
    def export_to_csv(self) -> str:
        """Export data to CSV format"""
        if not self.monitor.validated_stocks:
            return None
        
        df = pd.DataFrame([s.to_dict() for s in self.monitor.validated_stocks])
        filename = f'sse_market_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f"Exported to {filename}")
        return filename
