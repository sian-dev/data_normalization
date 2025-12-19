"""
복지 데이터 파서 v4.5 (단계별 질문 + 이해 확인) - Gemini API 버전
- ⭐ Step 1: 혜택 개수 파악
- ⭐ Step 2: 각 혜택 조건 파싱
- ⭐ Step 3: 이해 확인 및 재파싱
- Pydantic Schema를 사용하여 JSON 출력 안정화
"""
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal # 🚨 [수정] Literal, List, Dict 등의 타입 힌트 추가
from pydantic import BaseModel, Field, conint, conlist, ConfigDict # 🚨 [수정] ConfigDict import
from google import genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv

# ==============================================================================
# 1. Pydantic 스키마 정의 (JSON 구조 강제)
# ==============================================================================

# Step 1: 혜택 개수 파악
class BenefitCount(BaseModel):
    benefit_count: int = Field(description="확인된 별도 혜택의 개수.")
    benefit_descriptions: List[str] = Field(description="파싱할 혜택별 설명 목록. 예: '대상자 - 지원내용'.")
    reasoning: str = Field(description="혜택을 나눈 이유를 설명.")

# Step 2: 개별 혜택 파싱 - 조건부 JSON 구조
class AndConditions(BaseModel):
    age_min_months: Optional[int] = Field(None, description="최소 나이 (개월 단위, 숫자)")
    age_max_months: Optional[int] = Field(None, description="최대 나이 (개월 단위, 숫자)")
    income_type: Optional[str] = Field(None, description="소득 유형: '기준중위소득' | '차상위계층' | '기초생활수급자'")
    income_max_percent: Optional[conint(ge=1)] = Field(None, description="소득 상한 (%, 숫자)")
    household_type: Optional[str] = Field(None, description="가구 유형 ('한부모', '맞벌이' 등). ⭐주의: 배열이 아닌 문자열만 허용.")
    household_members_min: Optional[conint(ge=1)] = None
    household_members_max: Optional[conint(ge=1)] = None
    children_min: Optional[conint(ge=1)] = None
    children_max: Optional[conint(ge=1)] = None
    birth_order: Optional[conint(ge=1)] = Field(None, description="출생 순서 (1=첫째, 2=둘째, 등).")
    residence_min_months: Optional[conint(ge=1)] = None
    childcare_type: Optional[str] = Field(None, description="양육 형태: '가정' | '어린이집' | '유치원'")
    requires_grandparent_care: Optional[bool] = Field(None, description="조부모 양육 필요 (true 또는 null).")
    requires_dual_income: Optional[bool] = Field(None, description="맞벌이 필요 (true 또는 null).")
    requires_disability: Optional[bool] = Field(None, description="아동 장애 필요 (true 또는 null).")
    requires_parent_disability: Optional[bool] = Field(None, description="부모 장애 필요 (true 또는 null).")
    disability_level: Optional[str] = Field(None, description="장애 등급: '경증' | '중증'.")
    child_has_serious_disease: Optional[bool] = None
    child_has_rare_disease: Optional[bool] = None
    child_has_chronic_disease: Optional[bool] = None
    child_has_cancer: Optional[bool] = None
    parent_has_serious_disease: Optional[bool] = None
    parent_has_rare_disease: Optional[bool] = None
    parent_has_chronic_disease: Optional[bool] = None
    parent_has_cancer: Optional[bool] = None
    parent_has_infertility: Optional[bool] = None
    is_violence_victim: Optional[bool] = None
    is_abuse_victim: Optional[bool] = None
    is_defector: Optional[bool] = None
    is_national_merit: Optional[bool] = None
    is_foster_child: Optional[bool] = None
    is_single_mother: Optional[bool] = None
    is_low_income: Optional[bool] = None
    pregnancy_weeks_min: Optional[conint(ge=1)] = None
    pregnancy_weeks_max: Optional[conint(ge=1)] = None
    birth_within_months: Optional[conint(ge=1)] = None
    education_level: Optional[str] = Field(None, description="교육 수준: '초등' | '중등' | '고등'.")
    is_enrolled: Optional[bool] = None
    housing_type: Optional[str] = Field(None, description="주거 유형: '자가' | '전세' | '월세'.")

