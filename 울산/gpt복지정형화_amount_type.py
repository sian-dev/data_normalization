"""
엄격한 JSON 구조 강제 파서 (GPT-4o)
- 모든 복지가 동일한 구조
- conditions와 benefits만 사용
"""
import datetime # 이 줄을 추가합니다.
# 다른 import 문들...
import json
from openai import OpenAI
import xml.etree.ElementTree as ET

class StrictGPTParser:
    def __init__(self, api_key):
        """OpenAI API 초기화"""
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
    
    def create_strict_prompt(self, service_name, target_text, criteria_text, support_text):
        """엄격한 JSON 구조 강제 프롬프트"""
        prompt = f"""복지 정보를 정형 데이터로 변환하세요.

서비스명: {service_name}
대상자: {target_text}
선정기준: {criteria_text}
지원내용: {support_text}

---

⚠️ 반드시 아래 JSON 형식을 정확히 따라야 합니다!

{{
  "conditions": {{
    "age_min_months": null,
    "age_max_months": null,
    "income_max_percent": null,
    "income_type": null,
    "residence_min_months": null,
    "household_type": null,
    "children_min": null,
    "children_max": null,
    "pregnancy_weeks_min": null,
    "pregnancy_weeks_max": null,
    "birth_within_months": null,
    "requires_dual_income": null,
    "requires_grandparent_care": null,
    "requires_disability": null,
    "disability_level": null,
    "requires_parent_disability": null,
    "parent_disability_level": null,
    "birth_special": null,
    "housing_type": null,
    "other_conditions": null
  }},
  "benefits": [
    {{
      "amount": null,
      "amount_type": null,
      "support_count": null,
      "support_period": null,
      "max_amount_per_child": null,
      "max_amount_total": null,
      "birth_order": null,
      "support_type": null,
      "support_description": ""
    }}
  ]
}}

---

【필수 규칙】

1. 나이 (개월 단위):
   - "영아" → age_max_months: 72, age_min_months: 0
   - "영유아" → age_max_months: 72, age_min_months: 0
   - "만 5세 이하" → age_max_months: 60, age_min_months: 0
   - "만 3세~7세" → age_min_months: 36, age_max_months: 84
   - "임산부" → age_min_months: null, age_max_months: null (임신 조건 사용)
   - 최소 나이 없으면 → age_min_months: 0 (또는 null)

2. 거주:
   - "6개월 거주" → residence_min_months: 6
   - "주민등록" → residence_min_months: 1

3. 금액:
   - "30만원" → amount: 300000
   - "1,000원" → amount: 1000

4. ⚠️ amount_type (매우 중요! 아래 4가지만 사용):
   - 매월 지급 → "월정액"
   - 1년에 1번 → "연정액"  
   - 한 번만 지급 → "일회성"
   - 여러 번 나누어 지급 → "분할"
   - 금액 없으면 → null
   
   ❌ 절대 사용 금지: "10회분할", "1회", "5회분할", "월", "연안", "단위" 등
   ✅ 반드시 사용: "월정액", "연정액", "일회성", "분할", null

5. support_count와 support_period:
   - "월 10만원" → support_count: 12, support_period: "년", amount_type: "월정액"
   - "연 100만원" → support_count: 1, support_period: "년", amount_type: "연정액"
   - "일회성 60만원" → support_count: 1, support_period: "일회성", amount_type: "일회성"
   - "10회 분할 지급" → support_count: 10, support_period: "분할", amount_type: "분할"
   - "5회 나누어 지급" → support_count: 5, support_period: "분할", amount_type: "분할"
   - 정보 없으면 → null

6. support_type (아래만 사용):
   - 현금 지급 → "현금"
   - 바우처/이용권 → "바우처"
   - 물품 제공 → "현물"
   - 서비스 제공 → "서비스"
   - 정보 없으면 → "서비스"

7. 없는 정보는 null

8. benefits는 반드시 배열 []

---

【절대 규칙】
- conditions, benefits 키만 사용
- target, support_details 등 금지
- amount_type은 "월정액", "연정액", "일회성", "분할", null만 가능
- support_type은 "현금", "바우처", "현물", "서비스"만 가능
- age_min_months는 0 또는 null (최소 나이 제한 없으면 0)

JSON만 출력하세요."""

        return prompt
    
    def parse_service(self, service_name, target_text, criteria_text, support_text):
        """단일 서비스 파싱"""
        try:
            prompt = self.create_strict_prompt(
                service_name, target_text, criteria_text, support_text
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "JSON 형식으로만 응답. conditions와 benefits 키만 사용."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # JSON 추출
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            result = json.loads(content)
            
            # 구조 검증
            if not self.validate_structure(result):
                print(f"  ⚠️  구조 오류!")
                return self.get_empty_result()
            
            return result
            
        except Exception as e:
            print(f"  ⚠️  오류: {e}")
            return self.get_empty_result()
    
    def validate_structure(self, result):
        """구조 검증"""
        if not isinstance(result, dict):
            return False
        
        if 'conditions' not in result or 'benefits' not in result:
            return False
        
        if not isinstance(result['benefits'], list):
            return False
        
        forbidden = ['target', 'support_details', 'selection_criteria']
        if any(k in result for k in forbidden):
            return False
        
        return True
    
    def get_empty_result(self):
        """기본 구조"""
        return {
            "conditions": {
                "age_min_months": None,
                "age_max_months": None,
                "income_max_percent": None,
                "income_type": None,
                "residence_min_months": None,
                "household_type": None,
                "children_min": None,
                "children_max": None,
                "pregnancy_weeks_min": None,
                "pregnancy_weeks_max": None,
                "birth_within_months": None,
                "requires_dual_income": None,
                "requires_grandparent_care": None,
                "requires_disability": None,
                "disability_level": None,
                "requires_parent_disability": None,
                "parent_disability_level": None,
                "birth_special": None,
                "housing_type": None,
                "other_conditions": None
            },
            "benefits": [
                {
                    "amount": None,
                    "amount_type": None,
                    "support_count": None,
                    "support_period": None,
                    "max_amount_per_child": None,
                    "max_amount_total": None,
                    "birth_order": None,
                    "support_type": "서비스",
                    "support_description": ""
                }
            ]
        }
    
    def batch_parse_xml(self, xml_path, limit=None):
        """XML 일괄 파싱"""
        tree = ET.parse(xml_path)
        root = tree.getroot()
        services = root.findall('.//servList')
        
        if limit:
            services = services[:limit]
        
        print(f"\n엄격한 GPT 파싱: {len(services)}개\n")
        
        results = []
        valid_count = 0
        
        for idx, service in enumerate(services, 1):
            serv_id = self.get_text(service, 'servId')
            serv_nm = self.get_text(service, 'servNm')
            detail_url = self.get_text(service, 'servDtlLink')
            
            # 지역 정보 추출
            ctpv = service.find('ctpvNm')
            sgg = service.find('sggNm')
            
            ctpv_text = ctpv.text.strip() if ctpv is not None and ctpv.text else None
            sgg_text = sgg.text.strip() if sgg is not None and sgg.text else None
            
            # sigungu가 "교육청"이면 NULL 처리
            if sgg_text and '교육청' in sgg_text:
                sgg_text = None
            
            # source 자동 판단
            if ctpv_text is None:
                source = '중앙부처'
            else:
                source = ctpv_text
            
            wanted_dtl = service.find('wantedDtl')
            if wanted_dtl is not None:
                tgtr_text = self.get_text(wanted_dtl, 'sprtTrgtCn') or self.get_text(wanted_dtl, 'tgtrDtlCn')
                slct_text = self.get_text(wanted_dtl, 'slctCritCn')
                alw_text = self.get_text(wanted_dtl, 'alwServCn')
            else:
                tgtr_text = slct_text = alw_text = ""
            
            print(f"[{idx}/{len(services)}] {serv_nm[:40]:<40}", end=' ')
            
            parsed = self.parse_service(serv_nm, tgtr_text, slct_text, alw_text)
            
            if self.validate_structure(parsed):
                print("✓")
                valid_count += 1
            else:
                print("✗")
            
            results.append({
                'service_id': serv_id,
                'service_name': serv_nm,
                'detail_url': detail_url,
                'sido': ctpv_text,      # ⭐ 추가
                'sigungu': sgg_text,    # ⭐ 추가 (교육청은 NULL)
                'source': source,       # ⭐ 추가
                'original_data': {
                    'target_text': tgtr_text,
                    'criteria_text': slct_text,
                    'support_text': alw_text
                },
                'parsed_data': parsed
            })
        
        print(f"\n✅ 완료: {valid_count}/{len(results)} 유효\n")
        
        return results
    
    def get_text(self, element, tag):
        child = element.find(tag)
        return child.text.strip() if child is not None and child.text else ''
    
    def save_results(self, results, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"💾 저장: {output_path}")

"""
엄격한 JSON 구조 강제 파서 (GPT-4o-mini)
- 모든 복지가 동일한 구조
- conditions와 benefits만 사용
"""
import json
from openai import OpenAI
import xml.etree.ElementTree as ET

class StrictGPTParser:
    def __init__(self, api_key):
        """OpenAI API 초기화"""
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
    
    def create_strict_prompt(self, service_name, target_text, criteria_text, support_text):
        """엄격한 JSON 구조 강제 프롬프트"""
        prompt = f"""복지 정보를 정형 데이터로 변환하세요.

서비스명: {service_name}
대상자: {target_text}
선정기준: {criteria_text}
지원내용: {support_text}

---

⚠️ 반드시 아래 JSON 형식을 정확히 따라야 합니다!

{{
  "conditions": {{
    "age_min_months": null,
    "age_max_months": null,
    "income_max_percent": null,
    "income_type": null,
    "residence_min_months": null,
    "household_type": null,
    "children_min": null,
    "children_max": null,
    "pregnancy_weeks_min": null,
    "pregnancy_weeks_max": null,
    "birth_within_months": null,
    "requires_dual_income": null,
    "requires_grandparent_care": null,
    "requires_disability": null,
    "disability_level": null,
    "requires_parent_disability": null,
    "parent_disability_level": null,
    "birth_special": null,
    "housing_type": null,
    "other_conditions": null
  }},
  "benefits": [
    {{
      "amount": null,
      "amount_type": null,
      "support_count": null,
      "support_period": null,
      "max_amount_per_child": null,
      "max_amount_total": null,
      "birth_order": null,
      "support_type": null,
      "support_description": ""
    }}
  ]
}}

---

【필수 규칙】

1. 나이 (개월 단위):
   - "영아" → age_max_months: 72, age_min_months: 0
   - "영유아" → age_max_months: 72, age_min_months: 0
   - "만 5세 이하" → age_max_months: 60, age_min_months: 0
   - "만 3세~7세" → age_min_months: 36, age_max_months: 84
   - "임산부" → age_min_months: null, age_max_months: null (임신 조건 사용)
   - 최소 나이 없으면 → age_min_months: 0 (또는 null)

2. 거주:
   - "6개월 거주" → residence_min_months: 6
   - "주민등록" → residence_min_months: 1

3. 금액:
   - "30만원" → amount: 300000
   - "1,000원" → amount: 1000

4. ⚠️ income_type (매우 중요! 아래 4가지만 사용):
   - "기준중위소득" (띄어쓰기 없이)
   - "차상위계층"
   - "기초생활수급자"
   - null (소득 제한 없음)
   
   【변환 규칙】
   - "기준 중위소득" → "기준중위소득"
   - "중위소득" → "기준중위소득"
   - "기초수급" → "기초생활수급자"
   - "기초생활보장 수급자" → "기초생활수급자"
   - "차상위" → "차상위계층"
   - "법정저소득층" → "기초생활수급자"
   - "저소득층" → "기초생활수급자"
   
   【자동 매핑】
   - "차상위계층" → income_max_percent: 50 자동 설정
   - "기초생활수급자" → income_max_percent: 50 자동 설정
   
   【복수 조건 - 배열 사용】
   - "기초생활수급자 및 차상위계층" → ["기초생활수급자", "차상위계층"]
   
   ❌ 절대 금지: "한부모가족"을 income_type에 넣지 말 것!

5. ⚠️ household_type (매우 중요! 아래 값만 사용):
   - "한부모가족"
   - "법정 한부모가정"
   - "조손가족"
   - "다문화가족"
   - "다자녀가정"
   - "맞벌이가족"
   - "장애인 가구"
   - "범죄피해가정"
   - "탈북민"
   - "국가유공자 자녀"
   - "특수교육대상자"
   - null
   
   【변환 규칙】
   - "한부모", "한부모가정" → "한부모가족"
   - "법정한부모" → "법정 한부모가정"
   - "조손", "조손가정" → "조손가족"
   - "다문화", "다문화가정" → "다문화가족"
   - "다자녀" → "다자녀가정"
   - "맞벌이", "맞벌이가정" → "맞벌이가족"
   - "장애인가족", "장애인 가정" → "장애인 가구"
   
   【복수 조건 - 배열 사용】
   - "한부모, 조손, 다문화" → ["한부모가족", "조손가족", "다문화가족"]
   
   ❌ 절대 금지: income_type에 가구 형태 넣지 말 것!

6. 거주:

6. ⚠️ amount_type (매우 중요! 아래 4가지만 사용):
   - 매월 지급 → "월정액"
   - 1년에 1번 → "연정액"  
   - 한 번만 지급 → "일회성"
   - 여러 번 나누어 지급 → "분할"
   - 금액 없으면 → null
   
   ❌ 절대 사용 금지: "10회분할", "1회", "5회분할", "월", "연안", "단위" 등
   ✅ 반드시 사용: "월정액", "연정액", "일회성", "분할", null

7. support_count와 support_period:
   - "월 10만원" → support_count: 12, support_period: "년", amount_type: "월정액"
   - "연 100만원" → support_count: 1, support_period: "년", amount_type: "연정액"
   - "일회성 60만원" → support_count: 1, support_period: "일회성", amount_type: "일회성"
   - "10회 분할 지급" → support_count: 10, support_period: "분할", amount_type: "분할"
   - "5회 나누어 지급" → support_count: 5, support_period: "분할", amount_type: "분할"
   - 정보 없으면 → null

8. support_type (아래만 사용):
   - 현금 지급 → "현금"
   - 바우처/이용권 → "바우처"
   - 물품 제공 → "현물"
   - 서비스 제공 → "서비스"
   - 정보 없으면 → "서비스"

9. 없는 정보는 null

10. benefits는 반드시 배열 []

---

【절대 규칙】
- conditions, benefits 키만 사용
- target, support_details 등 금지
- income_type은 "기준중위소득", "차상위계층", "기초생활수급자", null만 가능
- household_type은 지정된 11가지 값만 가능
- amount_type은 "월정액", "연정액", "일회성", "분할", null만 가능
- support_type은 "현금", "바우처", "현물", "서비스"만 가능
- age_min_months는 0 또는 null (최소 나이 제한 없으면 0)
- income_type과 household_type을 절대 혼동하지 말 것!

【변환 예시】

예시 1: "저소득층 한부모가정"
→ income_type: "기초생활수급자", household_type: "한부모가족"

예시 2: "기초생활수급자 및 차상위계층 다자녀가정"
→ income_type: ["기초생활수급자", "차상위계층"], household_type: "다자녀가정"

예시 3: "기준 중위소득 150% 이하 탈북민"
→ income_max_percent: 150, income_type: "기준중위소득", household_type: "탈북민"

예시 4: "국가유공자 자녀, 장애인 가구"
→ income_type: null, household_type: ["국가유공자 자녀", "장애인 가구"]

JSON만 출력하세요."""

        return prompt
    
    def parse_service(self, service_name, target_text, criteria_text, support_text):
        """단일 서비스 파싱"""
        try:
            prompt = self.create_strict_prompt(
                service_name, target_text, criteria_text, support_text
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 복지 데이터 파싱 전문가입니다. JSON 형식으로만 응답하세요. conditions와 benefits 키만 사용하세요. income_type은 반드시 '기준중위소득', '차상위계층', '기초생활수급자', null 중 하나만 사용하세요. household_type과 income_type을 절대 혼동하지 마세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # JSON 추출
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            result = json.loads(content)
            
            # 구조 검증
            if not self.validate_structure(result):
                print(f"  ⚠️  구조 오류!")
                return self.get_empty_result()
            
            return result
            
        except Exception as e:
            print(f"  ⚠️  오류: {e}")
            return self.get_empty_result()
    
    def validate_structure(self, result):
        """구조 검증"""
        if not isinstance(result, dict):
            return False
        
        if 'conditions' not in result or 'benefits' not in result:
            return False
        
        if not isinstance(result['benefits'], list):
            return False
        
        forbidden = ['target', 'support_details', 'selection_criteria']
        if any(k in result for k in forbidden):
            return False
        
        return True
    
    def get_empty_result(self):
        """기본 구조"""
        return {
            "conditions": {
                "age_min_months": None,
                "age_max_months": None,
                "income_max_percent": None,
                "income_type": None,
                "residence_min_months": None,
                "household_type": None,
                "children_min": None,
                "children_max": None,
                "pregnancy_weeks_min": None,
                "pregnancy_weeks_max": None,
                "birth_within_months": None,
                "requires_dual_income": None,
                "requires_grandparent_care": None,
                "requires_disability": None,
                "disability_level": None,
                "requires_parent_disability": None,
                "parent_disability_level": None,
                "birth_special": None,
                "housing_type": None,
                "other_conditions": None
            },
            "benefits": [
                {
                    "amount": None,
                    "amount_type": None,
                    "support_count": None,
                    "support_period": None,
                    "max_amount_per_child": None,
                    "max_amount_total": None,
                    "birth_order": None,
                    "support_type": "서비스",
                    "support_description": ""
                }
            ]
        }
    
    def batch_parse_xml(self, xml_path, limit=None):
        """XML 일괄 파싱"""
        tree = ET.parse(xml_path)
        root = tree.getroot()
        services = root.findall('.//servList')
        
        if limit:
            services = services[:limit]
        
        print(f"\n엄격한 GPT 파싱: {len(services)}개\n")
        
        results = []
        valid_count = 0
        
        for idx, service in enumerate(services, 1):
            serv_id = self.get_text(service, 'servId')
            serv_nm = self.get_text(service, 'servNm')
            detail_url = self.get_text(service, 'servDtlLink')
            
            # 지역 정보 추출
            ctpv = service.find('ctpvNm')
            sgg = service.find('sggNm')
            
            ctpv_text = ctpv.text.strip() if ctpv is not None and ctpv.text else None
            sgg_text = sgg.text.strip() if sgg is not None and sgg.text else None
            
            # sigungu가 "교육청"이면 NULL 처리
            if sgg_text and '교육청' in sgg_text:
                sgg_text = None
            
            # source 자동 판단
            if ctpv_text is None:
                source = '중앙부처'
            else:
                source = ctpv_text
            
            wanted_dtl = service.find('wantedDtl')
            if wanted_dtl is not None:
                tgtr_text = self.get_text(wanted_dtl, 'sprtTrgtCn') or self.get_text(wanted_dtl, 'tgtrDtlCn')
                slct_text = self.get_text(wanted_dtl, 'slctCritCn')
                alw_text = self.get_text(wanted_dtl, 'alwServCn')
            else:
                tgtr_text = slct_text = alw_text = ""
            
            print(f"[{idx}/{len(services)}] {serv_nm[:40]:<40}", end=' ')
            
            parsed = self.parse_service(serv_nm, tgtr_text, slct_text, alw_text)
            
            if self.validate_structure(parsed):
                print("✓")
                valid_count += 1
            else:
                print("✗")
            
            results.append({
                'service_id': serv_id,
                'service_name': serv_nm,
                'detail_url': detail_url,
                'sido': ctpv_text,      # ⭐ 추가
                'sigungu': sgg_text,    # ⭐ 추가 (교육청은 NULL)
                'source': source,       # ⭐ 추가
                'original_data': {
                    'target_text': tgtr_text,
                    'criteria_text': slct_text,
                    'support_text': alw_text
                },
                'parsed_data': parsed
            })
        
        print(f"\n✅ 완료: {valid_count}/{len(results)} 유효\n")
        
        return results
    
    def get_text(self, element, tag):
        child = element.find(tag)
        return child.text.strip() if child is not None and child.text else ''
    
    def save_results(self, results, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"💾 저장: {output_path}")


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv

    # .env 파일에서 환경 변수를 로드합니다.
    load_dotenv()
    API_KEY = os.getenv('OPENAI_API_KEY')
    
    parser = StrictGPTParser(api_key=API_KEY)
    
    results = parser.batch_parse_xml(
        './울산/중앙부 복지 목록.xml',
        # './울산/지자체 복지 목록 울산.xml',
        limit=300
    )
    
        # 1. 현재 날짜와 시간을 가져와 '월일_시분' 형식으로 만듭니다.
    # 예: 12월 9일 12시 00분 -> "1209_1200"
    now = datetime.datetime.now()
    timestamp = now.strftime("%m%d_%H%M") # %m=월, %d=일, %H=시, %M=분

    # 2. 파일 이름을 동적으로 생성합니다.
    base_name = 'parsed_strict_gpt중앙부'
    # base_name = 'parsed_strict_gpt울산'
    file_name = f"{base_name}_{timestamp}.json" # f-string 사용

    # 3. 파일 저장 함수 호출
    parser.save_results(results, file_name)
