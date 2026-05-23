#!/usr/bin/env python3
"""
AI 주식 추천 시스템 테스트 스크립트
"""

import os
from dotenv import load_dotenv
from stock_analyzer import StockAnalyzer, get_stock_candidates
from portfolio_manager import PortfolioManager
from excel_reporter import ExcelReporter
import yfinance as yf
import json
import time

def test_basic_functionality():
    """기본 기능 테스트"""
    print("🧪 AI 주식 추천 시스템 테스트 시작...")
    
    # 환경 변수 로드
    load_dotenv()
    
    # OpenAI API 키 확인
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print("❌ OpenAI API 키가 설정되지 않았습니다.")
        print("   .env 파일에서 OPENAI_API_KEY를 설정해주세요.")
        return False
    
    print("✅ OpenAI API 키 확인 완료")
    
    # StockAnalyzer 테스트
    try:
        analyzer = StockAnalyzer()
        print("✅ StockAnalyzer 초기화 완료")
    except Exception as e:
        print(f"❌ StockAnalyzer 초기화 실패: {e}")
        return False
    
    # 주식 후보 목록 테스트
    try:
        candidates = get_stock_candidates()
        total_stocks = sum(len(stocks) for stocks in candidates.values())
        print(f"✅ 주식 후보 목록 로드 완료 ({total_stocks}개 주식)")
    except Exception as e:
        print(f"❌ 주식 후보 목록 로드 실패: {e}")
        return False
    
    # 개별 주식 정보 테스트
    try:
        test_symbol = 'AAPL'
        stock_info = analyzer.get_enhanced_stock_info(test_symbol)
        if stock_info:
            print(f"✅ {test_symbol} 주식 정보 수집 완료")
            print(f"   - 현재가: ${stock_info['current_price']:.2f}")
            print(f"   - 회사명: {stock_info['name']}")
            print(f"   - RSI: {stock_info['rsi']:.1f}")
        else:
            print(f"❌ {test_symbol} 주식 정보 수집 실패")
            return False
    except Exception as e:
        print(f"❌ 주식 정보 수집 테스트 실패: {e}")
        return False
    
    # 뉴스 수집 테스트
    try:
        news_items = analyzer.get_yahoo_finance_news_enhanced(test_symbol)
        print(f"✅ {test_symbol} 뉴스 수집 완료 ({len(news_items)}개 뉴스)")
        if news_items:
            print(f"   - 첫 번째 뉴스: {news_items[0]['title'][:50]}...")
    except Exception as e:
        print(f"❌ 뉴스 수집 테스트 실패: {e}")
        return False
    
    # 점수 계산 테스트
    try:
        score_info = analyzer.calculate_stock_score(stock_info, len(news_items))
        print(f"✅ 점수 계산 완료 (총점: {score_info['total_score']}/100)")
        print(f"   - 기술 점수: {score_info['technical_score']}/30")
        print(f"   - 뉴스 점수: {score_info['news_score']}/20")
    except Exception as e:
        print(f"❌ 점수 계산 테스트 실패: {e}")
        return False
    
    # 투자 금액 필터링 테스트
    try:
        investment_amount = 10000
        suitable_stocks = analyzer.filter_stocks_by_investment(['AAPL', 'MSFT', 'GOOGL'], investment_amount)
        print(f"✅ 투자 금액 필터링 완료 ({len(suitable_stocks)}개 주식 적합)")
    except Exception as e:
        print(f"❌ 투자 금액 필터링 테스트 실패: {e}")
        return False
    
    print("\n🎉 모든 테스트 통과!")
    return True

