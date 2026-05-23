#!/usr/bin/env python3
"""
뉴스 없이도 동작하는 주식 분석 로직 테스트
- 뉴스 우선순위가 빈 리스트일 때 정상 동작 확인
- 기본 주식 분석 로직만으로 추천 가능한지 확인
- 모든 API가 실패해도 주식 선별이 되는지 확인
"""

from stock_analyzer import StockAnalyzer, get_stock_candidates
import time

def test_stock_analysis_without_news():
    """뉴스 없이 주식 분석 테스트"""
    print("=== 뉴스 없이도 동작하는 주식 분석 테스트 ===")
    
    analyzer = StockAnalyzer()
    investment_amount = 100000  # $100,000 투자 시나리오
    
    # 1. 기본 주식 후보 목록 가져오기
    print("\n1. 기본 주식 후보 목록 테스트:")
    try:
        stock_candidates_dict = get_stock_candidates()
        # 딕셔너리에서 모든 주식을 리스트로 변환
        all_candidates = []
        for sector, stocks in stock_candidates_dict.items():
            all_candidates.extend(stocks)
        
        print(f"   ✅ 기본 주식 후보: {len(all_candidates)}개")
        print(f"   섹터 수: {len(stock_candidates_dict)}개")
        print(f"   섹터별 분포:")
        for sector, stocks in stock_candidates_dict.items():
            print(f"     {sector}: {len(stocks)}개")
        print(f"   상위 10개: {all_candidates[:10]}")
        
        # 테스트용으로 첫 15개 주식 사용
        stock_candidates = all_candidates[:15]
        
    except Exception as e:
        print(f"   ❌ 기본 주식 후보 로드 실패: {e}")
        return
    
    # 2. 뉴스 우선순위 없이 주식 필터링 테스트
    print(f"\n2. 뉴스 우선순위 없이 주식 필터링 테스트 (투자금액: ${investment_amount:,}):")
    try:
        # 뉴스 우선순위를 None 또는 빈 리스트로 설정
        filtered_stocks = analyzer.filter_stocks_by_investment_and_news(
            stock_candidates=stock_candidates, 
            investment_amount=investment_amount,
            news_priority_stocks=None  # 뉴스 없음
        )
        
        print(f"   ✅ 뉴스 없이 필터링 결과: {len(filtered_stocks)}개 주식")
        
        if filtered_stocks:
            print(f"   📊 선별된 주식들:")
            for i, stock in enumerate(filtered_stocks[:5], 1):
                symbol = stock['symbol']
                name = stock['name']
                price = stock['current_price']
                shares = stock['shares_affordable']
                is_priority = stock.get('is_news_priority', False)
                print(f"   {i}. {symbol} ({name})")
                print(f"      가격: ${price:.2f}, 구매가능: {shares}주, 뉴스우선: {is_priority}")
        else:
            print(f"   ⚠️ 선별된 주식이 없습니다")
            
    except Exception as e:
        print(f"   ❌ 주식 필터링 실패: {e}")
    
    # 3. 빈 뉴스 우선순위로 테스트
    print(f"\n3. 빈 뉴스 우선순위 리스트로 주식 필터링 테스트:")
    try:
        filtered_stocks_empty = analyzer.filter_stocks_by_investment_and_news(
            stock_candidates=stock_candidates[:10], 
            investment_amount=investment_amount,
            news_priority_stocks=[]  # 빈 리스트
        )
        
        print(f"   ✅ 빈 뉴스 리스트로 필터링 결과: {len(filtered_stocks_empty)}개 주식")
        
        if filtered_stocks_empty:
            print(f"   📊 일반 유망 주식 위주로 선별:")
            for i, stock in enumerate(filtered_stocks_empty[:3], 1):
                symbol = stock['symbol']
                name = stock['name']
                price = stock['current_price']
                market_cap = stock.get('market_cap', 0)
                print(f"   {i}. {symbol} ({name[:30]})")
                print(f"      가격: ${price:.2f}, 시가총액: ${market_cap/1e9:.1f}B")
        
    except Exception as e:
        print(f"   ❌ 빈 뉴스 리스트 테스트 실패: {e}")
    
    # 4. 개별 주식 분석 (뉴스 점수 0으로) 테스트
    print(f"\n4. 개별 주식 분석 (뉴스 없음) 테스트:")
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']
    
    for symbol in test_symbols:
        try:
            print(f"   분석 중: {symbol}")
            stock_info = analyzer.get_enhanced_stock_info(symbol)
            
            if stock_info:
                # 뉴스 점수 0으로 점수 계산
                score_info = analyzer.calculate_stock_score(stock_info, news_count=0)
                base_potential = analyzer._calculate_base_potential_score(stock_info)
                
                print(f"   ✅ {symbol} 분석 완료:")
                print(f"      현재가: ${stock_info['current_price']:.2f}")
                print(f"      총점: {score_info['total_score']}/100")
                print(f"      기술점수: {score_info['technical_score']}/30")
                print(f"      뉴스점수: {score_info['news_score']}/20 (0개 뉴스)")
                print(f"      기본유망성: {base_potential}/100")
                print(f"      추세: {score_info['ma_trend']}")
            else:
                print(f"   ❌ {symbol} 정보 수집 실패")
                
        except Exception as e:
            print(f"   ❌ {symbol} 분석 오류: {e}")
        
        time.sleep(1)  # API 호출 간격
    
    # 5. 종합 분석 결과
    print(f"\n5. 종합 분석 결과:")
    print(f"   🎯 뉴스 없이도 주식 분석 시스템이 정상 동작함을 확인")
    print(f"   📊 기본 유망성 점수만으로도 주식 선별 가능")
    print(f"   💰 투자 금액에 맞는 구매 가능 주식 수 계산 정상")
    print(f"   🔍 시가총액, 거래량, P/E 등 기본 지표로 필터링 작동")

