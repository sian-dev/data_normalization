"""
복지 데이터 파서 v4.5 (단계별 질문 + 이해 확인)
- ⭐ Step 1: 혜택 개수 파악
- ⭐ Step 2: 각 혜택 조건 파싱
- ⭐ Step 3: 이해 확인 및 재파싱
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
    
    def step1_count_benefits(self, service_name, target_text, criteria_text, support_text):
        """Step 1: 혜택 개수 파악"""
        prompt = f"""
서비스명: {service_name}
대상자: {target_text}
선정기준: {criteria_text}
지원내용: {support_text}

이 복지 서비스에는 몇 개의 별도 혜택(benefit)이 있나요?

조건이 다르면 별도 혜택입니다:
- "0세 100만원, 1세 50만원" → 2개
- "첫째 200만원, 둘째 300만원" → 2개
- "기준중위소득 80% 50만원, 120% 30만원" → 2개

조건이 같으면 1개입니다:
- "0~2세 매월 50만원" → 1개
- "한부모 또는 맞벌이 가정 100만원" → 1개

JSON 형식으로 답하세요:
{{
  "benefit_count": 숫자,
  "benefit_descriptions": [
    "혜택1 설명",
    "혜택2 설명"
  ]
}}
"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a welfare benefit analyzer. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def step2_parse_benefit(self, service_name, benefit_description, target_text, criteria_text, support_text):
        """Step 2: 개별 혜택 파싱"""
        prompt = f"""
서비스명: {service_name}
혜택 설명: {benefit_description}

전체 정보:
대상자: {target_text}
선정기준: {criteria_text}
지원내용: {support_text}

---

【⭐ 필수 JSON 구조 ⭐】

{{
  "amount": 숫자 또는 null,
  "amount_type": "일시금" | "월" | "년" | "회" | null,
  "amount_unit": "원" | "포인트" | null,
  "benefit_type": "현금" | "서비스" | "물품" | "감면" | "포인트",
  "payment_cycle": "일시금" | "5회분할" | "매월" | null,
  "payment_timing": "신청 후 다음달" | "즉시" | null,
  "description": "상세 설명",

  "and_conditions": {{
    "age_min_months": 1,
    "age_max_months": 11,
    "income_type": "기준중위소득",
    "income_max_percent": 150,
    "household_type": "한부모",
    "household_members_min": null,
    "household_members_max": null,
    "children_min": null,
    "children_max": null,
    "birth_order": 1,
    "birth_within_months": null,
  }},
  "or_conditions": {{
    "household_type": ["한부모", "맞벌이"],
    "income_type": []
  }}
}}

---

【⭐ 핵심 규칙 ⭐】

1. "0세", "1세" = 나이 (age_max_months)
   "첫째", "둘째" = 출생순서 (birth_order)

2. "출생 후 12개월 이내 신청" → birth_within_months: 12
   "0세 아동" → age_max_months: 11

3. Boolean은 true 또는 null만! false 금지!

4. 나이는 무조건 개월 단위!
   "85세" → age_min_months: 1020 (85 × 12)

5. "한부모 또는 맞벌이" → or_conditions의 household_type: ["한부모", "맞벌이"]
   "한부모만" → and_conditions의 household_type: "한부모"

---

JSON만 반환하세요. 설명 없이!
"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a welfare data parser. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def step3_verify_parsing(self, original_text, parsed_benefit):
        """Step 3: 이해 확인"""
        and_cond = parsed_benefit.get('and_conditions', {})
        or_cond = parsed_benefit.get('or_conditions', {})
        
        # 추출된 조건 정리
        extracted = []
        
        if and_cond.get('age_min_months') or and_cond.get('age_max_months'):
            min_age = and_cond.get('age_min_months', 0)
            max_age = and_cond.get('age_max_months', '제한없음')
            extracted.append(f"나이: {min_age}개월 ~ {max_age}개월")
        
        if and_cond.get('income_type'):
            income_text = f"{and_cond['income_type']} {and_cond.get('income_max_percent', '')}%"
            extracted.append(f"소득: {income_text}")
        
        if and_cond.get('household_type'):
            extracted.append(f"가구형태: {and_cond['household_type']}")
        
        if and_cond.get('birth_order'):
            order_text = {1: "첫째", 2: "둘째", 3: "셋째"}.get(and_cond['birth_order'], f"{and_cond['birth_order']}째")
            extracted.append(f"출생순서: {order_text}")
        
        if and_cond.get('childcare_type'):
            extracted.append(f"양육형태: {and_cond['childcare_type']}")
        
        if or_cond.get('household_type'):
            extracted.append(f"가구형태(OR): {' 또는 '.join(or_cond['household_type'])}")
        
        if or_cond.get('income_type'):
            extracted.append(f"소득(OR): {' 또는 '.join(or_cond['income_type'])}")
        
        prompt = f"""
