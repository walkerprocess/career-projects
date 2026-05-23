#!/usr/bin/env python3
"""
향상된 뉴스 수집 및 분석 기능 테스트 스크립트
- 카테고리별 최소 15개 뉴스 수집
- 더 정교한 키워드 추출
- 상세한 뉴스 분석 및 영향도 분석
- 한줄평 포함 GPT 분석
"""

from enhanced_news_collector import EnhancedNewsCollector
import time

def test_enhanced_news_collection():
    """향상된 뉴스 수집 기능 테스트 - 최소 15개 보장"""
    print("=== 향상된 뉴스 수집 테스트 (최소 15개 보장) ===")
    
    collector = EnhancedNewsCollector()
    
    # 테스트 주식
    test_symbols = ['AAPL', 'TSLA', 'JPM']
    
    for symbol in test_symbols:
        print(f"\n📰 {symbol} 상세 뉴스 수집 (목표: 15개):")
        try:
            detailed_news = collector.get_detailed_stock_news(symbol, max_news=15)
            
            if isinstance(detailed_news, dict):
                news_list = detailed_news.get('news', [])
                total_news = detailed_news.get('total_news', 0)
                news_summary = detailed_news.get('news_summary', '')
                impact_summary = detailed_news.get('impact_summary', '')
                
                print(f"  ✅ {symbol} 뉴스 수집 완료: {total_news}개")
                
                # 뉴스 요약 출력
                if news_summary:
                    print(f"  📝 뉴스 요약:")
                    print(f"    {news_summary[:200]}...")
                
                # 영향도 분석 출력
                if impact_summary:
                    print(f"  📊 영향도 분석:")
                    print(f"    {impact_summary[:200]}...")
                
                # 개별 뉴스 분석
                sources = {}
                categories = {}
                mentioned_stocks = set()
                impact_stats = {'긍정적': 0, '부정적': 0, '중립적': 0}
                
                for news in news_list:
                    source = news.get('source', 'Unknown')
                    category = news.get('category', 'Unknown')
                    sources[source] = sources.get(source, 0) + 1
                    categories[category] = categories.get(category, 0) + 1
                    mentioned_stocks.update(news.get('mentioned_stocks', []))
                    
                    # 영향도 통계
                    impact_analysis = news.get('impact_analysis', {})
                    impact = impact_analysis.get('impact', '중립적')
                    impact_stats[impact] += 1
                
                print(f"  📊 소스별 분포:")
                for source, count in sources.items():
                    print(f"    {source}: {count}개")
                
                print(f"  📊 카테고리별 분포:")
                for category, count in categories.items():
                    print(f"    {category}: {count}개")
                
                print(f"  📊 영향도 분포:")
                for impact, count in impact_stats.items():
                    print(f"    {impact}: {count}개")
                
                print(f"  🔗 언급된 주식: {', '.join(list(mentioned_stocks)[:10])}")
                
                # 상위 뉴스 출력
                print(f"  📰 주요 뉴스 (상위 3개):")
                for i, news in enumerate(news_list[:3], 1):
                    title = news.get('title', '제목 없음')
                    impact = news.get('impact_analysis', {}).get('impact', '중립적')
                    confidence = news.get('impact_analysis', {}).get('confidence', '중간')
                    summary = news.get('summary', '')[:100]
                    print(f"    {i}. {title[:60]}... ({impact}, {confidence})")
                    print(f"       요약: {summary}...")
            else:
                print(f"  ❌ {symbol} 뉴스 수집 실패: 잘못된 형식")
                
        except Exception as e:
            print(f"  ❌ {symbol} 뉴스 수집 오류: {e}")
        
        time.sleep(2)

def test_comprehensive_news_collection():
    """종합 뉴스 수집 테스트 - 카테고리별 최소 15개"""
    print("\n=== 종합 뉴스 수집 테스트 (카테고리별 최소 15개) ===")
    
    collector = EnhancedNewsCollector()
    
    try:
        # 종합 뉴스 수집 (카테고리별 15개)
        comprehensive_news = collector.collect_comprehensive_news(
            categories=['business', 'technology', 'general'], 
            max_articles_per_category=15,
            force_refresh=True
        )
        
        print(f"✅ 종합 뉴스 수집 완료")
        print(f"  총 뉴스 수: {comprehensive_news['total_articles']}개")
        print(f"  언급된 주식: {len(comprehensive_news['mentioned_stocks'])}개")
        
        # 카테고리별 뉴스 수 확인
        for category, news_list in comprehensive_news['news_by_category'].items():
            print(f"  📰 {category}: {len(news_list)}개 뉴스")
            if len(news_list) < 15:
                print(f"    ⚠️ 목표보다 {15 - len(news_list)}개 적음")
            else:
                print(f"    ✅ 목표 달성")
        
        # 키워드 추출 테스트
        print(f"\n🔍 키워드 추출 테스트:")
        keywords = collector.extract_keywords_from_news(comprehensive_news)
        print(f"  추출된 키워드: {len(keywords)}개")
        print(f"  상위 키워드: {', '.join(keywords[:15])}")
        
    except Exception as e:
        print(f"❌ 종합 뉴스 수집 오류: {e}")

