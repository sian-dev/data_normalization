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

---

이 복지 서비스에는 몇 개의 별도 혜택이 있나요?

【예시로 배우기】

✅ 2개 혜택:
   입력: "첫째 200만원, 둘째 300만원"
   → 혜택1: 첫째 - 200만원
   → 혜택2: 둘째 - 300만원
   이유: 금액이 다름

✅ 2개 혜택:
   입력: "0세 일시금 100만원, 1세 매월 10만원"
   → 혜택1: 0세 - 일시금 100만원
   → 혜택2: 1세 - 매월 10만원
   이유: 나이와 지급방식 모두 다름

✅ 3개 혜택:
   입력: "초등 10만원, 중등 20만원, 고등 30만원"
   → 혜택1: 초등 - 10만원
   → 혜택2: 중등 - 20만원
   → 혜택3: 고등 - 30만원
   이유: 학년별로 금액이 다름

✅ 1개 혜택 (대상자만 다름):
   입력: "한부모 또는 맞벌이 가정 100만원"
   → 혜택1: 한부모 또는 맞벌이 - 100만원
   이유: 지원내용이 같고 대상자만 다름 (OR 조건)

✅ 1개 혜택 (대상자만 다름):
   입력: "임산부, 영아, 85세 이상 교통비 1,000원"
   → 혜택1: 임산부/영아/85세 - 교통비 1,000원
   이유: 지원내용이 같고 대상자만 다름 (OR 조건)

✅ 1개 혜택 (나이 범위):
   입력: "0~2세 매월 50만원"
   → 혜택1: 0~2세 - 매월 50만원
   이유: 나이 범위로 표현, 금액 동일

❌ 잘못된 예:
   입력: "임산부, 영아, 85세 이상 교통비 1,000원"
   잘못: 혜택1: 임산부 - 1,000원
        혜택2: 영아 - 1,000원
        혜택3: 85세 - 1,000원
   → 지원내용이 같으면 1개로 묶어야 함!

---

【핵심 원칙】
- 지원금액/내용/방식이 다르면 → 별도 혜택
- 대상자만 다르면 → 1개 혜택 (OR 조건)

---

JSON 형식으로 답하세요:
{{
  "benefit_count": 숫자,
  "benefit_descriptions": [
    "대상자 - 지원내용",
    "대상자 - 지원내용"
  ],
  "reasoning": "혜택을 이렇게 나눈 이유"
}}
"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a welfare benefit analyzer. Count benefits accurately based on support differences."},
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
    "birth_order": 2,
    "residence_min_months": null,
    "childcare_type": "가정",
    "requires_grandparent_care": null,
    "requires_dual_income": null,
    "requires_disability": null,
    "requires_parent_disability": null,
    "disability_level": null,
    "child_has_serious_disease": null,
    "child_has_rare_disease": null,
    "child_has_chronic_disease": null,
    "child_has_cancer": null,
    "parent_has_serious_disease": null,
    "parent_has_rare_disease": null,
    "parent_has_chronic_disease": null,
    "parent_has_cancer": null,
    "parent_has_infertility": null,
    "is_violence_victim": null,
    "is_abuse_victim": null,
    "is_defector": null,
    "is_national_merit": null,
    "is_foster_child": null,
    "is_single_mother": null,
    "is_low_income": null,
    "pregnancy_weeks_min": null,
    "pregnancy_weeks_max": null,
    "birth_within_months": null,
    "education_level": null,
    "is_enrolled": null,
    "housing_type": null
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

5. ⭐⭐⭐ 중요! AND vs OR 구분:
   - "한부모만" → and_conditions의 household_type: "한부모" (문자열)
   - "한부모 또는 맞벌이" → or_conditions의 household_type: ["한부모", "맞벌이"] (배열)
   
   ❌ 잘못된 예:
   and_conditions의 household_type: ["한부모"]  → 배열 금지!
   
   ✅ 올바른 예:
   and_conditions의 household_type: "한부모"  → 문자열만!
   or_conditions의 household_type: ["한부모", "맞벌이"]  → 배열만!

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

다음 필드 타입과 의미를 정확히 지켰나요?

【나이 조건】
- age_min_months: 최소 나이 (개월 단위, 숫자)
- age_max_months: 최대 나이 (개월 단위, 숫자)

【소득 조건】
- income_type: 소득 유형 ("기준중위소득" | "차상위계층" | "기초생활수급자")
- income_max_percent: 소득 상한 (%, 숫자)

【가구 조건】
- household_type: 가구 유형 ("한부모" | "조손" | "다문화" | "맞벌이", 문자열!)
  ⭐ 주의: ["한부모"] 같은 배열 금지! 문자열만 허용!
- household_members_min: 최소 가구원 수 (숫자)
- household_members_max: 최대 가구원 수 (숫자)

