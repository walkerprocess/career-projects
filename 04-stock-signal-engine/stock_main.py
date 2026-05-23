import yfinance as yf
import openai
import pandas as pd
import requests
from bs4 import BeautifulSoup
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
import time
from stock_analyzer import StockAnalyzer, get_stock_candidates
from portfolio_manager import PortfolioManager
from excel_reporter import ExcelReporter
from enhanced_news_collector import EnhancedNewsCollector

# 환경 변수 로드
load_dotenv()

# OpenAI API 키 설정
openai.api_key = os.getenv('OPENAI_API_KEY')

class StockRecommender:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.analyzer = StockAnalyzer()
        self.portfolio_manager = PortfolioManager()
        self.excel_reporter = ExcelReporter()
        self.enhanced_news_collector = EnhancedNewsCollector()
        
    def analyze_stock_with_gpt(self, stock_info, news_items, investment_amount, score_info):
        """상세한 GPT 분석 - 뉴스 내용을 포함한 완전한 분석 제공"""
        try:
            # 캐시 확인 먼저
            cache_key = f"gpt_analysis_{stock_info['symbol']}_{score_info['total_score']}"
            cached_analysis = self.analyzer.load_cache(cache_key)
            if cached_analysis:
                return cached_analysis
            
            # 상세한 정보 준비
            symbol = stock_info['symbol']
            price = stock_info['current_price']
            score = score_info['total_score']
            sector = stock_info.get('sector', 'Unknown')
            market_cap = stock_info.get('market_cap', 0)
            pe_ratio = stock_info.get('pe_ratio', 0)
            volume = stock_info.get('volume', 0)
            beta = stock_info.get('beta', 0)
            
            # 뉴스 내용 요약
            news_summary = ""
            if news_items:
                news_summary = "주요 뉴스 내용:\n"
                for i, news in enumerate(news_items[:5], 1):  # 상위 5개 뉴스만
                    title = news.get('title', '')
                    content = news.get('content', '')
                    impact = news.get('impact', '중립적')
                    source = news.get('source', 'Unknown')
                    news_summary += f"{i}. {title} ({impact}, {source})\n"
                    if content and len(content) > 50:
                        news_summary += f"   내용: {content[:100]}...\n"
            
            # 상세한 프롬프트 구성
            prompt = f"""
주식 분석 요청: {symbol}에 대한 상세한 투자 분석

기본 정보:
- 주식 티커: {symbol}
- 현재가: ${price:.2f}
- 종합점수: {score}/100
- 섹터: {sector}
- 시가총액: ${market_cap:,.0f}
- P/E 비율: {pe_ratio:.2f}
- 거래량: {volume:,.0f}
- 베타: {beta:.2f}
- 투자금액: ${investment_amount:,.0f}

{news_summary}

위 정보를 바탕으로 {symbol}에 대한 상세한 투자 분석을 제공해주세요.

분석 구조:
1. 현재 상황 평가 (가격, 거래량, 시장 위치)
2. 뉴스 기반 전망 분석 (최근 뉴스가 주가에 미치는 영향)
3. 투자 매력도 분석 (기술적/기본적 지표 종합)
4. 리스크 요인 (시장, 섹터, 회사별 리스크)
5. 투자 권장사항 (매수/매도/관망 및 이유)

각 섹션을 완전한 문장으로 작성하고, 뉴스 내용을 구체적으로 언급하여 분석해주세요.
# 기호는 사용하지 마세요.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 전문 주식 분석가입니다. 주어진 주식 정보와 뉴스 내용을 바탕으로 상세하고 실용적인 투자 분석을 제공해주세요. 뉴스 내용을 구체적으로 언급하고, 투자 결정에 도움이 되는 실질적인 정보를 제공해주세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,  # 더 긴 분석을 위해 토큰 수 증가
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            
            # 결과가 완전하지 않으면 기본 분석으로 보완
            if len(result.strip()) < 100 or result.count('.') < 4:
                result = self._generate_comprehensive_analysis(stock_info, score_info, news_items)
            
            # 캐시 저장
            self.analyzer.save_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            print(f"GPT 분석 오류: {e}")
            # 기본 분석 반환 (GPT 없이)
            return self._generate_comprehensive_analysis(stock_info, score_info, news_items)
    
    def _generate_comprehensive_analysis(self, stock_info, score_info, news_items):
        """GPT 없이 상세한 기본 분석 생성 - 뉴스 내용 포함"""
        symbol = stock_info['symbol']
        price = stock_info['current_price']
        score = score_info['total_score']
        sector = stock_info.get('sector', 'Unknown')
        market_cap = stock_info.get('market_cap', 0)
        pe_ratio = stock_info.get('pe_ratio', 0)
        volume = stock_info.get('volume', 0)
        beta = stock_info.get('beta', 0)
        
        # 뉴스 요약
        news_summary = ""
        if news_items:
            positive_news = sum(1 for news in news_items if news.get('impact') == '긍정적')
            negative_news = sum(1 for news in news_items if news.get('impact') == '부정적')
            neutral_news = len(news_items) - positive_news - negative_news
            
            news_summary = f"뉴스 분석: 총 {len(news_items)}개 뉴스 중 긍정적 {positive_news}개, 부정적 {negative_news}개, 중립적 {neutral_news}개"
        
        # 점수 기반 평가
        if score >= 80:
            rating = "매우 우수"
            recommendation = "강력 매수"
            risk_level = "낮음"
        elif score >= 70:
            rating = "우수"
            recommendation = "매수"
            risk_level = "낮음-보통"
        elif score >= 60:
            rating = "양호"
            recommendation = "관망-매수"
            risk_level = "보통"
        elif score >= 50:
            rating = "보통"
            recommendation = "관망"
            risk_level = "보통-높음"
        else:
            rating = "주의"
            recommendation = "관망-매도"
            risk_level = "높음"
        
        # 시가총액 평가
        if market_cap > 10000000000:  # 100억 달러 이상
            size_comment = "대형주로 안정성이 높습니다"
        elif market_cap > 1000000000:  # 10억 달러 이상
            size_comment = "중형주로 성장 잠재력이 있습니다"
        else:
            size_comment = "소형주로 변동성이 클 수 있습니다"
        
        # P/E 비율 평가
        if pe_ratio > 0 and pe_ratio < 20:
            pe_comment = "밸류에이션이 합리적입니다"
        elif pe_ratio > 0 and pe_ratio < 30:
            pe_comment = "밸류에이션이 보통 수준입니다"
        elif pe_ratio > 0:
            pe_comment = "밸류에이션이 높을 수 있습니다"
        else:
            pe_comment = "P/E 비율 정보가 부족합니다"
        
        # 베타 평가
        if beta > 0:
            if beta > 1.5:
                beta_comment = "높은 변동성을 보입니다"
            elif beta > 1.0:
                beta_comment = "시장 평균보다 높은 변동성을 보입니다"
            elif beta > 0.5:
                beta_comment = "시장 평균 수준의 변동성을 보입니다"
            else:
                beta_comment = "낮은 변동성을 보입니다"
        else:
            beta_comment = "베타 정보가 부족합니다"
        
        analysis = f"""📊 {symbol} 종합 투자 분석

현재 상황: {symbol}은(는) 현재 ${price:.2f}에 거래되고 있으며, 종합 점수 {score}/100으로 {rating}한 수준입니다. {sector} 섹터에 속하며, {size_comment}. 거래량은 {volume:,.0f}주이며, {beta_comment}.

{news_summary}

투자 매력도: 종합 점수 {score}점은 기술적 지표, 뉴스 분석, 기본적 분석을 종합한 결과입니다. {pe_comment}. 현재 가격 대비 투자 가치가 있는 것으로 판단됩니다.

리스크 요인: 위험도는 {risk_level} 수준으로 평가되며, 시장 변동성과 섹터별 리스크를 고려해야 합니다. 특히 {sector} 섹터의 특성상 산업 트렌드 변화에 민감할 수 있습니다.