def test_enhanced_gpt_analysis():
    """향상된 GPT 분석 테스트 - 뉴스 요약, 영향 분석, 한줄평 포함"""
    print("\n=== 향상된 GPT 분석 테스트 ===")
    
    collector = EnhancedNewsCollector()
    
    try:
        # 뉴스 수집
        news_data = collector.collect_comprehensive_news(
            categories=['business', 'technology'], 
            max_articles_per_category=10,
            force_refresh=False
        )
        
        # GPT 분석
        gpt_stocks = collector.analyze_news_for_stocks_using_gpt(news_data, max_stocks=6)
        
        print(f"✅ GPT 분석 완료: {len(gpt_stocks)}개 주식 추천")
        
        for i, stock in enumerate(gpt_stocks, 1):
            symbol = stock['symbol']
            name = stock['name']
            description = stock['description']
            sector = stock['sector']
            print(f"  {i}. {symbol} ({name}) - {sector}")
            print(f"     추천 이유: {description}")
        
    except Exception as e:
        print(f"❌ GPT 분석 오류: {e}")

def test_news_api_functionality():
    """NEWS API 기능 테스트"""
    print("\n=== NEWS API 기능 테스트 ===")
    collector = EnhancedNewsCollector()
    
    if not collector.news_api_key:
        print("❌ NEWS API 키가 설정되지 않았습니다.")
        print("   .env 파일에 NEWS_API_KEY를 추가해주세요.")
        return
    
    print(f"✅ NEWS API 키 확인됨")
    
    categories = ['business', 'technology', 'general']
    for category in categories:
        print(f"\n📰 {category} 카테고리 뉴스 수집 (목표: 15개):")
        try:
            articles = collector.get_news_api_articles(category, max_articles=15)
            print(f"  ✅ {category}: {len(articles)}개 뉴스 수집")
            
            if len(articles) < 15:
                print(f"    ⚠️ 목표보다 {15 - len(articles)}개 적음")
            else:
                print(f"    ✅ 목표 달성")
            
            # 상위 3개 뉴스 출력
            for i, article in enumerate(articles[:3], 1):
                title = article.get('title', '제목 없음')
                source = article.get('source', 'Unknown')
                impact = article.get('impact', '중립적')
                mentioned = article.get('mentioned_stocks', [])
                print(f"    {i}. {title[:50]}...")
                print(f"       소스: {source}, 영향: {impact}")
                if mentioned:
                    print(f"       언급된 주식: {', '.join(mentioned[:5])}")
                    
        except Exception as e:
            print(f"  ❌ {category} 뉴스 수집 오류: {e}")
        
        time.sleep(2)

def test_enhanced_keyword_extraction():
    """향상된 키워드 추출 테스트"""
    print("\n=== 향상된 키워드 추출 테스트 ===")
    
    collector = EnhancedNewsCollector()
    
    # 테스트 텍스트
    test_texts = [
        "Apple's latest AI technology announcement and strong earnings beat expectations, driving stock price surge",
        "Tesla's electric vehicle sales growth and autonomous driving breakthrough lead to positive market sentiment",
        "Microsoft's cloud services expansion and AI partnerships create bullish outlook for tech sector"
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n📝 테스트 텍스트 {i}:")
        print(f"  원문: {text[:100]}...")
        
        # 키워드 추출
        keywords = collector._extract_keywords_from_text(text)
        print(f"  추출된 키워드: {len(keywords)}개")
        print(f"  키워드: {', '.join(keywords[:10])}")
        
        # 주식 티커 추출
        tickers = collector.extract_stock_symbols_from_text(text)
        print(f"  추출된 티커: {', '.join(tickers)}")

def main():
    """메인 테스트 함수"""
    print("🚀 향상된 뉴스 수집 및 분석 시스템 테스트 시작")
    print("=" * 60)
    
    # 1. NEWS API 기능 테스트
    test_news_api_functionality()
    
    # 2. 향상된 키워드 추출 테스트
    test_enhanced_keyword_extraction()
    
    # 3. 종합 뉴스 수집 테스트
    test_comprehensive_news_collection()
    
    # 4. 향상된 뉴스 수집 테스트
    test_enhanced_news_collection()
    
    # 5. 향상된 GPT 분석 테스트
    test_enhanced_gpt_analysis()
    
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")

if __name__ == "__main__":
    main() 