class OrConditions(BaseModel):
    household_type: List[str] = Field([], description="가구 유형 OR 조건. ⭐주의: 배열만 허용.")
    income_type: List[str] = Field([], description="소득 유형 OR 조건. ⭐주의: 배열만 허용.")

class ParsedBenefit(BaseModel):
    amount: Optional[int | str] = Field(None, description="지원 금액(숫자) 또는 상세 내용(문자열).")
    amount_type: Optional[str] = Field(None, description="금액 유형: '일시금' | '월' | '년' | '회'.")
    amount_unit: Optional[str] = Field(None, description="금액 단위: '원' | '포인트'.")
    benefit_type: Optional[str] = Field(None, description="혜택 유형: '현금' | '서비스' | '물품' | '감면' | '포인트'.")
    payment_cycle: Optional[str] = Field(None, description="지급 주기: '일시금' | '5회분할' | '매월'.")
    payment_timing: Optional[str] = Field(None, description="지급 시기: '신청 후 다음달' | '즉시'.")
    description: Optional[str] = Field(None, description="지원 내용 상세 설명.")
    and_conditions: AndConditions
    or_conditions: OrConditions

# Step 3: 이해 확인
class VerificationResult(BaseModel):
    is_correct: bool = Field(description="파싱이 정확하면 true, 오류나 누락이 있으면 false.")
    missing_conditions: List[str] = Field(description="원본에 있었으나 누락된 조건 목록.")
    wrong_conditions: List[str] = Field(description="잘못 파싱된 조건과 이유 목록.")
    type_errors: List[str] = Field(description="타입 오류가 발생한 필드 목록.")
    suggestions: str = Field(description="수정 제안.")

# Step 4: 파싱 근거
class ReasoningDetail(BaseModel):
    value: Optional[int | str | List[str] | bool]
    reason: str
    source_text: str
    is_and: Optional[bool]
    is_or: Optional[bool]
    confidence: str

class EmptyReasoning(BaseModel):
    reason: str
    confidence: str
    
class SummaryDetail(BaseModel): # 🚨 [복구] SummaryDetail 클래스 정의 추가
    core_conditions: str
    warnings: List[str]
    need_fix: List[str]
    need_reparse: bool
    overall_confidence: str

class ReasoningResult(BaseModel):
    """
    Step 4: 파싱 결과에 대한 근거 및 요약 정보를 담는 스키마
    """
    
    # 🚨 [수정] ConfigDict import 후 사용
    model_config = ConfigDict(
        extra='ignore',  # 모델 정의에 없는 필드는 무시 (Gemini 호환성 유지)
    )
    
    and_filled_reasoning: Dict[str, ReasoningDetail] = Field(..., description="AND 조건 필드별 근거")
    or_filled_reasoning: Dict[str, ReasoningDetail] = Field(..., description="OR 조건 필드별 근거")
    # and_empty_reasoning 필드는 제외하고 복구
    summary: SummaryDetail = Field(..., description="전체 파싱 결과 요약 및 신뢰도")