투자 권장사항: {recommendation}을 권장합니다. 분산 투자를 통해 리스크를 관리하고, 정기적인 포트폴리오 리밸런싱을 통해 최적의 수익을 추구하시기 바랍니다."""
        
        return analysis
    
    def get_top_stocks(self, investment_amount, selected_sectors=None, force_refresh=True):
        """뉴스 기반 우선순위와 30주 이상 구매 가능한 주식들을 추천합니다."""
        print("🔍 뉴스 분석을 통한 우선순위 주식 탐지 중...")
        
        # 1단계: 뉴스를 먼저 수집하고 그 뉴스에서 주식 이름 추출
        print("📰 1단계: 종합 뉴스 수집 및 주식 티커 추출...")
        news_analysis_result = self.enhanced_news_collector.get_stocks_from_news_analysis(force_refresh=force_refresh)
        
        # 결과 형태 확인 및 처리
        if isinstance(news_analysis_result, dict):
            news_priority_stocks = news_analysis_result.get('priority_stocks', [])
            keyword_stocks = news_analysis_result.get('keyword_stocks', [])
            total_found = news_analysis_result.get('total_found', 0)
            keywords_used = news_analysis_result.get('keywords_used', [])
        else:
            news_priority_stocks = news_analysis_result if isinstance(news_analysis_result, list) else []
            keyword_stocks = []
            total_found = len(news_priority_stocks)
            keywords_used = []
        
        print(f"📰 뉴스에서 {len(news_priority_stocks)}개 우선순위 주식 발견")
        print(f"🤖 GPT 키워드 분석으로 {len(keyword_stocks)}개 관련 주식 발견")
        if keywords_used:
            print(f"🔍 사용된 키워드: {', '.join(keywords_used[:10])}")
        
        # 키워드 분석 주식들을 우선순위에 추가
        for keyword_stock in keyword_stocks:
            symbol = keyword_stock.get('symbol', '')
            if symbol and symbol not in news_priority_stocks:
                news_priority_stocks.append(symbol)
                print(f"🤖 키워드 분석 주식 추가: {symbol} - {keyword_stock.get('name', 'Unknown')}")
        
        # 키워드 분석 정보 저장
        keyword_analysis_info = {
            'total_keywords': len(keywords_used),
            'keyword_stocks': keyword_stocks,
            'keywords_used': keywords_used[:10]  # 상위 10개만
        }
        
        # 2단계: 섹터별 주식 후보
        all_candidates = get_stock_candidates()
        
        # 선택된 섹터가 있으면 해당 섹터만, 없으면 모든 섹터
        if selected_sectors:
            stock_candidates = []
            for sector in selected_sectors:
                if sector in all_candidates:
                    stock_candidates.extend(all_candidates[sector])
        else:
            stock_candidates = []
            for sector_stocks in all_candidates.values():
                stock_candidates.extend(sector_stocks)
        
        print(f"📋 총 {len(stock_candidates)}개 주식 후보 준비 완료")
        
        # 3단계: 뉴스 우선순위와 30주 구매 가능 필터링
        suitable_stocks = self.analyzer.filter_stocks_by_investment_and_news(
            stock_candidates, investment_amount, news_priority_stocks
        )
        
        if not suitable_stocks:
            print("❌ 조건에 맞는 주식을 찾을 수 없습니다.")
            return []
        
        print(f"✅ 조건에 맞는 {len(suitable_stocks)}개 주식 발견")
        
        # 4단계: 최대 2개 주식 분석 (Rate limit 방지)
        limited_stocks = suitable_stocks[:2]
        
        recommendations = []
        total_stocks = len(limited_stocks)
        
        for i, stock_info in enumerate(limited_stocks):
            print(f"🔍 분석 진행 중: {i+1}/{total_stocks} - {stock_info['symbol']}")
            
            # 뉴스 가져오기 (향상된 버전)
            news_result = self.analyzer.get_yahoo_finance_news_enhanced(stock_info['symbol'])
            
            # 결과 형태 확인 및 처리
            if isinstance(news_result, dict):
                news_items = news_result.get('news', [])
                mentioned_stocks = news_result.get('mentioned_stocks', [])
            else:
                news_items = news_result if isinstance(news_result, list) else []
                mentioned_stocks = []
            
            # 점수 계산 (뉴스 우선순위 보너스 적용)
            base_score_info = self.analyzer.calculate_stock_score(stock_info, len(news_items))
            
            # 🎯 새로운 우선순위 기반 보너스 점수 시스템
            priority_bonus = 0
            affordability_bonus = 0
            tier_bonus = 0
            keyword_bonus = 0
            
            # 뉴스 우선순위 보너스
            if stock_info['symbol'] in news_priority_stocks:
                priority_bonus = 15  # 15점 보너스
                print(f"🌟 {stock_info['symbol']} - 뉴스 우선순위 보너스 +{priority_bonus}점")
            
            # 키워드 분석 보너스
            is_keyword_stock = any(stock['symbol'] == stock_info['symbol'] for stock in keyword_stocks)
            if is_keyword_stock:
                keyword_bonus = 20  # 키워드 분석 주식은 20점 보너스
                print(f"🤖 {stock_info['symbol']} - GPT 키워드 분석 보너스 +{keyword_bonus}점")
            
            # 구매 가능 주식 수 보너스
            shares_can_buy = stock_info.get('shares_affordable', 0)
            if shares_can_buy >= 30:
                affordability_bonus = 15  # 30주 이상: 15점
                print(f"💰 {stock_info['symbol']} - {shares_can_buy}주 구매 가능, 보너스 +{affordability_bonus}점")
            elif shares_can_buy >= 20:
                affordability_bonus = 10  # 20주 이상: 10점
                print(f"💰 {stock_info['symbol']} - {shares_can_buy}주 구매 가능, 보너스 +{affordability_bonus}점")
            elif shares_can_buy >= 10:
                affordability_bonus = 5   # 10주 이상: 5점
                print(f"💰 {stock_info['symbol']} - {shares_can_buy}주 구매 가능, 보너스 +{affordability_bonus}점")
            
            # 티어별 추가 보너스
            base_potential_score = self.analyzer._calculate_base_potential_score(stock_info)
            if stock_info['symbol'] in news_priority_stocks and shares_can_buy >= 30 and base_potential_score >= 70:
                tier_bonus = 20  # 1순위: 뉴스+30주+유망
                print(f"🥇 {stock_info['symbol']} - 1순위 티어 보너스 +{tier_bonus}점")
            elif stock_info['symbol'] in news_priority_stocks and shares_can_buy >= 20 and base_potential_score >= 70:
                tier_bonus = 15  # 2순위: 뉴스+20주+유망
                print(f"🥈 {stock_info['symbol']} - 2순위 티어 보너스 +{tier_bonus}점")
            elif stock_info['symbol'] in news_priority_stocks and base_potential_score >= 60:
                tier_bonus = 10  # 3순위: 뉴스 최다 언급
                print(f"🥉 {stock_info['symbol']} - 3순위 티어 보너스 +{tier_bonus}점")
            elif base_potential_score >= 65:
                tier_bonus = 5   # 4순위: 일반 유망
                print(f"📊 {stock_info['symbol']} - 4순위 티어 보너스 +{tier_bonus}점")
            
            # 최종 점수 계산
            final_score = base_score_info['total_score'] + priority_bonus + affordability_bonus + tier_bonus + keyword_bonus
            score_info = {
                **base_score_info,
                'total_score': final_score,
                'priority_bonus': priority_bonus,
                'affordability_bonus': affordability_bonus,
                'tier_bonus': tier_bonus,
                'keyword_bonus': keyword_bonus,
                'base_potential_score': base_potential_score,
                'shares_affordable': shares_can_buy
            }
            
            # GPT 분석
            analysis = self.analyze_stock_with_gpt(stock_info, news_items, investment_amount, score_info)
            
            # 키워드 분석 정보 추가
            keyword_info = ""
            if is_keyword_stock:
                for stock in keyword_stocks:
                    if stock['symbol'] == stock_info['symbol']:
                        keyword_info = stock.get('description', '')
                        break
            
            recommendations.append({
                'symbol': stock_info['symbol'],
                'stock_info': stock_info,
                'analysis': analysis,
                'score_info': score_info,
                'news_count': len(news_items),
                'news_items': news_items,
                'mentioned_stocks': mentioned_stocks,
                'is_news_priority': stock_info['symbol'] in news_priority_stocks,
                'is_keyword_stock': is_keyword_stock,
                'keyword_info': keyword_info,
                'shares_affordable': shares_can_buy,
                'keyword_analysis_info': keyword_analysis_info if is_keyword_stock else None
            })
            
            # API 호출 간격 최적화 (Rate limit 방지)
            time.sleep(0.3)  # 0.05초에서 0.3초로 증가
        
        # 점수순으로 정렬
        recommendations.sort(key=lambda x: x['score_info']['total_score'], reverse=True)
        
        # 상위 2개 반환 (감소)
        top_recommendations = recommendations[:2]
        
        print(f"🏆 최종 추천: {len(top_recommendations)}개 주식")
        for i, rec in enumerate(top_recommendations, 1):
            symbol = rec['symbol']
            score = rec['score_info']['total_score']
            shares = rec['shares_affordable']
            is_priority = "⭐" if rec['is_news_priority'] else ""
            is_keyword = "🤖" if rec['is_keyword_stock'] else ""
            print(f"{i}. {symbol} - 점수: {score}/100, 구매가능: {shares}주 {is_priority}{is_keyword}")
        
        return top_recommendations

    def calculate_trading_strategy_for_recommendation(self, stock_info, investment_amount, risk_tolerance="보통"):
        """추천 주식에 대한 거래 전략 계산 - 예산 기반 정확한 계산"""
        current_price = stock_info['current_price']
        if current_price <= 0:
            return None
        
        # 리스크 톨러런스에 따른 설정
        risk_settings = {
            "보수적": {"allocation": 0.15, "stop_loss": 0.05, "take_profit": 0.15},  # 15% 할당
            "보통": {"allocation": 0.20, "stop_loss": 0.08, "take_profit": 0.20},    # 20% 할당
            "공격적": {"allocation": 0.25, "stop_loss": 0.12, "take_profit": 0.30}   # 25% 할당
        }
        
        settings = risk_settings.get(risk_tolerance, risk_settings["보통"])
        
        # 🎯 예산 기반 정확한 투자 금액 계산
        stock_investment = investment_amount * settings["allocation"]
        
        # 거래 수수료 고려 (매수/매도 각각 $10)
        commission = 20  # 매수 $10 + 매도 $10
        
        # 수수료를 제외한 실제 주식 구매 가능 금액
        available_for_stocks = stock_investment - commission
        
        if available_for_stocks <= 0:
            return {
                'error': f"투자 금액 ${stock_investment:,.0f}이 수수료 ${commission}보다 작습니다."
            }
        
        # 구매 가능 주식 수 계산 (소수점 버림)
        shares = int(available_for_stocks / current_price)
        
        if shares == 0:
            return {
                'error': f"현재 가격 ${current_price:.2f}로는 예산 ${available_for_stocks:,.0f}로 주식을 구매할 수 없습니다."
            }
        
        # 실제 투자 금액 (주식 가격 + 수수료)
        actual_stock_cost = shares * current_price
        total_investment = actual_stock_cost + commission
        
        # 손절가 및 목표가
        stop_loss_price = current_price * (1 - settings["stop_loss"])
        take_profit_price = current_price * (1 + settings["take_profit"])
        
        # 수익성 분석
        potential_profit = (take_profit_price - current_price) * shares - commission
        potential_loss = (current_price - stop_loss_price) * shares + commission
        
        # 리스크/리워드 비율
        risk_reward_ratio = potential_profit / potential_loss if potential_loss > 0 else 0
        
        # 예산 사용률 계산
        budget_usage = (total_investment / investment_amount) * 100
        
        return {
            'shares': shares,
            'investment_amount': actual_stock_cost,
            'total_cost': total_investment,  # 주식 + 수수료
            'current_price': current_price,
            'stop_loss_price': stop_loss_price,
            'take_profit_price': take_profit_price,
            'potential_profit': potential_profit,
            'potential_loss': potential_loss,
            'risk_reward_ratio': risk_reward_ratio,
            'commission': commission,
            'budget_usage': budget_usage,
            'settings': settings
        }

    def get_detailed_buy_reasons(self, recommendation):
        """뉴스 기반 상세 매수 이유 분석 (링크 없는 뉴스, 생성/가공 뉴스 제외)"""
        try:
            buy_reasons = []
            news_items = recommendation.get('news_items', [])
            # 제외할 소스
            excluded_sources = {'Web Crawl', 'Generated', 'Market Analysis', 'GPT 뉴스 분석'}
            for news in news_items:
                title = news.get('title', '')
                content = news.get('content', '')
                category = news.get('category', '')
                source = news.get('source', '')
                impact = news.get('impact', '중립적')
                confidence = news.get('confidence', '중간')
                url = news.get('url', '')
                # 링크 없거나, 생성/가공 뉴스 소스면 제외
                if not url or source in excluded_sources:
                    continue
                reason = self._extract_buy_reason_from_news(title, content, category, impact, confidence)
                if reason:
                    buy_reasons.append({
                        'category': self._get_category_display_name(category),
                        'reason': reason,
                        'news_source': source,
                        'impact': impact,
                        'confidence': confidence,
                        'full_content': content[:200] + '...' if len(content) > 200 else content,
                        'url': url
                    })
            unique_reasons = []
            seen_reasons = set()
            for reason in buy_reasons:
                reason_key = reason['reason'][:60]
                if reason_key not in seen_reasons:
                    unique_reasons.append(reason)
                    seen_reasons.add(reason_key)
                    if len(unique_reasons) >= 8:
                        break
            return unique_reasons
        except Exception as e:
            print(f"매수 이유 분석 오류: {e}")
            return []
    
    def _extract_buy_reason_from_news(self, title, content, category, impact, confidence):
        """뉴스 제목과 내용에서 매수 이유 추출"""
        title_lower = title.lower()
        content_lower = content.lower()
        
        # 긍정적 키워드 매칭 (확장)
        positive_keywords = {
            'stock_specific': [
                '상승', '급등', '호재', '성장', '확대', '증가', '개선', '강세', '기대', '전망',
                'rise', 'gain', 'growth', 'increase', 'improve', 'strong', 'positive', 'expect', 'outlook'
            ],
            'sector': [
                '섹터 성장', '산업 확대', '시장 확대', '수요 증가', '트렌드', '혁신', '발전',
                'sector growth', 'industry expansion', 'market expansion', 'demand increase', 'innovation'
            ],
            'market': [
                '시장 회복', '경제 개선', '금리 하락', '인플레이션 둔화', '회복', '개선',
                'market recovery', 'economic improvement', 'rate cut', 'inflation easing', 'recovery'
            ],
            'global': [
                '글로벌 수요', '해외 시장', '수출 증가', '국제 경쟁력', '글로벌', '해외',
                'global demand', 'overseas market', 'export increase', 'international'
            ],
            'tech_trend': [
                '기술 혁신', 'AI 발전', '디지털 전환', '신기술', '혁신', '기술',
                'technology innovation', 'AI advancement', 'digital transformation', 'innovation'
            ]
        }
        
        # 카테고리별 키워드 확인
        keywords = positive_keywords.get(category, positive_keywords['stock_specific'])
        
        # 키워드 매칭 및 상세 이유 생성
        matched_keywords = []
        for keyword in keywords:
            if keyword in title_lower or keyword in content_lower:
                matched_keywords.append(keyword)
        
        if matched_keywords:
            # 상세한 매수 이유 생성
            if category == 'stock_specific':
                return f"주식별 뉴스에서 '{', '.join(matched_keywords[:3])}' 키워드 발견 - {impact}적 전망 ({confidence} 신뢰도)"
            elif category == 'sector':
                return f"섹터 뉴스에서 '{', '.join(matched_keywords[:3])}' 트렌드 확인 - 산업 성장 기대 ({confidence} 신뢰도)"
            elif category == 'market':
                return f"시장 뉴스에서 '{', '.join(matched_keywords[:3])}' 환경 개선 - 시장 회복 기대 ({confidence} 신뢰도)"
            elif category == 'global':
                return f"글로벌 뉴스에서 '{', '.join(matched_keywords[:3])}' 확인 - 해외 수요 증가 ({confidence} 신뢰도)"
            elif category == 'tech_trend':
                return f"기술 트렌드에서 '{', '.join(matched_keywords[:3])}' 발견 - 혁신 동력 확인 ({confidence} 신뢰도)"
        
        # 기본 매수 이유 (키워드가 없어도)
        if category == 'stock_specific':
            return f"주식별 뉴스에서 {impact}적 전망 확인 - {confidence} 신뢰도"
        elif category == 'sector':
            return f"섹터 뉴스에서 산업 성장 동력 확인 - {confidence} 신뢰도"
        elif category == 'market':
            return f"시장 뉴스에서 {impact}적 환경 변화 확인 - {confidence} 신뢰도"
        elif category == 'global':
            return f"글로벌 뉴스에서 해외 시장 기회 확인 - {confidence} 신뢰도"
        elif category == 'tech_trend':
            return f"기술 트렌드에서 혁신 동력 확인 - {confidence} 신뢰도"
        
        return f"뉴스 분석을 통한 {impact}적 전망 확인 - {confidence} 신뢰도"
    
    def _get_category_display_name(self, category):
        """카테고리 표시명 반환"""
        category_names = {
            'stock_specific': '주식별 뉴스',
            'sector': '섹터 트렌드',
            'market': '시장 환경',
            'global': '글로벌 동향',
            'tech_trend': '기술 혁신'
        }
        return category_names.get(category, category)

    def validate_and_adjust_budget(self, recommendations, investment_amount, risk_tolerance="보통"):
        """추천 주식들의 예산 검증 및 조정 - 150%까지 허용"""
        total_required = 0
        valid_recommendations = []
        
        # 리스크 톨러런스에 따른 할당 비율
        allocation_ratio = {
            "보수적": 0.15,
            "보통": 0.20,
            "공격적": 0.25
        }.get(risk_tolerance, 0.20)
        
        # 각 주식별 필요 예산 계산
        for rec in recommendations:
            strategy = self.calculate_trading_strategy_for_recommendation(
                rec['stock_info'], investment_amount, risk_tolerance
            )
            
            if strategy and 'error' not in strategy:
                total_required += strategy['total_cost']
                rec['trading_strategy'] = strategy
                valid_recommendations.append(rec)
            else:
                print(f"⚠️ {rec['stock_info']['symbol']}: 거래 전략 계산 실패")
        
        # 예산 초과 여부 확인 (150%까지 허용)
        max_budget = investment_amount * 1.5  # 150%까지 허용
        budget_exceeded = total_required > max_budget
        budget_usage = (total_required / investment_amount) * 100
        
        print(f"💰 예산 검증:")
        print(f"  총 필요 예산: ${total_required:,.0f}")
        print(f"  사용 가능 예산: ${investment_amount:,.0f}")
        print(f"  최대 허용 예산: ${max_budget:,.0f} (150%)")
        print(f"  예산 사용률: {budget_usage:.1f}%")
        print(f"  예산 초과: {'예' if budget_exceeded else '아니오'}")
        
        # 예산 초과 시 조정 (150% 초과 시에만)
        if budget_exceeded:
            print("🔄 예산 초과로 주식 수 조정 중...")
            adjusted_recommendations = self._adjust_recommendations_for_budget(
                valid_recommendations, max_budget, risk_tolerance
            )
            return adjusted_recommendations
        else:
            return valid_recommendations

def main():
    st.set_page_config(
        page_title="AI 주식 추천 시스템",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("🤖 AI 주식 추천 시스템")
    st.markdown("Yahoo Finance 뉴스와 GPT-4o를 활용한 1개월 주식 추천 & 포트폴리오 관리")
    
    # 포트폴리오 매니저 초기화
    portfolio_manager = PortfolioManager()
    excel_reporter = ExcelReporter()
    
    # 사이드바 - 투자 설정
    with st.sidebar:
        st.header("💰 투자 설정")
        investment_amount = st.number_input(
            "투자 가능 금액 (USD)",
            min_value=100,
            max_value=1000000,
            value=10000,
            step=1000,
            help="투자할 수 있는 금액을 입력하세요"
        )
        
        st.markdown("---")
        st.header("🏢 섹터 선택")
        sectors = {
            'tech': '🖥️ 기술 (대/중/소형주)',
            'finance': '🏦 금융 (은행/투자/보험)',
            'healthcare': '🏥 헬스케어 (제약/바이오/의료기기)',
            'consumer': '🛒 소비재 (리테일/자동차/여행)',
            'industrial': '🏭 산업재 (제조/물류/건설)',
            'energy': '⚡ 에너지 (석유/가스/신재생)',
            'communication': '📡 통신 (미디어/방송/엔터)',
            'materials': '🏗️ 소재 (화학/광업/금속)',
            'utilities': '💡 유틸리티 (전력/가스/수도)',
            'reits': '🏢 REITs (부동산/인프라)'
        }
        
        selected_sectors = st.multiselect(
            "분석할 섹터 선택 (선택하지 않으면 전체 섹터)",
            options=list(sectors.keys()),
            format_func=lambda x: sectors[x],
            help="특정 섹터만 분석하려면 선택하세요"
        )
        
        st.markdown("---")
        st.header("⚖️ 리스크 설정")
        risk_tolerance = st.selectbox(
            "투자 스타일",
            ["보수적", "보통", "공격적"],
            help="투자 스타일에 따른 리스크 설정"
        )
        
        # 리스크 설정 설명
        if risk_tolerance == "보수적":
            st.info("🔒 보수적: 안전한 투자, 낮은 위험, 적당한 수익")
        elif risk_tolerance == "보통":
            st.info("⚖️ 보통: 균형잡힌 투자, 중간 위험, 중간 수익")
        else:
            st.info("🚀 공격적: 적극적 투자, 높은 위험, 높은 수익")
        
        st.markdown("---")
        st.markdown("### 📊 분석 기준")
        st.markdown("- Yahoo Finance 최신 뉴스")
        st.markdown("- GPT-4o AI 분석")
        st.markdown("- 기술적 지표 (RSI, 이동평균)")
        st.markdown("- 1개월 상승 가능성")
        
        st.markdown("---")
        st.markdown("### 📰 강화된 뉴스 분석")
        st.markdown("- **주식별 뉴스:** 6개 (다중 소스 수집)")
        st.markdown("- **섹터별 뉴스:** 6개 (섹터 트렌드 + 주요 기업)")
        st.markdown("- **경제/시장 뉴스:** 6개 (Fed, 인플레이션, GDP 등)")
        st.markdown("- **글로벌 경제:** 6개 (중국, 유럽, 지정학적 위험)")
        st.markdown("- **기술 트렌드:** 6개 (AI, 클라우드, 반도체 등)")
        st.markdown("- **총 30개 뉴스** 기반 종합 분석")
        st.markdown("- **🔥 뉴스 우선순위:** 자주 언급되는 주식 우선 분석")
        
        st.markdown("---")
        st.markdown("### 💰 예산 기반 정확한 계산")
        st.markdown("- **거래 수수료 고려:** 매수/매도 각각 $10 포함")
        st.markdown("- **리스크별 할당:** 보수적 15%, 보통 20%, 공격적 25%")
        st.markdown("- **예산 검증:** 총 투자비가 예산을 초과하지 않도록 조정")
        st.markdown("- **정확한 주식 수:** 소수점 버림으로 실제 구매 가능한 수량")
        st.markdown("- **예산 사용률:** 실시간으로 예산 사용 현황 표시")
        st.markdown("- **150% 허용:** 예산을 최대 150%까지 사용 가능")
        st.markdown("- **TLS 우회:** curl_cffi를 통한 Rate limit 문제 해결")
        
        st.markdown("---")
        st.markdown("### 🎯 스마트 추천 시스템")
        st.markdown("- **🥇 1순위:** 뉴스 우선순위 + 30주 이상 구매 + 유망한 주식")
        st.markdown("- **🥈 2순위:** 뉴스 우선순위 + 20주 이상 구매 + 유망한 주식")
        st.markdown("- **🥉 3순위:** 뉴스 최다 언급 주식 (구매 가능 주식 수 관계없이)")
        st.markdown("- **📊 4순위:** 일반 유망 주식")
        st.markdown("- **확장된 후보:** 240개+ 주식 (대/중/소형주 포함)")
        st.markdown("- **보너스 점수:** 뉴스 우선순위 +15점, 구매가능 +15점, 티어 +20점")
        st.markdown("- **다양한 섹터:** 기존 7개 → 10개 섹터 (REITs, 소재, 유틸리티)")
        st.markdown("- **2개 주식 추천:** 베스트 2개 주식만 선별하여 추천")
        
        st.markdown("---")
        st.markdown("### 📈 엑셀 리포트")
        excel_summary = excel_reporter.get_excel_summary()
        if "status" not in excel_summary:
            st.markdown(f"**파일:** {excel_summary['파일명']}")
            st.markdown(f"**수정일:** {excel_summary['수정일']}")
            st.markdown(f"**시트 수:** {excel_summary['시트 수']}개")
            
            if st.button("📊 엑셀 파일 열기"):
                import subprocess
                try:
                    subprocess.run(['start', excel_reporter.excel_file], shell=True)
                    st.success("엑셀 파일이 열렸습니다!")
                except:
                    st.error("엑셀 파일을 열 수 없습니다. 수동으로 열어주세요.")
        else:
            st.markdown("엑셀 파일이 아직 생성되지 않았습니다.")
    
    # 현재 포트폴리오 상태 표시
    portfolio = portfolio_manager.load_portfolio()
    
    if portfolio['current_stocks']:
        st.header("📊 현재 포트폴리오 상태")
        
        # 포트폴리오 성과 계산
        performance = portfolio_manager.get_performance_summary(portfolio)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "포트폴리오 가치",
                f"${performance['portfolio_value']:,.0f}",
                f"{performance['total_return_pct']:.2f}%"
            )
        
        with col2:
            st.metric(
                "총 수익",
                f"${performance['total_return_amount']:,.0f}",
                f"{performance['total_return_pct']:.2f}%"
            )
        
        with col3:
            if performance['best_performer']:
                st.metric(
                    "최고 성과",
                    performance['best_performer']['symbol'],
                    f"{performance['best_performer']['return_pct']:.2f}%"
                )
        
        with col4:
            if performance['worst_performer']:
                st.metric(
                    "최저 성과",
                    performance['worst_performer']['symbol'],
                    f"{performance['worst_performer']['return_pct']:.2f}%"
                )
        
        # 현재 보유 주식 목록
        st.subheader("📋 보유 주식 목록")
        updated_portfolio = portfolio_manager.calculate_portfolio_performance(portfolio)
        
        for stock in updated_portfolio['current_stocks']:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.write(f"**{stock['symbol']}** - {stock['name']}")
                st.write(f"수량: {stock['quantity']}주")
            
            with col2:
                st.write(f"매수가: ${stock['purchase_price']:.2f}")
                st.write(f"현재가: ${stock['current_price']:.2f}")
            
            with col3:
                st.write(f"수익률: {stock['return_pct']:.2f}%")
                st.write(f"수익금: ${stock['return_amount']:,.0f}")
            
            with col4:
                st.write(f"현재 가치: ${stock['current_value']:,.0f}")
        
        st.markdown("---")
    
    # 메인 컨텐츠
    if st.button("🚀 뉴스 기반 스마트 주식 추천", type="primary"):
        # 새로운 시스템 정보 표시
        st.info("🔥 NEW: 뉴스 우선순위 + 30주 이상 구매 가능 주식 중심 추천!")
        
        # 진행 상황 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("뉴스 분석 기반 스마트 주식 추천을 진행합니다..."):
            recommender = StockRecommender()
            
            # 진행 상황 업데이트
            status_text.text("🔍 30개 뉴스 소스에서 우선순위 주식 탐지 중...")
            progress_bar.progress(10)
            
            status_text.text("📊 240개+ 주식 후보에서 조건 맞는 주식 필터링 중...")
            progress_bar.progress(30)
            
            status_text.text("🎯 뉴스 우선순위 + 30주 구매 가능 주식 분석 중...")
            progress_bar.progress(60)
            
            recommendations = recommender.get_top_stocks(investment_amount, selected_sectors, force_refresh=True)
            
            progress_bar.progress(90)
            status_text.text("🏆 최종 추천 결과 준비 중...")
        
        progress_bar.progress(100)
        status_text.text("✅ 뉴스 기반 스마트 추천 완료!")
        
        if recommendations:
            # 추천 히스토리 저장
            portfolio_manager.save_recommendation_history(recommendations)
            
            st.success(f"🎯 투자 금액 ${investment_amount:,.0f}에 맞는 뉴스 기반 스마트 추천 완료!")
            
            # 추천 통계 표시
            col1, col2, col3, col4 = st.columns(4)
            
            news_priority_count = sum(1 for rec in recommendations if rec.get('is_news_priority', False))
            tier1_count = sum(1 for rec in recommendations if rec.get('shares_affordable', 0) >= 30 and rec.get('is_news_priority', False))
            tier2_count = sum(1 for rec in recommendations if 20 <= rec.get('shares_affordable', 0) < 30 and rec.get('is_news_priority', False))
            avg_score = sum(rec['score_info']['total_score'] for rec in recommendations) / len(recommendations)
            
            with col1:
                st.metric("1순위 (뉴스+30주)", f"{tier1_count}/{len(recommendations)}개", "🥇")
            with col2:
                st.metric("2순위 (뉴스+20주)", f"{tier2_count}/{len(recommendations)}개", "🥈")
            with col3:
                st.metric("뉴스 우선순위", f"{news_priority_count}/{len(recommendations)}개", "⭐")
            with col4:
                st.metric("평균 점수", f"{avg_score:.1f}/100", "📊")
            
            # 이전 세션과 비교 분석
            st.markdown("## 📈 이전 세션 대비 수익률 비교")
            previous_recommendations = portfolio_manager.get_previous_session_recommendations()
            
            if previous_recommendations:
                comparison_data = []
                for current_rec in recommendations:
                    symbol = current_rec['stock_info']['symbol']
                    current_score = current_rec['score_info']['total_score']
                    
                    # 이전 세션에서 같은 주식 찾기
                    previous_rec = None
                    for prev_rec in previous_recommendations:
                        if prev_rec['stock_info']['symbol'] == symbol:
                            previous_rec = prev_rec
                            break
                    
                    if previous_rec:
                        previous_score = previous_rec['score_info']['total_score']
                        score_change = current_score - previous_score
                        comparison_data.append({
                            'symbol': symbol,
                            'current_score': current_score,
                            'previous_score': previous_score,
                            'score_change': score_change,
                            'improvement': score_change > 0
                        })
                
                if comparison_data:
                    # 개선된 주식들 표시
                    improved_stocks = [data for data in comparison_data if data['improvement']]
                    if improved_stocks:
                        st.success(f"🚀 {len(improved_stocks)}개 주식이 이전 세션 대비 개선되었습니다!")
                        
                        for data in improved_stocks:
                            st.markdown(f"**{data['symbol']}**: {data['previous_score']} → {data['current_score']} (+{data['score_change']})")
                    
                    # 악화된 주식들 표시
                    worsened_stocks = [data for data in comparison_data if not data['improvement']]
                    if worsened_stocks:
                        st.warning(f"⚠️ {len(worsened_stocks)}개 주식이 이전 세션 대비 악화되었습니다.")
                        
                        for data in worsened_stocks:
                            st.markdown(f"**{data['symbol']}**: {data['previous_score']} → {data['current_score']} ({data['score_change']})")
                else:
                    st.info("이전 세션과 중복되는 주식이 없습니다.")
            else:
                st.info("이전 세션 데이터가 없습니다. 이번이 첫 번째 세션입니다.")
            
            # 포트폴리오 리밸런싱 분석
            should_rebalance, stocks_to_sell, stocks_to_buy = portfolio_manager.should_rebalance_portfolio(
                recommendations, portfolio
            )
            
            if should_rebalance:
                st.warning("🔄 포트폴리오 리밸런싱이 권장됩니다!")
                
                # 리밸런싱 계획 생성
                rebalancing_plan = portfolio_manager.create_rebalancing_plan(
                    stocks_to_sell, stocks_to_buy, portfolio
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📤 매도 권장")
                    if rebalancing_plan['stocks_to_sell']:
                        for stock in rebalancing_plan['stocks_to_sell']:
                            st.write(f"**{stock['symbol']}** - {stock['name']}")
                            st.write(f"수익률: {stock['return_pct']:.2f}%")
                            st.write(f"매도 가치: ${stock['current_value']:,.0f}")
                    else:
                        st.write("매도할 주식 없음")
                
                with col2:
                    st.subheader("📥 매수 권장")
                    if rebalancing_plan['stocks_to_buy']:
                        for stock in rebalancing_plan['stocks_to_buy']:
                            st.write(f"**{stock['symbol']}** - {stock['name']}")
                            st.write(f"예상 수익률: {stock['expected_return']:.1f}%")
                            st.write(f"매수 수량: {stock['quantity']}주")
                            st.write(f"매수 금액: ${stock['total_cost']:,.0f}")
                    else:
                        st.write("매수할 주식 없음")
                
                # 리밸런싱 실행 버튼
                if st.button("✅ 리밸런싱 실행", type="secondary"):
                    # 포트폴리오 업데이트
                    updated_portfolio = portfolio_manager.update_portfolio_after_rebalancing(
                        portfolio, rebalancing_plan
                    )
                    updated_portfolio['total_investment'] = investment_amount
                    
                    # 포트폴리오 저장
                    portfolio_manager.save_portfolio(updated_portfolio)
                    
                    st.success("포트폴리오가 성공적으로 업데이트되었습니다!")
                    st.rerun()
            
            # 엑셀 리포트 생성
            with st.spinner("엑셀 리포트를 생성하고 있습니다..."):
                try:
                    print("📊 엑셀 리포트 생성 시작...")
                    
                    # 포트폴리오 성과 계산
                    updated_portfolio = portfolio_manager.calculate_portfolio_performance(portfolio)
                    print(f"📈 포트폴리오 성과 계산 완료: {len(updated_portfolio.get('current_stocks', []))}개 주식")
                    
                    # 엑셀 리포트 생성
                    excel_reporter.create_excel_report(updated_portfolio, recommendations)
                    
                    # 엑셀 파일 상태 확인
                    excel_summary = excel_reporter.get_excel_summary()
                    if "status" not in excel_summary:
                        st.success(f"📊 엑셀 리포트가 성공적으로 생성되었습니다!")
                        st.info(f"📁 파일 위치: {excel_reporter.excel_file}")
                        st.info(f"📅 생성 시간: {excel_summary['수정일']}")
                        st.info(f"📋 시트 수: {excel_summary['시트 수']}개")
                    else:
                        st.warning(f"⚠️ 엑셀 파일 상태: {excel_summary['status']}")
                        
                except Exception as e:
                    st.error(f"❌ 엑셀 리포트 생성 실패: {e}")
                    print(f"엑셀 리포트 생성 오류: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 상위 2개 주식 표시 (감소)
            top_recommendations = recommendations[:2]
            
            # 거래 전략 계산
            trading_strategies = []
            for rec in top_recommendations:
                strategy = recommender.calculate_trading_strategy_for_recommendation(
                    rec['stock_info'], investment_amount, risk_tolerance
                )
                trading_strategies.append(strategy)
            
            # 🎯 예산 검증 및 조정
            validated_recommendations = recommender.validate_and_adjust_budget(
                top_recommendations, investment_amount, risk_tolerance
            )
            
            if not validated_recommendations:
                st.error("❌ 예산에 맞는 주식을 찾을 수 없습니다. 투자 금액을 늘리거나 리스크 설정을 조정해보세요.")
                return
            
            # 예산 사용률 표시
            total_used = sum(rec['trading_strategy']['total_cost'] for rec in validated_recommendations)
            budget_usage = (total_used / investment_amount) * 100
            
            st.success(f"✅ 예산 검증 완료! 총 ${total_used:,.0f} 사용 ({budget_usage:.1f}%)")
            
            # 검증된 추천 주식들로 표시
            for i, rec in enumerate(validated_recommendations, 1):
                with st.container():
                    st.markdown(f"## 🏆 추천 주식 #{i}")
                    
                    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                    
                    with col1:
                        stock_info = rec['stock_info']
                        score_info = rec['score_info']
                        
                        # 특별 표시 (뉴스 우선순위 또는 30주+ 구매 가능)
                        special_flags = []
                        tier_info = ""
                        
                        # 티어별 표시
                        base_potential_score = score_info.get('base_potential_score', 0)
                        if rec.get('is_news_priority', False) and rec.get('shares_affordable', 0) >= 30 and base_potential_score >= 70:
                            special_flags.append("🥇 1순위")
                            tier_info = "뉴스+30주+유망"
                        elif rec.get('is_news_priority', False) and rec.get('shares_affordable', 0) >= 20 and base_potential_score >= 70:
                            special_flags.append("🥈 2순위")
                            tier_info = "뉴스+20주+유망"
                        elif rec.get('is_news_priority', False) and base_potential_score >= 60:
                            special_flags.append("🥉 3순위")
                            tier_info = "뉴스최다언급"
                        elif base_potential_score >= 65:
                            special_flags.append("📊 4순위")
                            tier_info = "일반유망"
                        
                        if rec.get('is_news_priority', False):
                            special_flags.append("⭐ 뉴스우선")
                        if rec.get('is_keyword_stock', False):
                            special_flags.append("🤖 GPT키워드")
                        if rec.get('shares_affordable', 0) >= 30:
                            special_flags.append("💰 30주+")
                        elif rec.get('shares_affordable', 0) >= 20:
                            special_flags.append("💰 20주+")
                        
                        flag_text = " | ".join(special_flags) if special_flags else ""
                        
                        st.metric(
                            label=f"{stock_info['symbol']} - {stock_info['name'][:20]}",
                            value=f"${stock_info['current_price']:.2f}",
                            delta=f"점수: {score_info['total_score']}/100"
                        )
                        
                        if flag_text:
                            st.markdown(f"**🏷️ {flag_text}**")
                        if tier_info:
                            st.markdown(f"**🎯 {tier_info}**")
                        
                        # 키워드 분석 정보 표시
                        if rec.get('is_keyword_stock', False) and rec.get('keyword_info'):
                            st.markdown(f"**🤖 GPT 키워드 분석:** {rec['keyword_info']}")
                        
                        st.markdown(f"**섹터:** {stock_info['sector']}")
                        st.markdown(f"**시가총액:** ${stock_info['market_cap']:,.0f}")
                        st.markdown(f"**거래량:** {stock_info['volume']:,.0f}")
                        st.markdown(f"**구매 가능:** {rec.get('shares_affordable', 0)}주")
                    
                    with col2:
                        st.markdown("### 📊 기술적 지표")
                        st.markdown(f"**RSI:** {score_info['rsi']:.1f}")
                        st.markdown(f"**이동평균 추세:** {score_info['ma_trend']}")
                        st.markdown(f"**P/E 비율:** {stock_info['pe_ratio']:.2f}")
                        st.markdown(f"**베타:** {stock_info['beta']:.2f}")
                    
                    with col3:
                        st.markdown("### 📰 강화된 뉴스 분석")
                        
                        # 뉴스를 카테고리별로 분류
                        news_by_category = {
                            'stock_specific': [],
                            'sector': [],
                            'market': [],
                            'global': [],
                            'tech_trend': []
                        }
                        
                        for news in rec['news_items']:
                            category = news.get('category', 'stock_specific')
                            if category in news_by_category:
                                news_by_category[category].append(news)
                        
                        st.markdown(f"**📊 총 뉴스 수:** {rec['news_count']}개 (목표: 30개)")
                        st.markdown(f"**📈 주식별:** {len(news_by_category['stock_specific'])}개")
                        st.markdown(f"**🏢 섹터별:** {len(news_by_category['sector'])}개")
                        st.markdown(f"**💼 시장/경제:** {len(news_by_category['market'])}개")
                        st.markdown(f"**🌍 글로벌:** {len(news_by_category['global'])}개")
                        st.markdown(f"**🔬 기술:** {len(news_by_category['tech_trend'])}개")
                        
                        # 언급된 다른 주식들 표시
                        mentioned_stocks = rec.get('mentioned_stocks', [])
                        if mentioned_stocks:
                            st.markdown(f"**🔗 연관 주식:** {', '.join(mentioned_stocks[:5])}")
                        
                        # 점수 세부 정보
                        st.markdown("---")
                        st.markdown(f"**📊 기본 점수:** {score_info.get('base_score', 50)}/50")
                        st.markdown(f"**📈 기술 점수:** {score_info['technical_score']}/30")
                        st.markdown(f"**📰 뉴스 점수:** {score_info['news_score']}/20")
                        
                        # 보너스 점수
                        if score_info.get('priority_bonus', 0) > 0:
                            st.markdown(f"**⭐ 뉴스 보너스:** +{score_info['priority_bonus']}")
                        if score_info.get('keyword_bonus', 0) > 0:
                            st.markdown(f"**🤖 키워드 보너스:** +{score_info['keyword_bonus']}")
                        if score_info.get('affordability_bonus', 0) > 0:
                            st.markdown(f"**💰 구매가능 보너스:** +{score_info['affordability_bonus']}")
                        if score_info.get('tier_bonus', 0) > 0:
                            st.markdown(f"**🎯 티어 보너스:** +{score_info['tier_bonus']}")
                        
                        # 유망성 점수
                        base_potential = score_info.get('base_potential_score', 0)
                        st.markdown(f"**🔍 유망성 점수:** {base_potential}/100")
                    
                    with col4:
                        st.markdown("### 💰 거래 전략")
                        strategy = rec['trading_strategy']
                        if strategy and 'error' not in strategy:
                            st.metric("매수 수량", f"{strategy['shares']}주")
                            st.metric("주식 비용", f"${strategy['investment_amount']:,.0f}")
                            st.metric("총 비용", f"${strategy['total_cost']:,.0f}")
                            st.metric("예산 사용률", f"{strategy['budget_usage']:.1f}%")
                            
                            st.markdown(f"**손절가:** ${strategy['stop_loss_price']:.2f}")
                            st.markdown(f"**목표가:** ${strategy['take_profit_price']:.2f}")
                            st.markdown(f"**예상 수익:** ${strategy['potential_profit']:,.0f}")
                            st.markdown(f"**최대 손실:** ${strategy['potential_loss']:,.0f}")
                            st.markdown(f"**R/R 비율:** {strategy['risk_reward_ratio']:.2f}")
                        else:
                            st.error("거래 전략 계산 불가")
                    
                    # 🆕 뉴스 기반 상세 매수 이유 표시
                    st.markdown("### 📰 뉴스 기반 매수 이유")
                    buy_reasons = recommender.get_detailed_buy_reasons(rec)
                    
                    if buy_reasons:
                        # 카테고리별로 그룹화하여 표시
                        reasons_by_category = {}
                        for reason in buy_reasons:
                            category = reason['category']
                            if category not in reasons_by_category:
                                reasons_by_category[category] = []
                            reasons_by_category[category].append(reason)
                        
                        # 카테고리별로 표시
                        for category, reasons in reasons_by_category.items():
                            st.markdown(f"**🔍 {category}:**")
                            for reason in reasons:
                                # 영향도에 따른 색상 표시
                                impact_color = "🟢" if reason['impact'] == '긍정적' else "🟡" if reason['impact'] == '중립적' else "🔴"
                                confidence_icon = "🔴" if reason['confidence'] == '높음' else "🟡" if reason['confidence'] == '중간' else "🟢"
                                
                                st.markdown(f"{impact_color} {reason['reason']}")
                                
                                # 상세 내용 표시 (접을 수 있는 형태)
                                with st.expander(f"📄 상세 뉴스 내용 보기"):
                                    st.markdown(f"**제목:** {reason.get('news_source', 'Market Analysis')}")
                                    st.markdown(f"**내용:** {reason.get('full_content', '상세 내용 없음')}")
                                    st.markdown(f"**신뢰도:** {confidence_icon} {reason['confidence']}")
                                    
                                    # URL 링크 추가 (매수 이유에 해당하는 뉴스의 URL)
                                    news_url = reason.get('url', '')
                                    if news_url and news_url != '':
                                        st.markdown(f"**🔗 [원문 기사 읽기]({news_url})**")
                                        st.markdown(f"*위 링크를 클릭하면 실제 기사를 확인할 수 있습니다.*")
                                    else:
                                        st.markdown("**🔗 원문 링크:** 제공되지 않음 (생성된 뉴스)")
                    else:
                        st.info("뉴스 기반 매수 이유를 분석 중입니다...")
                    
                    # 🆕 상세 뉴스 내용 표시
                    st.markdown("### 📰 주요 뉴스 상세 내용")
                    
                    # 카테고리별로 주요 뉴스 표시
                    for category, news_list in news_by_category.items():
                        if news_list:
                            category_name = recommender._get_category_display_name(category)
                            st.markdown(f"**{category_name} 뉴스:**")
                            
                            for j, news in enumerate(news_list[:2]):  # 카테고리당 최대 2개
                                with st.expander(f"📰 {news.get('title', '제목 없음')}"):
                                    st.markdown(f"**제목:** {news.get('title', '제목 없음')}")
                                    st.markdown(f"**내용:** {news.get('content', '내용 없음')}")
                                    st.markdown(f"**출처:** {news.get('source', 'Market Analysis')}")
                                    st.markdown(f"**영향도:** {news.get('impact', '중립적')}")
                                    st.markdown(f"**신뢰도:** {news.get('confidence', '중간')}")
                                    
                                    # 날짜 정보 표시
                                    if news.get('date'):
                                        st.markdown(f"**날짜:** {news.get('date')}")
                                    
                                    # URL 링크 추가
                                    news_url = news.get('url', '')
                                    if news_url and news_url != '':
                                        st.markdown(f"**🔗 [원문 기사 읽기]({news_url})**")
                                        st.markdown(f"*위 링크를 클릭하면 실제 기사를 확인할 수 있습니다.*")
                                    else:
                                        st.markdown("**🔗 원문 링크:** 제공되지 않음 (생성된 뉴스)")
                                    
                                    # 언급된 주식들
                                    mentioned = news.get('mentioned_stocks', [])
                                    if mentioned:
                                        st.markdown(f"**언급된 주식:** {', '.join(mentioned)}")
                    
                    # AI 분석 결과
                    st.markdown("### 📋 AI 분석 결과")
                    st.text_area(
                        f"{stock_info['symbol']} 상세 분석",
                        value=rec['analysis'],
                        height=300,
                        key=f"analysis_{i}"
                    )
                    
                    # 거래 전략 상세 정보
                    if strategy and 'error' not in strategy:
                        st.markdown("### 🎯 구체적 거래 전략")
                        
                        col_strat1, col_strat2 = st.columns(2)
                        
                        with col_strat1:
                            st.markdown("**📈 매수 전략:**")
                            st.markdown(f"- **매수 가격:** ${strategy['current_price']:.2f}")
                            st.markdown(f"- **매수 수량:** {strategy['shares']}주")
                            st.markdown(f"- **주식 비용:** ${strategy['investment_amount']:,.0f}")
                            st.markdown(f"- **거래 수수료:** ${strategy['commission']}")
                            st.markdown(f"- **총 투자비:** ${strategy['total_cost']:,.0f}")
                            st.markdown(f"- **예산 사용률:** {strategy['budget_usage']:.1f}%")
                        
                        with col_strat2:
                            st.markdown("**📉 매도 전략:**")
                            st.markdown(f"- **손절가:** ${strategy['stop_loss_price']:.2f} ({(1-strategy['settings']['stop_loss'])*100:.0f}%)")
                            st.markdown(f"- **목표가:** ${strategy['take_profit_price']:.2f} ({(1+strategy['settings']['take_profit'])*100:.0f}%)")
                            st.markdown(f"- **예상 수익:** ${strategy['potential_profit']:,.0f}")
                            st.markdown(f"- **리스크/리워드:** {strategy['risk_reward_ratio']:.2f}")
                            st.markdown(f"- **최대 손실:** ${strategy['potential_loss']:,.0f}")
                    
                    # 가격 차트
                    if not stock_info['price_history'].empty:
                        fig = go.Figure()
                        
                        # 종가
                        fig.add_trace(go.Scatter(
                            x=stock_info['price_history'].index,
                            y=stock_info['price_history']['Close'],
                            mode='lines',
                            name='종가',
                            line=dict(color='blue', width=2)
                        ))
                        
                        # 이동평균
                        if 'MA20' in stock_info['price_history'].columns:
                            fig.add_trace(go.Scatter(
                                x=stock_info['price_history'].index,
                                y=stock_info['price_history']['MA20'],
                                mode='lines',
                                name='20일 이동평균',
                                line=dict(color='orange', width=1)
                            ))
                        
                        if 'MA50' in stock_info['price_history'].columns:
                            fig.add_trace(go.Scatter(
                                x=stock_info['price_history'].index,
                                y=stock_info['price_history']['MA50'],
                                mode='lines',
                                name='50일 이동평균',
                                line=dict(color='red', width=1)
                            ))
                        
                        fig.update_layout(
                            title=f"{stock_info['symbol']} 60일 가격 추이",
                            xaxis_title="날짜",
                            yaxis_title="가격 (USD)",
                            height=400,
                            hovermode='x unified'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("---")
            
            # 전체 투자 요약
            if validated_recommendations:
                st.markdown("## 📊 전체 투자 요약")
                
                total_stock_cost = sum(rec['trading_strategy']['investment_amount'] for rec in validated_recommendations)
                total_commission = sum(rec['trading_strategy']['commission'] for rec in validated_recommendations)
                total_investment = sum(rec['trading_strategy']['total_cost'] for rec in validated_recommendations)
                total_potential_profit = sum(rec['trading_strategy']['potential_profit'] for rec in validated_recommendations)
                total_potential_loss = sum(rec['trading_strategy']['potential_loss'] for rec in validated_recommendations)
                total_shares = sum(rec['trading_strategy']['shares'] for rec in validated_recommendations)
                
                col_budget1, col_budget2 = st.columns(2)
                
                with col_budget1:
                    st.markdown("**💰 예산 사용 현황:**")
                    st.markdown(f"- **사용된 예산:** ${total_investment:,.0f}")
                    st.markdown(f"- **남은 예산:** ${investment_amount - total_investment:,.0f}")
                    st.markdown(f"- **사용률:** {budget_usage:.1f}%")
                    st.markdown(f"- **최대 허용:** 150% (${investment_amount * 1.5:,.0f})")
                    
                    if budget_usage > 150:
                        st.error("❌ 예산을 150% 초과했습니다!")
                    elif budget_usage > 100:
                        st.warning("⚠️ 예산을 초과했지만 150% 이내입니다.")
                    elif budget_usage > 90:
                        st.info("ℹ️ 예산을 거의 다 사용했습니다.")
                    else:
                        st.success("✅ 예산 내에서 투자 가능합니다.")
                
                with col_budget2:
                    st.markdown("**📈 수익성 분석:**")
                    st.markdown(f"- **총 예상 수익:** ${total_potential_profit:,.0f}")
                    st.markdown(f"- **총 최대 손실:** ${total_potential_loss:,.0f}")
                    if total_potential_loss > 0:
                        overall_rr = total_potential_profit / total_potential_loss
                        st.markdown(f"- **전체 R/R 비율:** {overall_rr:.2f}")
                    
                    # 수익률 계산
                    if total_investment > 0:
                        potential_return_pct = (total_potential_profit / total_investment) * 100
                        st.markdown(f"- **예상 수익률:** {potential_return_pct:.1f}%")
                
                # 투자 분배 차트
                st.markdown("### 📈 투자 분배")
                
                # 티어별 분류
                tier1_stocks = []
                tier2_stocks = []
                tier3_stocks = []
                tier4_stocks = []
                
                for rec in validated_recommendations:
                    symbol = rec['stock_info']['symbol']
                    amount = rec['trading_strategy']['total_cost']
                    shares = rec['trading_strategy']['shares']
                    
                    # 티어 분류
                    base_potential_score = rec['score_info'].get('base_potential_score', 0)
                    shares_affordable = rec.get('shares_affordable', 0)
                    is_news_priority = rec.get('is_news_priority', False)
                    
                    stock_data = {
                        'symbol': symbol,
                        'amount': amount,
                        'shares': shares,
                        'tier': 0
                    }
                    
                    if is_news_priority and shares_affordable >= 30 and base_potential_score >= 70:
                        stock_data['tier'] = 1
                        tier1_stocks.append(stock_data)
                    elif is_news_priority and shares_affordable >= 20 and base_potential_score >= 70:
                        stock_data['tier'] = 2
                        tier2_stocks.append(stock_data)
                    elif is_news_priority and base_potential_score >= 60:
                        stock_data['tier'] = 3
                        tier3_stocks.append(stock_data)
                    elif base_potential_score >= 65:
                        stock_data['tier'] = 4
                        tier4_stocks.append(stock_data)
                
                col_invest1, col_invest2 = st.columns(2)
                
                with col_invest1:
                    st.markdown("**💰 투자금 분배:**")
                    
                    if tier1_stocks:
                        st.markdown("🥇 **1순위 (뉴스+30주+유망):**")
                        for stock in tier1_stocks:
                            percentage = (stock['amount'] / total_investment) * 100
                            st.markdown(f"- **{stock['symbol']}:** ${stock['amount']:,.0f} ({percentage:.1f}%)")
                    
                    if tier2_stocks:
                        st.markdown("🥈 **2순위 (뉴스+20주+유망):**")
                        for stock in tier2_stocks:
                            percentage = (stock['amount'] / total_investment) * 100
                            st.markdown(f"- **{stock['symbol']}:** ${stock['amount']:,.0f} ({percentage:.1f}%)")
                    
                    if tier3_stocks:
                        st.markdown("🥉 **3순위 (뉴스최다언급):**")
                        for stock in tier3_stocks:
                            percentage = (stock['amount'] / total_investment) * 100
                            st.markdown(f"- **{stock['symbol']}:** ${stock['amount']:,.0f} ({percentage:.1f}%)")
                    
                    if tier4_stocks:
                        st.markdown("📊 **4순위 (일반유망):**")
                        for stock in tier4_stocks:
                            percentage = (stock['amount'] / total_investment) * 100
                            st.markdown(f"- **{stock['symbol']}:** ${stock['amount']:,.0f} ({percentage:.1f}%)")
                
                with col_invest2:
                    st.markdown("**📊 매수 수량 및 특징:**")
                    all_stocks = tier1_stocks + tier2_stocks + tier3_stocks + tier4_stocks
                    for stock in all_stocks:
                        tier_icon = "🥇" if stock['tier'] == 1 else "🥈" if stock['tier'] == 2 else "🥉" if stock['tier'] == 3 else "📊"
                        st.markdown(f"- **{stock['symbol']}:** {stock['shares']}주 {tier_icon}")
                
                # 뉴스 기반 리스크 관리 팁
                st.markdown("### ⚠️ 뉴스 기반 리스크 관리")
                st.markdown(f"- **투자 스타일:** {risk_tolerance}")
                st.markdown(f"- **4단계 우선순위:** 뉴스+구매가능+유망성 기반 위험 분산")
                st.markdown(f"- **뉴스 모니터링:** 추천 주식 관련 뉴스 지속 추적")
                st.markdown(f"- **구매 가능 주식:** 30주+ 우선, 20주+ 차선으로 충분한 수량 확보")
                st.markdown(f"- **손절/목표가:** 각 주식별 설정값 준수")
                st.markdown(f"- **연관 주식 추적:** 뉴스에서 함께 언급되는 주식들 모니터링")

        else:
            st.error("추천할 수 있는 주식을 찾을 수 없습니다. 투자 금액이나 섹터 선택을 조정해보세요.")
    
    # 추천 히스토리 표시
    history = portfolio_manager.load_recommendation_history()
    if history:
        st.header("📈 추천 히스토리")
        
        # 최근 5일간의 추천 표시
        recent_history = history[-5:]
        
        for entry in recent_history:
            date = datetime.fromisoformat(entry['date']).strftime('%Y-%m-%d')
            st.subheader(f"📅 {date}")
            
            for rec in entry['recommendations'][:2]:  # 상위 2개만 표시
                symbol = rec['stock_info']['symbol']
                name = rec['stock_info']['name']
                score = rec['score_info']['total_score']
                price = rec['stock_info']['current_price']
                
                st.write(f"**{symbol}** - {name} (점수: {score}/100, 가격: ${price:.2f})")
    
    # 하단 정보
    st.markdown("---")
    st.markdown("### ℹ️ 주의사항")
    st.markdown("- 이 추천은 AI 분석 결과이며, 투자 결정은 본인의 판단에 따라야 합니다.")
    st.markdown("- 과거 성과가 미래 수익을 보장하지 않습니다.")
    st.markdown("- 투자 전 충분한 리서치를 진행하시기 바랍니다.")
    st.markdown("- 분산 투자를 통해 위험을 관리하세요.")
    st.markdown("- 포트폴리오는 자동으로 관리되며, 매일 실행하여 최적의 수익을 추구합니다.")
    st.markdown("- 엑셀 리포트는 매일 자동으로 업데이트되어 한 달간의 수익을 추적합니다.")

if __name__ == "__main__":
    import streamlit as st
    from enhanced_news_collector import EnhancedNewsCollector
    import plotly.graph_objects as go
    st.set_page_config(page_title="AI 주식 추천 시스템", page_icon="📈", layout="wide")
    st.title("🤖 AI 뉴스 기반 주식 추천 (심화 분석)")
    st.markdown("뉴스 기사 전체를 GPT-4o가 심화 분석하여, 실제로 기사 이슈와 직접적으로 연결된 미국 상장주 중 전망이 가장 좋은 2개만 추천합니다.")

    if st.button("🚀 뉴스 기반 심화 추천", type="primary"):
        st.info("분야별 10개 기사 심화 분석 → 관련 주식 15개 추출 → 데이터+뉴스 종합 평가 → 최종 2개 추천!")
        with st.spinner("뉴스 수집 및 GPT 심화 분석 중..."):
            collector = EnhancedNewsCollector()
            # 1. 분야별 10개 기사 수집
            news_data = collector.collect_comprehensive_news(
                categories=['business', 'technology', 'health', 'general', 'science'],
                max_articles_per_category=10, force_refresh=True
            )
            all_articles = []
            for news_list in news_data['news_by_category'].values():
                all_articles.extend(news_list[:10])
            # 2. 기사 전체를 GPT-4o로 심화 분석하여 관련 주식 15개 추출
            candidates = collector.extract_15_stocks_from_news(all_articles)
            if not candidates:
                st.error("뉴스에서 관련 주식을 추출하지 못했습니다. 다시 시도해 주세요.")
                st.stop()
            # 3. 15개 후보의 yfinance 데이터 수집
            symbols = [c['symbol'] for c in candidates]
            finance_data = collector.fetch_yahoo_finance_data(symbols)
            # 4. 후보, 데이터, 기사 전체를 GPT-4o로 종합 평가하여 최종 2개 종목 선정
            top2 = collector.select_top2_stocks(candidates, finance_data, all_articles)
        if top2:
            st.success(f"최종 추천 종목 2개")
            for stock in top2:
                symbol = stock['symbol']
                st.header(f"{symbol} 추천")
                st.markdown(f"**추천 사유:** {stock['final_reason']}")
                st.markdown("**관련 뉴스:**")
                for news in stock.get('related_news', [])[:3]:
                    st.markdown(f"- [{news['title']}]({news['url']}) - {news['summary']}")
                # 주가 차트
                hist = finance_data.get(symbol, {}).get('history')
                if hist is not None and not hist.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='종가'))
                    fig.update_layout(title=f"{symbol} 최근 60일 주가 차트", xaxis_title="날짜", yaxis_title="가격 (USD)", height=350)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("주가 차트 데이터를 불러올 수 없습니다.")
        else:
            st.error("최종 추천 종목을 선정하지 못했습니다. 다시 시도해 주세요.")
