import requests
from bs4 import BeautifulSoup

# 1. URL과 브라우저처럼 보이게 하는 필수 헤더 설정
url = "https://news.naver.com/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # 2. 현재 네이버 뉴스 메인에서 기사 제목을 담고 있는 클래스들
    # 'cjs_t' 외에도 헤드라인용 클래스를 추가했습니다.
    titles = soup.select(".cjs_t, .sh_text_headline, .sh_text_headline_n, .cnf_news_title") 

    print(f"--- 추출 시작 (찾은 개수: {len(titles)}개) ---")

    if not titles:
        # 만약 하나도 못 찾았다면, 페이지의 전체 텍스트 중 일부를 출력해 확인
        print("기사 제목을 찾을 수 없습니다. 사이트 구조가 변경되었을 수 있습니다.")
    else:
        for i, title in enumerate(titles[:10], 1):
            # strip=True로 불필요한 공백 제거
            print(f"{i}. {title.get_text(strip=True)}")

except Exception as e:
    print(f"오류 발생: {e}")