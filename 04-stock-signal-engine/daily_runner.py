#!/usr/bin/env python3
"""
하루에 한 번씩 실행되는 자동 포트폴리오 관리 스크립트
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from stock_analyzer import StockAnalyzer, get_stock_candidates
from portfolio_manager import PortfolioManager
from excel_reporter import ExcelReporter
import openai
import yfinance

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_runner.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class DailyPortfolioManager:
    def __init__(self):
        load_dotenv()
        self.analyzer = StockAnalyzer()
        self.portfolio_manager = PortfolioManager()
        self.excel_reporter = ExcelReporter()
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # 설정값
        self.investment_amount = 10000  # 기본 투자 금액
        self.min_return_threshold = 2.0  # 리밸런싱 임계값
        
    def run_daily_analysis(self):
        """일일 분석 및 포트폴리오 관리 실행"""
        logging.info("🚀 일일 포트폴리오 분석 시작")
        
        try:
            # 현재 포트폴리오 로드
            portfolio = self.portfolio_manager.load_portfolio()
            logging.info(f"현재 포트폴리오 로드 완료: {len(portfolio['current_stocks'])}개 주식 보유")
            
            # 새로운 주식 추천 받기
            recommendations = self.get_daily_recommendations()
            
            if not recommendations:
                logging.warning("추천할 수 있는 주식이 없습니다.")
                return
            
            # 추천 히스토리 저장
            self.portfolio_manager.save_recommendation_history(recommendations)
            logging.info(f"추천 히스토리 저장 완료: {len(recommendations)}개 주식")
            
            # 포트폴리오 리밸런싱 분석
            should_rebalance, stocks_to_sell, stocks_to_buy = self.portfolio_manager.should_rebalance_portfolio(
                recommendations, portfolio, self.min_return_threshold
            )
            
            if should_rebalance:
                logging.info("🔄 포트폴리오 리밸런싱 필요")
                
                # 리밸런싱 계획 생성
                rebalancing_plan = self.portfolio_manager.create_rebalancing_plan(
                    stocks_to_sell, stocks_to_buy, portfolio
                )
                
                # 리밸런싱 실행
                self.execute_rebalancing(rebalancing_plan, portfolio)
                
                logging.info("✅ 포트폴리오 리밸런싱 완료")
            else:
                logging.info("📊 현재 포트폴리오 유지 (리밸런싱 불필요)")
            
            # 성과 리포트 생성
            self.generate_daily_report(portfolio)
            
            # 엑셀 리포트 생성
            self.generate_excel_report(portfolio, recommendations)
            
        except Exception as e:
            logging.error(f"일일 분석 중 오류 발생: {e}")
            raise
    
    def get_daily_recommendations(self):
        """일일 주식 추천 받기"""
        logging.info("📈 일일 주식 추천 분석 시작")
        
        # 모든 섹터의 주식 후보
        all_candidates = get_stock_candidates()
        stock_candidates = []
        for sector_stocks in all_candidates.values():
            stock_candidates.extend(sector_stocks)
        
        # 투자 금액에 맞는 주식 필터링
        suitable_stocks = self.analyzer.filter_stocks_by_investment(stock_candidates, self.investment_amount)
        
        recommendations = []
        
        for stock_info in suitable_stocks:
            logging.info(f"분석 중: {stock_info['symbol']}")
            
            try:
                # 뉴스 가져오기
                news_items = self.analyzer.get_yahoo_finance_news_enhanced(stock_info['symbol'])
                
                # 점수 계산
                score_info = self.analyzer.calculate_stock_score(stock_info, len(news_items))
                
                # GPT 분석 (간소화된 버전)
                analysis = self.get_quick_gpt_analysis(stock_info, news_items, score_info)
                
                recommendations.append({
                    'symbol': stock_info['symbol'],
                    'stock_info': stock_info,
                    'analysis': analysis,
                    'score_info': score_info,
                    'news_count': len(news_items)
                })
                
            except Exception as e:
                logging.error(f"주식 분석 오류 ({stock_info['symbol']}): {e}")
                continue
        
        # 점수순으로 정렬
        recommendations.sort(key=lambda x: x['score_info']['total_score'], reverse=True)
        logging.info(f"추천 분석 완료: {len(recommendations)}개 주식")
        
        return recommendations[:2]  # 상위 2개 반환
    
    def get_quick_gpt_analysis(self, stock_info, news_items, score_info):
        """빠른 GPT 분석 (API 비용 절약)"""
        try:
            # 뉴스 요약
            news_summary = ""
            for i, news in enumerate(news_items[:3], 1):
                news_summary += f"{i}. {news['title']}\n"
            
            prompt = f"""
            주식: {stock_info['symbol']} - {stock_info['name']}
            현재가: ${stock_info['current_price']:.2f}
            점수: {score_info['total_score']}/100
            RSI: {score_info['rsi']:.1f}
            
            최근 뉴스:
            {news_summary}
            
            이 주식의 1개월 예상 수익률을 간단히 분석해주세요. (한 문장으로)
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "주식 분석가입니다. 간결하게 답변해주세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"GPT 분석 오류: {e}")
            return "분석 중 오류 발생"
    
    def execute_rebalancing(self, rebalancing_plan, portfolio):
        """리밸런싱 실행"""
        logging.info("🔄 리밸런싱 실행 시작")
        
        # 매도할 주식들
        if rebalancing_plan['stocks_to_sell']:
            logging.info("📤 매도할 주식들:")
            for stock in rebalancing_plan['stocks_to_sell']:
                logging.info(f"  - {stock['symbol']}: {stock['return_pct']:.2f}% 수익률")
        
        # 매수할 주식들
        if rebalancing_plan['stocks_to_buy']:
            logging.info("📥 매수할 주식들:")
            for stock in rebalancing_plan['stocks_to_buy']:
                logging.info(f"  - {stock['symbol']}: {stock['quantity']}주, ${stock['total_cost']:,.0f}")
        
        # 포트폴리오 업데이트
        updated_portfolio = self.portfolio_manager.update_portfolio_after_rebalancing(
            portfolio, rebalancing_plan
        )
        updated_portfolio['total_investment'] = self.investment_amount
        
        # 포트폴리오 저장
        self.portfolio_manager.save_portfolio(updated_portfolio)
        logging.info("💾 포트폴리오 저장 완료")
    
    def generate_daily_report(self, portfolio):
        """일일 성과 리포트 생성"""
        logging.info("📊 일일 성과 리포트 생성")
        
        # 포트폴리오 성과 계산
        performance = self.portfolio_manager.get_performance_summary(portfolio)
        
        # 리포트 내용
        report = {
            'date': datetime.now().isoformat(),
            'portfolio_value': performance['portfolio_value'],
            'total_return_pct': performance['total_return_pct'],
            'total_return_amount': performance['total_return_amount'],
            'total_stocks': performance['total_stocks'],
            'best_performer': performance['best_performer'],
            'worst_performer': performance['worst_performer']
        }
        
        # 리포트 저장
        report_file = os.path.join(self.portfolio_manager.data_dir, f"daily_report_{datetime.now().strftime('%Y%m%d')}.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 로그에 성과 출력
        logging.info(f"📈 일일 성과 요약:")
        logging.info(f"  - 포트폴리오 가치: ${performance['portfolio_value']:,.0f}")
        logging.info(f"  - 총 수익률: {performance['total_return_pct']:.2f}%")
        logging.info(f"  - 총 수익: ${performance['total_return_amount']:,.0f}")
        
        if performance['best_performer']:
            logging.info(f"  - 최고 성과: {performance['best_performer']['symbol']} ({performance['best_performer']['return_pct']:.2f}%)")
        
        if performance['worst_performer']:
            logging.info(f"  - 최저 성과: {performance['worst_performer']['symbol']} ({performance['worst_performer']['return_pct']:.2f}%)")
    
    def generate_excel_report(self, portfolio, recommendations):
        """엑셀 리포트 생성"""
        logging.info("📊 엑셀 리포트 생성")
        
        try:
            # 포트폴리오 성과 계산
            updated_portfolio = self.portfolio_manager.calculate_portfolio_performance(portfolio)
            
            # 엑셀 리포트 생성
            self.excel_reporter.create_excel_report(updated_portfolio, recommendations)
            
            logging.info("✅ 엑셀 리포트 생성 완료")
            
        except Exception as e:
            logging.error(f"엑셀 리포트 생성 오류: {e}")
    
    def check_market_conditions(self):
        """시장 상황 체크"""
        logging.info("🌍 시장 상황 체크")
        
        # 주요 지수 체크 (S&P 500, NASDAQ)
        major_indices = ['^GSPC', '^IXIC']
        
        for index in major_indices:
            try:
                ticker = yfinance.Ticker(index)
                info = ticker.info
                current_price = info.get('regularMarketPrice', 0)
                
                if index == '^GSPC':
                    logging.info(f"S&P 500: ${current_price:,.2f}")
                elif index == '^IXIC':
                    logging.info(f"NASDAQ: ${current_price:,.2f}")
                    
            except Exception as e:
                logging.error(f"지수 조회 오류 ({index}): {e}")

def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🤖 AI 주식 추천 시스템 - 일일 자동 실행")
    print("=" * 60)
    
    try:
        # OpenAI API 키 확인
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key or api_key == 'your_openai_api_key_here':
            print("❌ OpenAI API 키가 설정되지 않았습니다.")
            print("   .env 파일에서 OPENAI_API_KEY를 설정해주세요.")
            return
        
        # 일일 매니저 실행
        manager = DailyPortfolioManager()
        
        # 시장 상황 체크
        manager.check_market_conditions()
        
        # 일일 분석 실행
        manager.run_daily_analysis()
        
        print("\n" + "=" * 60)
        print("✅ 일일 분석 완료!")
        print("   로그 파일: daily_runner.log")
        print("   포트폴리오 데이터: portfolio_data/")
        print("   엑셀 리포트: portfolio_data/portfolio_performance.xlsx")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 실행 중 오류 발생: {e}")
        logging.error(f"메인 실행 오류: {e}")
        return

if __name__ == "__main__":
    main() 