원본 텍스트:
{original_text}

추출한 조건:
{chr(10).join(f"- {item}" for item in extracted)}

---

다음 데이터를 정확히 추출했나요?

1. 나이 조건 (0세, 1세, 영아, 85세 등)
2. 소득 조건 (기준중위소득 %, 차상위, 기초생활수급자 등)
3. 가구형태 (한부모, 조손, 다문화, 맞벌이)
4. 출생순서 (첫째, 둘째, 셋째)
5. 양육형태 (가정양육, 어린이집, 유치원)
6. 특수조건 (장애, 질환, 임산부 등)

---

다음 필드 타입을 정확히 지켰나요?

- age_min_months: 숫자 또는 null
- age_max_months: 숫자 또는 null
- income_type: "기준중위소득" | "차상위계층" | "기초생활수급자" | null
- income_max_percent: 숫자 또는 null
- household_type: "한부모" | "조손" | "다문화" | "맞벌이" | null
- household_members_min: 숫자 또는 null
- household_members_max: 숫자 또는 null
- children_min: 숫자 또는 null
- children_max: 숫자 또는 null
- birth_order: 1 | 2 | 3 | 숫자 | null
- residence_min_months: 숫자 또는 null
- childcare_type: "가정" | "어린이집" | "유치원" | null
- requires_grandparent_care: true | null
- requires_dual_income: true | null
- requires_disability: true | null
- requires_parent_disability: true | null
- disability_level: "경증" | "중증" | null
- child_has_serious_disease: true | null
- child_has_rare_disease: true | null
- child_has_chronic_disease: true | null
- child_has_cancer: true | null
- parent_has_serious_disease: true | null
- parent_has_rare_disease: true | null
- parent_has_chronic_disease: true | null
- parent_has_cancer: true | null
- parent_has_infertility: true | null
- is_violence_victim: true | null
- is_abuse_victim: true | null
- is_defector: true | null
- is_national_merit: true | null
- is_foster_child: true | null
- is_single_mother: true | null
- is_low_income: true | null
- pregnancy_weeks_min: 숫자 또는 null
- pregnancy_weeks_max: 숫자 또는 null
- birth_within_months: 숫자 또는 null
- education_level: "초등" | "중등" | "고등" | null
- is_enrolled: true | null
- housing_type: "자가" | "전세" | "월세" | null

---

