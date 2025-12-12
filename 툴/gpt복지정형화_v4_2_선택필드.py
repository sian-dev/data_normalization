"""
복지 데이터 파서 v4.2 (프롬프트 강화 및 간결화)
- ⭐ 필드명 강제, 사용 가능 필드 목록 명시
- ⭐ 규칙 간결화 및 강화
"""
import json
from datetime import datetime
from openai import OpenAI
import xml.etree.ElementTree as ET

class WelfareParserV4_2:
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

{{
  "benefits": [
    {{
      "amount": 1000000,
      "amount_type": "월",
      "amount_unit": "원",
      "benefit_type": "현금",
      "payment_cycle": "매월",
      "description": "설명",
      
      "and_conditions": {{
        "age_max_months": 11,
        "income_type": "기준중위소득",
        "income_max_percent": 150
      }},
      "or_conditions": {{}}
    }}
  ]
}}

---

【❌ 절대 금지 필드명 ❌】

다음 필드는 절대 사용 금지! 대신 지정된 필드 사용:

❌ age_min_years → ✅ age_min_months (나이는 무조건 개월 단위!)
❌ age_max_years → ✅ age_max_months
❌ age_years → ✅ age_min_months 또는 age_max_months
❌ disability_severity → ✅ disability_level
❌ is_pregnant → ✅ parent_has_infertility 또는 pregnancy_weeks_min
❌ is_homeless, is_emergency_patient, is_unclaimed_deceased → 사용 금지
❌ activity_support_score_min → 사용 금지

변환 예시:
- "85세 이상" → age_min_months: 1020 (85 × 12)
- "6세~64세" → age_min_months: 72, age_max_months: 768

---

【✅ 사용 가능한 필드만 ✅】

아래 필드만 사용! 이 목록에 없으면 절대 만들지 마세요!

## 나이 (무조건 개월 단위!)
age_min_months, age_max_months

## 소득
income_type ("기준중위소득" | "차상위계층" | "기초생활수급자")
income_max_percent

## 가구
household_type ("한부모" | "조손" | "다문화" | "맞벌이")
household_members_min, household_members_max

## 자녀
children_min, children_max (자녀 수)
birth_order (1=첫째, 2=둘째, 3=셋째)

## 장애
requires_disability (아동 장애)
requires_parent_disability (부모 장애)
disability_level ("경증" | "중증")

## 질환
child_has_serious_disease, child_has_rare_disease, child_has_chronic_disease, child_has_cancer
parent_has_serious_disease, parent_has_rare_disease, parent_has_chronic_disease, parent_has_cancer, parent_has_infertility

## 특수상황
is_violence_victim, is_abuse_victim, is_defector, is_national_merit, is_foster_child, is_single_mother, is_low_income

## 양육
childcare_type ("가정" | "어린이집" | "유치원")
requires_grandparent_care, requires_dual_income

## 임신출산
pregnancy_weeks_min, pregnancy_weeks_max
birth_within_months (출산 후 신청기한)

## 기타
residence_min_months (거주기간)
education_level ("초등" | "중등" | "고등")
is_enrolled (재학여부)
housing_type ("자가" | "전세" | "월세")

---

【⭐ 핵심 규칙 ⭐】

1. 조건이 다르면 → 별도 benefit
   예: "0세 100만원, 1세 50만원" → benefits 2개

2. "0세", "1세" = 나이! 출생순서 아님!
   "첫째", "둘째" = 출생순서!

3. "출생 후 12개월 이내 신청" → birth_within_months: 12
   "0세 아동" → age_max_months: 11

4. Boolean은 true 또는 null만! false 금지!

5. 나이는 무조건 개월 단위!
   "85세" → age_min_months: 1020

---

JSON만 반환하세요. 설명 없이!
"""
        
        import time
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a welfare data parser. Return only valid JSON. Follow field name rules strictly."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
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
    
    def fix_parsed_data(self, benefit):
        """파싱 결과 자동 수정 (후처리)"""
        and_cond = benefit.get('and_conditions', {})
        
        # 1. years → months 자동 변환
        if 'age_min_years' in and_cond:
            years = and_cond.pop('age_min_years')
            and_cond['age_min_months'] = years * 12
            print(f"    ⚠️ 수정: age_min_years: {years} → age_min_months: {years * 12}")
        
        if 'age_max_years' in and_cond:
            years = and_cond.pop('age_max_years')
            and_cond['age_max_months'] = years * 12
            print(f"    ⚠️ 수정: age_max_years: {years} → age_max_months: {years * 12}")
        
        if 'age_years' in and_cond:
            years = and_cond.pop('age_years')
            and_cond['age_max_months'] = years * 12
            print(f"    ⚠️ 수정: age_years: {years} → age_max_months: {years * 12}")
        
        # 2. disability_severity → disability_level
        if 'disability_severity' in and_cond:
            value = and_cond.pop('disability_severity')
            and_cond['disability_level'] = value
            print(f"    ⚠️ 수정: disability_severity → disability_level: {value}")
        
        # 3. False 값 제거
        for key, value in list(and_cond.items()):
            if value is False:
                and_cond[key] = None
                print(f"    ⚠️ 수정: {key}: false → null")
        
        # 4. 지원하지 않는 필드 제거
        unsupported = [
            'is_homeless', 'is_emergency_patient', 'is_unclaimed_deceased',
            'activity_support_score_min', 'is_pregnant'
        ]
        
        for field in unsupported:
            if field in and_cond:
                and_cond.pop(field)
                print(f"    ⚠️ 제거: {field} (DB 미지원)")
        
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
                
                # ⭐ 후처리: 자동 수정
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
    
    parser = WelfareParserV4_2(api_key=API_KEY)
    
    results = parser.batch_parse_xml(
        # 'wantedDtl포함된xml목록/복지목록울산.xml',
        'wantedDtl포함된xml목록/복지목록중앙부.xml',
        limit=None  # 전체 파싱
    )
    
    now = datetime.now()
    timestamp = now.strftime("%m%d_%H%M")
    file_name = f"정형화데이터_중앙부_v4.2_{timestamp}.json"
    # file_name = f"정형화데이터_울산_v4.2_{timestamp}.json"
    
    parser.save_results(results, file_name)
    
    print("\n🎉 v4.2 파싱 완료!")
    print("변경사항:")
    print("  1. 프롬프트 대폭 간결화 (800줄 → 150줄)")
    print("  2. 필드명 강제 규칙 추가")
    print("  3. 사용 가능 필드 목록 명시")
    print("  4. 자동 후처리 (years→months, 필드 제거)")