class WelfareParserV4_5:
    def __init__(self, api_key):
        """Gemini API 초기화"""
        self.client = genai.Client(api_key=api_key)
        # gpt-4o-mini 대신 gemini-2.5-flash 사용
        self.model = "gemini-2.5-flash"
    
    # WelfareParserV4_5 클래스 내부에 정의되어야 합니다.
    def _call_gemini_json(self, prompt: str, schema: BaseModel) -> dict:
        """Gemini API를 호출하고 JSON 스키마를 적용하여 응답을 받는 헬퍼 함수"""
        
        schema_json = schema.model_json_schema()
        
        # 🚨 [최종 수정된 부분] Pydantic이 생성한 Gemini에서 금지하는 속성 제거
        if 'additionalProperties' in schema_json:
            del schema_json['additionalProperties']
            
        # 모든 $defs 내의 추가 속성도 제거
        if '$defs' in schema_json:
            for def_name in list(schema_json['$defs'].keys()):
                 if 'additionalProperties' in schema_json['$defs'][def_name]:
                     del schema_json['$defs'][def_name]['additionalProperties']

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema_json 
        )
        
        messages = [
            # 롤은 'user'로, 파트는 'text'를 사용하여 프롬프트 내용을 전달합니다.
            types.Content(role="user", parts=[types.Part(text=prompt)])
        ]

        raw_response_text = "API 호출 실패 (텍스트 없음)"
        try:
            # 1. API 호출
            response = self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=config,
            )
            
            raw_response_text = response.text
            
            # 2. JSON 문자열을 딕셔너리로 변환하여 반환
            return json.loads(raw_response_text)

        except json.JSONDecodeError as e:
            # JSON 파싱 실패
            print("\n" + "="*60)
            print(f"🚨🚨 [Step 1 JSON 파싱 실패] 🚨🚨")
            print(f"오류: JSONDecodeError - {str(e)}")
            print(f"Pydantic 스키마: {schema.__name__}")
            print(f"--- [RAW API 응답 텍스트 (JSON이 아님)] ---")
            print(raw_response_text[:500] + ('...' if len(raw_response_text) > 500 else '')) 
            print("="*60 + "\n")
            return {}
            
        except Exception as e:
            # 기타 예외 (APIError, Pydantic ValidationError, 기타 통신 오류 등)
            print("\n" + "="*60)
            print(f"🚨🚨 [Step 1 기타 오류] 🚨🚨")
            print(f"오류 유형: {type(e).__name__} - {str(e)[:100]}")
            print(f"Pydantic 스키마: {schema.__name__}")
            print(f"--- [RAW API 응답 텍스트 (디버깅용)] ---")
            print(raw_response_text[:500] + ('...' if len(raw_response_text) > 500 else '')) 
            print("="*60 + "\n")
            return {}

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
- 지원금액/내용/방식/대상자그룹이 다르면 → 별도 혜택
- 지원금액/내용/방식이 같고 대상자 조건만 OR(또는)로 연결되면 → 1개 혜택

---

위의 원칙에 따라 JSON 형식으로 답하세요.
"""
        return self._call_gemini_json(prompt, BenefitCount)
    
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

【⭐ 필수 JSON 구조 및 규칙 ⭐】

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

위의 규칙을 준수하여 ParsedBenefit 스키마에 맞게 JSON만 반환하세요. 설명 없이!
"""
        return self._call_gemini_json(prompt, ParsedBenefit)
    
    def step3_verify_parsing(self, original_text, parsed_benefit):
        """Step 3: 이해 확인"""
        
        and_cond = parsed_benefit.get('and_conditions', {})
        or_cond = parsed_benefit.get('or_conditions', {})
        
        # 추출된 조건 정리 (출력용)
        extracted = []
        
        # Helper to convert months to years/months for display
        def to_display_age(months):
            if months is None:
                return '제한없음'
            if months < 12:
                return f"{months}개월"
            years = months // 12
            months_rem = months % 12
            return f"{years}세{f' {months_rem}개월' if months_rem > 0 else ''}"

        
        if and_cond.get('age_min_months') or and_cond.get('age_max_months'):
            min_age_display = to_display_age(and_cond.get('age_min_months'))
            max_age_display = to_display_age(and_cond.get('age_max_months'))
            extracted.append(f"나이: {min_age_display} ~ {max_age_display}")
        
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

다음 필드 타입과 의미를 정확히 지켰나요? (ParsedBenefit 스키마 재확인)

【나이 조건】
- age_min_months: 최소 나이 (개월 단위, 숫자)
- age_max_months: 최대 나이 (개월 단위, 숫자)

【소득 조건】
- income_type: 소득 유형 ("기준중위소득" | "차상위계층" | "기초생활수급자")
- income_max_percent: 소득 상한 (%, 숫자)

【가구 조건】
- household_type: 가구 유형 ("한부모" | "조손" | "다문화" | "맞벌이", 문자열!)
    ⭐ 주의: ["한부모"] 같은 배열 금지! 문자열만 허용!
- household_members_min/max: 가구원 수 (숫자)