def test_portfolio_management():
    """포트폴리오 관리 기능 테스트"""
    print("\n📊 포트폴리오 관리 기능 테스트...")
    
    try:
        # PortfolioManager 초기화
        portfolio_manager = PortfolioManager()
        print("✅ PortfolioManager 초기화 완료")
        
        # 테스트 포트폴리오 생성
        test_portfolio = {
            'current_stocks': [
                {
                    'symbol': 'AAPL',
                    'name': 'Apple Inc.',
                    'purchase_price': 150.0,
                    'quantity': 10,
                    'purchase_date': '2024-01-01T00:00:00'
                },
                {
                    'symbol': 'MSFT',
                    'name': 'Microsoft Corporation',
                    'purchase_price': 300.0,
                    'quantity': 5,
                    'purchase_date': '2024-01-01T00:00:00'
                }
            ],
            'total_investment': 10000,
            'last_updated': None
        }
        
        # 포트폴리오 저장 테스트
        portfolio_manager.save_portfolio(test_portfolio)
        print("✅ 포트폴리오 저장 완료")
        
        # 포트폴리오 로드 테스트
        loaded_portfolio = portfolio_manager.load_portfolio()
        print(f"✅ 포트폴리오 로드 완료 ({len(loaded_portfolio['current_stocks'])}개 주식)")
        
        # 포트폴리오 성과 계산 테스트
        performance = portfolio_manager.calculate_portfolio_performance(loaded_portfolio)
        print(f"✅ 포트폴리오 성과 계산 완료")
        print(f"   - 포트폴리오 가치: ${performance['portfolio_value']:,.0f}")
        print(f"   - 총 수익률: {performance['total_return_pct']:.2f}%")
        
        # 성과 요약 테스트
        summary = portfolio_manager.get_performance_summary(loaded_portfolio)
        print(f"✅ 성과 요약 완료")
        print(f"   - 총 수익: ${summary['total_return_amount']:,.0f}")
        print(f"   - 보유 주식 수: {summary['total_stocks']}개")
        
        # 추천 히스토리 테스트
        test_recommendations = [
            {
                'symbol': 'AAPL',
                'stock_info': {'symbol': 'AAPL', 'name': 'Apple Inc.', 'current_price': 160.0},
                'score_info': {'total_score': 85},
                'analysis': '테스트 분석'
            }
        ]
        
        portfolio_manager.save_recommendation_history(test_recommendations)
        print("✅ 추천 히스토리 저장 완료")
        
        history = portfolio_manager.load_recommendation_history()
        print(f"✅ 추천 히스토리 로드 완료 ({len(history)}개 기록)")
        
        # 리밸런싱 판단 테스트
        should_rebalance, stocks_to_sell, stocks_to_buy = portfolio_manager.should_rebalance_portfolio(
            test_recommendations, loaded_portfolio
        )
        print(f"✅ 리밸런싱 판단 완료")
        print(f"   - 리밸런싱 필요: {should_rebalance}")
        print(f"   - 매도할 주식: {len(stocks_to_sell)}개")
        print(f"   - 매수할 주식: {len(stocks_to_buy)}개")
        
        print("\n🎉 포트폴리오 관리 테스트 통과!")
        return True
        
    except Exception as e:
        print(f"❌ 포트폴리오 관리 테스트 실패: {e}")
        return False

def test_excel_reporter():
    """엑셀 리포트 기능 테스트"""
    print("\n📊 엑셀 리포트 기능 테스트...")
    
    try:
        # ExcelReporter 초기화
        excel_reporter = ExcelReporter("test_excel_data")
        print("✅ ExcelReporter 초기화 완료")
        
        # 테스트 데이터 준비
        test_portfolio = {
            'current_stocks': [
                {
                    'symbol': 'AAPL',
                    'name': 'Apple Inc.',
                    'purchase_price': 150.0,
                    'current_price': 160.0,
                    'quantity': 10,
                    'cost': 1500.0,
                    'current_value': 1600.0,
                    'return_amount': 100.0,
                    'return_pct': 6.67,
                    'purchase_date': '2024-01-01T00:00:00'
                }
            ],
            'portfolio_value': 1600.0,
            'total_investment': 10000,
            'total_return': 100.0,
            'total_return_pct': 6.67
        }
        
        test_recommendations = [
            {
                'symbol': 'MSFT',
                'stock_info': {
                    'symbol': 'MSFT',
                    'name': 'Microsoft Corporation',
                    'current_price': 320.0
                },
                'score_info': {
                    'total_score': 85,
                    'technical_score': 25,
                    'news_score': 15,
                    'rsi': 65.5,
                    'ma_trend': '상승'
                },
                'analysis': '테스트 분석 - 1개월 목표가 $350 (9.4% 상승)'
            }
        ]
        
        # 엑셀 리포트 생성 테스트
        excel_reporter.create_excel_report(test_portfolio, test_recommendations)
        print("✅ 엑셀 리포트 생성 완료")
        
        # 엑셀 파일 요약 정보 테스트
        summary = excel_reporter.get_excel_summary()
        print(f"✅ 엑셀 파일 요약 완료")
        print(f"   - 파일명: {summary['파일명']}")
        print(f"   - 시트 수: {summary['시트 수']}개")
        print(f"   - 시트 목록: {', '.join(summary['시트 목록'])}")
        
        # 테스트 파일 정리
        import shutil
        if os.path.exists("test_excel_data"):
            shutil.rmtree("test_excel_data")
        
        print("\n🎉 엑셀 리포트 테스트 통과!")
        return True
        
    except Exception as e:
        print(f"❌ 엑셀 리포트 테스트 실패: {e}")
        return False

