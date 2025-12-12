"""
복지 데이터 파서 v4.0 (완전판)
- ⭐⭐⭐ v4.0 핵심 변경: Benefits 중심 구조!
- 모든 조건은 benefits 내부에 포함
- 서비스 레벨 조건 제거 (지역만 서비스 레벨)
- 혜택별 독립적인 조건
"""
import json
from datetime import datetime
from openai import OpenAI
import xml.etree.ElementTree as ET

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
      // 혜택 정보 (필수)
      "amount": 1000000,
      "amount_type": "월",
      "amount_unit": "원",
      "benefit_type": "현금",
      "payment_cycle": "매월",
      "payment_method": "계좌입금",
      "payment_timing": "신청 후 다음달",
      "description": "0세 가정 양육 월 100만원 지원",
      
      // ⭐ 이 혜택의 조건 (필수!)
      "and_conditions": {{
        // 사용할 조건만 입력! 해당 없으면 빈 객체 {{}}
        "age_min_months": 0,
        "age_max_months": 11,
        "income_type": "기준중위소득",
        "income_max_percent": 150,
        "childcare_type": "가정",
        "birth_order": 1,
        "birth_within_months": 12,
        "residence_min_months": 6
      }},
      "or_conditions": {{
        // OR 조건이 있으면 입력! 없으면 빈 객체 {{}}
        "household_type": ["맞벌이", "한부모"]
      }}
    }}
  ]
}}

⚠️ 중요: 위 예시는 완전한 형태입니다!
- and_conditions에 필요한 조건만 입력하세요
- 없는 조건은 생략하거나 null로 설정
- 예시에 없는 다른 조건도 사용 가능 (아래 조건 목록 참고)