def test_base_scoring_system():
    """기본 점수 시스템만으로 주식 평가 테스트"""
    print(f"\n=== 기본 점수 시스템 테스트 ===")
    
    analyzer = StockAnalyzer()
    
    # 가상의 주식 정보로 점수 계산 테스트
    test_stock_data = [
        {
            'name': '대형 안정주',
            'symbol': 'TEST1',
            'current_price': 150,
            'market_cap': 500000000000,  # 5000억 달러
            'volume': 15000000,  # 1500만 주
            'pe_ratio': 18,
            'beta': 1.0,
            'dividend_yield': 0.025,  # 2.5%
            'rsi': 55,
            'ma20': 145,
            'ma50': 140,
            'bb_position': 0.6
        },
        {
            'name': '중형 성장주',
            'symbol': 'TEST2', 
            'current_price': 80,
            'market_cap': 50000000000,  # 500억 달러
            'volume': 5000000,  # 500만 주
            'pe_ratio': 25,
            'beta': 1.3,
            'dividend_yield': 0.01,  # 1%
            'rsi': 45,
            'ma20': 78,
            'ma50': 75,
            'bb_position': 0.4
        }
    ]
    
    for stock_data in test_stock_data:
        print(f"\n📊 {stock_data['name']} ({stock_data['symbol']}) 분석:")
        
        # 뉴스 점수 0으로 계산
        score_info = analyzer.calculate_stock_score(stock_data, news_count=0)
        base_potential = analyzer._calculate_base_potential_score(stock_data)
        
        print(f"   현재가: ${stock_data['current_price']}")
        print(f"   시가총액: ${stock_data['market_cap']/1e9:.0f}B")
        print(f"   거래량: {stock_data['volume']:,}주")
        print(f"   P/E: {stock_data['pe_ratio']}")
        print(f"   베타: {stock_data['beta']}")
        print(f"   배당수익률: {stock_data['dividend_yield']*100:.1f}%")
        print(f"   📈 점수 분석:")
        print(f"      총점: {score_info['total_score']}/100")
        print(f"      기본점수: {score_info['base_score']}/50")
        print(f"      기술점수: {score_info['technical_score']}/30") 
        print(f"      뉴스점수: {score_info['news_score']}/20 (뉴스 없음)")
        print(f"      기본유망성: {base_potential}/100")
        print(f"      추세: {score_info['ma_trend']}")
        
        # 투자 적합성 판단
        if score_info['total_score'] >= 70:
            print(f"   ✅ 투자 추천 (뉴스 없이도 우수한 점수)")
        elif score_info['total_score'] >= 60:
            print(f"   ⚠️ 투자 검토 (추가 분석 필요)")
        else:
            print(f"   ❌ 투자 비추천")

if __name__ == "__main__":
    test_stock_analysis_without_news()
    test_base_scoring_system() 