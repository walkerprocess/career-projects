import requests
import time
import pickle
import os
import random
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import yfinance as yf
from dotenv import load_dotenv
import concurrent.futures
import threading
from yfinance_patch import YFinancePatch

# 환경 변수 로드
load_dotenv()

class EnhancedNewsCollector:
    def __init__(self):
        self.cache_dir = "cache"
        self.ensure_cache_directory()
        self.news_api_key = os.getenv('NEWS_API_KEY')
        self.news_api_base_url = "https://newsapi.org/v2"
        self.request_timestamps = []
        self.max_requests_per_minute = 15
        self.min_delay_between_requests = 4.0
        self.max_retries = 3
        self.base_delay = 2.0
        self.stock_pattern = re.compile(r'\b[A-Z]{1,5}\b')
        self.rate_limit_lock = threading.Lock()
        self.exclude_words = {
            'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE',
            'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'MAN', 'NEW', 'NOW', 'OLD',
            'SEE', 'TWO', 'WAY', 'WHO', 'BOY', 'DID', 'ITS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO',
            'USE', 'FED', 'GDP', 'CEO', 'CFO', 'CTO', 'IPO', 'SEC', 'IRS', 'FDA', 'EPA', 'FBI',
            'CIA', 'USA', 'UK', 'EU', 'UN', 'WHO', 'WTO', 'IMF', 'NATO', 'UN', 'EU', 'US', 'UK'
        }
        # 실제 주식 티커 목록 (주요 주식들) - 더 많은 주식 추가
        self.valid_stock_symbols = {
            # 대형 기술주
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'ADBE', 'CRM',
            'ORCL', 'CSCO', 'INTC', 'AMD', 'QCOM', 'AVGO', 'ADI', 'AMAT', 'KLAC', 'LRCX',
            'MU', 'TXN', 'IBM', 'HPQ', 'DELL', 'WDAY', 'SNOW', 'PLTR', 'ZM', 'TEAM', 'OKTA',
            'CRWD', 'ZS', 'NET', 'DDOG', 'MDB', 'ESTC', 'SPLK', 'PATH', 'RBLX', 'U',
            
            # 대형 소비재
            'KO', 'PEP', 'PG', 'JNJ', 'UNH', 'HD', 'LOW', 'COST', 'WMT', 'TGT', 'SBUX', 
            'MCD', 'NKE', 'DIS', 'CMCSA', 'VZ', 'T', 'TMUS', 'CHTR', 'CME', 'MAR', 'HLT',
            'BKNG', 'EXPE', 'ABNB', 'UBER', 'LYFT', 'DASH', 'SHOP', 'EBAY', 'ETSY',
            
            # 금융주
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'AXP', 'C', 'USB', 'PNC', 'TFC',
            'SCHW', 'COF', 'AIG', 'MET', 'PRU', 'ALL', 'TRV', 'PGR', 'CB', 'MMC', 'AJG',
            'SPGI', 'MCO', 'FICO', 'ICE', 'CME', 'NDAQ', 'CBOE', 'MKTX',
            
            # 헬스케어
            'JNJ', 'PFE', 'ABT', 'TMO', 'DHR', 'UNH', 'ANTM', 'CI', 'HUM', 'CVS', 'WBA', 
            'ISRG', 'GILD', 'AMGN', 'BMY', 'LLY', 'MRK', 'ABBV', 'VRTX', 'REGN', 'BIIB',
            'ALXN', 'ILMN', 'DXCM', 'IDXX', 'ALGN', 'WST', 'COO', 'MTD', 'WAT', 'TMO',
            
            # 산업재
            'CAT', 'DE', 'BA', 'RTX', 'LMT', 'GD', 'NOC', 'HON', 'GE', 'UPS', 'FDX',
            'UNP', 'CSX', 'NSC', 'CP', 'KSU', 'EMR', 'ETN', 'ITW', 'MMM', 'DOV', 'XYL',
            'AME', 'FTV', 'PH', 'ROK', 'DHR', 'DOV', 'XYL', 'AME', 'FTV', 'PH', 'ROK',
            
            # 에너지
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'HAL', 'BKR', 'KMI', 'WMB', 'ENB', 'PXD',
            'VLO', 'MPC', 'PSX', 'OXY', 'DVN', 'PXD', 'VLO', 'MPC', 'PSX', 'OXY', 'DVN',
            
            # 소재
            'LIN', 'APD', 'FCX', 'NEM', 'AA', 'NUE', 'STLD', 'X', 'CLF', 'NEM', 'FCX',
            'APD', 'LIN', 'ECL', 'IFF', 'ALB', 'LTHM', 'SQM', 'MOS', 'NTR', 'CF', 'NUE',
            
            # 유틸리티
            'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'XEL', 'SRE', 'DTE', 'ED', 'EIX',
            'PCG', 'WEC', 'AEE', 'CMS', 'CNP', 'D', 'DTE', 'ED', 'EIX', 'PCG', 'WEC',
            
            # REITs
            'PLD', 'AMT', 'CCI', 'EQIX', 'DLR', 'PSA', 'SPG', 'O', 'WELL', 'VICI', 'AMH',
            'AVB', 'EQR', 'MAA', 'UDR', 'ESS', 'CPT', 'BXP', 'VNO', 'SLG', 'KIM', 'REG',
            
            # 기타 주요 주식
            'BRK.A', 'BRK.B', 'V', 'MA', 'PYPL', 'SQ', 'COIN', 'ROKU', 'SPOT', 'TWTR', 
            'SNAP', 'PINS', 'ZM', 'TEAM', 'OKTA', 'CRWD', 'ZS', 'NET', 'DDOG', 'MDB',
            'ESTC', 'SPLK', 'PATH', 'RBLX', 'U', 'DASH', 'ABNB', 'SHOP', 'EBAY', 'ETSY',
            
            # 추가 대형주
            'V', 'MA', 'PYPL', 'SQ', 'COIN', 'ROKU', 'SPOT', 'TWTR', 'SNAP', 'PINS',
            'ZM', 'TEAM', 'OKTA', 'CRWD', 'ZS', 'NET', 'DDOG', 'MDB', 'ESTC', 'SPLK',
            'PATH', 'RBLX', 'U', 'DASH', 'ABNB', 'SHOP', 'EBAY', 'ETSY', 'ZM', 'TEAM',
            
            # 중소형 성장주
            'CRWD', 'ZS', 'NET', 'DDOG', 'MDB', 'ESTC', 'SPLK', 'PATH', 'RBLX', 'U',
            'DASH', 'ABNB', 'SHOP', 'EBAY', 'ETSY', 'ZM', 'TEAM', 'OKTA', 'CRWD', 'ZS',
            'NET', 'DDOG', 'MDB', 'ESTC', 'SPLK', 'PATH', 'RBLX', 'U', 'DASH', 'ABNB',
            
            # 추가 섹터별 주식
            'TSLA', 'F', 'GM', 'TM', 'HMC', 'NIO', 'XPEV', 'LI', 'LCID', 'RIVN', 'FSR',
            'NKLA', 'WKHS', 'CANOO', 'ARVL', 'GOEV', 'HYLN', 'IDEX', 'SOLO', 'WKHS',
            
            # 바이오테크
            'MRNA', 'BNTX', 'NVAX', 'INO', 'VAX', 'OCGN', 'SAVA', 'INO', 'VAX', 'OCGN',
            'SAVA', 'INO', 'VAX', 'OCGN', 'SAVA', 'INO', 'VAX', 'OCGN', 'SAVA', 'INO',
            
            # 반도체
            'NVDA', 'AMD', 'INTC', 'QCOM', 'AVGO', 'ADI', 'AMAT', 'KLAC', 'LRCX', 'MU',
            'TXN', 'MRVL', 'ON', 'STM', 'NXPI', 'MCHP', 'ADI', 'AMAT', 'KLAC', 'LRCX',
            
            # 클라우드/SaaS
            'MSFT', 'GOOGL', 'AMZN', 'CRM', 'WDAY', 'SNOW', 'PLTR', 'ZM', 'TEAM', 'OKTA',
            'CRWD', 'ZS', 'NET', 'DDOG', 'MDB', 'ESTC', 'SPLK', 'PATH', 'RBLX', 'U',
            
            # 전기차/자율주행
            'TSLA', 'NIO', 'XPEV', 'LI', 'LCID', 'RIVN', 'FSR', 'NKLA', 'WKHS', 'CANOO',
            'ARVL', 'GOEV', 'HYLN', 'IDEX', 'SOLO', 'WKHS', 'CANOO', 'ARVL', 'GOEV',
            
            # 게임/엔터테인먼트
            'ATVI', 'EA', 'TTWO', 'ZNGA', 'RBLX', 'U', 'NTDOY', 'SNE', 'MSFT', 'GOOGL',
            'META', 'NFLX', 'DIS', 'CMCSA', 'VZ', 'T', 'TMUS', 'CHTR', 'CME', 'MAR',
            
            # 금융기술
            'V', 'MA', 'PYPL', 'SQ', 'COIN', 'ROKU', 'SPOT', 'TWTR', 'SNAP', 'PINS',
            'ZM', 'TEAM', 'OKTA', 'CRWD', 'ZS', 'NET', 'DDOG', 'MDB', 'ESTC', 'SPLK',
            
            # 추가 주요 주식들
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'ADBE', 'CRM',
            'ORCL', 'CSCO', 'INTC', 'AMD', 'QCOM', 'AVGO', 'ADI', 'AMAT', 'KLAC', 'LRCX',
            'MU', 'TXN', 'IBM', 'HPQ', 'DELL', 'WDAY', 'SNOW', 'PLTR', 'ZM', 'TEAM', 'OKTA'
        }
        # 1. 빅테크/초대형주 심볼 리스트 추가
        self.BIG_TECH_SYMBOLS = {
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'BRK.B', 'BRK.A', 'V', 'MA', 'JPM', 'UNH', 'XOM', 'PG', 'LLY', 'HD', 'CVX', 'KO', 'PEP'
        }
    def ensure_cache_directory(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    def get_cache_path(self, key):
        return os.path.join(self.cache_dir, f"{key}.pkl")
    def load_cache(self, key, max_age_hours=2):
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
        with self.rate_limit_lock:
            current_time = time.time()
            self.request_timestamps = [t for t in self.request_timestamps if current_time - t < 60]
            if len(self.request_timestamps) >= self.max_requests_per_minute:
                sleep_time = 60 - (current_time - self.request_timestamps[0])
                if sleep_time > 0:
                    print(f"뉴스 Rate limit 도달, {sleep_time:.1f}초 대기...")
                    time.sleep(sleep_time)
            if self.request_timestamps:
                time_since_last = current_time - self.request_timestamps[-1]
                if time_since_last < self.min_delay_between_requests:
                    sleep_time = self.min_delay_between_requests - time_since_last
                    time.sleep(sleep_time)
            self.request_timestamps.append(current_time)
    def extract_stock_symbols_from_text(self, text):
        """더 정확한 주식 티커 추출"""
        potential_symbols = set()
        
        # 대문자로 변환하고 단어 경계에서 추출
        text_upper = text.upper()
        
        # 정규식으로 2-5글자 대문자 조합 찾기
        matches = self.stock_pattern.findall(text_upper)
        
        for match in matches:
            # 기본 필터링
            if (match not in self.exclude_words and 
                len(match) >= 2 and 
                len(match) <= 5 and
                match.isalpha() and  # 알파벳만
                match in self.valid_stock_symbols):  # 실제 주식 티커인지 확인
                potential_symbols.add(match)
        
        # 추가 검증: 주식 티커 패턴 확인
        verified_symbols = set()
        for symbol in potential_symbols:
            # 일반적인 주식 티커 패턴 확인
            if (len(symbol) >= 2 and 
                symbol.isalpha() and 
                not symbol.endswith('S') or  # 복수형 제외
                symbol in ['MS', 'TS', 'US', 'AS', 'IS', 'IN', 'ON', 'AT', 'TO', 'OF', 'BY', 'UP', 'GO']):  # 일반 단어 제외
                continue
            verified_symbols.add(symbol)
        
        return list(verified_symbols)
    def get_news_api_articles(self, category, query=None, max_articles=10):
        if not self.news_api_key:
            print("NEWS API 키가 설정되지 않았습니다.")
            return []
        self._rate_limit_check()
        try:
            category_queries = {
                'business': ['stock market', 'earnings', 'financial', 'investment'],
                'technology': ['artificial intelligence', 'tech stocks', 'semiconductor', 'software'],
                'general': ['economy', 'federal reserve', 'inflation', 'GDP'],
                'health': ['healthcare stocks', 'pharmaceutical', 'biotech'],
                'science': ['technology innovation', 'research', 'development']
            }
            if query:
                search_query = query
            else:
                search_query = ' OR '.join(category_queries.get(category, ['stock market']))
            params = {
                'q': search_query,
                'apiKey': self.news_api_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': max_articles
            }
            response = requests.get(f"{self.news_api_base_url}/everything", params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                processed_articles = []
                for article in articles:
                    title = article.get('title', '')
                    description = article.get('description', '')
                    content = article.get('content', '')
                    full_text = f"{title} {description} {content}"
                    mentioned_stocks = self.extract_stock_symbols_from_text(full_text)
                    processed_articles.append({
                        'title': title,
                        'content': description or content or title,
                        'url': article.get('url', ''),
                        'source': article.get('source', {}).get('name', 'News API'),
                        'published_at': article.get('publishedAt', ''),
                        'category': category,
                        'mentioned_stocks': mentioned_stocks,
                        'impact': self._analyze_news_sentiment(title, description),
                        'confidence': self._analyze_news_confidence(article)
                    })
                return processed_articles
            else:
                print(f"NEWS API 오류: {response.status_code}")
                return []
        except Exception as e:
            print(f"NEWS API 요청 오류: {e}")
            return []
    def crawl_finance_websites(self, category, max_articles=5):
        self._rate_limit_check()
        websites = {
            'business': [
                'https://finance.yahoo.com/news/',
                'https://www.marketwatch.com/latest-news',
                'https://www.cnbc.com/markets/'
            ],
            'technology': [
                'https://techcrunch.com/',
                'https://www.theverge.com/',
                'https://www.wired.com/'
            ],
            'general': [
                'https://www.reuters.com/business/',
                'https://www.bloomberg.com/markets',
                'https://www.ft.com/markets'
            ]
        }
        articles = []
        site_list = websites.get(category, websites['business'])
        for site in site_list[:2]:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(site, headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    if 'yahoo.com' in site:
                        articles.extend(self._parse_yahoo_finance(soup, category))
                    elif 'marketwatch.com' in site:
                        articles.extend(self._parse_marketwatch(soup, category))
                    elif 'cnbc.com' in site:
                        articles.extend(self._parse_cnbc(soup, category))
                    else:
                        articles.extend(self._parse_generic_site(soup, category))
            except Exception as e:
                print(f"크롤링 오류 ({site}): {e}")
                continue
        return articles[:max_articles]
    def _parse_yahoo_finance(self, soup, category):
        articles = []
        try:
            news_links = soup.find_all('a', href=re.compile(r'/news/'))
            for link in news_links[:5]:
                title = link.get_text(strip=True)
                if title and len(title) > 20:
                    mentioned_stocks = self.extract_stock_symbols_from_text(title)
                    articles.append({
                        'title': title,
                        'content': title,
                        'url': f"https://finance.yahoo.com{link.get('href')}",
                        'source': 'Yahoo Finance',
                        'category': category,
                        'mentioned_stocks': mentioned_stocks,
                        'impact': self._analyze_news_sentiment(title, title),
                        'confidence': '높음'
                    })
        except Exception as e:
            print(f"Yahoo Finance 파싱 오류: {e}")
        return articles
    def _parse_marketwatch(self, soup, category):
        articles = []
        try:
            news_links = soup.find_all('a', class_=re.compile(r'link'))
            for link in news_links[:5]:
                title = link.get_text(strip=True)
                if title and len(title) > 20:
                    mentioned_stocks = self.extract_stock_symbols_from_text(title)
                    articles.append({
                        'title': title,
                        'content': title,
                        'url': link.get('href'),
                        'source': 'MarketWatch',
                        'category': category,
                        'mentioned_stocks': mentioned_stocks,
                        'impact': self._analyze_news_sentiment(title, title),
                        'confidence': '높음'
                    })
        except Exception as e:
            print(f"MarketWatch 파싱 오류: {e}")
        return articles
    def _parse_cnbc(self, soup, category):
        articles = []
        try:
            news_links = soup.find_all('a', href=re.compile(r'/202'))
            for link in news_links[:5]:
                title = link.get_text(strip=True)
                if title and len(title) > 20:
                    mentioned_stocks = self.extract_stock_symbols_from_text(title)
                    articles.append({
                        'title': title,
                        'content': title,
                        'url': f"https://www.cnbc.com{link.get('href')}",
                        'source': 'CNBC',
                        'category': category,
                        'mentioned_stocks': mentioned_stocks,
                        'impact': self._analyze_news_sentiment(title, title),
                        'confidence': '높음'
                    })
        except Exception as e:
            print(f"CNBC 파싱 오류: {e}")
        return articles
    def _parse_generic_site(self, soup, category):
        articles = []
        try:
            title_tags = soup.find_all(['h1', 'h2', 'h3', 'h4'])
            for tag in title_tags[:5]:
                title = tag.get_text(strip=True)
                if title and len(title) > 20:
                    mentioned_stocks = self.extract_stock_symbols_from_text(title)
                    articles.append({
                        'title': title,
                        'content': title,
                        'url': '',
                        'source': 'Web Crawl',
                        'category': category,
                        'mentioned_stocks': mentioned_stocks,
                        'impact': self._analyze_news_sentiment(title, title),
                        'confidence': '중간'
                    })
        except Exception as e:
            print(f"일반 사이트 파싱 오류: {e}")
        return articles
    def _analyze_news_sentiment(self, title, content):
        text = f"{title} {content}".lower()
        positive_keywords = ['rise', 'gain', 'up', 'positive', 'growth', 'increase', 'strong', 'bullish', 'surge', 'rally']
        negative_keywords = ['fall', 'drop', 'down', 'negative', 'decline', 'weak', 'bearish', 'crash', 'plunge']
        positive_count = sum(1 for keyword in positive_keywords if keyword in text)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text)
        if positive_count > negative_count:
            return '긍정적'
        elif negative_count > positive_count:
            return '부정적'
        else:
            return '중립적'
    def _analyze_news_confidence(self, article):
        source = article.get('source', {}).get('name', '').lower()
        high_confidence_sources = ['reuters', 'bloomberg', 'cnbc', 'marketwatch', 'yahoo finance']
        medium_confidence_sources = ['techcrunch', 'the verge', 'wired', 'forbes']
        if any(source in high_confidence_sources for source in high_confidence_sources):
            return '높음'
        elif any(source in medium_confidence_sources for source in medium_confidence_sources):
            return '중간'
        else:
            return '낮음'
    def collect_comprehensive_news(self, categories=None, max_articles_per_category=15, force_refresh=False):
        if categories is None:
            categories = ['business', 'technology', 'general', 'health', 'science']
        
        # force_refresh가 True이면 캐시를 무시하고 항상 새로운 뉴스 수집
        if not force_refresh:
            cache_key = f"comprehensive_news_{datetime.now().strftime('%Y%m%d_%H')}"
            cached_news = self.load_cache(cache_key, max_age_hours=2)
            if cached_news:
                print(f"캐시에서 종합 뉴스 로드: {len(cached_news)}개 카테고리")
                return cached_news
        
        all_news = {}
        all_mentioned_stocks = set()
        print("🔍 종합 뉴스 수집 시작...")
        
        # 병렬 처리로 뉴스 수집
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # 각 카테고리별 뉴스 수집 작업 제출
            future_to_category = {
                executor.submit(self._collect_category_news, category, max_articles_per_category): category 
                for category in categories
            }
            
            # 결과 수집
            for future in concurrent.futures.as_completed(future_to_category):
                try:
                    category, category_news = future.result()
                    all_news[category] = category_news
                    
                    # 언급된 주식 수집
                    for news in category_news:
                        all_mentioned_stocks.update(news.get('mentioned_stocks', []))
                        
                except Exception as e:
                    category = future_to_category[future]
                    print(f"❌ {category} 카테고리 뉴스 수집 실패: {e}")
                    all_news[category] = []
        
        result = {
            'news_by_category': all_news,
            'mentioned_stocks': list(all_mentioned_stocks),
            'total_articles': sum(len(news) for news in all_news.values()),
            'collection_time': datetime.now().isoformat()
        }
        
        # 캐시 저장 (force_refresh가 True여도 저장)
        if not force_refresh:
            cache_key = f"comprehensive_news_{datetime.now().strftime('%Y%m%d_%H')}"
            self.save_cache(cache_key, result)
        
        print(f"🎯 종합 뉴스 수집 완료:")
        print(f"  총 뉴스 수: {result['total_articles']}개")
        print(f"  언급된 주식: {len(result['mentioned_stocks'])}개")
        print(f"  주식 목록: {', '.join(result['mentioned_stocks'][:20])}")
        return result
    def extract_keywords_from_news(self, news_data):
        """뉴스에서 주요 키워드 추출 - 더 정교한 분석"""
        all_text = ""
        category_keywords = {}
        
        # 카테고리별로 키워드 추출
        for category, news_list in news_data.get('news_by_category', {}).items():
            category_text = ""
            for news in news_list:
                title = news.get('title', '')
                content = news.get('content', '')
                category_text += f" {title} {content}"
            
            # 카테고리별 키워드 추출
            category_keywords[category] = self._extract_keywords_from_text(category_text)
            all_text += category_text
        
        # 전체 키워드 추출
        all_keywords = self._extract_keywords_from_text(all_text)
        
        # 카테고리별 키워드와 전체 키워드 결합
        combined_keywords = []
        
        # 카테고리별 상위 키워드들 추가
        for category, keywords in category_keywords.items():
            combined_keywords.extend(keywords[:5])  # 카테고리당 상위 5개
        
        # 전체 키워드 추가
        combined_keywords.extend(all_keywords[:15])
        
        # 중복 제거 및 빈도순 정렬
        keyword_freq = {}
        for keyword in combined_keywords:
            keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
        
        sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
        final_keywords = [keyword for keyword, freq in sorted_keywords[:30]]  # 상위 30개
        
        print(f"🔍 키워드 분석 결과:")
        print(f"  카테고리별 키워드: {sum(len(kw) for kw in category_keywords.values())}개")
        print(f"  전체 키워드: {len(all_keywords)}개")
        print(f"  최종 키워드: {len(final_keywords)}개")
        print(f"  상위 키워드: {', '.join(final_keywords[:10])}")
        
        return final_keywords
    
    def _extract_keywords_from_text(self, text):
        """텍스트에서 키워드 추출 - 더 정교하고 의미있는 분석"""
        # 확장된 불용어 목록 - 더 정교한 필터링
        stop_words = {
            # 기본 불용어
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
            'mine', 'yours', 'his', 'hers', 'ours', 'theirs', 'what', 'which', 'who', 'whom',
            'whose', 'where', 'when', 'why', 'how', 'all', 'any', 'both', 'each', 'few',
            'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don',
            'should', 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', 'couldn',
            'didn', 'doesn', 'hadn', 'hasn', 'haven', 'isn', 'ma', 'mightn', 'mustn', 'needn',
            'shan', 'shouldn', 'wasn', 'weren', 'won', 'wouldn',
            
            # 시간 관련
            'new', 'time', 'year', 'day', 'week', 'month', 'today', 'yesterday', 'tomorrow', 
            'now', 'then', 'here', 'there', 'up', 'down', 'out', 'off', 'over', 'under', 
            'above', 'below', 'inside', 'outside', 'into', 'onto', 'upon', 'within', 'without',
            'against', 'among', 'between', 'through', 'during', 'before', 'after', 'since', 
            'until', 'while', 'when', 'where', 'why', 'how', 'what', 'which', 'who', 'whom', 
            'whose', 'that', 'this', 'these', 'those',
            
            # 뉴스 관련 일반 단어
            'said', 'says', 'according', 'report', 'reports', 'news', 'latest', 'update',
            'announced', 'announces', 'announcement', 'company', 'companies', 'business',
            'market', 'markets', 'stock', 'stocks', 'shares', 'share', 'price', 'prices',
            'trading', 'trade', 'investor', 'investors', 'investment', 'investments',
            
            # 금융 관련 일반 단어
            'earnings', 'revenue', 'profit', 'loss', 'growth', 'decline', 'increase', 'decrease',
            'quarter', 'annual', 'fiscal', 'financial', 'economic', 'economy', 'economic',
            'dollar', 'dollars', 'percent', 'percentage', 'million', 'billion', 'trillion',
            'quarterly', 'yearly', 'monthly', 'weekly', 'daily',
            
            # 기술 관련 일반 단어
            'technology', 'tech', 'digital', 'online', 'internet', 'web', 'mobile', 'app',
            'application', 'software', 'hardware', 'device', 'system', 'platform', 'service',
            'product', 'solution', 'innovation', 'development', 'research', 'study', 'analysis',
            
            # 기업 관련 일반 단어
            'corporate', 'executive', 'chief', 'officer', 'director', 'manager', 'employee',
            'customer', 'client', 'partner', 'vendor', 'supplier', 'competitor', 'rival',
            'industry', 'sector', 'field', 'area', 'domain', 'market', 'segment',
            
            # 성과 관련 일반 단어
            'performance', 'result', 'outcome', 'achievement', 'success', 'failure', 'win',
            'lose', 'gain', 'loss', 'profit', 'benefit', 'advantage', 'disadvantage',
            'positive', 'negative', 'good', 'bad', 'better', 'worse', 'best', 'worst',
            'high', 'low', 'big', 'small', 'large', 'tiny', 'major', 'minor',
            
            # 동작 관련 일반 단어
            'make', 'take', 'give', 'get', 'put', 'set', 'go', 'come', 'see', 'look',
            'find', 'show', 'tell', 'say', 'speak', 'talk', 'write', 'read', 'think',
            'know', 'understand', 'believe', 'feel', 'want', 'need', 'like', 'love',
            'hate', 'hope', 'expect', 'plan', 'decide', 'choose', 'select', 'pick',
            
            # 상태 관련 일반 단어
            'open', 'close', 'start', 'stop', 'begin', 'end', 'finish', 'complete',
            'continue', 'pause', 'wait', 'hold', 'keep', 'maintain', 'support', 'help',
            'assist', 'guide', 'lead', 'follow', 'join', 'leave', 'enter', 'exit',
            
            # 수량 관련 일반 단어
            'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
            'first', 'second', 'third', 'fourth', 'fifth', 'last', 'next', 'previous',
            'current', 'recent', 'old', 'new', 'young', 'fresh', 'modern', 'traditional',
            
            # 위치 관련 일반 단어
            'north', 'south', 'east', 'west', 'center', 'central', 'local', 'global',
            'national', 'international', 'regional', 'worldwide', 'domestic', 'foreign',
            'home', 'away', 'near', 'far', 'close', 'distant', 'remote', 'nearby',
            
            # 기타 일반 단어
            'way', 'method', 'approach', 'strategy', 'plan', 'program', 'project',
            'work', 'job', 'task', 'duty', 'responsibility', 'role', 'function',
            'part', 'piece', 'section', 'portion', 'fraction', 'half', 'quarter',
            'full', 'empty', 'full', 'complete', 'partial', 'total', 'entire'
        }
        
        # 텍스트 정리
        text_lower = text.lower()
        
        # 특수문자 제거 및 단어 분리 (더 정교한 패턴)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text_lower)
        
        # 키워드 빈도 계산 및 필터링
        word_freq = {}
        for word in words:
            if (word not in stop_words and 
                len(word) >= 3 and 
                len(word) <= 20 and  # 더 긴 단어도 허용 (기술 용어 등)
                not word.isdigit() and  # 숫자만 있는 단어 제외
                not re.match(r'^[0-9]+$', word) and  # 순수 숫자 제외
                not re.match(r'^[a-z]+[0-9]+$', word) and  # 단어+숫자 조합 제외 (예: test123)
                not re.match(r'^[0-9]+[a-z]+$', word)):  # 숫자+단어 조합 제외 (예: 123test)
                
                # 추가 필터링: 너무 일반적인 조합 제외
                if not (word in ['www', 'com', 'org', 'net', 'edu', 'gov', 'mil'] or
                       word.endswith('ing') and len(word) <= 6 or  # 너무 짧은 -ing 형태 제외
                       word.endswith('ed') and len(word) <= 5 or   # 너무 짧은 -ed 형태 제외
                       word.endswith('ly') and len(word) <= 6 or   # 너무 짧은 -ly 형태 제외
                       word.endswith('er') and len(word) <= 5 or   # 너무 짧은 -er 형태 제외
                       word.endswith('est') and len(word) <= 6):   # 너무 짧은 -est 형태 제외
                    
                    word_freq[word] = word_freq.get(word, 0) + 1
        
        # 빈도순으로 정렬하여 상위 키워드 반환 (더 많은 키워드 반환)
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [keyword for keyword, freq in sorted_keywords[:30]]  # 20개에서 30개로 증가
    
    def normalize_ticker(self, symbol):
        """티커를 대문자, 앞의 숫자/기호/공백/괄호 등 제거, 점/슬래시/하이픈 허용 형태로 정규화"""
        import re
        symbol = symbol.strip()
        # 앞에 붙는 숫자, 마침표, 별표, 공백, 괄호 등 모두 제거
        symbol = re.sub(r'^[\d\s\*\.#\-\(\)]+', '', symbol)
        # 괄호가 있으면 앞부분만
        symbol = symbol.split('(')[0].strip()
        # 대문자 변환
        symbol = symbol.upper()
        # 알파벳/숫자/점/하이픈/슬래시만 허용
        symbol = re.sub(r'[^A-Z0-9\./-]', '', symbol)
        return symbol

    def validate_stock_symbol(self, symbol):
        """주식 티커가 유효한지 확인 (info가 비어있지 않으면 유효, 점→하이픈 변환 재시도)"""
        try:
            import yfinance as yf
            clean_symbol = self.normalize_ticker(symbol)
            if not clean_symbol or len(clean_symbol) > 7:
                return False, None

            # 1차 시도: 원본
            ticker = yf.Ticker(clean_symbol)
            info = ticker.info
            if info and (info.get('longName') or info.get('shortName') or info.get('symbol')):
                return True, {
                    'symbol': clean_symbol,
                    'name': info.get('longName', info.get('shortName', clean_symbol)),
                    'sector': info.get('sector', 'Unknown'),
                    'market_cap': info.get('marketCap', 0)
                }

            # 2차 시도: 점→하이픈 변환
            if '.' in clean_symbol:
                alt_symbol = clean_symbol.replace('.', '-')
                ticker = yf.Ticker(alt_symbol)
                info = ticker.info
                if info and (info.get('longName') or info.get('shortName') or info.get('symbol')):
                    return True, {
                        'symbol': alt_symbol,
                        'name': info.get('longName', info.get('shortName', alt_symbol)),
                        'sector': info.get('sector', 'Unknown'),
                        'market_cap': info.get('marketCap', 0)
                    }
                print(f"❌ info 없음(점→하이픈): {alt_symbol}")

            print(f"❌ info 없음: {clean_symbol}")
            return False, None
        except Exception as e:
            print(f"티커 검증 오류 ({symbol}): {e}")
            return False, None

    def analyze_news_for_stocks_using_gpt(self, news_data, max_stocks=8):
        """GPT를 사용한 뉴스 기반 주식 분석 - 뉴스 요약, 영향 분석, 한줄평 포함"""
        try:
            from openai import OpenAI
            client = OpenAI()
            
            # 뉴스 요약 및 영향 분석 생성
            news_summary = self._create_detailed_news_summary_for_gpt(news_data)
            impact_analysis = self._create_impact_analysis_for_gpt(news_data)
            
            prompt = f"""
당신은 주식 분석 전문가입니다. 아래 뉴스 내용을 바탕으로 관련된 실제 거래되는 미국 주식을 추천해주세요.

{news_summary}

{impact_analysis}

위 뉴스들을 종합적으로 분석하여 다음 형식으로 주식을 추천해주세요:

AAPL: 애플의 최신 AI 기술 발표와 실적 호조로 인한 긍정적 전망
MSFT: 클라우드 서비스 성장과 AI 파트너십 확대로 인한 강세 예상
NVDA: 반도체 수요 증가와 AI 칩 시장 확대로 인한 성장 기대

추천 기준:
- 뉴스에서 직접 언급된 주식 우선
- 뉴스 영향이 긍정적인 주식 우선
- 실제 상장된 미국 주식만 추천
- 회사명이나 설명이 아닌 티커만 사용하세요
- 복합 티커는 점(.)을 사용하세요 (예: BRK.B, BF.B)
- 실제 상장되지 않은 회사명은 사용하지 마세요
- 티커 앞에 숫자나 기호를 붙이지 마세요

뉴스 내용을 구체적으로 언급하여 왜 이 주식을 추천하는지 설명해주세요.
마지막에 전체적인 시장 전망에 대한 한줄평을 추가해주세요.

한줄평 형식:
[한줄평] 전체적인 시장 전망과 투자 방향성에 대한 간단한 요약
"""
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 주식 분석 전문가입니다. 주어진 뉴스 내용을 바탕으로 관련된 실제 거래되는 미국 주식을 정확하게 추천해주세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,  # 토큰 수 증가
                temperature=0.3
            )
            result = response.choices[0].message.content
            # 결과 파싱 및 검증
            stocks = []
            one_line_assessment = ""
            lines = result.strip().split('\n')
            
            for line in lines:
                if '[한줄평]' in line:
                    one_line_assessment = line.replace('[한줄평]', '').strip()
                    continue
                    
                if ':' in line and len(line.strip()) > 5:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        raw_ticker = parts[0].strip()
                        ticker = self.normalize_ticker(raw_ticker)
                        description = parts[1].strip()
                        is_valid, stock_info = self.validate_stock_symbol(ticker)
                        if is_valid and stock_info:
                            stocks.append({
                                'symbol': stock_info['symbol'],
                                'name': stock_info['name'],
                                'sector': stock_info['sector'],
                                'market_cap': stock_info['market_cap'],
                                'description': description,
                                'source': 'GPT 뉴스 분석',
                                'confidence': '높음'
                            })
                            print(f"✅ 유효한 주식 발견: {stock_info['symbol']} - {stock_info['name']}")
                        else:
                            print(f"❌ 유효하지 않은 티커: {ticker} (원본: {raw_ticker})")
            
            print(f"🤖 GPT 뉴스 분석 결과: {len(stocks)}개 유효한 주식 발견")
            for stock in stocks:
                print(f"  - {stock['symbol']} ({stock['name']}): {stock['description']}")
            
            if one_line_assessment:
                print(f"📝 한줄평: {one_line_assessment}")
            
            return stocks[:max_stocks]
        except Exception as e:
            print(f"GPT 뉴스 분석 오류: {e}")
            return []
    
    def _create_detailed_news_summary_for_gpt(self, news_data):
        """GPT 분석을 위한 상세 뉴스 요약 생성"""
        summary = "📰 주요 뉴스 내용 및 분석:\n\n"
        
        for category, news_list in news_data.get('news_by_category', {}).items():
            if news_list:
                summary += f"[{category.upper()} 카테고리] - {len(news_list)}개 뉴스\n"
                for i, news in enumerate(news_list[:5], 1):  # 카테고리당 상위 5개
                    title = news.get('title', '')
                    content = news.get('content', '')
                    source = news.get('source', 'Unknown')
                    impact = news.get('impact', '중립적')
                    mentioned_stocks = news.get('mentioned_stocks', [])
                    
                    summary += f"{i}. {title} ({impact}, {source})\n"
                    if content and len(content) > 50:
                        summary += f"   내용: {content[:200]}...\n"
                    if mentioned_stocks:
                        summary += f"   언급된 주식: {', '.join(mentioned_stocks[:5])}\n"
                    summary += "\n"
        
        return summary
    
    def _create_impact_analysis_for_gpt(self, news_data):
        """GPT 분석을 위한 영향도 분석 생성"""
        analysis = "📊 뉴스 영향도 분석:\n\n"
        
        # 전체 뉴스 통계
        total_news = sum(len(news) for news in news_data.get('news_by_category', {}).values())
        all_mentioned_stocks = news_data.get('mentioned_stocks', [])
        
        # 카테고리별 영향 분석
        category_impacts = {}
        for category, news_list in news_data.get('news_by_category', {}).items():
            if news_list:
                positive_count = sum(1 for news in news_list if news.get('impact') == '긍정적')
                negative_count = sum(1 for news in news_list if news.get('impact') == '부정적')
                neutral_count = len(news_list) - positive_count - negative_count
                
                category_impacts[category] = {
                    'total': len(news_list),
                    'positive': positive_count,
                    'negative': negative_count,
                    'neutral': neutral_count
                }
        
        analysis += f"총 뉴스 수: {total_news}개\n"
        analysis += f"언급된 주식: {len(all_mentioned_stocks)}개\n\n"
        
        analysis += "카테고리별 영향도:\n"
        for category, impacts in category_impacts.items():
            analysis += f"- {category}: 긍정적 {impacts['positive']}개, 부정적 {impacts['negative']}개, 중립적 {impacts['neutral']}개\n"
        
        analysis += "\n주요 투자 테마:\n"
        # 키워드 분석 결과 추가
        keywords = self.extract_keywords_from_news(news_data)
        analysis += f"- 핵심 키워드: {', '.join(keywords[:10])}\n"
        
        return analysis
    def get_stocks_from_news_analysis(self, force_refresh=False):
        """뉴스 분석에서 우선순위 주식 추출 - 키워드 분석 포함"""
        print("🔍 뉴스 분석에서 우선순위 주식 추출 중...")
        
        # force_refresh가 True이면 캐시를 무시
        if not force_refresh:
            cache_key = "news_priority_stocks_enhanced"
            cached_stocks = self.load_cache(cache_key, max_age_hours=4)
            if cached_stocks:
                print(f"캐시에서 우선순위 주식 로드: {len(cached_stocks)}개")
                return cached_stocks
        
        # 뉴스 수집 (force_refresh 적용)
        news_data = self.collect_comprehensive_news(force_refresh=force_refresh)
        mentioned_stocks = news_data.get('mentioned_stocks', [])
        
        priority_stocks = []
        
        # 1. 직접 언급된 주식들
        if mentioned_stocks:
            stock_frequency = {}
            for stock in mentioned_stocks:
                stock_frequency[stock] = stock_frequency.get(stock, 0) + 1
            sorted_stocks = sorted(stock_frequency.items(), key=lambda x: x[1], reverse=True)
            priority_stocks = [stock for stock, freq in sorted_stocks[:20]]
            print(f"📊 직접 언급된 주식: {len(priority_stocks)}개")
        
        # 2. 키워드 분석을 통한 관련 주식 찾기 (항상 실행)
        print("🔍 키워드 분석을 통한 관련 주식 탐색 중...")
        keywords = self.extract_keywords_from_news(news_data)
        print(f"📝 추출된 키워드: {', '.join(keywords[:15])}")
        
        keyword_stocks = self.analyze_news_for_stocks_using_gpt(news_data, max_stocks=8)
        if keyword_stocks:
            keyword_symbols = [stock['symbol'] for stock in keyword_stocks]
            # 중복 제거하면서 키워드 주식들을 우선순위에 추가
            for symbol in keyword_symbols:
                if symbol not in priority_stocks:
                    priority_stocks.append(symbol)
            print(f"🤖 GPT 키워드 분석 주식: {len(keyword_stocks)}개 추가")
        
        # 최소 4개 보장
        if len(priority_stocks) < 4:
            # 기본 주식들 추가
            default_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META']
            for stock in default_stocks:
                if stock not in priority_stocks:
                    priority_stocks.append(stock)
            print(f"📋 기본 주식 {len(default_stocks)}개 추가")
        
        result = {
            'priority_stocks': priority_stocks[:30],
            'keyword_stocks': keyword_stocks,
            'total_found': len(priority_stocks),
            'keywords_used': keywords[:15]  # 사용된 키워드 정보 추가
        }
        
        # 캐시 저장 (force_refresh가 True여도 저장)
        if not force_refresh:
            cache_key = "news_priority_stocks_enhanced"
            self.save_cache(cache_key, result)
        
        print(f"🎯 뉴스 기반 우선순위 주식 추출 완료:")
        print(f"  총 발견 주식: {len(mentioned_stocks)}개")
        print(f"  우선순위 주식: {len(priority_stocks)}개")
        print(f"  키워드 분석 주식: {len(keyword_stocks)}개")
        print(f"  상위 10개: {', '.join(priority_stocks[:10])}")
        
        return result
    def get_detailed_stock_news(self, symbol, max_news=15):
        """주식별 상세 뉴스 수집 - 최소 15개, 뉴스 요약 및 영향 분석 포함"""
        print(f"📰 {symbol} 상세 뉴스 수집 중... (목표: {max_news}개)")
        cache_key = f"detailed_news_{symbol}_{datetime.now().strftime('%Y%m%d_%H')}"
        cached_news = self.load_cache(cache_key, max_age_hours=2)
        if cached_news:
            print(f"캐시에서 {symbol} 뉴스 로드: {len(cached_news)}개")
            return cached_news
        
        all_news = []
        
        # 1단계: 주식별 직접 뉴스 수집
        stock_news = self.get_news_api_articles('business', query=symbol, max_articles=max_news//2)
        all_news.extend(stock_news)
        print(f"  📡 주식별 뉴스: {len(stock_news)}개 수집")
        
        # 2단계: 섹터별 뉴스 수집
        try:
            stock_info = yf.Ticker(symbol).info
            sector = stock_info.get('sector', 'Technology')
            sector_queries = {
                'Technology': ['technology stocks', 'tech sector', 'software stocks'],
                'Healthcare': ['healthcare stocks', 'pharmaceutical', 'biotech stocks'],
                'Financial Services': ['financial stocks', 'banking sector', 'finance stocks'],
                'Consumer Cyclical': ['consumer stocks', 'retail stocks', 'consumer goods'],
                'Energy': ['energy stocks', 'oil stocks', 'renewable energy'],
                'Industrials': ['industrial stocks', 'manufacturing stocks', 'aerospace'],
                'Consumer Defensive': ['consumer defensive', 'food stocks', 'beverage stocks'],
                'Real Estate': ['real estate stocks', 'reit stocks', 'property stocks'],
                'Utilities': ['utility stocks', 'electric stocks', 'gas stocks'],
                'Basic Materials': ['materials stocks', 'mining stocks', 'chemical stocks'],
                'Communication Services': ['communication stocks', 'media stocks', 'telecom stocks']
            }
            sector_query = sector_queries.get(sector, f'{sector} stocks')
            
            # 섹터별 뉴스 수집 (여러 쿼리 사용)
            sector_news = []
            for query in sector_query[:2]:  # 상위 2개 쿼리 사용
                if len(all_news) >= max_news:
                    break
                sector_articles = self.get_news_api_articles('business', query=query, max_articles=max_news//4)
                sector_news.extend(sector_articles)
            all_news.extend(sector_news)
            print(f"  🏭 섹터별 뉴스: {len(sector_news)}개 수집 ({sector})")
        except Exception as e:
            print(f"  ⚠️ 섹터 뉴스 수집 오류: {e}")
        
        # 3단계: 시장 전체 뉴스 수집
        if len(all_news) < max_news:
            market_queries = ['stock market', 'market news', 'trading news']
            market_news = []
            for query in market_queries:
                if len(all_news) >= max_news:
                    break
                market_articles = self.get_news_api_articles('business', query=query, max_articles=max_news//6)
                market_news.extend(market_articles)
            all_news.extend(market_news)
            print(f"  📊 시장 뉴스: {len(market_news)}개 수집")
        
        # 4단계: 중복 제거 및 뉴스 요약/영향 분석 추가
        unique_news = []
        seen_titles = set()
        for news in all_news:
            title_key = news['title'][:50].lower()
            if title_key not in seen_titles:
                # 뉴스 요약 및 영향 분석 추가
                news['summary'] = self._create_news_summary(news)
                news['impact_analysis'] = self._analyze_news_impact(news, symbol)
                unique_news.append(news)
                seen_titles.add(title_key)
        
        # 최종 결과: 최소 15개 목표이지만, 가능한 모든 뉴스를 수집
        final_news = unique_news[:max_news] if len(unique_news) > max_news else unique_news
        
        # 뉴스 요약 및 영향 분석 결과 저장
        result = {
            'news': final_news,
            'total_news': len(final_news),
            'symbol': symbol,
            'collection_time': datetime.now().isoformat(),
            'news_summary': self._create_overall_news_summary(final_news, symbol),
            'impact_summary': self._create_impact_summary(final_news, symbol)
        }
        
        self.save_cache(cache_key, result)
        print(f"✅ {symbol} 뉴스 수집 완료: {len(final_news)}개 (목표: {max_news}개)")
        if len(final_news) < max_news:
            print(f"  ⚠️ 목표보다 {max_news - len(final_news)}개 적게 수집됨 (가능한 모든 최신 뉴스 수집)")
        
        return result
    
    def _create_news_summary(self, news_item):
        """개별 뉴스 요약 생성"""
        title = news_item.get('title', '')
        content = news_item.get('content', '')
        
        # 제목과 내용을 결합하여 요약
        full_text = f"{title} {content}"
        
        # 핵심 내용 추출 (첫 200자)
        summary = full_text[:200].strip()
        if len(full_text) > 200:
            summary += "..."
        
        return summary
    
    def _analyze_news_impact(self, news_item, symbol):
        """뉴스가 특정 주식에 미치는 영향 분석"""
        title = news_item.get('title', '').lower()
        content = news_item.get('content', '').lower()
        full_text = f"{title} {content}"
        
        # 긍정적 키워드 (확장)
        positive_keywords = [
            'surge', 'jump', 'rise', 'gain', 'increase', 'growth', 'profit', 'earnings beat',
            'positive', 'strong', 'excellent', 'outperform', 'upgrade', 'buy', 'bullish',
            'innovation', 'breakthrough', 'success', 'win', 'deal', 'partnership', 'expansion',
            'higher', 'better', 'improve', 'boost', 'rally', 'climb', 'soar', 'leap',
            'outperform', 'beat', 'exceed', 'outpace', 'advance', 'progress', 'develop',
            'launch', 'release', 'announce', 'introduce', 'expand', 'grow', 'increase',
            'positive outlook', 'strong performance', 'record high', 'new high',
            'dividend increase', 'stock buyback', 'merger', 'acquisition', 'partnership'
        ]
        
        # 부정적 키워드 (확장)
        negative_keywords = [
            'fall', 'drop', 'decline', 'loss', 'decrease', 'weak', 'negative', 'downgrade',
            'sell', 'bearish', 'problem', 'issue', 'concern', 'risk', 'warning', 'miss',
            'disappoint', 'fail', 'bankruptcy', 'layoff', 'cut', 'reduce', 'lower',
            'worse', 'poor', 'bad', 'weak', 'soft', 'slow', 'delay', 'cancel', 'suspend',
            'investigation', 'lawsuit', 'fine', 'penalty', 'recall', 'defect', 'error',
            'negative outlook', 'weak performance', 'record low', 'new low',
            'dividend cut', 'stock dilution', 'restructuring', 'downsizing', 'closure'
        ]
        
        # 심볼 언급 확인
        symbol_mentioned = symbol.lower() in full_text
        
        # 영향도 계산
        positive_count = sum(1 for keyword in positive_keywords if keyword in full_text)
        negative_count = sum(1 for keyword in negative_keywords if keyword in full_text)
        
        # 추가 긍정/부정 신호 분석
        if any(word in full_text for word in ['beat', 'exceed', 'outperform', 'strong']):
            positive_count += 2
        if any(word in full_text for word in ['miss', 'disappoint', 'weak', 'poor']):
            negative_count += 2
        
        # 영향 판단 (더 정교한 로직)
        if positive_count > negative_count:
            impact = '긍정적'
            confidence = '높음' if positive_count > negative_count + 3 else '중간'
        elif negative_count > positive_count:
            impact = '부정적'
            confidence = '높음' if negative_count > positive_count + 3 else '중간'
        else:
            impact = '중립적'
            confidence = '중간'
        
        return {
            'impact': impact,
            'confidence': confidence,
            'symbol_mentioned': symbol_mentioned,
            'positive_keywords': positive_count,
            'negative_keywords': negative_count,
            'relevance': '높음' if symbol_mentioned else '중간'
        }
    
    def _create_overall_news_summary(self, news_list, symbol):
        """전체 뉴스 요약 생성"""
        if not news_list:
            return f"{symbol}에 대한 최근 뉴스가 없습니다."
        
        # 카테고리별 뉴스 분류
        categories = {}
        for news in news_list:
            category = news.get('category', 'general')
            if category not in categories:
                categories[category] = []
            categories[category].append(news)
        
        summary = f"{symbol} 최근 뉴스 요약:\n\n"
        
        for category, news_items in categories.items():
            summary += f"[{category.upper()} 카테고리] - {len(news_items)}개 뉴스\n"
            for i, news in enumerate(news_items[:3], 1):  # 카테고리당 상위 3개
                title = news.get('title', '')
                impact = news.get('impact_analysis', {}).get('impact', '중립적')
                summary += f"  {i}. {title[:60]}... ({impact})\n"
            summary += "\n"
        
        return summary
    
    def _create_impact_summary(self, news_list, symbol):
        """뉴스 영향 종합 분석"""
        if not news_list:
            return f"{symbol}에 대한 뉴스 영향 분석이 불가능합니다."
        
        # 영향도 통계
        impact_stats = {'긍정적': 0, '부정적': 0, '중립적': 0}
        confidence_stats = {'높음': 0, '중간': 0, '낮음': 0}
        symbol_mentions = 0
        
        for news in news_list:
            impact_analysis = news.get('impact_analysis', {})
            impact = impact_analysis.get('impact', '중립적')
            confidence = impact_analysis.get('confidence', '중간')
            symbol_mentioned = impact_analysis.get('symbol_mentioned', False)
            
            impact_stats[impact] += 1
            confidence_stats[confidence] += 1
            if symbol_mentioned:
                symbol_mentions += 1
        
        # 주요 영향 요약
        dominant_impact = max(impact_stats.items(), key=lambda x: x[1])
        
        summary = f"{symbol} 뉴스 영향 분석:\n\n"
        summary += f"📊 영향도 분포:\n"
        summary += f"  - 긍정적: {impact_stats['긍정적']}개\n"
        summary += f"  - 부정적: {impact_stats['부정적']}개\n"
        summary += f"  - 중립적: {impact_stats['중립적']}개\n\n"
        summary += f"🎯 주요 영향: {dominant_impact[0]} ({dominant_impact[1]}개 뉴스)\n"
        summary += f"📈 직접 언급: {symbol_mentions}개 뉴스\n"
        summary += f"🔍 신뢰도 높음: {confidence_stats['높음']}개 뉴스\n\n"
        
        # 투자 관점 분석
        if dominant_impact[0] == '긍정적' and dominant_impact[1] > len(news_list) * 0.4:
            summary += "💡 투자 관점: 뉴스 전반적으로 긍정적, 단기 상승 가능성 있음"
        elif dominant_impact[0] == '부정적' and dominant_impact[1] > len(news_list) * 0.4:
            summary += "⚠️ 투자 관점: 뉴스 전반적으로 부정적, 단기 하락 가능성 있음"
        else:
            summary += "📊 투자 관점: 뉴스 영향 혼재, 중립적 관찰 필요"
        
        return summary
    def _collect_category_news(self, category, max_articles):
        """단일 카테고리 뉴스 수집 (병렬 처리용) - 최소 15개 보장"""
        print(f"📰 {category} 카테고리 뉴스 수집 중... (목표: {max_articles}개)")
        category_news = []
        # 1단계: NEWS API에서 뉴스 수집 (최대한 많이)
        api_news = self.get_news_api_articles(category, max_articles=max_articles)
        category_news.extend(api_news)
        print(f"  📡 NEWS API: {len(api_news)}개 수집")
        # 2단계: API 부족 시 웹 크롤링으로 보완
        if len(category_news) < max_articles:
            needed_articles = max_articles - len(category_news)
            print(f"  🌐 크롤링으로 {needed_articles}개 추가 수집 시도...")
            crawled_news = self.crawl_finance_websites(category, max_articles=needed_articles)
            category_news.extend(crawled_news)
            print(f"  🌐 크롤링: {len(crawled_news)}개 추가 수집")
        # 2.5단계: 여전히 부족하면 Currents API 시도
        if len(category_news) < max_articles:
            needed_articles = max_articles - len(category_news)
            print(f"  🌊 Currents API로 {needed_articles}개 추가 수집 시도...")
            try:
                currents_news = self._try_currents_api(category, None, needed_articles)
                category_news.extend(currents_news)
                print(f"  🌊 Currents API: {len(currents_news)}개 추가 수집")
            except Exception as e:
                print(f"  Currents API 오류: {e}")
        # 3단계: 여전히 부족하면 추가 소스에서 수집
        if len(category_news) < max_articles:
            remaining_needed = max_articles - len(category_news)
            print(f"  🔍 추가 소스에서 {remaining_needed}개 더 수집 시도...")
            additional_queries = {
                'business': ['earnings report', 'stock market news', 'financial news'],
                'technology': ['AI news', 'tech innovation', 'software stocks'],
                'general': ['economic news', 'market trends', 'investment news'],
                'health': ['biotech news', 'pharmaceutical', 'healthcare innovation'],
                'science': ['research news', 'scientific breakthrough', 'innovation']
            }
            queries = additional_queries.get(category, ['stock market'])
            for query in queries[:2]:
                if len(category_news) >= max_articles:
                    break
                additional_news = self.get_news_api_articles('business', query=query, max_articles=remaining_needed//2)
                category_news.extend(additional_news)
                print(f"  📡 추가 쿼리 '{query}': {len(additional_news)}개 수집")
        # 중복 제거
        unique_news = []
        seen_titles = set()
        for news in category_news:
            title_key = news['title'][:50].lower()
            if title_key not in seen_titles:
                unique_news.append(news)
                seen_titles.add(title_key)
        # 최종 결과: 최소 15개 목표이지만, 가능한 모든 뉴스를 수집
        final_news = unique_news[:max_articles] if len(unique_news) > max_articles else unique_news
        print(f"  ✅ {category}: {len(final_news)}개 뉴스 수집 완료 (목표: {max_articles}개)")
        if len(final_news) < max_articles:
            print(f"  ⚠️ {category}: 목표보다 {max_articles - len(final_news)}개 적게 수집됨 (가능한 모든 최신 뉴스 수집)")
        return category, final_news
    def _try_currents_api(self, category, query=None, max_articles=10):
        """Currents API를 통한 뉴스 수집 (에러 발생 시 빈 리스트 반환)"""
        api_key = os.getenv('CURRENTS_API_KEY')
        if not api_key:
            print("CURRENTS API 키가 설정되지 않았습니다.")
            return []
        try:
            url = "https://api.currentsapi.services/v1/search"
            # 카테고리별 기본 쿼리
            category_queries = {
                'business': 'stock market OR earnings OR financial OR investment',
                'technology': 'artificial intelligence OR tech stocks OR semiconductor OR software',
                'general': 'economy OR federal reserve OR inflation OR GDP',
                'health': 'healthcare stocks OR pharmaceutical OR biotech',
                'science': 'technology innovation OR research OR development'
            }
            search_query = query if query else category_queries.get(category, 'stock market')
            params = {
                'apiKey': api_key,
                'language': 'en',
                'keywords': search_query,
                'limit': max_articles
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                news_list = data.get('news', [])
                processed = []
                for article in news_list:
                    title = article.get('title', '')
                    description = article.get('description', '')
                    content = article.get('description', '')
                    url_ = article.get('url', '')
                    source = article.get('source', 'Currents API')
                    published = article.get('published', '')
                    full_text = f"{title} {description} {content}"
                    mentioned_stocks = self.extract_stock_symbols_from_text(full_text)
                    processed.append({
                        'title': title,
                        'content': description or content or title,
                        'url': url_,
                        'source': source,
                        'published_at': published,
                        'category': category,
                        'mentioned_stocks': mentioned_stocks,
                        'impact': self._analyze_news_sentiment(title, description),
                        'confidence': '중간'
                    })
                return processed
            else:
                print(f"CURRENTS API 오류: {response.status_code}")
                return []
        except Exception as e:
            print(f"CURRENTS API 요청 오류: {e}")
            return []
    def analyze_articles_with_gpt(self, articles):
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        results = []
        for article in articles:
            prompt = f"""
            기사 제목: {article['title']}
            기사 내용: {article['content']}
            위 기사에서 언급된 미국 상장 주식 중, 너무 대중적인 빅테크/초대형주(예: AAPL, MSFT, GOOGL, AMZN, META, TSLA, NVDA 등)는 제외하고, 향후 성장성이 높거나 혁신적인 중소형주, 신성장주, 틈새시장 강자 위주로 추천해줘.
            각 주식의 투자 매력/전망/리스크를 2~3문장으로 요약하고, 실제 티커와 함께 아래 형식으로 써줘.
            예시:
            PLTR: 팔란티어는 AI/빅데이터 수요 증가로 성장 기대. 최근 대형 계약 수주.
            CELH: 셀시우스는 에너지음료 시장에서 빠른 성장세. 실적 개선 지속.
            """
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "당신은 미국 주식 분석 전문가입니다. 기사 내용을 바탕으로 실제 상장 주식만 추천하고, 그 이유를 명확히 써주세요."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.3
                )
                content = response.choices[0].message.content
                # 결과 파싱 (티커: 설명)
                for line in content.strip().split('\n'):
                    if ':' in line:
                        ticker, reason = line.split(':', 1)
                        ticker = self.normalize_ticker(ticker.strip())
                        is_valid, stock_info = self.validate_stock_symbol(ticker)
                        if is_valid:
                            results.append({
                                "symbol": ticker,
                                "reason": reason.strip(),
                                "article_title": article['title'],
                                "article_url": article['url']
                            })
            except Exception as e:
                print(f"GPT 기사 분석 오류: {e}")
        return results
    # 4. get_recommendations_from_news 함수 추가
    def get_recommendations_from_news(self, categories=None, min_articles=5, max_articles=10):
        news_data = self.collect_comprehensive_news(categories, max_articles_per_category=max_articles, force_refresh=True)
        all_articles = []
        for news_list in news_data['news_by_category'].values():
            all_articles.extend(news_list[:max_articles])
        gpt_results = self.analyze_articles_with_gpt(all_articles)
        recommendations = {}
        for res in gpt_results:
            symbol = res['symbol']
            if symbol in self.BIG_TECH_SYMBOLS:
                continue  # 빅테크/초대형주 제외
            if symbol not in recommendations:
                recommendations[symbol] = []
            recommendations[symbol].append({
                "reason": res['reason'],
                "article_title": res['article_title'],
                "article_url": res['article_url']
            })
        return recommendations
    # --- 뉴스 기사 심화 분석 및 종목 추출 ---
    def extract_15_stocks_from_news(self, articles):
        """
        기사 전체를 GPT-4o로 심화 분석하여 기사 이슈와 직접적으로 관련 있는 미국 상장 주식 15개를 추출
        각 종목별로 어떤 이슈와 연결되는지 간단히 설명도 포함
        """
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        all_text = ""
        for art in articles:
            all_text += f"제목: {art['title']}\n내용: {art['content']}\n\n"
        prompt = f'''
아래는 최근 미국 증시 관련 뉴스 기사들입니다.

{all_text}

이 기사들에서 언급된 이슈와 직접적으로 관련 있는 미국 상장 주식 15개를 뽑아줘.
각 종목별로 어떤 이슈와 연결되는지 간단히 써줘. (예: PLTR: 정부 데이터 계약, AI 수요 증가 등)
형식:
AAPL: AI 성장 이슈, 실적 호조 등
PLTR: 정부 데이터 계약, AI 수요 증가 등
'''
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 미국 주식 분석 전문가입니다. 기사 전체를 심화 분석하여, 기사 이슈와 직접적으로 연결되는 미국 상장 주식만 뽑아주세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            content = response.choices[0].message.content
            results = []
            for line in content.strip().split('\n'):
                if ':' in line:
                    ticker, reason = line.split(':', 1)
                    ticker = self.normalize_ticker(ticker.strip())
                    is_valid, stock_info = self.validate_stock_symbol(ticker)
                    if is_valid:
                        results.append({
                            "symbol": ticker,
                            "reason": reason.strip(),
                            "related_issues": reason.strip()
                        })
                if len(results) >= 15:
                    break
            return results
        except Exception as e:
            print(f"GPT 15종목 추출 오류: {e}")
            return []

    def fetch_yahoo_finance_data(self, symbols):
        """
        YFinancePatch 기반으로 429 우회, 캐시 활용, 지연/재시도 강화. info는 patch에서, history(차트)는 yfinance로만.
        """
        import yfinance as yf
        import time, random
        from yfinance_patch import YFinancePatch
        patch = YFinancePatch()
        results = {}
        for symbol in symbols:
            # info: patch에서 가져옴(429 우회, 캐시 활용)
            info = None
            for attempt in range(5):
                try:
                    info = patch.get_stock_info(symbol)
                    if info:
                        break
                except Exception as e:
                    if "429" in str(e) or "Too Many Requests" in str(e):
                        wait = 60 + attempt * 30
                        print(f"429 오류({symbol}), {wait}초 대기 후 재시도...")
                        time.sleep(wait)
                    else:
                        print(f"YFinancePatch info 오류({symbol}): {e}")
                        break
            # history(차트): yfinance로만(차트는 429 영향 적음)
            hist = None
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2mo")
            except Exception as e:
                print(f"yfinance 차트 오류({symbol}): {e}")
            results[symbol] = {
                "info": info,
                "history": hist
            }
            # 각 요청마다 4~5초 랜덤 지연
            time.sleep(random.uniform(4.0, 5.0))
        return results

    def select_top2_stocks(self, candidates, finance_data, articles):
        """
        15개 후보, 실데이터, 기사 이슈를 GPT-4o에 종합 평가시켜 최종 2개 종목과 추천 사유, 관련 뉴스까지 뽑음
        """
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        # 후보별 요약
        candidate_text = ""
        for c in candidates:
            symbol = c['symbol']
            info = finance_data.get(symbol, {}).get('info', {})
            sector = info.get('sector', 'Unknown')
            pe = info.get('trailingPE', 'N/A')
            market_cap = info.get('marketCap', 'N/A')
            candidate_text += f"{symbol}: {c['reason']} (섹터: {sector}, PER: {pe}, 시가총액: {market_cap})\n"
        # 기사 이슈 요약
        news_issues = ""
        for art in articles[:5]:
            news_issues += f"- {art['title']}: {art['content'][:100]}...\n"
        prompt = f'''
아래는 최근 미국 증시 뉴스 기사에서 뽑은 이슈와 관련 주식 15개, 그리고 각 주식의 주요 데이터입니다.

{candidate_text}

주요 뉴스 이슈:
{news_issues}

이 15개 후보 중에서 뉴스 이슈와 데이터가 가장 긍정적으로 연결되는 2개를 뽑고, 각 종목별로 왜 추천하는지 심화 설명을 써줘. 그리고 각 종목별로 기사와 직접적으로 연결되는 이슈(기사 제목, 요약, 링크 2~3개)를 골라줘.
형식:
[
  {
    "symbol": "PLTR",
    "final_reason": "...",
    "related_news": [
      {"title": "...", "summary": "...", "url": "..."},
      ...
    ]
  },
  ...
]
'''
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 미국 주식 분석 전문가입니다. 기사, 데이터, 이슈를 종합적으로 심화 분석하여 최적의 2개 종목을 뽑고, 이유와 관련 뉴스까지 명확히 써주세요. JSON 형식으로 답변하세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            import json
            content = response.choices[0].message.content
            # JSON 파싱 시도
            try:
                # GPT가 코드블록으로 감싸는 경우 제거
                if content.strip().startswith('```'):
                    content = content.strip().split('```')[1]
                result = json.loads(content)
                return result
            except Exception as e:
                print(f"GPT JSON 파싱 오류: {e}\n{content}")
                return []
        except Exception as e:
            print(f"GPT 최종 2종목 선정 오류: {e}")
            return []