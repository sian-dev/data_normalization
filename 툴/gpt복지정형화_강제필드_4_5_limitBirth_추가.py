"""
복지 데이터 파서 v4.5 (타입 명시 + 필드 추가)
- ⭐ income_min_percent 추가 (소득 하한)
- ⭐ requires_parent_disability_level 추가
- ⭐ 모든 필드 타입 명시 (숫자|문자열|true|null)
- ⭐ and_conditions 모든 필드 필수! 값 없으면 null
"""
import json
from datetime import datetime
from openai import OpenAI
import xml.etree.ElementTree as ET

class WelfareParserV4_5:
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

【⭐ 필수 JSON 구조 ⭐】

⚠️ 중요: and_conditions의 모든 필드는 필수입니다! 타입을 정확히 지켜주세요!

{{
  "benefits": [
    {{
      "amount": <숫자>,
      "amount_type": <"월"|"년"|"회"|null>,
      "amount_unit": <"원"|"만원"|null>,
      "benefit_type": <"현금"|"바우처"|"서비스"|"현물"|null>,
      "payment_cycle": <문자열|null>,
      "payment_method": <문자열|null>,
      "payment_timing": <문자열|null>,
      "description": <문자열>,
      
      "and_conditions": {{
        "age_min_months": <숫자|null>,
        "age_max_months": <숫자|null>,
        "income_type": <"기준중위소득"|"차상위계층"|"기초생활수급자"|null>,
        "income_min_percent": <숫자|null>,
        "income_max_percent": <숫자|null>,
        "household_type": <"한부모"|"조손"|"다문화"|"맞벌이"|null>,
        "household_members_min": <숫자|null>,
        "household_members_max": <숫자|null>,
        "children_min": <숫자|null>,
        "children_max": <숫자|null>,
        "birth_order": <1|2|3|숫자|null>,
        "birth_order_min": <1|2|3|숫자|null>,
        "birth_order_max": <1|2|3|숫자|null>,
        "residence_min_months": <숫자|null>,
        "childcare_type": <"가정"|"어린이집"|"유치원"|null>,
        "requires_grandparent_care": <true|null>,
        "requires_dual_income": <true|null>,
        "requires_disability": <true|null>,
        "requires_parent_disability": <true|null>,
        "child_disability_level": <"경증"|"중증"|null>,
        "child_has_serious_disease": <true|null>,
        "child_has_rare_disease": <true|null>,
        "child_has_chronic_disease": <true|null>,
        "child_has_cancer": <true|null>,
        "parent_has_serious_disease": <true|null>,
        "parent_has_rare_disease": <true|null>,
        "parent_has_chronic_disease": <true|null>,
        "parent_has_cancer": <true|null>,
        "parent_has_infertility": <true|null>,
        "is_violence_victim": <true|null>,
        "is_abuse_victim": <true|null>,
        "is_defector": <true|null>,
        "is_national_merit": <true|null>,
        "is_foster_child": <true|null>,
        "is_single_mother": <true|null>,
        "is_low_income": <true|null>,
        "pregnancy_weeks_min": <숫자|null>,
        "pregnancy_weeks_max": <숫자|null>,
        "birth_within_months": <숫자|null>,
        "limit_birth_date": <"YYYY-MM-DD"|null>,
        "education_level": <"초등"|"중등"|"고등"|null>,
        "is_enrolled": <true|null>,
        "housing_type": <"자가"|"전세"|"월세"|null>
      }},
      "or_conditions": {{
        "household_type": <["한부모", "맞벌이"]|[]>,
        "income_type": <["기준중위소득", "차상위계층"]|[]>,
        "age_min_months": <숫자|null>,
        "age_max_months": <숫자|null>,
        "income_min_percent": <숫자|null>,
        "income_max_percent": <숫자|null>,
        "household_members_min": <숫자|null>,
        "household_members_max": <숫자|null>,
        "children_min": <숫자|null>,
        "children_max": <숫자|null>,
        "birth_order": <1|2|3|숫자|null>,
        "birth_order_min": <1|2|3|숫자|null>,
        "birth_order_max": <1|2|3|숫자|null>,
        "residence_min_months": <숫자|null>,
        "childcare_type": <["가정", "어린이집", "유치원"]|null>,
        "requires_grandparent_care": <true|null>,
        "requires_dual_income": <true|null>,
        "requires_disability": <true|null>,
        "requires_parent_disability": <true|null>,
        "child_disability_level": <["경증", "중증"]|null>,
        "parent_disability_level": <["경증", "중증"]|null>,
        "child_has_serious_disease": <true|null>,
        "child_has_rare_disease": <true|null>,
        "child_has_chronic_disease": <true|null>,
        "child_has_cancer": <true|null>,
        "parent_has_serious_disease": <true|null>,
        "parent_has_rare_disease": <true|null>,
        "parent_has_chronic_disease": <true|null>,
        "parent_has_cancer": <true|null>,
        "parent_has_infertility": <true|null>,
        "is_violence_victim": <true|null>,
        "is_abuse_victim": <true|null>,
        "is_defector": <true|null>,
        "is_national_merit": <true|null>,
        "is_foster_child": <true|null>,
        "is_single_mother": <true|null>,
        "is_low_income": <true|null>,
        "pregnancy_weeks_min": <숫자|null>,
        "pregnancy_weeks_max": <숫자|null>,
        "birth_within_months": <숫자|null>,
        "limit_birth_date": <"YYYY-MM-DD"|null>,
        "education_level": <["초등", "중등", "고등"]|null>,
        "is_enrolled": <true|null>,
        "housing_type": <["자가", "전세", "월세"]|null>
      }}
    }}
  ]
}}