【자녀 조건】
- children_min: 최소 자녀 수 (숫자)
- children_max: 최대 자녀 수 (숫자)
- birth_order: 출생 순서 (1=첫째, 2=둘째, 3=셋째, 숫자)

【거주/양육 조건】
- residence_min_months: 최소 거주 기간 (개월, 숫자)
- childcare_type: 양육 형태 ("가정" | "어린이집" | "유치원")
- requires_grandparent_care: 조부모 양육 필요 (true만 허용, null)
- requires_dual_income: 맞벌이 필요 (true만 허용, null)

【장애 조건】
- requires_disability: 아동 장애 필요 (true만 허용, null)
- requires_parent_disability: 부모 장애 필요 (true만 허용, null)
- disability_level: 장애 등급 ("경증" | "중증")

【질환 조건】
- child_has_serious_disease: 아동 중증질환 (true만 허용, null)
- child_has_rare_disease: 아동 희귀질환 (true만 허용, null)
- child_has_chronic_disease: 아동 만성질환 (true만 허용, null)
- child_has_cancer: 아동 암 (true만 허용, null)
- parent_has_serious_disease: 부모 중증질환 (true만 허용, null)
- parent_has_rare_disease: 부모 희귀질환 (true만 허용, null)
- parent_has_chronic_disease: 부모 만성질환 (true만 허용, null)
- parent_has_cancer: 부모 암 (true만 허용, null)
- parent_has_infertility: 부모 난임 (true만 허용, null)

【특수 상황】
- is_violence_victim: 가정폭력 피해자 (true만 허용, null)
- is_abuse_victim: 아동학대 피해자 (true만 허용, null)
- is_defector: 북한이탈주민 (true만 허용, null)
- is_national_merit: 국가유공자 (true만 허용, null)
- is_foster_child: 가정위탁아동 (true만 허용, null)
- is_single_mother: 미혼모 (true만 허용, null)
- is_low_income: 저소득층 (true만 허용, null)

【임신/출산 조건】
- pregnancy_weeks_min: 최소 임신 주수 (숫자)
- pregnancy_weeks_max: 최대 임신 주수 (숫자)
- birth_within_months: 출산 후 신청 기한 (개월, 숫자)

【교육 조건】
- education_level: 교육 수준 ("초등" | "중등" | "고등")
- is_enrolled: 재학 여부 (true만 허용, null)

【주거 조건】
- housing_type: 주거 유형 ("자가" | "전세" | "월세")

【OR 조건】
- or_conditions.household_type: 가구형태 OR 조건 (배열, ["한부모", "맞벌이"])
  ⭐ 주의: and_conditions와 달리 배열만 허용!
- or_conditions.income_type: 소득유형 OR 조건 (배열, ["기준중위소득", "차상위계층"])

---

