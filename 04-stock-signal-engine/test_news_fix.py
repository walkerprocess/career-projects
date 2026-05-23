#!/usr/bin/env python3
"""
개선된 뉴스 수집 시스템 테스트
- CURRENTS API 연결 문제 해결 확인
- GPT 뉴스 생성 JSON 파싱 오류 해결 확인
- 하드코딩된 fallback 뉴스 동작 확인
"""

from enhanced_news_collector import EnhancedNewsCollector
import time

def test_currents_and_gpt_fix():
    """CURRENTS API와 GPT 뉴스 생성 문제 해결 테스트"""
    print("=== 개선된 뉴스 수집 시스템 테스트 ===")
    
    collector = EnhancedNewsCollector()
    
    # 1. CURRENTS API 직접 테스트
    print("\n1. CURRENTS API 직접 테스트:")
    try:
        currents_news = collector._try_currents_api('business', None, 5)
        print(f"   ✅ CURRENTS API 결과: {len(currents_news)}개 뉴스")
        for i, news in enumerate(currents_news[:2], 1):
            print(f"   {i}. {news['title'][:50]}... ({news['source']})")
    except Exception as e:
        print(f"   ❌ CURRENTS API 오류: {e}")
    
    time.sleep(2)
    
    # 2. GPT 뉴스 생성 직접 테스트
    print("\n2. GPT 뉴스 생성 직접 테스트:")
    try:
        gpt_news = collector._get_news_via_gpt('technology', None, 3)
        print(f"   ✅ GPT 뉴스 생성 결과: {len(gpt_news)}개 뉴스")
        for i, news in enumerate(gpt_news[:2], 1):
            print(f"   {i}. {news['title'][:50]}... ({news['source']})")
            print(f"      URL: {news['url']}")
            if news.get('mentioned_stocks'):
                print(f"      언급된 주식: {', '.join(news['mentioned_stocks'])}")
    except Exception as e:
        print(f"   ❌ GPT 뉴스 생성 오류: {e}")
    
    time.sleep(2)
    
    # 3. 하드코딩된 fallback 테스트
    print("\n3. 하드코딩된 fallback 뉴스 테스트:")
    try:
        fallback_news = collector._generate_fallback_news('business', 4)
        print(f"   ✅ Fallback 뉴스 생성 결과: {len(fallback_news)}개 뉴스")
        for i, news in enumerate(fallback_news[:3], 1):
            print(f"   {i}. {news['title'][:50]}...")
            if news.get('mentioned_stocks'):
                print(f"      언급된 주식: {', '.join(news['mentioned_stocks'])}")
    except Exception as e:
        print(f"   ❌ Fallback 뉴스 생성 오류: {e}")
    
    # 4. 전체 뉴스 수집 플로우 테스트
    print("\n4. 전체 뉴스 수집 플로우 테스트:")
    try:
        all_news = collector.get_news_api_articles('business', max_articles=5)
        print(f"   ✅ 전체 플로우 결과: {len(all_news)}개 뉴스")
        for i, news in enumerate(all_news[:3], 1):
            print(f"   {i}. {news['title'][:50]}... ({news['source']})")
        
        # 소스별 분류
        sources = {}
        for news in all_news:
            source = news['source']
            sources[source] = sources.get(source, 0) + 1
        
        print(f"   📊 소스별 분포: {sources}")
        
    except Exception as e:
        print(f"   ❌ 전체 플로우 오류: {e}")

if __name__ == "__main__":
    test_currents_and_gpt_fix() 