JSON 형식으로 답하세요:
{{
  "is_correct": true 또는 false,
  "missing_conditions": ["누락된 조건1", "누락된 조건2"],
  "wrong_conditions": ["잘못된 조건1: 이유"],
  "type_errors": ["필드명: 타입오류 설명"],
  "suggestions": "수정 제안"
}}
"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a data verification expert. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def parse_service(self, service_name, target_text, criteria_text, support_text, max_retries=2):
        """전체 파싱 프로세스"""
        import time
        
        try:
            # Step 1: 혜택 개수 파악
            print(f"\n  🔍 Step 1: 혜택 개수 파악...", end=' ')
            count_result = self.step1_count_benefits(service_name, target_text, criteria_text, support_text)
            benefit_count = count_result.get('benefit_count', 1)
            benefit_descriptions = count_result.get('benefit_descriptions', [])
            print(f"{benefit_count}개")
            
            benefits = []
            
            # Step 2: 각 혜택 파싱
            for idx, desc in enumerate(benefit_descriptions, 1):
                print(f"  🔍 Step 2-{idx}: 혜택 파싱...", end=' ')
                benefit = self.step2_parse_benefit(service_name, desc, target_text, criteria_text, support_text)
                print("✅")
                
                # Step 3: 이해 확인
                print(f"  ✔️  Step 3-{idx}: 이해 확인...", end=' ')
                verification = self.step3_verify_parsing(
                    f"{target_text}\n{criteria_text}\n{support_text}",
                    benefit
                )
                
                if verification.get('is_correct'):
                    print("정확!")
                    benefits.append(benefit)
                else:
                    print("⚠️ 재파싱 필요")
                    
                    # 누락/오류 정보 출력
                    if verification.get('missing_conditions'):
                        print(f"    - 누락: {', '.join(verification['missing_conditions'])}")
                    if verification.get('wrong_conditions'):
                        print(f"    - 오류: {', '.join(verification['wrong_conditions'])}")
                    if verification.get('type_errors'):
                        print(f"    - 타입: {', '.join(verification['type_errors'])}")
                    
                    # 재파싱 (최대 1회)
                    if max_retries > 0:
                        print(f"  🔄 재파싱 중...", end=' ')
                        
                        # 피드백 포함하여 재파싱
                        feedback = []
                        if verification.get('missing_conditions'):
                            feedback.append(f"누락: {', '.join(verification['missing_conditions'])}")
                        if verification.get('wrong_conditions'):
                            feedback.append(f"오류: {', '.join(verification['wrong_conditions'])}")
                        if verification.get('type_errors'):
                            feedback.append(f"타입: {', '.join(verification['type_errors'])}")
                        
                        retry_benefit = self.step2_parse_benefit(
                            service_name,
                            desc + f"\n\n주의사항:\n" + "\n".join(feedback),
                            target_text,
                            criteria_text,
                            support_text
                        )
                        print("✅")
                        benefits.append(retry_benefit)
                    else:
                        benefits.append(benefit)
            
            return {"benefits": benefits}
            
        except Exception as e:
            print(f"❌ 오류: {str(e)[:50]}")
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
        
        # 2. False 값 제거
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
            
            print(f"\n{'='*80}")
            print(f"[{idx}/{len(serv_list)}] {service_name}")
            print(f"{'='*80}")
            
            try:
                parsed = self.parse_service(service_name, target_text, criteria_text, support_text)
                
                # 후처리
                if parsed and 'benefits' in parsed:
                    for benefit in parsed['benefits']:
                        benefit = self.fix_parsed_data(benefit)
                
                if parsed and 'benefits' in parsed and len(parsed.get('benefits', [])) > 0:
                    success_count += 1
                else:
                    error_count += 1
                
            except Exception as e:
                print(f"  ❌ 전체 오류: {str(e)[:50]}")
                error_count += 1
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
        'wantedDtl포함된xml목록/복지목록울산.xml',
        # 'wantedDtl포함된xml목록/복지목록중앙부.xml',
        limit=3  # 테스트용
    ) 
    
    now = datetime.now()
    timestamp = now.strftime("%m%d_%H%M")

    # file_name = f"정형화데이터_중앙부_v4.2_{timestamp}.json"
    file_name = f"정형화데이터_울산_v4.2_{timestamp}.json"

    parser.save_results(results, file_name)
    
    print("\n🎉 v4.5 파싱 완료!")
    print("변경사항:")
    print("  1. Step 1: 혜택 개수 파악 (조건별 분리)")
    print("  2. Step 2: 각 혜택 개별 파싱")
    print("  3. Step 3: 이해 확인 및 재파싱")
    print("  4. 정확도 향상 예상")