"""
복지 데이터 파서 v4.0 (완전판)
- ⭐⭐⭐ v4.0 핵심 변경: Benefits 중심 구조!
- 모든 조건은 benefits 내부에 포함
- 서비스 레벨 조건 제거 (지역만 서비스 레벨)
- 혜택별 독립적인 조건
- **birth_within_months 와 age_max_months 구분 명확히 반영**
"""
import json
from datetime import datetime
from openai import OpenAI
import xml.etree.ElementTree as ET
import time
import os
from dotenv import load_dotenv

class WelfareParserV4_0:
    def __init__(self, api_key):
        """OpenAI API 초기화"""
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
    
    def parse_service(self, service_name, target_text, criteria_text, support_text, max_retries=3):
        """GPT로 파싱 (재시도 로직 포함)"""
        prompt = f"""
복지 서비스 정보를 정형 데이터로 변환하세요.

서비스명: {service_name}
대상자: {target_text}
선정기준: {criteria_text}
지원내용: {support_text}

---

【⭐⭐⭐ 필수 JSON 구조 ⭐⭐⭐】

{{
  "benefits": [
    {{
      // 혜택 정보
      "amount": 1000000,
      "amount_type": "월",
      "benefit_type": "현금",
      "description": "...",
      
      // ⭐ 이 혜택의 조건 (필수!)
      "and_conditions": {{
        "age_min_months": 0,
        "age_max_months": 11,
        "childcare_type": "가정",
        "birth_within_months": 12, // 출산 후 신청 기한 (예: 출생 후 12개월 이내)
        ...
      }},
      "or_conditions": {{
        "household_type": ["맞벌이", "한부모"],
        ...
      }}
    }}
  ]
}}

❌❌❌ 절대 금지 ❌❌❌
{{
  "and_conditions": {{ ... }},  // 최상위 레벨 금지!
  "or_conditions": {{ ... }},  // 최상위 레벨 금지!
  "benefits": [ ... ]
}}

✅✅✅ 반드시 지켜야 할 규칙 ✅✅✅
1. 모든 조건은 benefits[].and_conditions 안에!
2. OR 조건은 benefits[].or_conditions 안에!
3. 각 benefit은 반드시 and_conditions와 or_conditions를 가져야 함 (빈 객체라도!)
4. 조건이 다르면 → 별도 benefit 생성!
5. 조건이 같으면 → 같은 benefit에 조건 중복!

---

【혜택별 조건 분리 규칙】⭐⭐⭐

원칙: 혜택마다 조건이 다르면 → 별도 benefits 생성!

예시 1: 0세 100만원, 1세 50만원
→ benefits 2개 (나이 조건 다름)

{{
  "benefits": [
    {{
      "amount": 1000000,
      "and_conditions": {{"age_min_months": 0, "age_max_months": 11}},
      "or_conditions": {{}}
    }},
    {{
      "amount": 500000,
      "and_conditions": {{"age_min_months": 12, "age_max_months": 23}},
      "or_conditions": {{}}
    }}
  ]
}}

... (중략)

---

【필수 규칙】⭐⭐⭐

## 1. 나이 (개월 단위) ⭐ 범위 파싱 필수!

**단일 기준:**
- "영유아" → age_max_months: 84
- "영아" → age_max_months: 24
- "0세" → age_min_months: 0, age_max_months: 11
- "1세" → age_min_months: 12, age_max_months: 23
- "만 5세 이하" → age_max_months: 60
- "만 8세 이하" → age_max_months: 96

**중요: 0세, 1세, 2세는 나이입니다! 출생순서가 아닙니다!**

---

## 2. 출산 후 신청 개월 (birth_within_months) ⭐⭐⭐

**용도:** 출산 후 **신청 마감 기간**을 나타냄. 나이 조건(age_max_months)과 다름!
(예: '출생일로부터 12개월 이내에 신청')

**키워드:**
- "출생일로부터 12개월 이내 신청" → birth_within_months: 12
- "출생일 기준 6개월 이내" → birth_within_months: 6
- 조건 없으면 → birth_within_months: null

---

## 3. 소득 (4가지만)

- "기준중위소득" (띄어쓰기 없음)
- "차상위계층"
- "기초생활수급자"
- null

---

## 6. 출생순서 (birth_order) ⭐⭐⭐

**❌❌❌ 매우 중요 ❌❌❌**

"0세", "1세", "2세"는 **나이**입니다! **출생순서가 아닙니다!**

---

【최종 체크리스트】

... (중략)

✅ "0세", "1세"를 birth_order로 착각하지 않았는가?
✅ **"출생 후 N개월 이내 신청"은 birth_within_months로 파싱했는가?**

---

❌❌❌ 절대 금지 사항 (다시 한번!) ❌❌❌

... (중략)

5. **age_max_months (최대 나이)**와 **birth_within_months (신청 기한)** 혼동 금지!
... (중략)

JSON만 반환하세요. 설명이나 마크다운 없이!
"""
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a welfare data parser. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
                return result
                
            except Exception as e:
                error_msg = str(e)
                
                # Rate limit 오류 확인 및 재시도 로직
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    wait_time = (attempt + 1) * 10 
                    print(f"⏳ (Rate limit, {wait_time}초 대기 후 재시도 {attempt + 1}/{max_retries})", end=' ')
                    time.sleep(wait_time)
                    continue
                
                # 그 외 오류 및 재시도 로직
                elif attempt < max_retries - 1:
                    wait_time = 3
                    print(f"⏳ (오류, {wait_time}초 대기 후 재시도 {attempt + 1}/{max_retries})", end=' ')
                    time.sleep(wait_time)
                    continue
                else:
                    # 최종 실패
                    print(f"❌ 최종 실패: {error_msg[:50]}")
                    return {
                        "benefits": [],
                        "parser_error": error_msg
                    }
        
        # 모든 재시도 실패
        return {
            "benefits": []
        }
    
    def batch_parse_xml(self, xml_path, limit=None):
        """XML 파일 배치 파싱 (limit 지원)"""
        print(f"📂 XML 파일 읽기: {xml_path}")
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except FileNotFoundError:
            print(f"❌ 파일 경로 오류: {xml_path} 파일을 찾을 수 없습니다.")
            return []
        except Exception as e:
            print(f"❌ XML 파싱 오류: {e}")
            return []
            
        services = []
        serv_list = root.findall('.//servList')
        total = len(serv_list)
        
        # limit 처리
        if limit:
            serv_list = serv_list[:limit]
            print(f"📊 총 {total}개 중 {limit}개만 파싱...")
        else:
            print(f"📊 총 {total}개 서비스 파싱 시작...")
        
        # ⭐ 통계 카운터
        success_count = 0
        error_count = 0
        error_services = []
        
        for idx, serv in enumerate(serv_list, 1):
            service_id = serv.find('servId').text if serv.find('servId') is not None else ''
            service_name = serv.find('servNm').text if serv.find('servNm') is not None else ''
            detail_url = serv.find('servDtlLink').text if serv.find('servDtlLink') is not None else ''
            sido = serv.find('ctpvNm').text if serv.find('ctpvNm') is not None else ''
            sigungu = serv.find('sggNm').text if serv.find('sggNm') is not None else None
            
            # 상세 정보
            detail = serv.find('.//wantedDtl')
            if detail is not None:
                target_text = detail.find('sprtTrgtCn').text if detail.find('sprtTrgtCn') is not None else ''
                criteria_text = detail.find('slctCritCn').text if detail.find('slctCritCn') is not None else ''
                support_text = detail.find('alwServCn').text if detail.find('alwServCn') is not None else ''
            else:
                target_text = ''
                criteria_text = ''
                support_text = ''
            
            print(f"[{idx}/{len(serv_list)}] {service_name[:50]}...", end=' ')
            
            # GPT 파싱
            try:
                parsed = self.parse_service(service_name, target_text, criteria_text, support_text)
                
                # ⭐ 파싱 결과 검증
                if parsed and 'benefits' in parsed and len(parsed.get('benefits', [])) > 0:
                    print("✅")
                    success_count += 1
                else:
                    print("⚠️ (benefits 없음)")
                    error_count += 1
                    error_services.append(service_name)
                
            except Exception as e:
                error_message = str(e)
                print(f"❌ (오류: {error_message[:30]})")
                error_count += 1
                error_services.append(service_name)
                parsed = {
                    "benefits": [],
                       "parser_error": error_message # 오류 메시지 저장
                }
            
            services.append({
                "service_id": service_id,
                "service_name": service_name,
                "detail_url": detail_url,
                "sido": sido,
                "sigungu": sigungu if sigungu else None,
                "source": sido,
                "original_data": {
                    "target_text": target_text,
                    "criteria_text": criteria_text,
                    "support_text": support_text
                },
                "parsed_data": parsed
            })
        
        # ⭐ 최종 통계 출력
        print(f"\n{'='*80}")
        print(f"📊 파싱 완료 통계")
        print(f"{'='*80}")
        print(f"✅ 성공: {success_count}개")
        print(f"❌ 실패: {error_count}개")
        
        total_parsed = len(serv_list)
        if total_parsed > 0:
            print(f"📈 성공률: {success_count / total_parsed * 100:.1f}%")
        
        if error_services:
            print(f"\n⚠️ 오류 발생 서비스:")
            for i, name in enumerate(error_services[:10], 1):
                print(f"  {i}. {name}")
            if len(error_services) > 10:
                print(f"  ... 외 {len(error_services) - 10}개")
        
        return services
    
    def save_results(self, results, output_path):
        """결과를 JSON 파일로 저장"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 완료! {len(results)}개 서비스 저장: {output_path}")

# 사용 예시
if __name__ == '__main__':
    # .env 파일에서 환경 변수를 로드합니다.
    load_dotenv()
    API_KEY = os.getenv('OPENAI_API_KEY')
    
    if not API_KEY:
        print("❌ OPENAI_API_KEY를 .env 파일에 설정하세요!")
        exit(1)
    
    # 🚨 경로 설정 필요: XML 파일 경로를 실행 환경에 맞게 변경하세요.
    XML_PATH = 'wantedDtl포함된xml목록/복지목록울산.xml'
    # XML_PATH = 'wantedDtl포함된xml목록/복지목록중앙부.xml'
    
    parser = WelfareParserV4_0(api_key=API_KEY)
    
    results = parser.batch_parse_xml(
        XML_PATH,
        # limit=1 # 테스트를 위해 1개만 파싱하려면 이 주석을 해제하세요.
    )
    
    # 1. 현재 날짜와 시간을 가져와 '월일_시분' 형식으로 만듭니다.
    now = datetime.now()
    timestamp = now.strftime("%m%d_%H%M")

    # 2. 파일 이름을 동적으로 생성합니다.
    base_name = '정형화데이터_울산_v4.0'
    # base_name = '정형화데이터_중앙부_v4.0'
    file_name = f"{base_name}_{timestamp}.json"

    # 3. 파일 저장 함수 호출
    parser.save_results(results, file_name)
    
    print("\n🎉 v4.0 파싱 완료!")
    print("주요 변경사항:")
    print("  1. Benefits 중심 구조")
    print("  2. 혜택별 독립적인 조건")
    print("  3. **'출생 후 신청 개월' (birth_within_months) 필드와 '최대 나이' (age_max_months) 필드 구분 명확화**")