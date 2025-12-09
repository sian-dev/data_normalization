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
    "sido": "울산광역시",
    "sigungu": "남구",
    "age_min_months": 0,
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
      "support_type": "서비스",
      "support_description": ""
    }}
  ]
}}

규칙:
1. "영아" → age_max_months: 12
2. "6개월 거주" → residence_min_months: 6
3. "30만원" → amount: 300000
4. 없는 정보는 null
5. benefits는 반드시 배열

절대 규칙: conditions, benefits 키만 사용! target, support_details 등 금지!

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

            # XML에서 지역 정보 추출
            ctpv = service.find('ctpvNm')
            sgg = service.find('sggNm')

            ctpv_text = ctpv.text.strip() if ctpv is not None and ctpv.text else None
            sgg_text = sgg.text.strip() if sgg is not None and sgg.text else None

            # source 자동 판단
            if ctpv_text is None:
                source = '중앙부처'
            else:
                source = ctpv_text  # '울산광역시', '서울특별시', '부산광역시' 등

            results.append({
                'service_id': serv_id,
                'service_name': serv_nm,
                'detail_url': detail_url,
                'original_data': {
                    'target_text': tgtr_text,
                    'criteria_text': slct_text,
                    'support_text': alw_text
                },
                'sido': ctpv_text,      # None=전국, '울산광역시'=울산
                'sigungu': sgg_text,    # None=전체, '남구'=남구
                'source': source,       # '중앙부처' 또는 '울산광역시' 등
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
        # './울산/중앙부 복지 목록.xml',
        './울산/지자체 복지 목록 울산.xml',
        limit=300
    )
    
    parser.save_results(results, 'parsed_strict_gpt울산.json')