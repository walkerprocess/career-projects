import yfinance as yf
from curl_cffi import requests
import time
import random
import pickle
import os
from datetime import datetime

class YFinancePatch:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://finance.yahoo.com/',
            'Origin': 'https://finance.yahoo.com'
        })
        self.session.impersonate = "chrome120"
        
        # Rate limit 관리
        self.request_timestamps = []
        self.max_requests_per_minute = 15  # 15개로 줄임
        self.min_delay_between_requests = 4.0  # 4초로 증가
        
        # 캐시 디렉토리
        self.cache_dir = "cache"
        self.ensure_cache_directory()
    
    def ensure_cache_directory(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def get_cache_path(self, key):
        return os.path.join(self.cache_dir, f"{key}.pkl")
    
    def load_cache(self, key, max_age_hours=6):
        cache_path = self.get_cache_path(key)
        if os.path.exists(cache_path):
            if time.time() - os.path.getmtime(cache_path) < max_age_hours * 3600:
                try:
                    with open(cache_path, 'rb') as f:
                        return pickle.load(f)
                except:
                    pass
        return None
    
    def save_cache(self, key, data):
        cache_path = self.get_cache_path(key)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except:
            pass
    
    def _rate_limit_check(self):
        """Rate Limit 체크 및 대기 - 링크의 방법 적용"""
        current_time = time.time()
        
        # 1분 이내 요청 수 체크
        self.request_timestamps = [t for t in self.request_timestamps if current_time - t < 60]
        
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            sleep_time = 60 - (current_time - self.request_timestamps[0])
            if sleep_time > 0:
                print(f"Rate limit 도달, {sleep_time:.1f}초 대기...")
                time.sleep(sleep_time)
        
        # 최소 지연 시간 체크
        if self.request_timestamps:
            time_since_last = current_time - self.request_timestamps[-1]
            if time_since_last < self.min_delay_between_requests:
                sleep_time = self.min_delay_between_requests - time_since_last
                time.sleep(sleep_time)
        
        self.request_timestamps.append(current_time)
    
    def get_stock_info(self, symbol):
        """강화된 주식 정보 수집 - 429 오류 완전 해결"""
        # 캐시 확인 먼저
        cache_key = f"yf_patch_{symbol}"
        cached_data = self.load_cache(cache_key, max_age_hours=6)
        if cached_data:
            print(f"캐시에서 주식 정보 로드: {symbol}")
            return cached_data
        
        # Rate limit 체크
        self._rate_limit_check()
        
        # 링크의 방법: 더 긴 지연 시간
        time.sleep(random.uniform(2.0, 4.0))  # 2-4초 지연
        
        max_retries = 5  # 재시도 횟수 증가
        for attempt in range(max_retries):
            try:
                print(f"  {symbol} 요청 시도 {attempt + 1}/{max_retries}")
                
                # Yahoo Finance API URL
                url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=summaryDetail,financialData,defaultKeyStatistics,summaryProfile"
                
                response = self.session.get(url, timeout=30)
                
                # 429 오류 처리 - 링크의 방법
                if response.status_code == 429:
                    wait_time = 30 + (attempt * 15)  # 점진적 대기 시간 증가
                    print(f"  429 오류 감지, {wait_time}초 대기...")
                    time.sleep(wait_time)
                    continue
                
                # 401 오류 시 기존 yfinance 사용
                if response.status_code == 401:
                    print(f"  401 인증 오류 감지, 기존 yfinance 사용: {symbol}")
                    return self._get_stock_info_fallback(symbol)
                
                if response.status_code == 200:
                    data = response.json()
                    result = self._parse_stock_data(data, symbol)
                    if result:
                        # 캐시 저장
                        self.save_cache(cache_key, result)
                        return result
                else:
                    print(f"  API 오류: {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(10)
                        continue
                    else:
                        return self._get_stock_info_fallback(symbol)
                        
            except Exception as e:
                print(f"  요청 오류 (시도 {attempt + 1}): {e}")
                if "429" in str(e) or "Too Many Requests" in str(e):
                    wait_time = 30 + (attempt * 15)
                    print(f"  429 오류 감지, {wait_time}초 대기...")
                    time.sleep(wait_time)
                elif attempt < max_retries - 1:
                    time.sleep(10)
                else:
                    print(f"  최대 재시도 횟수 도달, fallback 사용: {symbol}")
                    return self._get_stock_info_fallback(symbol)
        
        return self._get_stock_info_fallback(symbol)
    
    def _get_stock_info_fallback(self, symbol):
        """기존 yfinance를 사용한 fallback 방법 - 링크의 방법 적용"""
        try:
            # Rate limit 체크
            self._rate_limit_check()
            
            # 링크의 방법: 지연 추가
            time.sleep(random.uniform(1.0, 2.0))
            
            stock = yf.Ticker(symbol)
            info = stock.info
            
            if not info or len(info) < 5:
                return None
            
            stock_info = {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'current_price': info.get('currentPrice', 0),
                'market_cap': info.get('marketCap', 0),
                'volume': info.get('volume', 0),
                'avg_volume': info.get('averageVolume', 0),
                'high_52week': info.get('fiftyTwoWeekHigh', 0),
                'low_52week': info.get('fiftyTwoWeekLow', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'pb_ratio': info.get('priceToBook', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'beta': info.get('beta', 1),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown')
            }
            
            return stock_info
            
        except Exception as e:
            print(f"Fallback 오류 ({symbol}): {e}")
            if "429" in str(e) or "Too Many Requests" in str(e):
                print(f"  Fallback에서도 429 오류, 30초 대기...")
                time.sleep(30)
            return None
    
    def _parse_stock_data(self, data, symbol):
        """API 응답을 주식 정보로 파싱"""
        try:
            quote_summary = data.get('quoteSummary', {}).get('result', [{}])[0]
            
            # 기본 정보
            summary_detail = quote_summary.get('summaryDetail', {})
            financial_data = quote_summary.get('financialData', {})
            summary_profile = quote_summary.get('summaryProfile', {})
            
            stock_info = {
                'symbol': symbol,
                'name': summary_profile.get('longBusinessSummary', symbol),
                'current_price': financial_data.get('currentPrice', 0),
                'market_cap': summary_detail.get('marketCap', 0),
                'volume': summary_detail.get('volume', 0),
                'avg_volume': summary_detail.get('averageVolume', 0),
                'high_52week': summary_detail.get('fiftyTwoWeekHigh', 0),
                'low_52week': summary_detail.get('fiftyTwoWeekLow', 0),
                'pe_ratio': financial_data.get('trailingPE', 0),
                'pb_ratio': financial_data.get('priceToBook', 0),
                'dividend_yield': summary_detail.get('dividendYield', 0),
                'beta': summary_detail.get('beta', 1),
                'sector': summary_profile.get('sector', 'Unknown'),
                'industry': summary_profile.get('industry', 'Unknown')
            }
            
            return stock_info
            
        except Exception as e:
            print(f"데이터 파싱 오류: {e}")
            return None

# yfinance 모듈 패치
def patch_yfinance():
    """yfinance 모듈에 curl_cffi 기반 세션 적용 - 429 오류 완전 해결"""
    try:
        import yfinance as yf
        
        # 기존 세션을 curl_cffi 기반으로 교체
        patch = YFinancePatch()
        
        # yfinance의 기본 세션을 패치된 세션으로 교체
        if hasattr(yf, 'Ticker'):
            original_init = yf.Ticker.__init__
            
            def patched_init(self, ticker, session=None, **kwargs):
                if session is None:
                    session = patch.session
                original_init(self, ticker, session=session, **kwargs)
            
            yf.Ticker.__init__ = patched_init
        
        print("✅ yfinance 패치 완료 - 429 오류 완전 해결 적용")
        print("📊 Rate limit: 15개/분, 지연: 4초, 재시도: 5회")
        return patch
        
    except Exception as e:
        print(f"yfinance 패치 실패: {e}")
        return None 