❌❌❌ 절대 금지 ❌❌❌
{{
  "and_conditions": {{ ... }},  // 최상위 레벨 금지!
  "or_conditions": {{ ... }},   // 최상위 레벨 금지!
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

예시 2: 가정양육 100만원, 어린이집 46만원
→ benefits 2개 (양육방식 다름)

{{
  "benefits": [
    {{
      "amount": 1000000,
      "and_conditions": {{"childcare_type": "가정"}},
      "or_conditions": {{}}
    }},
    {{
      "amount": 460000,
      "and_conditions": {{"childcare_type": "어린이집"}},
      "or_conditions": {{}}
    }}
  ]
}}

예시 3: 첫째 70만원, 둘째 250만원, 셋째 500만원
→ benefits 3개 (출생순서 다름)

{{
  "benefits": [
    {{
      "amount": 700000,
      "and_conditions": {{"birth_order": 1}},
      "or_conditions": {{}}
    }},
    {{
      "amount": 2500000,
      "and_conditions": {{"birth_order": 2}},
      "or_conditions": {{}}
    }},
    {{
      "amount": 5000000,
      "and_conditions": {{"birth_order": 3}},
      "or_conditions": {{}}
    }}
  ]
}}

예시 4: 복합 조건 (0세×가정, 0세×어린이집, 1세×가정, 1세×어린이집)
→ benefits 4개 (나이×양육방식 조합)

{{
  "benefits": [
    {{
      "amount": 1000000,
      "and_conditions": {{"age_max_months": 11, "childcare_type": "가정"}},
      "or_conditions": {{}}
    }},
    {{
      "amount": 460000,
      "and_conditions": {{"age_max_months": 11, "childcare_type": "어린이집"}},
      "or_conditions": {{}}
    }},
    {{
      "amount": 500000,
      "and_conditions": {{"age_max_months": 23, "childcare_type": "가정"}},
      "or_conditions": {{}}
    }},
    {{
      "amount": 25000,
      "and_conditions": {{"age_max_months": 23, "childcare_type": "어린이집"}},
      "or_conditions": {{}}
    }}
  ]
}}

---

【공통 조건 처리】⭐⭐⭐

여러 혜택이 같은 조건을 공유하면?
→ 각 혜택마다 조건 반복! (중복 OK!)

예시: "울산시민 중 0세는 100만원, 1세는 50만원"

✅ 올바른 파싱:
{{
  "benefits": [
    {{
      "amount": 1000000,
      "and_conditions": {{
        "age_max_months": 11,
        "residence_min_months": 6  // 반복!
      }},
      "or_conditions": {{}}
    }},
    {{
      "amount": 500000,
      "and_conditions": {{
        "age_max_months": 23,
        "residence_min_months": 6  // 반복!
      }},
      "or_conditions": {{}}
    }}
  ]
}}

⚠️ 중요: 조건 중복은 괜찮습니다! 각 혜택이 독립적이어야 합니다!

---

【조건 없는 경우】

조건이 없으면?
→ and_conditions: {{}}, or_conditions: {{}}

예시:
{{
  "benefits": [
    {{
      "amount": 100000,
      "and_conditions": {{}},  // 빈 객체 (조건 없음)
      "or_conditions": {{}}    // 빈 객체 (OR 조건 없음)
    }}
  ]
}}

❌ 금지: and_conditions 또는 or_conditions 누락!

---

【필수 규칙】⭐⭐⭐

## 1. 나이 vs 출산 후 신청기한 ⭐⭐⭐

**⭐ 매우 중요: age_max_months vs birth_within_months 구분! ⭐**

### age_min_months, age_max_months
**아동의 현재 나이 조건**

단일 기준:
- "영유아" → age_max_months: 84
- "영아" → age_max_months: 24
- "0세" → age_min_months: 0, age_max_months: 11
- "1세" → age_min_months: 12, age_max_months: 23
- "만 5세 이하" → age_max_months: 60
- "만 8세 이하" → age_max_months: 96

범위 기준:
- "24개월~36개월" → age_min_months: 24, age_max_months: 36
- "만 2세~5세" → age_min_months: 24, age_max_months: 60
- "6개월 이상" → age_min_months: 6, age_max_months: null

### birth_within_months
**출산 후 신청 가능 기간 (신청 기한)**

키워드:
- "출생일부터 12개월 이내 신청" → birth_within_months: 12
- "출산 후 1년 이내" → birth_within_months: 12
- "출생 후 6개월 이내 신청" → birth_within_months: 6
- "영아 출생일 기준 12개월 이내" → birth_within_months: 12

**❌❌❌ 매우 중요한 구분 ❌❌❌**

잘못된 예시:
```
원문: "출생일부터 12개월 이내에 신청"
❌ age_max_months: 12  // 틀림! (이건 1세 미만이라는 뜻)
✅ birth_within_months: 12  // 정답! (출산 후 12개월 이내 신청)
```

올바른 예시:
```
원문: "0세 아동, 출생 후 12개월 이내 신청"
✅ age_max_months: 11  // 0세 아동
✅ birth_within_months: 12  // 출생 후 12개월 이내 신청
```

**구분 방법:**
- "~세", "~개월 아동", "만 ~세 이하" → age_max_months
- "출생 후 ~개월 이내 신청", "출생일부터 ~개월 이내" → birth_within_months

**중요: 0세, 1세, 2세는 나이입니다! 출생순서가 아닙니다!**

❌ "노인", "만 65세 이상"은 절대 파싱하지 마세요!

---

## 2. 소득 (4가지만)

- "기준중위소득" (띄어쓰기 없음)
- "차상위계층"
- "기초생활수급자"
- null

자동 매핑:
- "차상위계층" → income_max_percent: 50
- "기초생활수급자" → income_max_percent: 50

---

## 3. 가구형태 및 특수 조건

**가구형태:**
"한부모가족", "법정 한부모가정", "조손가족", "다문화가족", 
"다자녀가정", "맞벌이가족"

**중요한 구분:**
- "조손가족" → household_type: "조손가족" (부모 없이 조부모+손주만 거주)
- "조부모가 돌보는" → requires_grandparent_care: true (부모는 있지만 조부모가 양육)

**양육 관련:**
- requires_grandparent_care: 조부모 양육 필요
  - "조부모가 돌보는" → true
  - "손주를 돌보는 조부모" → true
  - "부모 대신 조부모가" → true

- requires_dual_income: 맞벌이 필요
  - "맞벌이 가정" → true

---

## 4. 가구원 수 (household_members) ⭐⭐⭐

**가구원 = 본인 + 자녀 + 동거 가족 (부모, 조부모 등)**

키워드:
- "1인 가구" → household_members_min: 1, household_members_max: 1
- "2인 가구" → household_members_min: 2, household_members_max: 2
- "3인 가구 이상" → household_members_min: 3
- "4인 이하" → household_members_max: 4

**중요:** 자녀 수 ≠ 가구원 수!
- children_min/max: 자녀만 (1명, 2명, 3명)
- household_members: 본인+자녀+가족 (3명, 4명, 5명)

---

## 5. 자녀 수 (children_min/max) ⭐⭐⭐

**자녀 = 본인의 자녀만 (가구원 ≠ 자녀)**

키워드:
- "1자녀" → children_min: 1, children_max: 1
- "2자녀" → children_min: 2, children_max: 2
- "2자녀 이상" → children_min: 2
- "3자녀 이상" → children_min: 3
- "다자녀" → children_min: 2 (보통 2명 이상)

**중요:** 자녀 수 ≠ 출생순서 ≠ 가구원 수!
- children_min/max: 총 자녀 수 (1명, 2명, 3명)
- birth_order: 해당 아동의 순서 (첫째, 둘째, 셋째)
- household_members: 본인+자녀+동거가족

---

## 6. 출생순서 (birth_order) ⭐⭐⭐

키워드:
- "첫째" → birth_order: 1
- "둘째" → birth_order: 2
- "셋째" → birth_order: 3
- "셋째 이상", "셋째이후" → birth_order: 3
- "출생순서 무관" → birth_order: null

**❌❌❌ 매우 중요 ❌❌❌**

"0세", "1세", "2세"는 **나이**입니다! **출생순서가 아닙니다!**

❌ 잘못된 예시:
원문: "0세 100만원, 1세 50만원"
→ birth_order: 1, birth_order: 2  // 완전히 틀림!

✅ 올바른 예시:
원문: "0세 100만원, 1세 50만원"
→ age_max_months: 11, age_max_months: 23  // 정답!
→ birth_order: null

✅ 올바른 예시 2:
원문: "첫째 70만원, 둘째 250만원"
→ birth_order: 1, birth_order: 2  // 정답!

---

## 6. 아동/부모 질환 구분 ⭐⭐⭐

### 아동 질환 (child_*)
- child_has_serious_disease: 아동 중증질환
- child_has_rare_disease: 아동 희귀질환
- child_has_chronic_disease: 아동 난치질환
- child_has_cancer: 아동 암, 백혈병

### 부모 질환 (parent_*)
- parent_has_serious_disease: 부모 중증질환
- parent_has_rare_disease: 부모 희귀질환
- parent_has_chronic_disease: 부모 난치질환
- parent_has_cancer: 부모 암
- parent_has_infertility: 부모 난임

**구분 방법:**
- "아동 암환자" → child_has_cancer
- "부모가 암환자" → parent_has_cancer
- "자녀 희귀질환" → child_has_rare_disease
- "임산부 난임" → parent_has_infertility

---

## 7. 특수 상황

- is_violence_victim: 폭력피해
- is_abuse_victim: 학대피해
- is_defector: 탈북민
- is_national_merit: 국가유공자
- is_foster_child: 위탁아동
- is_single_mother: 미혼모
- is_low_income: 저소득층

**⭐⭐⭐ 중요: Boolean 필드는 true 또는 null만! ⭐⭐⭐**

❌❌❌ 절대 금지 ❌❌❌
```json
{{
  "requires_grandparent_care": false,  // ← 절대 금지!
  "requires_disability": false,        // ← 절대 금지!
  "is_abuse_victim": false            // ← 절대 금지!
}}
```

✅✅✅ 올바른 사용 ✅✅✅
```json
{{
  "requires_grandparent_care": true,   // ← 조건 있으면 true
  "requires_grandparent_care": null    // ← 조건 없으면 null
}}
```

**이유:**
- false는 "조건이 아니다"를 의미 → 의미 없음!
- "조부모가 안 돌보는 경우"는 조건이 아님
- "장애가 없는 경우"는 조건이 아님
- 조건이 없으면 → null!

**예시:**
- "조부모 양육 필요" → requires_grandparent_care: true ✅
- "조부모 양육 불필요" → requires_grandparent_care: null ✅ (조건 없음)
- "조부모가 아닌 경우" → requires_grandparent_care: null ✅ (조건 없음)

---

## 8. 교육

- education_level: "초등" / "중등" / "고등" / null
- is_enrolled: true / false

---

## 9. 양육 방식 (childcare_type)

- "가정양육", "가정" → childcare_type: "가정"
- "어린이집", "어린이집 재원" → childcare_type: "어린이집"
- "유치원" → childcare_type: "유치원"
- null

---


【⭐⭐⭐ Benefits 표준 구조 ⭐⭐⭐】

**표준 구조 (모든 benefits는 이 구조를 따름!):**
```json
{{
  "amount": 숫자 또는 null,
  "amount_type": "일시금" | "월" | "년" | "회" | null,
  "amount_unit": "원" | "포인트" | null,
  "benefit_type": "현금" | "서비스" | "물품" | "감면" | "포인트",
  "payment_cycle": "일시금" | "5회분할" | "매월" | null,
  "payment_method": "계좌입금" | "카드" | "현장지급" | null,
  "payment_timing": "신청 후 다음달" | "즉시" | null,
  "description": "상세 설명",
  
  // ⭐ 혜택별 조건 (필수!)
  "and_conditions": {{
    "age_min_months": 0,
    "age_max_months": 11,
    ...
  }},
  "or_conditions": {{
    "household_type": ["맞벌이", "한부모"],
    ...
  }}
}}
```

**파싱 규칙:**

### 1. 금액 추출 (amount)
- "70만원" → amount: 700000
- "250만원" → amount: 2500000
- "10만 포인트" → amount: 100000
- "1,000원" → amount: 1000
- 금액 없으면 → amount: null

### 2. 금액 유형 (amount_type)
- "일시금" → amount_type: "일시금"
- "월" → amount_type: "월"
- "연" → amount_type: "년"
- "회당" → amount_type: "회"

### 3. 혜택 유형 (benefit_type) - 필수!
- 현금 지급 → benefit_type: "현금"
- 서비스 제공 → benefit_type: "서비스"
- 물품 지원 → benefit_type: "물품"
- 요금 감면 → benefit_type: "감면"
- 포인트 → benefit_type: "포인트"

### 4. 지급 주기 (payment_cycle) ⭐ 명확한 기준!

**일시금 (한 번만):**
- "일시금" → payment_cycle: "일시금"
- "1회 지급" → payment_cycle: "일시금"

**분할 지급:**
- "5회분할" → payment_cycle: "5회분할"
- "10회분할" → payment_cycle: "10회분할"

**정기 지급 (조건 끝날 때까지):**
- "매월" + amount_type: "월" → payment_cycle: "매월"
- amount_type: "월"이고 주기 없으면 → payment_cycle: "매월"

### 5. 설명 (description) - 필수!
항상 포함! 원문 내용 요약

---

【전체 응답 예시】

예시 1: 부모급여 (0세, 1세 각각 가정/어린이집)

```json
{{
  "benefits": [
    {{
      "amount": 1000000,
      "amount_type": "월",
      "amount_unit": "원",
      "benefit_type": "현금",
      "payment_cycle": "매월",
      "description": "0세 가정 양육 월 100만원",
      "and_conditions": {{
        "age_min_months": 0,
        "age_max_months": 11,
        "childcare_type": "가정",
        "income_type": "기준중위소득",
        "income_max_percent": 150
      }},
      "or_conditions": {{}}
    }},
    {{
      "amount": 460000,
      "amount_type": "월",
      "amount_unit": "원",
      "benefit_type": "현금",
      "payment_cycle": "매월",
      "description": "0세 어린이집 재원 시",
      "and_conditions": {{
        "age_min_months": 0,
        "age_max_months": 11,
        "childcare_type": "어린이집",
        "income_type": "기준중위소득",
        "income_max_percent": 150
      }},
      "or_conditions": {{}}
    }},
    {{
      "amount": 500000,
      "amount_type": "월",
      "amount_unit": "원",
      "benefit_type": "현금",
      "payment_cycle": "매월",
      "description": "1세 가정 양육 월 50만원",
      "and_conditions": {{
        "age_min_months": 12,
        "age_max_months": 23,
        "childcare_type": "가정",
        "income_type": "기준중위소득",
        "income_max_percent": 150
      }},
      "or_conditions": {{}}
    }},
    {{
      "amount": 25000,
      "amount_type": "월",
      "amount_unit": "원",
      "benefit_type": "현금",
      "payment_cycle": "매월",
      "description": "1세 어린이집 재원 시",
      "and_conditions": {{
        "age_min_months": 12,
        "age_max_months": 23,
        "childcare_type": "어린이집",
        "income_type": "기준중위소득",
        "income_max_percent": 150
      }},
      "or_conditions": {{}}
    }}
  ]
}}
```

예시 2: 출산장려금 (첫째, 둘째, 셋째)

```json
{{
  "benefits": [
    {{
      "amount": 700000,
      "amount_type": "일시금",
      "amount_unit": "원",
      "benefit_type": "현금",
      "payment_cycle": "일시금",
      "description": "첫째 출산장려금",
      "and_conditions": {{
        "birth_order": 1,
        "birth_within_months": 12,
        "residence_min_months": 6,
        "age_max_months": 12
      }},
      "or_conditions": {{}}
    }},
    {{
      "amount": 2500000,
      "amount_type": "분할",
      "amount_unit": "원",
      "benefit_type": "현금",
      "payment_cycle": "5회분할",
      "description": "둘째 출산장려금 (5회 분할)",
      "and_conditions": {{
        "birth_order": 2,
        "birth_within_months": 12,
        "residence_min_months": 6,
        "age_max_months": 12
      }},
      "or_conditions": {{}}
    }},
    {{
      "amount": 5000000,
      "amount_type": "분할",
      "amount_unit": "원",
      "benefit_type": "현금",
      "payment_cycle": "10회분할",
      "description": "셋째 출산장려금 (10회 분할)",
      "and_conditions": {{
        "birth_order": 3,
        "birth_within_months": 12,
        "residence_min_months": 6,
        "age_max_months": 12
      }},
      "or_conditions": {{}}
    }}
  ]
}}
```

예시 3: OR 조건 (조부모 손주 돌봄)

```json
{{
  "benefits": [
    {{
      "amount": 300000,
      "amount_type": "월",
      "amount_unit": "원",
      "benefit_type": "현금",
      "payment_cycle": "매월",
      "description": "조부모 손주 돌봄 수당",
      "and_conditions": {{
        "age_min_months": 24,
        "age_max_months": 35,
        "income_type": "기준중위소득",
        "income_max_percent": 150,
        "requires_grandparent_care": true
      }},
      "or_conditions": {{
        "household_type": ["맞벌이", "한부모", "다자녀"]
      }}
    }}
  ]
}}
```

---

【최종 체크리스트】

파싱 완료 후 반드시 확인:

✅ benefits 배열이 있는가?
✅ 각 benefit이 and_conditions를 가지는가? (빈 객체라도)
✅ 각 benefit이 or_conditions를 가지는가? (빈 객체라도)
✅ 최상위에 and_conditions가 없는가? (절대 금지!)
✅ 최상위에 or_conditions가 없는가? (절대 금지!)
✅ 조건이 다른 혜택은 별도 benefit인가?
✅ "0세", "1세"를 birth_order로 착각하지 않았는가?
✅ 공통 조건이 각 benefit에 반복되었는가?
✅ amount는 숫자인가? (문자열 X)
✅ benefit_type이 입력되었는가?
✅ description이 입력되었는가?

---

❌❌❌ 절대 금지 사항 (다시 한번!) ❌❌❌

1. 최상위 "and_conditions" 절대 금지!
2. 최상위 "or_conditions" 절대 금지!
3. and_conditions 또는 or_conditions 누락 금지!
4. "0세", "1세"를 birth_order로 착각 금지!
5. ⭐⭐⭐ False 값 절대 금지! ⭐⭐⭐
   - requires_*: false ← 절대 안 됨!
   - is_*: false ← 절대 안 됨!
   - has_*: false ← 절대 안 됨!
   - Boolean 필드는 오직 true 또는 null만!
   - "~가 아닌 경우", "~제외"는 조건이 아님!

---

JSON만 반환하세요. 설명이나 마크다운 없이!
"""
        
        import time
        
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
                
                # Rate limit 오류 확인
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    wait_time = (attempt + 1) * 10  # 10초, 20초, 30초
                    print(f"⏳ (Rate limit, {wait_time}초 대기 후 재시도 {attempt + 1}/{max_retries})", end=' ')
                    time.sleep(wait_time)
                    continue
                
                # 그 외 오류
                elif attempt < max_retries - 1:
                    wait_time = 3
                    print(f"⏳ (오류, {wait_time}초 대기 후 재시도 {attempt + 1}/{max_retries})", end=' ')
                    time.sleep(wait_time)
                    continue
                else:
                    # 최종 실패
                    print(f"❌ 최종 실패: {error_msg[:50]}")
                    return {
                        "benefits": []
                    }
        
        # 모든 재시도 실패
        return {
            "benefits": []
        }
    
    def batch_parse_xml(self, xml_path, limit=None):
        """XML 파일 배치 파싱 (limit 지원)"""
        print(f"📂 XML 파일 읽기: {xml_path}")
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
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

    # .env 파일에서 환경 변수를 로드합니다.
    load_dotenv()
    API_KEY = os.getenv('OPENAI_API_KEY')
    
    if not API_KEY:
        print("❌ OPENAI_API_KEY를 .env 파일에 설정하세요!")
        exit(1)
    
    parser = WelfareParserV4_0(api_key=API_KEY)
    
    results = parser.batch_parse_xml(
        # 'wantedDtl포함된xml목록/복지목록중앙부.xml',
        'wantedDtl포함된xml목록/복지목록울산.xml',
        limit=5 # 없으면 최대개수
    )
    
    # 1. 현재 날짜와 시간을 가져와 '월일_시분' 형식으로 만듭니다.
    now = datetime.now()
    timestamp = now.strftime("%m%d_%H%M")

    # 2. 파일 이름을 동적으로 생성합니다.
    # base_name = '정형화데이터_중앙부_v4.0'
    base_name = '정형화데이터_울산_v4.0'
    file_name = f"{base_name}_{timestamp}.json"

    # 3. 파일 저장 함수 호출
    parser.save_results(results, file_name)
    
    print("\n🎉 v4.0 파싱 완료!")
    print("변경사항:")
    print("  1. ⭐ Benefits 중심 구조 (모든 조건이 benefits 내부)")
    print("  2. 서비스 레벨 조건 제거 (지역만 서비스 레벨)")
    print("  3. 혜택별 독립적인 and_conditions, or_conditions")
    print("  4. 조건 중복 허용 (각 benefit마다 반복)")