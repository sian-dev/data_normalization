import json

file_path = '정형화데이터_경기 선작업리스트.json' # 실제 파일명으로 수정하세요

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, list):
        results = []
        
        for i, item in enumerate(data):
            # VS Code와 동일한 조건(들여쓰기 4칸)으로 줄 수 계산
            formatted_item = json.dumps(item, indent=4, ensure_ascii=False)
            line_count = len(formatted_item.splitlines())
            results.append({'index': i, 'lines': line_count})
        
        # 'lines'(줄 수)를 기준으로 내림차순 정렬
        results.sort(key=lambda x: x['lines'], reverse=True)

        print(f"{'순위':<5} | {'원본 인덱스':<10} | {'줄 수':<10}")
        print("-" * 35)
        
        # 상위 결과 출력 (너무 많으면 슬라이싱[:20] 등으로 조절 가능)
        for rank, res in enumerate(results, 1):
            print(f"{rank:<5} | {res['index']:<10} | {res['lines']:<10} 줄")
            
    else:
        print("데이터가 리스트([]) 형식이 아닙니다.")

except FileNotFoundError:
    print(f"파일을 찾을 수 없습니다: {file_path}")
except Exception as e:
    print(f"에러 발생: {e}")