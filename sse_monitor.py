#!/usr/bin/env python3
"""
SSE Market Monitor - Shanghai Stock Exchange Monitor
Handles data collection from EASTMONEY with anti-crawler mechanisms
"""

import requests
import pandas as pd
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SSEMarketMonitor:
    """Monitor Shanghai Stock Exchange market data with anti-crawler support"""
    
    # Anti-crawler headers - CRITICAL for EASTMONEY bypass
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://quote.eastmoney.com/',
        'Origin': 'https://quote.eastmoney.com',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }
    
    # EASTMONEY API endpoints
    BASE_URL = 'https://push2.eastmoney.com/api/qt/clist/get'
    
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
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create requests session with connection pooling and retries"""
        session = requests.Session()
        session.headers.update(self.HEADERS)
        
        # Add retry mechanism
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def update(self) -> bool:
        """
        Fetch and update market data from EASTMONEY
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Fetching SSE market data from EASTMONEY...")
            
            # Parameters for EASTMONEY API
            params = {
                'param': 'sh,sz',  # Shanghai & Shenzhen exchanges
                'fields': 'f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f19,f20',
                'pageindex': '0',
                'pagesize': str(self.max_stocks),
                'sortTypes': '0',
                'sortFields': 'f2',
                'ut': 'b2884a393a59ad6bfb0bda9987da3e0d',
            }
            
            # Make request with anti-crawler headers
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout,
                verify=True
            )
            
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            if data.get('rc') != 0:
                logger.warning(f"API returned non-zero code: {data.get('rc')}")
                return False
            
            # Process stocks
            stocks_data = data.get('data', {}).get('diff', [])
            
            if not stocks_data:
                logger.warning("No stock data received from EASTMONEY")
                return False
            
            self.validated_stocks = [
                StockData.from_dict(stock) for stock in stocks_data
            ]
            
            self.update_count += 1
            logger.info(f"Successfully fetched {len(self.validated_stocks)} stocks (Update #{self.update_count})")
            
            return True
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to EASTMONEY: {e}")
            return False
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error fetching market data: {e}")
            return False
    
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
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Create StockData from EASTMONEY API response"""
        try:
            return cls(
                code=data.get('f12', ''),
                name=data.get('f14', ''),
                price=float(data.get('f2', 0)) / 100,  # Convert from cents
                change_percent=float(data.get('f3', 0)) / 100,
                volume=int(data.get('f5', 0))
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse stock data: {e}")
            return None
    
    def is_valid(self) -> bool:
        """Check if stock data is valid"""
        return bool(self.code and self.name and self.price >= 0)
    
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
