import json
import os
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Tuple
import pickle

class PortfolioManager:
    def __init__(self, data_dir: str = "portfolio_data"):
        self.data_dir = data_dir
        self.ensure_data_directory()
        self.portfolio_file = os.path.join(data_dir, "portfolio.json")
        self.history_file = os.path.join(data_dir, "recommendation_history.json")
        self.performance_file = os.path.join(data_dir, "performance_tracker.json")
        
    def ensure_data_directory(self):
        """데이터 디렉토리가 존재하는지 확인하고 없으면 생성"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def save_portfolio(self, portfolio_data: Dict):
        """현재 포트폴리오를 저장"""
        portfolio_data['last_updated'] = datetime.now().isoformat()
        with open(self.portfolio_file, 'w', encoding='utf-8') as f:
            json.dump(portfolio_data, f, ensure_ascii=False, indent=2)
    
    def load_portfolio(self) -> Dict:
        """저장된 포트폴리오를 로드"""
        if os.path.exists(self.portfolio_file):
            with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'current_stocks': [],
            'total_investment': 0,
            'last_updated': None,
            'portfolio_value': 0,
            'total_return': 0,
            'daily_returns': []
        }
    
    def save_recommendation_history(self, recommendations: List[Dict]):
        """추천 히스토리를 저장 (JSON 안전 처리)"""
        try:
            # 기존 히스토리 로드
            history = self.load_recommendation_history()
            
            # 새 추천 추가 (pandas DataFrame을 dict로 변환)
            safe_recommendations = []
            for rec in recommendations:
                safe_rec = {}
                for key, value in rec.items():
                    if hasattr(value, 'to_dict'):  # pandas DataFrame
                        safe_rec[key] = value.to_dict()
                    elif hasattr(value, 'isoformat'):  # datetime
                        safe_rec[key] = value.isoformat()
                    elif hasattr(value, 'strftime'):  # Timestamp
                        safe_rec[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, dict):
                        # 중첩된 dict도 안전하게 처리
                        safe_dict = {}
                        for k, v in value.items():
                            if hasattr(v, 'to_dict'):
                                safe_dict[k] = v.to_dict()
                            elif hasattr(v, 'isoformat'):
                                safe_dict[k] = v.isoformat()
                            elif hasattr(v, 'strftime'):  # Timestamp
                                safe_dict[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                safe_dict[k] = v
                        safe_rec[key] = safe_dict
                    else:
                        safe_rec[key] = value
                safe_recommendations.append(safe_rec)
            
            history.append({
                'date': datetime.now().isoformat(),
                'recommendations': safe_recommendations
            })
            
            # 최대 30일간의 히스토리만 유지
            if len(history) > 30:
                history = history[-30:]
            
            # 임시 파일에 먼저 저장
            temp_file = f"{self.history_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            # 성공적으로 저장되면 원본 파일로 이동
            if os.path.exists(temp_file):
                if os.path.exists(self.history_file):
                    os.remove(self.history_file)
                os.rename(temp_file, self.history_file)
                
        except Exception as e:
            print(f"히스토리 저장 오류: {e}")
            # 임시 파일 정리
            temp_file = f"{self.history_file}.tmp"
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def load_recommendation_history(self) -> List[Dict]:
        """추천 히스토리를 로드 (강화된 오류 처리)"""
        if not os.path.exists(self.history_file):
            return []
        
        try:
            # 파일 크기 체크
            if os.path.getsize(self.history_file) == 0:
                print("빈 히스토리 파일 감지, 새로 시작합니다.")
                return []
            
            with open(self.history_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
                # 빈 파일 체크
                if not content:
                    return []
                
                # JSON 파싱 시도
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        return data
                    else:
                        print("잘못된 데이터 형식, 새로 시작합니다.")
                        return []
                except json.JSONDecodeError as e:
                    print(f"JSON 파싱 오류: {e}")
                    # 손상된 파일 백업
                    self._backup_corrupted_file(self.history_file)
                    return []
                    
        except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
            print(f"히스토리 파일 읽기 오류: {e}")
            return []
        except Exception as e:
            print(f"예상치 못한 오류: {e}")
            self._backup_corrupted_file(self.history_file)
            return []
    
    def _backup_corrupted_file(self, file_path: str):
        """손상된 파일을 백업하고 삭제"""
        try:
            if os.path.exists(file_path):
                backup_file = f"{file_path}.corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(file_path, backup_file)
                print(f"손상된 파일을 {backup_file}로 백업했습니다.")
        except Exception as e:
            print(f"파일 백업 실패: {e}")
            try:
                os.remove(file_path)
                print("손상된 파일을 삭제했습니다.")
            except:
                pass
    
    def get_current_stock_prices(self, symbols: List[str]) -> Dict[str, float]:
        """현재 주식 가격을 가져옴"""
        current_prices = {}
        for symbol in symbols:
            try:
                stock = yf.Ticker(symbol)
                current_price = stock.info.get('currentPrice', 0)
                if current_price == 0:
                    current_price = stock.info.get('regularMarketPrice', 0)
                current_prices[symbol] = current_price
            except Exception as e:
                print(f"가격 조회 오류 ({symbol}): {e}")
                current_prices[symbol] = 0
        return current_prices
    
    def calculate_portfolio_performance(self, portfolio: Dict) -> Dict:
        """포트폴리오 성과 계산"""
        if not portfolio['current_stocks']:
            return portfolio
        
        current_prices = self.get_current_stock_prices([stock['symbol'] for stock in portfolio['current_stocks']])
        
        total_value = 0
        total_cost = 0
        stock_performances = []
        
        for stock in portfolio['current_stocks']:
            symbol = stock['symbol']
            current_price = current_prices.get(symbol, 0)
            purchase_price = stock['purchase_price']
            quantity = stock['quantity']
            
            if current_price > 0:
                current_value = current_price * quantity
                cost = purchase_price * quantity
                return_pct = ((current_price - purchase_price) / purchase_price) * 100
                
                total_value += current_value
                total_cost += cost
                
                stock_performances.append({
                    'symbol': symbol,
                    'name': stock['name'],
                    'purchase_price': purchase_price,
                    'current_price': current_price,
                    'quantity': quantity,
                    'current_value': current_value,
                    'cost': cost,
                    'return_pct': return_pct,
                    'return_amount': current_value - cost
                })
        
        total_return_pct = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
        
        return {
            **portfolio,
            'current_stocks': stock_performances,
            'portfolio_value': total_value,
            'total_cost': total_cost,
            'total_return': total_value - total_cost,
            'total_return_pct': total_return_pct,
            'last_updated': datetime.now().isoformat()
        }
    
    def should_rebalance_portfolio(self, current_recommendations: List[Dict], portfolio: Dict, 
                                 min_return_threshold: float = 2.0) -> Tuple[bool, List[Dict], List[Dict]]:
        """포트폴리오 리밸런싱 필요성 판단"""
        if not portfolio['current_stocks']:
            return True, [], current_recommendations[:2]
        
        # 현재 포트폴리오 성과 계산
        updated_portfolio = self.calculate_portfolio_performance(portfolio)
        
        # 현재 보유 주식들의 수익률
        current_returns = {}
        for stock in updated_portfolio['current_stocks']:
            current_returns[stock['symbol']] = stock['return_pct']
        
        # 새로운 추천 주식들의 예상 수익률 (GPT 분석에서 추출)
        new_recommendations = []
        for rec in current_recommendations[:2]:
            # GPT 분석에서 예상 수익률 추출 (간단한 추정)
            analysis = rec.get('analysis', '')
            expected_return = self.extract_expected_return_from_analysis(analysis)
            new_recommendations.append({
                'symbol': rec['stock_info']['symbol'],
                'name': rec['stock_info']['name'],
                'expected_return': expected_return,
                'score': rec['score_info']['total_score'],
                'current_price': rec['stock_info']['current_price']
            })
        
        # 리밸런싱 판단 로직
        should_rebalance = False
        stocks_to_sell = []
        stocks_to_buy = []
        
        # 현재 보유 주식 중 성과가 나쁜 주식 찾기
        for stock in updated_portfolio['current_stocks']:
            if stock['return_pct'] < -min_return_threshold:  # 손실이 임계값을 넘으면
                stocks_to_sell.append(stock)
                should_rebalance = True
        
        # 새로운 추천 주식 중 더 좋은 기회 찾기
        for new_rec in new_recommendations:
            better_opportunity = False
            
            # 현재 보유 주식들과 비교
            for current_stock in updated_portfolio['current_stocks']:
                if (new_rec['expected_return'] > current_stock['return_pct'] + min_return_threshold and
                    new_rec['score'] > 70):  # 높은 점수의 새로운 기회
                    better_opportunity = True
                    break
            
            if better_opportunity:
                stocks_to_buy.append(new_rec)
                should_rebalance = True
        
        return should_rebalance, stocks_to_sell, stocks_to_buy
    
    def extract_expected_return_from_analysis(self, analysis: str) -> float:
        """GPT 분석에서 예상 수익률 추출"""
        try:
            # 분석 텍스트에서 목표가나 예상 수익률 찾기
            lines = analysis.split('\n')
            for line in lines:
                if '목표가' in line or '상승' in line:
                    # 숫자와 % 기호 찾기
                    import re
                    numbers = re.findall(r'(\d+(?:\.\d+)?)\s*%', line)
                    if numbers:
                        return float(numbers[0])
                    
                    # 달러 기호와 함께 있는 숫자 찾기
                    dollar_numbers = re.findall(r'\$(\d+(?:\.\d+)?)', line)
                    if dollar_numbers:
                        return 5.0  # 기본값
        except:
            pass
        
        return 3.0  # 기본 예상 수익률
    
    def create_rebalancing_plan(self, stocks_to_sell: List[Dict], stocks_to_buy: List[Dict], 
                               portfolio: Dict) -> Dict:
        """리밸런싱 계획 생성"""
        total_available_cash = portfolio.get('total_investment', 10000)
        
        # 매도할 주식들의 현금화
        cash_from_sales = 0
        for stock in stocks_to_sell:
            cash_from_sales += stock.get('current_value', 0)
        
        total_cash = total_available_cash + cash_from_sales
        
        # 매수할 주식들에 현금 분배
        buy_orders = []
        if stocks_to_buy:
            cash_per_stock = total_cash / len(stocks_to_buy)
            
            for stock in stocks_to_buy:
                # current_price 키가 없을 경우 기본값 사용
                current_price = stock.get('current_price', 100)
                if current_price <= 0:
                    current_price = 100  # 기본값
                
                quantity = int(cash_per_stock / current_price)
                if quantity > 0:
                    buy_orders.append({
                        'symbol': stock.get('symbol', 'UNKNOWN'),
                        'name': stock.get('name', 'Unknown Company'),
                        'quantity': quantity,
                        'price': current_price,
                        'total_cost': quantity * current_price,
                        'expected_return': stock.get('expected_return', 3.0)
                    })
        
        return {
            'stocks_to_sell': stocks_to_sell,
            'stocks_to_buy': buy_orders,
            'cash_from_sales': cash_from_sales,
            'total_cash_available': total_cash,
            'estimated_commission': len(stocks_to_sell + buy_orders) * 10,  # 거래 수수료 추정
            'rebalancing_date': datetime.now().isoformat()
        }
    
    def update_portfolio_after_rebalancing(self, portfolio: Dict, rebalancing_plan: Dict) -> Dict:
        """리밸런싱 후 포트폴리오 업데이트"""
        # 매도할 주식들 제거
        current_stocks = [stock for stock in portfolio['current_stocks'] 
                         if stock['symbol'] not in [s['symbol'] for s in rebalancing_plan['stocks_to_sell']]]
        
        # 매수할 주식들 추가
        for buy_order in rebalancing_plan['stocks_to_buy']:
            current_stocks.append({
                'symbol': buy_order['symbol'],
                'name': buy_order['name'],
                'purchase_price': buy_order['price'],
                'quantity': buy_order['quantity'],
                'purchase_date': datetime.now().isoformat()
            })
        
        return {
            **portfolio,
            'current_stocks': current_stocks,
            'last_rebalancing': rebalancing_plan['rebalancing_date']
        }
    
    def get_performance_summary(self, portfolio: Dict) -> Dict:
        """포트폴리오 성과 요약"""
        updated_portfolio = self.calculate_portfolio_performance(portfolio)
        
        if not updated_portfolio['current_stocks']:
            return {
                'total_return_pct': 0,
                'total_return_amount': 0,
                'best_performer': None,
                'worst_performer': None,
                'portfolio_value': 0
            }
        
        # 최고/최저 성과 주식 찾기
        best_stock = max(updated_portfolio['current_stocks'], key=lambda x: x['return_pct'])
        worst_stock = min(updated_portfolio['current_stocks'], key=lambda x: x['return_pct'])
        
        return {
            'total_return_pct': updated_portfolio['total_return_pct'],
            'total_return_amount': updated_portfolio['total_return'],
            'portfolio_value': updated_portfolio['portfolio_value'],
            'best_performer': {
                'symbol': best_stock['symbol'],
                'name': best_stock['name'],
                'return_pct': best_stock['return_pct']
            },
            'worst_performer': {
                'symbol': worst_stock['symbol'],
                'name': worst_stock['name'],
                'return_pct': worst_stock['return_pct']
            },
            'total_stocks': len(updated_portfolio['current_stocks'])
        }
    
    def get_previous_session_recommendations(self) -> List[Dict]:
        """이전 세션의 추천 주식 조회"""
        try:
            history = self.load_recommendation_history()
            
            if len(history) < 2:  # 최소 2개 세션이 있어야 이전 세션 존재
                return []
            
            # 가장 최근 세션 (현재) 제외하고 이전 세션 반환
            previous_session = history[-2]  # -1은 현재, -2는 이전
            
            if 'recommendations' in previous_session:
                return previous_session['recommendations']
            else:
                return []
                
        except Exception as e:
            print(f"이전 세션 추천 조회 오류: {e}")
            return []
    
    def get_session_comparison(self, current_recommendations: List[Dict]) -> Dict:
        """현재 세션과 이전 세션 비교 분석"""
        try:
            previous_recommendations = self.get_previous_session_recommendations()
            
            if not previous_recommendations:
                return {
                    'has_previous': False,
                    'improved_stocks': [],
                    'worsened_stocks': [],
                    'new_stocks': current_recommendations,
                    'removed_stocks': []
                }
            
            # 현재 주식 심볼들
            current_symbols = {rec['stock_info']['symbol'] for rec in current_recommendations}
            previous_symbols = {rec['stock_info']['symbol'] for rec in previous_recommendations}
            
            # 새로 추가된 주식들
            new_stocks = [rec for rec in current_recommendations 
                         if rec['stock_info']['symbol'] not in previous_symbols]
            
            # 제거된 주식들
            removed_stocks = [rec for rec in previous_recommendations 
                             if rec['stock_info']['symbol'] not in current_symbols]
            
            # 공통 주식들의 점수 변화 분석
            improved_stocks = []
            worsened_stocks = []
            
            for current_rec in current_recommendations:
                symbol = current_rec['stock_info']['symbol']
                current_score = current_rec['score_info']['total_score']
                
                # 이전 세션에서 같은 주식 찾기
                for previous_rec in previous_recommendations:
                    if previous_rec['stock_info']['symbol'] == symbol:
                        previous_score = previous_rec['score_info']['total_score']
                        score_change = current_score - previous_score
                        
                        comparison_data = {
                            'symbol': symbol,
                            'current_score': current_score,
                            'previous_score': previous_score,
                            'score_change': score_change,
                            'current_rec': current_rec,
                            'previous_rec': previous_rec
                        }
                        
                        if score_change > 0:
                            improved_stocks.append(comparison_data)
                        else:
                            worsened_stocks.append(comparison_data)
                        break
            
            return {
                'has_previous': True,
                'improved_stocks': improved_stocks,
                'worsened_stocks': worsened_stocks,
                'new_stocks': new_stocks,
                'removed_stocks': removed_stocks,
                'total_improved': len(improved_stocks),
                'total_worsened': len(worsened_stocks),
                'total_new': len(new_stocks),
                'total_removed': len(removed_stocks)
            }
            
        except Exception as e:
            print(f"세션 비교 분석 오류: {e}")
            return {
                'has_previous': False,
                'improved_stocks': [],
                'worsened_stocks': [],
                'new_stocks': current_recommendations,
                'removed_stocks': []
            }
    
    def save_selected_stocks(self, selected_stocks: List[Dict], session_id: str = None):
        """세션별 선택된 주식 저장"""
        try:
            if not session_id:
                session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            selected_file = os.path.join(self.data_dir, f"selected_stocks_{session_id}.json")
            
            # 선택된 주식 데이터 정리
            clean_selected_stocks = []
            for stock in selected_stocks:
                clean_stock = {
                    'symbol': stock['stock_info']['symbol'],
                    'name': stock['stock_info']['name'],
                    'current_price': stock['stock_info']['current_price'],
                    'score': stock['score_info']['total_score'],
                    'shares_affordable': stock.get('shares_affordable', 0),
                    'is_news_priority': stock.get('is_news_priority', False),
                    'selected_date': datetime.now().isoformat(),
                    'session_id': session_id
                }
                clean_selected_stocks.append(clean_stock)
            
            with open(selected_file, 'w', encoding='utf-8') as f:
                json.dump(clean_selected_stocks, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 선택된 주식 저장 완료: {len(clean_selected_stocks)}개")
            return session_id
            
        except Exception as e:
            print(f"선택된 주식 저장 오류: {e}")
            return None
    
    def load_selected_stocks(self, session_id: str = None) -> List[Dict]:
        """세션별 선택된 주식 로드"""
        try:
            if not session_id:
                # 가장 최근 세션 찾기
                selected_files = [f for f in os.listdir(self.data_dir) if f.startswith('selected_stocks_')]
                if not selected_files:
                    return []
                
                # 가장 최근 파일 선택
                selected_files.sort(reverse=True)
                session_id = selected_files[0].replace('selected_stocks_', '').replace('.json', '')
            
            selected_file = os.path.join(self.data_dir, f"selected_stocks_{session_id}.json")
            
            if not os.path.exists(selected_file):
                return []
            
            with open(selected_file, 'r', encoding='utf-8') as f:
                selected_stocks = json.load(f)
            
            return selected_stocks
            
        except Exception as e:
            print(f"선택된 주식 로드 오류: {e}")
            return []
    
    def get_selected_stocks_performance(self, selected_stocks: List[Dict]) -> Dict:
        """선택된 주식들의 성과 분석"""
        try:
            if not selected_stocks:
                return {
                    'total_selected': 0,
                    'total_investment': 0,
                    'current_value': 0,
                    'total_return': 0,
                    'total_return_pct': 0,
                    'best_performer': None,
                    'worst_performer': None
                }
            
            total_investment = 0
            current_value = 0
            stock_performances = []
            
            for stock in selected_stocks:
                symbol = stock['symbol']
                current_price = stock['current_price']
                shares = stock.get('shares_affordable', 0)
                
                if shares > 0:
                    investment = current_price * shares
                    total_investment += investment
                    current_value += investment
                    
                    stock_performances.append({
                        'symbol': symbol,
                        'name': stock['name'],
                        'current_price': current_price,
                        'shares': shares,
                        'investment': investment,
                        'score': stock['score']
                    })
            
            # 성과 계산 (현재는 기본값, 실제로는 가격 변화 추적 필요)
            total_return = current_value - total_investment
            total_return_pct = (total_return / total_investment * 100) if total_investment > 0 else 0
            
            # 최고/최저 성과 주식
            best_performer = max(stock_performances, key=lambda x: x['score']) if stock_performances else None
            worst_performer = min(stock_performances, key=lambda x: x['score']) if stock_performances else None
            
            return {
                'total_selected': len(selected_stocks),
                'total_investment': total_investment,
                'current_value': current_value,
                'total_return': total_return,
                'total_return_pct': total_return_pct,
                'best_performer': best_performer,
                'worst_performer': worst_performer,
                'stock_performances': stock_performances
            }
            
        except Exception as e:
            print(f"선택된 주식 성과 분석 오류: {e}")
            return {
                'total_selected': 0,
                'total_investment': 0,
                'current_value': 0,
                'total_return': 0,
                'total_return_pct': 0,
                'best_performer': None,
                'worst_performer': None
            } 