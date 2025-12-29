import json

file_path = '정형화데이터_경기 작업중.json' 

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, list):
        results = []
        
        for i, item in enumerate(data):
            # VS Code와 동일한 조건(들여쓰기 4칸)으로 줄 수 계산
            formatted_item = json.dumps(item, indent=4, ensure_ascii=False)
            line_count = len(formatted_item.splitlines())
            
            # sigungu 값이 없을 경우를 대비해 '정보 없음'으로 처리
            sigungu = item.get('sigungu', '정보 없음')
            # 서비스 이름도 같이 보고 싶으시면 아래 주석을 해제하세요
            # service_name = item.get('service_name', '이름 없음')
            
            results.append({
                'index': i, 
                'lines': line_count, 
                'sigungu': sigungu
            })
        
        # 'lines'(줄 수)를 기준으로 내림차순 정렬
        results.sort(key=lambda x: x['lines'], reverse=True)

        # 헤더 출력
        print(f"{'순위':<5} | {'시군구':<12} | {'줄 수':<8} | {'원본 인덱스':<10}")
        print("-" * 50)
        
        # 전체 결과 출력 (너무 많으면 results[:50] 처럼 제한 가능)
        for rank, res in enumerate(results, 1):
            print(f"{rank:<5} | {res['sigungu']:<12} | {res['lines']:<8} 줄 | Index: {res['index']}")
            
    else:
        print("데이터가 리스트([]) 형식이 아닙니다.")

except FileNotFoundError:
    print(f"파일을 찾을 수 없습니다: {file_path}")
except Exception as e:
    print(f"에러 발생: {e}")