⭐⭐⭐ 중요한 타입 체크:
1. Boolean은 true 또는 null만! false 절대 금지!
2. and_conditions.household_type은 문자열! 배열 금지!
3. or_conditions.household_type은 배열! 문자열 금지!
4. 나이는 무조건 개월 단위 숫자!

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
    
    def step4_explain_reasoning(self, original_text, parsed_benefit):
        """Step 4: 파싱 근거 확인"""
        import json
        
        and_cond = parsed_benefit.get('and_conditions', {})
        or_cond = parsed_benefit.get('or_conditions', {})
        
        # 값이 있는 필드와 없는 필드 분류
        filled_and_fields = {k: v for k, v in and_cond.items() if v is not None}
        empty_and_fields = [k for k, v in and_cond.items() if v is None]
        
        filled_or_fields = {k: v for k, v in or_cond.items() if v and len(v) > 0}
        
        prompt = f"""
원본 텍스트:
{original_text}

파싱한 결과:
AND 조건 (모두 만족 필요):
{json.dumps(filled_and_fields, ensure_ascii=False, indent=2)}

OR 조건 (하나라도 만족):
{json.dumps(filled_or_fields, ensure_ascii=False, indent=2)}

---

【질문 1】 AND 조건 필드의 근거를 설명하세요.

다음 필드에 왜 그 값을 넣었나요? 원본 텍스트의 어느 부분을 보고 판단했나요?

{chr(10).join(f"- {k}: {v} (AND 조건)" for k, v in filled_and_fields.items())}

---

【질문 2】 OR 조건 필드의 근거를 설명하세요.

다음 필드는 왜 OR 조건으로 설정했나요? "또는", "혹은" 같은 표현이 있었나요?

{chr(10).join(f"- {k}: {v} (OR 조건)" for k, v in filled_or_fields.items()) if filled_or_fields else "OR 조건 없음"}

---

【질문 3】 값이 없는 AND 조건 필드를 왜 비웠나요?

다음 필드는 왜 null로 유지했나요? 원본 텍스트에 해당 조건이 없었나요?

필드 목록:
{chr(10).join(f"- {field}" for field in empty_and_fields[:10])}
{"..." if len(empty_and_fields) > 10 else ""}

---

【질문 4】 총 요약 및 주의사항

이 파싱 결과에 대해:
1. 핵심 조건 요약 (한 문장)
2. 주의해야 할 점이나 애매한 부분
3. 수정이 필요할 수 있는 부분
4. 재파싱이 필요한지 여부

---

JSON 형식으로 답하세요:
{{
  "and_filled_reasoning": {{
    "age_max_months": {{
      "value": 11,
      "reason": "원본에 '0세'라는 표현이 있어서 만 0세(0~11개월)를 의미",
      "source_text": "0세 아동",
      "is_and": true,
      "confidence": "높음"
    }},
    "income_max_percent": {{
      "value": 150,
      "reason": "원본에 '기준중위소득 150% 이하'라는 명확한 표현",
      "source_text": "기준중위소득 150% 이하",
      "is_and": true,
      "confidence": "높음"
    }}
  }},
  "or_filled_reasoning": {{
    "household_type": {{
      "value": ["한부모", "맞벌이"],
      "reason": "원본에 '한부모 또는 맞벌이 가정'이라는 OR 표현이 명확함",
      "source_text": "한부모 또는 맞벌이 가정",
      "is_or": true,
      "confidence": "높음"
    }}
  }},
  "and_empty_reasoning": {{
    "household_type": {{
      "reason": "원본에 가구형태 제한이 없음. 모든 가구 대상",
      "confidence": "높음"
    }},
    "requires_disability": {{
      "reason": "원본에 장애 관련 조건이 없음",
      "confidence": "높음"
    }}
  }},
  "summary": {{
    "core_conditions": "0세 아동, 기준중위소득 150% 이하, 한부모 또는 맞벌이 가정 대상",
    "warnings": [
      "birth_within_months는 원본에 명시되지 않아 관례상 12개월로 추정함",
      "residence_min_months도 원본에 없어서 null 처리했으나 확인 필요"
    ],
    "need_fix": [
      "임산부 조건('임산부 또는 영아')이 원본에 있으나 현재 구조로 표현 불가"
    ],
    "need_reparse": false,
    "overall_confidence": "중간 - 일부 조건 추정함"
  }}
}}
"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a data reasoning explainer. Explain your parsing decisions clearly with AND/OR distinction."},
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
            reasoning = count_result.get('reasoning', '')
            
            print(f"{benefit_count}개")
            if reasoning:
                print(f"      └─ {reasoning}")
            
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
                    
                    # Step 4: 근거 확인 (정확한 경우에만)
                    print(f"  📝 Step 4-{idx}: 근거 확인...", end=' ')
                    reasoning = self.step4_explain_reasoning(
                        f"{target_text}\n{criteria_text}\n{support_text}",
                        benefit
                    )
                    print("✅")
                    
                    # 근거 출력
                    print(f"\n    ╔══════════════════════════════════════════════════════════════╗")
                    print(f"    ║ 【파싱 근거】                                                ║")
                    print(f"    ╚══════════════════════════════════════════════════════════════╝")
                    
                    # AND 조건 - 값이 있는 필드
                    and_filled_reasoning = reasoning.get('and_filled_reasoning', {})
                    if and_filled_reasoning:
                        print(f"\n    ✅ AND 조건 (값이 있는 필드):")
                        for field, info in and_filled_reasoning.items():
                            print(f"       📌 {field}: {info.get('value')}")
                            print(f"          └─ {info.get('reason')}")
                    
                    # OR 조건 - 값이 있는 필드
                    or_filled_reasoning = reasoning.get('or_filled_reasoning', {})
                    if or_filled_reasoning:
                        print(f"\n    🔀 OR 조건 (값이 있는 필드):")
                        for field, info in or_filled_reasoning.items():
                            print(f"       📌 {field}: {info.get('value')}")
                            print(f"          └─ {info.get('reason')}")
                    
                    # AND 조건 - 값이 없는 필드
                    and_empty_reasoning = reasoning.get('and_empty_reasoning', {})
                    if and_empty_reasoning:
                        print(f"\n    ⭕ AND 조건 (값이 없는 필드):")
                        for field, info in and_empty_reasoning.items():
                            print(f"       📌 {field}: null")
                            print(f"          └─ {info.get('reason')}")
                    
                    # 총 요약
                    summary = reasoning.get('summary', {})
                    if summary:
                        print(f"\n    ╔══════════════════════════════════════════════════════════════╗")
                        print(f"    ║ 【총 요약】                                                  ║")
                        print(f"    ╚══════════════════════════════════════════════════════════════╝")
                        
                        if summary.get('core_conditions'):
                            print(f"\n    💡 핵심: {summary['core_conditions']}")
                        
                        if summary.get('warnings'):
                            print(f"\n    ⚠️  주의:")
                            for warning in summary['warnings']:
                                print(f"       - {warning}")
                        
                        if summary.get('need_fix'):
                            print(f"\n    🔧 수정 필요:")
                            for fix in summary['need_fix']:
                                print(f"       - {fix}")
                        
                        if summary.get('need_reparse'):
                            print(f"\n    🔄 재파싱 권장")
                        
                        print(f"\n    신뢰도: {summary.get('overall_confidence', '중간')}")
                    
                    print()  # 줄바꿈
                    
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
                        
                        # 재파싱 후에도 근거 확인
                        print(f"  📝 Step 4-{idx}: 재파싱 근거 확인...", end=' ')
                        reasoning = self.step4_explain_reasoning(
                            f"{target_text}\n{criteria_text}\n{support_text}",
                            retry_benefit
                        )
                        print("✅")
                        
                        # 재파싱 근거 출력 - 모든 필드 나열
                        print(f"\n    ╔══════════════════════════════════════════════════════════════╗")
                        print(f"    ║ 【재파싱 근거】                                              ║")
                        print(f"    ╚══════════════════════════════════════════════════════════════╝")
                        
                        # AND 조건 - 값이 있는 필드
                        and_filled = reasoning.get('and_filled_reasoning', {})
                        if and_filled:
                            print(f"\n    ✅ AND 조건 (값이 있는 필드):")
                            for field, info in and_filled.items():
                                print(f"       📌 {field}: {info.get('value')}")
                                print(f"          └─ {info.get('reason')}")
                        
                        # OR 조건 - 값이 있는 필드
                        or_filled = reasoning.get('or_filled_reasoning', {})
                        if or_filled:
                            print(f"\n    🔀 OR 조건 (값이 있는 필드):")
                            for field, info in or_filled.items():
                                print(f"       📌 {field}: {info.get('value')}")
                                print(f"          └─ {info.get('reason')}")
                        
                        # AND 조건 - 값이 없는 필드
                        and_empty = reasoning.get('and_empty_reasoning', {})
                        if and_empty:
                            print(f"\n    ⭕ AND 조건 (값이 없는 필드):")
                            for field, info in and_empty.items():
                                print(f"       📌 {field}: null")
                                print(f"          └─ {info.get('reason')}")
                        
                        # 총 요약
                        summary = reasoning.get('summary', {})
                        if summary:
                            print(f"\n    ╔══════════════════════════════════════════════════════════════╗")
                            print(f"    ║ 【총 요약】                                                  ║")
                            print(f"    ╚══════════════════════════════════════════════════════════════╝")
                            
                            if summary.get('core_conditions'):
                                print(f"\n    💡 핵심: {summary['core_conditions']}")
                            
                            if summary.get('warnings'):
                                print(f"\n    ⚠️  주의:")
                                for warning in summary['warnings']:
                                    print(f"       - {warning}")
                            
                            if summary.get('need_fix'):
                                print(f"\n    🔧 수정 필요:")
                                for fix in summary['need_fix']:
                                    print(f"       - {fix}")
                            
                            print(f"\n    신뢰도: {summary.get('overall_confidence', '중간')}")
                        
                        print()
                        
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
    from datetime import datetime

    load_dotenv()
    API_KEY = os.getenv('OPENAI_API_KEY')
    
    if not API_KEY:
        print("❌ OPENAI_API_KEY를 .env 파일에 설정하세요!")
        exit(1)
    
    parser = WelfareParserV4_5(api_key=API_KEY)
    
    results = parser.batch_parse_xml(
        'wantedDtl포함된xml목록/복지목록울산.xml',
        # 'wantedDtl포함된xml목록/복지목록중앙부.xml',
        limit=1  # 테스트용
    )
    
    now = datetime.now()
    timestamp = now.strftime("%m%d_%H%M")
    # file_name = f"정형화데이터_중앙부_v4.5_{timestamp}.json"
    file_name = f"정형화데이터_울산_v4.5_{timestamp}.json"
    
    parser.save_results(results, file_name)
    
    print("\n🎉 v4.5 파싱 완료!")
    print("변경사항:")
    print("  1. Step 1: 혜택 개수 파악 + reasoning")
    print("  2. Step 2: 각 혜택 개별 파싱")
    print("  3. Step 3: 이해 확인 및 타입 검증 (필드별 설명)")
    print("  4. Step 4: 파싱 근거 설명 (AND/OR 구분)")
    print("  5. 재파싱 시 구체적 피드백")
    print("  6. AND household_type: 문자열, OR household_type: 배열")