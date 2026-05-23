import yfinance as yf
import time
import pickle
import os
import random
from datetime import datetime

class RobustNewsCollector:
    def __init__(self):
        self.cache_dir = "cache"
        self.ensure_cache_directory()
        
        # Rate limit 관리 - 링크의 방법 적용
        self.request_timestamps = []
        self.max_requests_per_minute = 10  # 뉴스는 더 적게
        self.min_delay_between_requests = 6.0  # 6초로 증가
        
        # 재시도 설정
        self.max_retries = 5
        self.base_delay = 3.0

    def ensure_cache_directory(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def get_cache_path(self, key):
        return os.path.join(self.cache_dir, f"{key}.pkl")

    def load_cache(self, key, max_age_hours=4):
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
                print(f"뉴스 Rate limit 도달, {sleep_time:.1f}초 대기...")
                time.sleep(sleep_time)
        
        # 최소 지연 시간 체크
        if self.request_timestamps:
            time_since_last = current_time - self.request_timestamps[-1]
            if time_since_last < self.min_delay_between_requests:
                sleep_time = self.min_delay_between_requests - time_since_last
                time.sleep(sleep_time)
        
        self.request_timestamps.append(current_time)

    def collect_robust_news(self, symbol, max_news=10, retry_count=5, delay=3.0):
        """yfinance의 공식 뉴스 API만 사용하여 뉴스 수집 - 429 오류 완전 해결"""
        # 캐시 확인
        cache_key = f"robust_news_{symbol}_{datetime.now().strftime('%Y%m%d_%H')}"
        cached_news = self.load_cache(cache_key, max_age_hours=4)
        if cached_news:
            print(f"캐시에서 뉴스 로드: {symbol}")
            return cached_news
        
        # Rate limit 체크
        self._rate_limit_check()
        
        print(f"yfinance 뉴스 수집 시작: {symbol}")

        news_items = []
        
        # 링크의 방법: 더 강력한 재시도 로직
        for attempt in range(retry_count):
            try:
                # 링크의 방법: 더 긴 지연 시간
                if attempt > 0:
                    wait_time = self.base_delay + (attempt * 5)  # 점진적 대기 시간 증가
                    print(f"  재시도 {attempt + 1}/{retry_count}, {wait_time}초 대기...")
                    time.sleep(wait_time)
                else:
                    # 첫 시도 전 기본 지연
                    time.sleep(random.uniform(2.0, 4.0))
                
                ticker = yf.Ticker(symbol)
                yf_news = ticker.news
                
                if yf_news and len(yf_news) > 0:
                    for news in yf_news[:max_news]:
                        news_items.append({
                            'symbol': symbol,
                            'title': news.get('title', ''),
                            'publisher': news.get('publisher', ''),
                            'link': news.get('link', ''),
                            'providerPublishTime': news.get('providerPublishTime', ''),
                            'type': news.get('type', ''),
                            'uuid': news.get('uuid', ''),
                        })
                    print(f"  {symbol} 뉴스 수집 성공: {len(news_items)}개")
                    break
                else:
                    print(f"  {symbol} 뉴스 없음")
                    break
                    
            except Exception as e:
                print(f"  {symbol} 뉴스 수집 오류 (시도 {attempt + 1}): {e}")
                
                # 429 오류 특별 처리 - 링크의 방법
                if "429" in str(e) or "Too Many Requests" in str(e):
                    wait_time = 30 + (attempt * 15)  # 점진적 대기 시간 증가
                    print(f"  429 오류 감지, {wait_time}초 대기...")
                    time.sleep(wait_time)
                elif attempt < retry_count - 1:
                    time.sleep(10)
                else:
                    print(f"  최대 재시도 횟수 도달: {symbol}")
        
        # 요청 사이에 지연 - 링크의 방법
        time.sleep(delay + random.uniform(1.0, 3.0))
        
        result = {
            'news': news_items,
            'mentioned_stocks': [],
            'total_sources': 1,
            'collection_time': datetime.now().isoformat()
        }
        
        # 캐시 저장
        self.save_cache(cache_key, result)
        print(f"뉴스 수집 완료: {len(news_items)}개")
        return result 