def test_yfinance_connection():
    """Yahoo Finance 연결 테스트"""
    print("\n📊 Yahoo Finance 연결 테스트...")
    
    try:
        # 간단한 주식 정보 가져오기
        aapl = yf.Ticker("AAPL")
        info = aapl.info
        
        if info and 'currentPrice' in info:
            print(f"✅ Yahoo Finance 연결 성공")
            print(f"   - AAPL 현재가: ${info['currentPrice']:.2f}")
            return True
        else:
            print("❌ Yahoo Finance에서 데이터를 가져올 수 없습니다.")
            return False
    except Exception as e:
        print(f"❌ Yahoo Finance 연결 실패: {e}")
        return False

def test_data_directory():
    """데이터 디렉토리 테스트"""
    print("\n📁 데이터 디렉토리 테스트...")
    
    try:
        # 포트폴리오 매니저로 디렉토리 생성 테스트
        portfolio_manager = PortfolioManager("test_data")
        
        # 테스트 파일 생성
        test_data = {"test": "data"}
        test_file = os.path.join("test_data", "test.json")
        
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        # 파일 읽기 테스트
        with open(test_file, 'r') as f:
            loaded_data = json.load(f)
        
        # 정리
        os.remove(test_file)
        os.rmdir("test_data")
        
        print("✅ 데이터 디렉토리 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 데이터 디렉토리 테스트 실패: {e}")
        return False

def test_enhanced_news_collection():
    """향상된 뉴스 수집 기능 테스트"""
    print("\n=== 향상된 뉴스 수집 테스트 ===")
    
    analyzer = StockAnalyzer()
    
    # 테스트 주식
    test_symbols = ['AAPL', 'TSLA', 'JPM']
    
    for symbol in test_symbols:
        print(f"\n📰 {symbol} 뉴스 수집 테스트:")
        
        # 뉴스 수집
        news_items = analyzer.get_yahoo_finance_news_enhanced(symbol)
        
        print(f"총 뉴스 수: {len(news_items)}개")
        
        # 카테고리별 분류
        news_by_category = {
            'stock_specific': [],
            'sector': [],
            'market': [],
            'global': [],
            'tech_trend': []
        }
        
        for news in news_items:
            category = news.get('category', 'stock_specific')
            if category in news_by_category:
                news_by_category[category].append(news)
        
        # 카테고리별 뉴스 수 출력
        for category, news_list in news_by_category.items():
            print(f"  {category}: {len(news_list)}개")
            for i, news in enumerate(news_list[:2], 1):  # 상위 2개만 표시
                print(f"    {i}. {news['title'][:60]}...")
        
        print(f"  소스별 분포:")
        sources = {}
        for news in news_items:
            source = news.get('source', 'Unknown')
            sources[source] = sources.get(source, 0) + 1
        
        for source, count in sources.items():
            print(f"    {source}: {count}개")
        
        time.sleep(2)  # API 호출 제한 방지

def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("🤖 AI 주식 추천 시스템 종합 테스트")
    print("=" * 60)
    
    # Yahoo Finance 연결 테스트
    if not test_yfinance_connection():
        print("\n❌ Yahoo Finance 연결에 실패했습니다.")
        print("   인터넷 연결을 확인해주세요.")
        return
    
    # 데이터 디렉토리 테스트
    if not test_data_directory():
        print("\n❌ 데이터 디렉토리 테스트에 실패했습니다.")
        return
    
    # 기본 기능 테스트
    if not test_basic_functionality():
        print("\n❌ 기본 기능 테스트에 실패했습니다.")
        return
    
    # 포트폴리오 관리 테스트
    if not test_portfolio_management():
        print("\n❌ 포트폴리오 관리 테스트에 실패했습니다.")
        return
    
    # 엑셀 리포트 테스트
    if not test_excel_reporter():
        print("\n❌ 엑셀 리포트 테스트에 실패했습니다.")
        return
    
    # 향상된 뉴스 수집 테스트
    test_enhanced_news_collection()
    
    print("\n" + "=" * 60)
    print("🎉 모든 테스트 통과!")
    print("   이제 다음 명령으로 애플리케이션을 실행할 수 있습니다:")
    print("   - 웹 인터페이스: streamlit run stock_main.py")
    print("   - 일일 자동 실행: python daily_runner.py")
    print("   - 엑셀 리포트: portfolio_data/portfolio_performance.xlsx")
    print("=" * 60)

if __name__ == "__main__":
    main() 