【자녀 조건】
- children_min/max: 자녀 수 (숫자)
- birth_order: 출생 순서 (1=첫째, 2=둘째, 3=셋째, 숫자)

【OR 조건】
- or_conditions.household_type: 가구형태 OR 조건 (배열, ["한부모", "맞벌이"])
    ⭐ 주의: and_conditions와 달리 배열만 허용!

---

⭐⭐⭐ 중요한 타입 체크:
1. Boolean은 true 또는 null만! false 절대 금지!
2. and_conditions.household_type은 문자열! 배열 금지!
3. or_conditions.household_type은 배열! 문자열 금지!
4. 나이는 무조건 개월 단위 숫자!

---

위의 검토를 기반으로 VerificationResult 스키마에 맞게 JSON 형식으로 답하세요.
"""
        return self._call_gemini_json(prompt, VerificationResult)
    
    def step4_explain_reasoning(self, original_text, parsed_benefit):
        """Step 4: 파싱 근거 확인"""
        
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
{json.dumps(filled_or_fields, ensure_ascii=False, indent=2) if filled_or_fields else 'OR 조건 없음'}

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

위의 질문에 답변하여 ReasoningResult 스키마에 맞게 JSON 형식으로 답하세요.
"""
        return self._call_gemini_json(prompt, ReasoningResult)
    
    def parse_service(self, service_name, target_text, criteria_text, support_text, max_retries=2):
        """전체 파싱 프로세스"""
        
        # 🚨 여기서 오류가 났을 때 RAW 텍스트를 출력하기 위해 전체 try-except를 강화합니다.
        try:
            # Step 1: 혜택 개수 파악
            print(f"\n  🔍 Step 1: 혜택 개수 파악...", end=' ')
            count_result = self.step1_count_benefits(service_name, target_text, criteria_text, support_text)
            
            # 🚨 디버깅: count_result가 비어있다면, _call_gemini_json에서 오류가 발생했음을 의미합니다.
            if not count_result:
                print("❌ Step 1 실패: _call_gemini_json에서 오류 발생 (RAW 응답 텍스트를 위에서 확인하세요).")
                return {"benefits": []}
                
            benefit_count = count_result.get('benefit_count', 1)
            benefit_descriptions = count_result.get('benefit_descriptions', [])
            reasoning = count_result.get('reasoning', '')
            
            print(f"{benefit_count}개")
            if reasoning:
                print(f"      └─ {reasoning}")
            
            # Step 1의 결과가 0개이거나 리스트가 없으면, 전체 텍스트를 하나의 혜택으로 간주하고 진행
            if benefit_count == 0 or not benefit_descriptions:
                benefit_descriptions = [f"대상자: {target_text} / 지원내용: {support_text}"]
                print("  ⚠️ 혜택 개수 0 또는 파악 불가. 전체를 1개 혜택으로 간주하고 진행.")


            benefits = []
            
            # Step 2: 각 혜택 파싱
            for idx, desc in enumerate(benefit_descriptions, 1):
                benefit = {}
                verification = {}
                
                # 시도 횟수 루프
                for attempt in range(max_retries):
                    print(f"  🔍 Step 2-{idx}: 혜택 파싱 (시도 {attempt+1})...", end=' ')
                    if attempt == 0:
                        benefit = self.step2_parse_benefit(service_name, desc, target_text, criteria_text, support_text)
                    else:
                        # 재파싱 시 피드백을 추가
                        feedback = []
                        if verification.get('missing_conditions'):
                            feedback.append(f"누락 조건 수정: {', '.join(verification['missing_conditions'])}")
                        if verification.get('wrong_conditions'):
                            feedback.append(f"오류 조건 수정: {', '.join(verification['wrong_conditions'])}")
                        if verification.get('type_errors'):
                            feedback.append(f"타입 오류 수정: {', '.join(verification['type_errors'])}")
                        
                        retry_desc = desc + f"\n\n**재파싱 피드백**: " + "; ".join(feedback)
                        benefit = self.step2_parse_benefit(service_name, retry_desc, target_text, criteria_text, support_text)
                    
                    if not benefit:
                        print(f"❌ Step 2 실패: API 호출 오류로 빈 응답 수신.")
                        break # Step 2 실패 시 다음 혜택으로 넘어감
                        
                    print("✅")
                    
                    # Step 3: 이해 확인
                    print(f"  ✔️  Step 3-{idx}: 이해 확인...", end=' ')
                    verification = self.step3_verify_parsing(
                        f"{target_text}\n{criteria_text}\n{support_text}",
                        benefit
                    )
                    
                    if verification.get('is_correct'):
                        print("정확!")
                        break # 정확하면 루프 종료
                    else:
                        print(f"⚠️ 재파싱 필요 (재시도 {attempt+1}/{max_retries})")
                        if verification.get('missing_conditions'):
                            print(f"    - 누락: {', '.join(verification['missing_conditions'])}")
                        if verification.get('wrong_conditions'):
                            print(f"    - 오류: {', '.join(verification['wrong_conditions'])}")
                        if verification.get('type_errors'):
                            print(f"    - 타입: {', '.join(verification['type_errors'])}")
                
                # 최종 결과에 대해 Step 4: 근거 확인
                print(f"  📝 Step 4-{idx}: 근거 확인...", end=' ')
                # Step 4는 재시도 루프 바깥에서 최종 결과에 대해 한번만 수행
                reasoning = self.step4_explain_reasoning(
                    f"{target_text}\n{criteria_text}\n{support_text}",
                    benefit
                )
                print("✅")
                
                # 최종 결과 후처리
                benefit = self.fix_parsed_data(benefit)
                
                # 근거 출력
                print(f"\n    ╔══════════════════════════════════════════════════════════════╗")
                print(f"    ║ 【파싱 근거 및 요약】                                        ║")
                print(f"    ╚══════════════════════════════════════════════════════════════╝")
                
                and_filled_reasoning = reasoning.get('and_filled_reasoning', {})
                if and_filled_reasoning:
                    print(f"\n    ✅ AND 조건:")
                    for field, info in and_filled_reasoning.items():
                        print(f"       📌 {field}: {info.get('value')} (원본: '{info.get('source_text')}')")
                        print(f"          └─ {info.get('reason')}")
                
                or_filled_reasoning = reasoning.get('or_filled_reasoning', {})
                if or_filled_reasoning:
                    print(f"\n    🔀 OR 조건:")
                    for field, info in or_filled_reasoning.items():
                        print(f"       📌 {field}: {info.get('value')} (원본: '{info.get('source_text')}')")
                        print(f"          └─ {info.get('reason')}")
                
                summary = reasoning.get('summary', {})
                if summary:
                    print(f"\n    💡 핵심: {summary.get('core_conditions', '요약 없음')}")
                    if summary.get('warnings'):
                        print(f"    ⚠️ 주의: {', '.join(summary['warnings'])}")
                    if summary.get('need_fix'):
                        print(f"    🔧 수정: {', '.join(summary['need_fix'])}")
                    print(f"    신뢰도: {summary.get('overall_confidence', '중간')}")
                
                benefits.append(benefit)
                print()
            
            return {"benefits": benefits}
            
        except Exception as e:
            # parse_service 전체를 포괄하는 예외 처리 (최후의 수단)
            print(f"\n{'='*80}")
            print(f"🚨🚨 [FINAL CATCH: 최상위 파싱 오류] 🚨🚨")
            print(f"오류 유형: {type(e).__name__} - {str(e)}")
            print(f"--- [재시도 안내] ---")
            print(f"이 오류는 주로 API 키 만료, 네트워크 문제, 또는 JSON 스키마를 따르지 않은 응답 때문입니다.")
            print(f"API 키(.env 파일의 GEMINI_API_KEY)를 다시 한번 확인해 주십시오.")
            print(f"{'='*80}")
            return {"benefits": []}

    def fix_parsed_data(self, benefit):
        """파싱 결과 자동 수정 (후처리)"""
        and_cond = benefit.get('and_conditions', {})
        
        # 2. Boolean은 true 또는 null만 허용하므로 False 값 제거
        for key, value in list(and_cond.items()):
            if value is False:
                and_cond[key] = None
                # print(f"    ⚠️ 수정: {key}: false → null (규칙 준수)")
        
        return benefit
    
    def batch_parse_xml(self, xml_path, limit=None):
        """XML 파일 배치 파싱"""
        print(f"📂 XML 파일 읽기: {xml_path}")
        
        # 파일이 로컬에 없거나 경로 오류가 있을 경우를 대비해 파일 접근 처리
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except FileNotFoundError:
            print(f"❌ 오류: XML 파일 경로를 찾을 수 없습니다: {xml_path}")
            return []
        except ET.ParseError:
            print(f"❌ 오류: XML 파일 파싱 오류. 파일 내용 확인이 필요합니다.")
            return []
            
        serv_list = root.findall('.//servList')
        total = len(serv_list)
        
        if limit and limit < total:
            serv_list = serv_list[:limit]
            print(f"📊 총 {total}개 중 {limit}개만 파싱...")
        else:
            print(f"📊 총 {total}개 서비스 파싱 시작...")
        
        services = []
        success_count = 0
        error_count = 0
        
        for idx, serv in enumerate(serv_list, 1):
            service_id = serv.find('servId').text if serv.find('servId') is not None else ''
            service_name = serv.find('servNm').text if serv.find('servNm') is not None else ''
            detail_url = serv.find('servDtlLink').text if serv.find('servDtlLink') is not None else ''
            sido = serv.find('ctpvNm').text if serv.find('ctpvNm') is not None else ''
            sigungu = serv.find('sggNm').text if serv.find('sggNm') is not None else None
            
            # wantedDtl 노드 내 상세 정보 추출
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
            print(f"대상자: {target_text[:50]}...")
            print(f"기준: {criteria_text[:50]}...")
            print(f"지원: {support_text[:50]}...")
            print(f"{'='*80}")
            
            parsed = self.parse_service(service_name, target_text, criteria_text, support_text)
            
            if parsed and 'benefits' in parsed and len(parsed.get('benefits', [])) > 0:
                success_count += 1
            else:
                error_count += 1
            
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
        if len(serv_list) > 0:
            print(f"✅ 성공: {success_count}개")
            print(f"❌ 실패: {error_count}개")
            print(f"📈 성공률: {success_count / len(serv_list) * 100:.1f}%")
        else:
            print("처리된 서비스가 없습니다.")
        
        return services
    
    def save_results(self, results, output_path):
        """결과를 JSON 파일로 저장"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 완료! {len(results)}개 서비스 저장: {output_path}")

# 사용 예시
if __name__ == '__main__':
    
    load_dotenv()
    # 환경 변수 이름을 GEMINI_API_KEY로 변경
    API_KEY = os.getenv('GEMINI_API_KEY')
    
    if not API_KEY:
        # OPENAI 대신 GEMINI API 키 설정 안내
        print("❌ GEMINI_API_KEY를 .env 파일에 설정하세요! (google-genai 라이브러리 필요)")
        exit(1)
    
    parser = WelfareParserV4_5(api_key=API_KEY)
    
    # XML 파일 경로 설정 (사용자 환경에 맞게 조정)
    # 🚨 경로를 실제 파일 위치에 맞게 수정해주세요! (예: './복지목록울산.xml')
    xml_file_path = './wantedDtl포함된xml목록/복지목록울산.xml' 

    results = parser.batch_parse_xml(
        xml_file_path,
        limit=1 # 테스트용으로 주석 처리
    )
    
    now = datetime.now()
    timestamp = now.strftime("%m%d_%H%M")
    file_name = f"정형화데이터_울산_v4.5_{timestamp}_gemini.json"
    
    if results:
        parser.save_results(results, file_name)
    else:
        print("\n❌ 파싱 결과가 없어 파일 저장을 생략합니다.")
    
    print("\n🎉 v4.5 파싱 완료 (Gemini 버전)!")
    print("변경사항:")
    print("  - Gemini API (gemini-2.5-flash) 사용")
    print("  - Pydantic을 이용한 JSON Schema 적용으로 구조화된 출력 보장")
    print("  - API 키 환경변수 이름을 'GEMINI_API_KEY'로 변경")