⚠️⚠️⚠️ 핵심 규칙 ⚠️⚠️⚠️

1. income_min_percent는 "기준중위소득 초과" 조건에 사용
   예: "기준중위소득 100% 초과 150% 이하"
   → income_min_percent: 100, income_max_percent: 150

2. requires_parent_disability_level → 사용 안 함
   부모 장애 등급은 or_conditions의 parent_disability_level 사용

3. limit_birth_date는 "특정 일자 이전 태생" 조건에 사용
   예: "2024년 12월 31일 이전 태생이면서 6세 미만"
   → limit_birth_date: "2024-12-31", age_max_months: 71

4. Boolean은 true 또는 null만! false 금지!

5. 나이는 무조건 개월 단위!

6. or_conditions 타입 규칙:
   - 카테고리형(household_type, income_type, childcare_type, education_level, housing_type, 
     child_disability_level, parent_disability_level)은 배열 형태
     예: household_type: ["한부모", "맞벌이"]
   - 숫자형(age, income_percent, children, birth_order 등)은 단일값
     예: age_max_months: 36 (배열 아님!)
   - Boolean형(requires_*, is_*, has_*)은 단일값
     예: requires_disability: true (배열 아님!)

---

JSON만 반환하세요. 설명 없이!
"""
        
        import time
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a welfare data parser. ALL fields in and_conditions are REQUIRED. If no value, use null. Follow the exact JSON structure."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
                
                # 구조 검증
                if result and 'benefits' in result:
                    for benefit in result['benefits']:
                        benefit = self.validate_benefit_structure(benefit, "current_service")
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    wait_time = (attempt + 1) * 10
                    print(f"⏳ (Rate limit, {wait_time}초 대기 후 재시도 {attempt + 1}/{max_retries})", end=' ')
                    time.sleep(wait_time)
                    continue
                
                elif attempt < max_retries - 1:
                    wait_time = 3
                    print(f"⏳ (오류, {wait_time}초 대기 후 재시도 {attempt + 1}/{max_retries})", end=' ')
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ 최종 실패: {error_msg[:50]}")
                    return {"benefits": []}
        
        return {"benefits": []}
    
    def validate_benefit_structure(self, benefit, service_name):
        """혜택 구조 검증"""
        required_fields = [
            'age_min_months', 'age_max_months',
            'income_type', 'income_min_percent', 'income_max_percent',
            'household_type', 'household_members_min', 'household_members_max',
            'children_min', 'children_max', 'birth_order','birth_order_min','birth_order_max',
            'residence_min_months',
            'childcare_type', 'requires_grandparent_care', 'requires_dual_income',
            'requires_disability', 'requires_parent_disability', 'child_disability_level',
            'child_has_serious_disease', 'child_has_rare_disease', 'child_has_chronic_disease', 'child_has_cancer',
            'parent_has_serious_disease', 'parent_has_rare_disease', 'parent_has_chronic_disease', 'parent_has_cancer', 'parent_has_infertility',
            'is_violence_victim', 'is_abuse_victim', 'is_defector', 'is_national_merit', 'is_foster_child', 'is_single_mother', 'is_low_income',
            'pregnancy_weeks_min', 'pregnancy_weeks_max', 'birth_within_months',
            'limit_birth_date',
            'education_level', 'is_enrolled',
            'housing_type'
        ]
        
        and_cond = benefit.get('and_conditions', {})
        
        # 누락된 필드 체크
        missing = [f for f in required_fields if f not in and_cond]
        
        if missing:
            print(f"    ⚠️ 누락 필드 자동 추가: {len(missing)}개")
            for field in missing:
                and_cond[field] = None
        
        # 불필요한 필드 체크
        extra = [f for f in and_cond.keys() if f not in required_fields]
        
        if extra:
            print(f"    ⚠️ 불필요한 필드 제거: {extra}")
            for field in extra:
                and_cond.pop(field)
        
        return benefit
    
    def fix_parsed_data(self, benefit):
        """파싱 결과 자동 수정 (후처리)"""
        and_cond = benefit.get('and_conditions', {})
        
        # False 값 제거
        for key, value in list(and_cond.items()):
            if value is False:
                and_cond[key] = None
                print(f"    ⚠️ 수정: {key}: false → null")
        
        return benefit
    
    def batch_parse_xml(self, xml_path, limit=None):
        """XML 파일 배치 파싱"""
        print(f"📂 XML 파일 읽기: {xml_path}")
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        services = []
        serv_list = root.findall('.//servList')
        total = len(serv_list)
        
        if limit:
            serv_list = serv_list[:limit]
            print(f"📊 총 {total}개 중 {limit}개만 파싱...")
        else:
            print(f"📊 총 {total}개 서비스 파싱 시작...")
        
        success_count = 0
        error_count = 0
        error_services = []
        
        for idx, serv in enumerate(serv_list, 1):
            service_id = serv.find('servId').text if serv.find('servId') is not None else ''
            service_name = serv.find('servNm').text if serv.find('servNm') is not None else ''
            detail_url = serv.find('servDtlLink').text if serv.find('servDtlLink') is not None else ''
            sido = serv.find('ctpvNm').text if serv.find('ctpvNm') is not None else ''
            sigungu = serv.find('sggNm').text if serv.find('sggNm') is not None else None
            
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
            
            try:
                parsed = self.parse_service(service_name, target_text, criteria_text, support_text)
                
                # 후처리
                if parsed and 'benefits' in parsed:
                    for benefit in parsed['benefits']:
                        benefit = self.fix_parsed_data(benefit)
                
                if parsed and 'benefits' in parsed and len(parsed.get('benefits', [])) > 0:
                    print("✅")
                    success_count += 1
                else:
                    print("⚠️ (benefits 없음)")
                    error_count += 1
                    error_services.append(service_name)
                
            except Exception as e:
                print(f"❌ (오류: {str(e)[:30]})")
                error_count += 1
                error_services.append(service_name)
                parsed = {"benefits": []}
            
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
        
        print(f"\n{'='*80}")
        print(f"📊 파싱 완료 통계")
        print(f"{'='*80}")
        print(f"✅ 성공: {success_count}개")
        print(f"❌ 실패: {error_count}개")
        print(f"📈 성공률: {success_count / len(serv_list) * 100:.1f}%")
        
        if error_services:
            print(f"\n⚠️ 오류 발생 서비스:")
            for i, name in enumerate(error_services[:10], 1):
                print(f"  {i}. {name}")
            if len(error_services) > 10:
                print(f"  ... 외 {len(error_services) - 10}개")
        
        return services
    
    def save_results(self, results, output_path):
        """결과를 JSON 파일로 저장"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 완료! {len(results)}개 서비스 저장: {output_path}")

# 사용 예시
if __name__ == '__main__':
    import os
    from dotenv import load_dotenv

    load_dotenv()
    API_KEY = os.getenv('OPENAI_API_KEY')
    
    if not API_KEY:
        print("❌ OPENAI_API_KEY를 .env 파일에 설정하세요!")
        exit(1)
    
    parser = WelfareParserV4_5(api_key=API_KEY)
    
    results = parser.batch_parse_xml(
        'wantedDtl포함된xml목록/복지목록경기.xml',
        # limit=1  # n개 파싱
        limit=None  # 전체 파싱
    )
    
    now = datetime.now()
    timestamp = now.strftime("%m%d_%H%M")
    file_name = f"정형화데이터_경기_v4.5_{timestamp}.json"
    
    parser.save_results(results, file_name)
    
    print("\n🎉 v4.5 파싱 완료!")
    print("변경사항:")
    print("  1. income_min_percent 추가 (소득 하한)")
    print("  2. parent_disability_level은 OR 조건에만 사용")
    print("  3. limit_birth_date 추가 (특정 일자 이전 태생)")