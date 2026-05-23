#!/usr/bin/env python3
"""
주식 거래 전략 계산기
버젯에 맞는 최적의 주식 거래 전략을 제시
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import streamlit as st

class StockTrader:
    def __init__(self):
        # yf.Session()은 존재하지 않으므로 완전 제거
        self.initialized = True
    
    def get_stock_analysis(self, symbol: str) -> Dict:
        """주식 분석 정보 가져오기"""
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            
            # 기본 정보
            current_price = info.get('currentPrice', 0)
            if current_price == 0:
                current_price = info.get('regularMarketPrice', 0)
            
            # 기술적 분석
            hist = stock.history(period="30d")
            if len(hist) > 10:
                # 이동평균
                hist['MA5'] = hist['Close'].rolling(window=5).mean()
                hist['MA20'] = hist['Close'].rolling(window=20).mean()
                
                # RSI 계산
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                hist['RSI'] = 100 - (100 / (1 + rs))
                
                latest = hist.iloc[-1]
                rsi = latest['RSI']
                ma5 = latest['MA5']
                ma20 = latest['MA20']
                
                # 추세 분석
                trend = "상승" if ma5 > ma20 else "하락" if ma5 < ma20 else "횡보"
                
                # 변동성 계산
                volatility = hist['Close'].pct_change().std() * 100
            else:
                rsi = 50
                trend = "정보부족"
                volatility = 0
            
            return {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'current_price': current_price,
                'market_cap': info.get('marketCap', 0),
                'volume': info.get('volume', 0),
                'rsi': rsi,
                'trend': trend,
                'volatility': volatility,
                'pe_ratio': info.get('trailingPE', 0),
                'beta': info.get('beta', 1),
                'sector': info.get('sector', 'Unknown')
            }
        except Exception as e:
            print(f"주식 분석 오류 ({symbol}): {e}")
            return None
    
    def calculate_trading_strategy(self, symbol: str, budget: float, risk_tolerance: str = "보통") -> Dict:
        """거래 전략 계산"""
        stock_info = self.get_stock_analysis(symbol)
        if not stock_info:
            return None
        
        current_price = stock_info['current_price']
        if current_price <= 0:
            return None
        
        # 리스크 톨러런스에 따른 설정
        risk_settings = {
            "보수적": {"max_allocation": 0.3, "stop_loss": 0.05, "take_profit": 0.15},
            "보통": {"max_allocation": 0.5, "stop_loss": 0.08, "take_profit": 0.20},
            "공격적": {"max_allocation": 0.7, "stop_loss": 0.12, "take_profit": 0.30}
        }
        
        settings = risk_settings.get(risk_tolerance, risk_settings["보통"])
        
        # 최대 투자 가능 금액
        max_investment = budget * settings["max_allocation"]
        
        # 구매 가능 주식 수
        max_shares = int(max_investment / current_price)
        
        if max_shares == 0:
            return {
                'error': f"현재 가격 ${current_price:.2f}로는 예산 ${budget:,.0f}로 주식을 구매할 수 없습니다."
            }
        
        # 실제 투자 금액
        actual_investment = max_shares * current_price
        
        # 손절가 및 목표가
        stop_loss_price = current_price * (1 - settings["stop_loss"])
        take_profit_price = current_price * (1 + settings["take_profit"])
        
        # 거래 수수료 (예상)
        commission = 10  # $10 고정 수수료
        
        # 수익성 분석
        potential_profit = (take_profit_price - current_price) * max_shares - commission
        potential_loss = (current_price - stop_loss_price) * max_shares + commission
        
        # 리스크/리워드 비율
        risk_reward_ratio = potential_profit / potential_loss if potential_loss > 0 else 0
        
        # 매매 권장
        recommendation = self._get_recommendation(stock_info, risk_reward_ratio)
        
        return {
            'stock_info': stock_info,
            'budget': budget,
            'risk_tolerance': risk_tolerance,
            'max_shares': max_shares,
            'actual_investment': actual_investment,
            'current_price': current_price,
            'stop_loss_price': stop_loss_price,
            'take_profit_price': take_profit_price,
            'potential_profit': potential_profit,
            'potential_loss': potential_loss,
            'risk_reward_ratio': risk_reward_ratio,
            'commission': commission,
            'recommendation': recommendation,
            'strategy_details': self._get_strategy_details(stock_info, max_shares, settings)
        }
    
    def _get_recommendation(self, stock_info: Dict, risk_reward_ratio: float) -> str:
        """매매 권장 결정"""
        rsi = stock_info['rsi']
        trend = stock_info['trend']
        volatility = stock_info['volatility']
        
        # RSI 기반 신호
        if rsi < 30:
            rsi_signal = "매수 기회"
        elif rsi > 70:
            rsi_signal = "매도 고려"
        else:
            rsi_signal = "중립"
        
        # 추세 기반 신호
        if trend == "상승":
            trend_signal = "상승 추세"
        elif trend == "하락":
            trend_signal = "하락 추세"
        else:
            trend_signal = "횡보"
        
        # 종합 권장
        if rsi < 30 and trend == "상승" and risk_reward_ratio > 2:
            return "강력 매수"
        elif rsi > 70 and trend == "하락":
            return "매도 고려"
        elif rsi < 40 and trend == "상승":
            return "매수"
        elif rsi > 60 and trend == "하락":
            return "매도"
        else:
            return "관망"
    
    def _get_strategy_details(self, stock_info: Dict, shares: int, settings: Dict) -> Dict:
        """전략 상세 정보"""
        return {
            'entry_strategy': f"현재가 ${stock_info['current_price']:.2f}에서 {shares}주 매수",
            'exit_strategy': f"손절가 ${stock_info['current_price'] * (1 - settings['stop_loss']):.2f}, 목표가 ${stock_info['current_price'] * (1 + settings['take_profit']):.2f}",
            'position_sizing': f"예산의 {settings['max_allocation']*100:.0f}% 할당",
            'risk_management': f"최대 손실 {settings['stop_loss']*100:.0f}%, 목표 수익 {settings['take_profit']*100:.0f}%",
            'timing': f"RSI: {stock_info['rsi']:.1f} ({'과매도' if stock_info['rsi'] < 30 else '과매수' if stock_info['rsi'] > 70 else '중립'})",
            'trend_analysis': f"추세: {stock_info['trend']}, 변동성: {stock_info['volatility']:.1f}%"
        }
    
    def compare_stocks(self, symbols: List[str], budget: float, risk_tolerance: str = "보통") -> List[Dict]:
        """여러 주식 비교 분석"""
        results = []
        
        for symbol in symbols:
            strategy = self.calculate_trading_strategy(symbol, budget, risk_tolerance)
            if strategy and 'error' not in strategy:
                results.append(strategy)
        
        # 리스크/리워드 비율로 정렬
        results.sort(key=lambda x: x['risk_reward_ratio'], reverse=True)
        
        return results

def main():
    st.set_page_config(
        page_title="주식 거래 전략 계산기",
        page_icon="💰",
        layout="wide"
    )
    
    st.title("💰 주식 거래 전략 계산기")
    st.markdown("버젯에 맞는 최적의 주식 거래 전략을 제시합니다")
    
    # 사이드바 설정
    with st.sidebar:
        st.header("⚙️ 거래 설정")
        
        budget = st.number_input(
            "투자 예산 (USD)",
            min_value=100,
            max_value=100000,
            value=10000,
            step=1000
        )
        
        risk_tolerance = st.selectbox(
            "리스크 톨러런스",
            ["보수적", "보통", "공격적"],
            help="투자 스타일에 따른 리스크 설정"
        )
        
        st.markdown("---")
        st.markdown("### 📊 분석 기준")
        st.markdown("- RSI (상대강도지수)")
        st.markdown("- 이동평균 추세")
        st.markdown("- 변동성 분석")
        st.markdown("- 리스크/리워드 비율")
        st.markdown("- 포지션 사이징")
    
    # 메인 컨텐츠
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("📈 단일 주식 분석")
        
        symbol = st.text_input(
            "주식 심볼 입력",
            value="AAPL",
            help="분석할 주식의 심볼을 입력하세요 (예: AAPL, TSLA, GOOGL)"
        ).upper()
        
        if st.button("🔍 분석하기", type="primary"):
            if symbol:
                trader = StockTrader()
                strategy = trader.calculate_trading_strategy(symbol, budget, risk_tolerance)
                
                if strategy and 'error' not in strategy:
                    st.success(f"✅ {symbol} 분석 완료!")
                    
                    # 주식 정보
                    stock_info = strategy['stock_info']
                    col1_info, col2_info = st.columns(2)
                    
                    with col1_info:
                        st.metric("현재가", f"${stock_info['current_price']:.2f}")
                        st.metric("RSI", f"{stock_info['rsi']:.1f}")
                        st.metric("추세", stock_info['trend'])
                    
                    with col2_info:
                        st.metric("시가총액", f"${stock_info['market_cap']:,.0f}")
                        st.metric("변동성", f"{stock_info['volatility']:.1f}%")
                        st.metric("P/E", f"{stock_info['pe_ratio']:.2f}")
                    
                    # 거래 전략
                    st.subheader("🎯 거래 전략")
                    
                    col1_strat, col2_strat = st.columns(2)
                    
                    with col1_strat:
                        st.metric("권장", strategy['recommendation'])
                        st.metric("매수 수량", f"{strategy['max_shares']}주")
                        st.metric("투자 금액", f"${strategy['actual_investment']:,.0f}")
                    
                    with col2_strat:
                        st.metric("손절가", f"${strategy['stop_loss_price']:.2f}")
                        st.metric("목표가", f"${strategy['take_profit_price']:.2f}")
                        st.metric("R/R 비율", f"{strategy['risk_reward_ratio']:.2f}")
                    
                    # 전략 상세
                    st.subheader("📋 전략 상세")
                    details = strategy['strategy_details']
                    
                    for key, value in details.items():
                        st.write(f"**{key}:** {value}")
                    
                    # 수익성 분석
                    st.subheader("💰 수익성 분석")
                    
                    col1_profit, col2_profit = st.columns(2)
                    
                    with col1_profit:
                        st.metric("예상 수익", f"${strategy['potential_profit']:,.0f}")
                    
                    with col2_profit:
                        st.metric("최대 손실", f"${strategy['potential_loss']:,.0f}")
                    
                elif strategy and 'error' in strategy:
                    st.error(strategy['error'])
                else:
                    st.error("주식 정보를 가져올 수 없습니다.")
    
    with col2:
        st.header("🔄 주식 비교 분석")
        
        symbols_input = st.text_area(
            "주식 심볼들 (한 줄에 하나씩)",
            value="AAPL\nTSLA\nGOOGL\nMSFT",
            help="비교할 주식들의 심볼을 한 줄에 하나씩 입력하세요"
        )
        
        if st.button("📊 비교 분석", type="secondary"):
            symbols = [s.strip().upper() for s in symbols_input.split('\n') if s.strip()]
            
            if symbols:
                trader = StockTrader()
                results = trader.compare_stocks(symbols, budget, risk_tolerance)
                
                if results:
                    st.success(f"✅ {len(results)}개 주식 분석 완료!")
                    
                    # 결과 테이블
                    data = []
                    for result in results:
                        stock_info = result['stock_info']
                        data.append({
                            '심볼': stock_info['symbol'],
                            '현재가': f"${stock_info['current_price']:.2f}",
                            'RSI': f"{stock_info['rsi']:.1f}",
                            '추세': stock_info['trend'],
                            '권장': result['recommendation'],
                            '매수수량': f"{result['max_shares']}주",
                            'R/R비율': f"{result['risk_reward_ratio']:.2f}",
                            '예상수익': f"${result['potential_profit']:,.0f}"
                        })
                    
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                    
                    # 최고 추천 주식
                    best_stock = results[0]
                    st.subheader("🏆 최고 추천")
                    st.info(f"**{best_stock['stock_info']['symbol']}** - {best_stock['recommendation']}")
                    st.write(f"**이유:** R/R 비율 {best_stock['risk_reward_ratio']:.2f}, RSI {best_stock['stock_info']['rsi']:.1f}, 추세 {best_stock['stock_info']['trend']}")
                else:
                    st.error("분석할 수 있는 주식이 없습니다.")
    
    # 하단 정보
    st.markdown("---")
    st.markdown("### ⚠️ 주의사항")
    st.markdown("- 이 분석은 참고용이며, 실제 투자 결정은 본인의 판단에 따라야 합니다.")
    st.markdown("- 과거 성과가 미래 수익을 보장하지 않습니다.")
    st.markdown("- 손절가와 목표가는 시장 상황에 따라 조정이 필요할 수 있습니다.")
    st.markdown("- 거래 수수료와 세금을 고려하여 실제 수익을 계산하세요.")

if __name__ == "__main__":
    main() 