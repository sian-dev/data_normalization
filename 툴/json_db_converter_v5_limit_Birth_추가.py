#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
복지 JSON → DB 변환 스크립트 v5.0
- 통합 테이블 (danz_welfare_services)
- fd_benefit_id: PRIMARY KEY (유니크)
- fd_service_id: 중복 가능
- 44개 OR 조건 지원 (limit_birth_date 추가)
- DB: 192.168.56.82
"""

import pymysql
import json
import glob

class WelfareConverter:
    def __init__(self):
        self.conn = pymysql.connect(
            host='192.168.56.82',
            user='work',
            password='1111',
            database='work_local',
            charset='utf8mb4'
        )
        self.cursor = self.conn.cursor()
        print("✅ DB 연결 성공!")
    
    def to_json(self, value):
        """값을 쉼표 구분 문자열로 변환"""
        if not value:
            return None
        if isinstance(value, bool):
            return 'true' if value else None
        if isinstance(value, list):
            if len(value) == 0:
                return None
            if all(isinstance(x, bool) for x in value):
                return 'true' if any(value) else None
            return ','.join(str(v) for v in value)
        return str(value)
    
    def insert_unified(self, service):
        """통합 테이블에 삽입 (서비스 + 혜택)"""
        
        service_id = service['service_id']
        service_name = service['service_name']
        detail_url = service.get('detail_url')
        sido = service.get('sido')
        if sido == '':
            sido = None
        sigungu = service.get('sigungu')
        source = service.get('source')
        
        original = service.get('original_data', {})
        target_text = original.get('target_text')
        criteria_text = original.get('criteria_text')
        support_text = original.get('support_text')
        
        benefits = service.get('parsed_data', {}).get('benefits', [])
        
        for benefit in benefits:
            and_cond = benefit.get('and_conditions', {})
            or_cond = benefit.get('or_conditions', {})
            
            # False 값 필터링
            for key, value in list(and_cond.items()):
                if value is False:
                    and_cond[key] = None
            
            # OR 조건 28개 (카테고리형)
            or_income = self.to_json(or_cond.get('income_type'))
            or_household = self.to_json(or_cond.get('household_type'))
            or_childcare = self.to_json(or_cond.get('childcare_type'))
            or_req_grandparent = self.to_json(or_cond.get('requires_grandparent_care'))
            or_req_dual = self.to_json(or_cond.get('requires_dual_income'))
            or_req_disability = self.to_json(or_cond.get('requires_disability'))
            or_req_parent_disability = self.to_json(or_cond.get('requires_parent_disability'))
            or_disability_level = self.to_json(or_cond.get('disability_level'))
            or_parent_disability_level = self.to_json(or_cond.get('parent_disability_level'))
            or_child_serious = self.to_json(or_cond.get('child_has_serious_disease'))
            or_child_rare = self.to_json(or_cond.get('child_has_rare_disease'))
            or_child_chronic = self.to_json(or_cond.get('child_has_chronic_disease'))
            or_child_cancer = self.to_json(or_cond.get('child_has_cancer'))
            or_parent_serious = self.to_json(or_cond.get('parent_has_serious_disease'))
            or_parent_rare = self.to_json(or_cond.get('parent_has_rare_disease'))
            or_parent_chronic = self.to_json(or_cond.get('parent_has_chronic_disease'))
            or_parent_cancer = self.to_json(or_cond.get('parent_has_cancer'))
            or_parent_infertility = self.to_json(or_cond.get('parent_has_infertility'))
            or_violence = self.to_json(or_cond.get('is_violence_victim'))
            or_abuse = self.to_json(or_cond.get('is_abuse_victim'))
            or_defector = self.to_json(or_cond.get('is_defector'))
            or_merit = self.to_json(or_cond.get('is_national_merit'))
            or_foster = self.to_json(or_cond.get('is_foster_child'))
            or_single = self.to_json(or_cond.get('is_single_mother'))
            or_low_income = self.to_json(or_cond.get('is_low_income'))
            or_education = self.to_json(or_cond.get('education_level'))
            or_enrolled = self.to_json(or_cond.get('is_enrolled'))
            or_housing = self.to_json(or_cond.get('housing_type'))
            
            # ⭐ 숫자 범위형 OR 조건 16개
            or_income_min_percent = self.to_json(or_cond.get('income_min_percent'))
            or_income_max_percent = self.to_json(or_cond.get('income_max_percent'))
            or_household_members_min = self.to_json(or_cond.get('household_members_min'))
            or_household_members_max = self.to_json(or_cond.get('household_members_max'))
            or_children_min = self.to_json(or_cond.get('children_min'))
            or_children_max = self.to_json(or_cond.get('children_max'))
            or_birth_order = self.to_json(or_cond.get('birth_order'))
            or_birth_order_min = self.to_json(or_cond.get('birth_order_min'))
            or_birth_order_max = self.to_json(or_cond.get('birth_order_max'))
            or_residence_min_months = self.to_json(or_cond.get('residence_min_months'))
            or_pregnancy_weeks_min = self.to_json(or_cond.get('pregnancy_weeks_min'))
            or_pregnancy_weeks_max = self.to_json(or_cond.get('pregnancy_weeks_max'))
            or_birth_within_months = self.to_json(or_cond.get('birth_within_months'))
            or_age_min_months = self.to_json(or_cond.get('age_min_months'))
            or_age_max_months = self.to_json(or_cond.get('age_max_months'))
            or_limit_birth_date = self.to_json(or_cond.get('limit_birth_date'))
            
            sql = """
            INSERT INTO danz_welfare_services (
              fd_service_id, fd_service_name, fd_detail_url,
              fd_sido, fd_sigungu, fd_source,
              fd_target_text, fd_criteria_text, fd_support_text,
              fd_amount, fd_amount_type, fd_amount_unit, fd_benefit_type,
              fd_payment_cycle, fd_payment_method, fd_payment_timing, fd_description,
              fd_age_min_months, fd_age_max_months,
              fd_income_type, fd_income_min_percent, fd_income_max_percent,
              fd_household_type, fd_household_members_min, fd_household_members_max,
              fd_children_min, fd_children_max,
              fd_birth_order, fd_birth_order_min, fd_birth_order_max,
              fd_residence_min_months,
              fd_childcare_type, fd_requires_grandparent_care, fd_requires_dual_income,
              fd_requires_disability, fd_requires_parent_disability,
              fd_child_disability_level, fd_parent_disability_level,
              fd_child_has_serious_disease, fd_child_has_rare_disease,
              fd_child_has_chronic_disease, fd_child_has_cancer,
              fd_parent_has_serious_disease, fd_parent_has_rare_disease,
              fd_parent_has_chronic_disease, fd_parent_has_cancer, fd_parent_has_infertility,
              fd_is_violence_victim, fd_is_abuse_victim, fd_is_defector,
              fd_is_national_merit, fd_is_foster_child, fd_is_single_mother, fd_is_low_income,
              fd_pregnancy_weeks_min, fd_pregnancy_weeks_max, fd_birth_within_months,
              fd_limit_birth_date,
              fd_education_level, fd_is_enrolled, fd_housing_type,
              fd_or_income_type, fd_or_household_type, fd_or_childcare_type,
              fd_or_requires_grandparent_care, fd_or_requires_dual_income,
              fd_or_requires_disability, fd_or_requires_parent_disability, 
              fd_or_disability_level, fd_or_parent_disability_level,
              fd_or_child_has_serious_disease, fd_or_child_has_rare_disease,
              fd_or_child_has_chronic_disease, fd_or_child_has_cancer,
              fd_or_parent_has_serious_disease, fd_or_parent_has_rare_disease,
              fd_or_parent_has_chronic_disease, fd_or_parent_has_cancer, fd_or_parent_has_infertility,
              fd_or_is_violence_victim, fd_or_is_abuse_victim, fd_or_is_defector,
              fd_or_is_national_merit, fd_or_is_foster_child, fd_or_is_single_mother, fd_or_is_low_income,
              fd_or_education_level, fd_or_is_enrolled, fd_or_housing_type,
              fd_or_income_min_percent, fd_or_income_max_percent, 
              fd_or_household_members_min, fd_or_household_members_max,
              fd_or_children_min, fd_or_children_max, fd_or_birth_order,
              fd_or_birth_order_min, fd_or_birth_order_max, fd_or_residence_min_months,
              fd_or_pregnancy_weeks_min, fd_or_pregnancy_weeks_max, fd_or_birth_within_months,
              fd_or_age_min_months, fd_or_age_max_months, fd_or_limit_birth_date
            ) VALUES (
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            try:
                self.cursor.execute(sql, (
                    # 서비스 정보 (9개)
                    service_id, service_name, detail_url,
                    sido, sigungu, source,
                    target_text, criteria_text, support_text,
                    # 혜택 정보 (8개)
                    benefit.get('amount'), benefit.get('amount_type'),
                    benefit.get('amount_unit'), benefit.get('benefit_type'),
                    benefit.get('payment_cycle'), benefit.get('payment_method'),
                    benefit.get('payment_timing'), benefit.get('description'),
                    # AND 조건 (43개)
                    and_cond.get('age_min_months'), and_cond.get('age_max_months'),
                    and_cond.get('income_type'), and_cond.get('income_min_percent'), and_cond.get('income_max_percent'),
                    and_cond.get('household_type'),
                    and_cond.get('household_members_min'), and_cond.get('household_members_max'),
                    and_cond.get('children_min'), and_cond.get('children_max'),
                    and_cond.get('birth_order'), and_cond.get('birth_order_min'),
                    and_cond.get('birth_order_max'), and_cond.get('residence_min_months'),
                    and_cond.get('childcare_type'),
                    and_cond.get('requires_grandparent_care'), and_cond.get('requires_dual_income'),
                    and_cond.get('requires_disability'), and_cond.get('requires_parent_disability'),
                    and_cond.get('child_disability_level'), and_cond.get('parent_disability_level'),
                    and_cond.get('child_has_serious_disease'), and_cond.get('child_has_rare_disease'),
                    and_cond.get('child_has_chronic_disease'), and_cond.get('child_has_cancer'),
                    and_cond.get('parent_has_serious_disease'), and_cond.get('parent_has_rare_disease'),
                    and_cond.get('parent_has_chronic_disease'), and_cond.get('parent_has_cancer'),
                    and_cond.get('parent_has_infertility'),
                    and_cond.get('is_violence_victim'), and_cond.get('is_abuse_victim'),
                    and_cond.get('is_defector'), and_cond.get('is_national_merit'),
                    and_cond.get('is_foster_child'), and_cond.get('is_single_mother'),
                    and_cond.get('is_low_income'),
                    and_cond.get('pregnancy_weeks_min'), and_cond.get('pregnancy_weeks_max'),
                    and_cond.get('birth_within_months'),
                    and_cond.get('limit_birth_date'),
                    and_cond.get('education_level'), and_cond.get('is_enrolled'),
                    and_cond.get('housing_type'),
                    # OR 조건 카테고리형 (28개)
                    or_income, or_household, or_childcare,
                    or_req_grandparent, or_req_dual,
                    or_req_disability, or_req_parent_disability, 
                    or_disability_level, or_parent_disability_level,
                    or_child_serious, or_child_rare, or_child_chronic, or_child_cancer,
                    or_parent_serious, or_parent_rare, or_parent_chronic, or_parent_cancer,
                    or_parent_infertility,
                    or_violence, or_abuse, or_defector, or_merit, or_foster, or_single,
                    or_low_income, or_education, or_enrolled, or_housing,
                    # OR 조건 숫자형 (16개)
                    or_income_min_percent, or_income_max_percent, 
                    or_household_members_min, or_household_members_max,
                    or_children_min, or_children_max, or_birth_order,
                    or_birth_order_min, or_birth_order_max, or_residence_min_months,
                    or_pregnancy_weeks_min, or_pregnancy_weeks_max, or_birth_within_months,
                    or_age_min_months, or_age_max_months, or_limit_birth_date
                ))  # 총 105개 (9+8+44+28+16)
            except Exception as e:
                print(f"❌ 삽입 오류: {e}")
                print(f"   Service ID: {service_id}")
                import traceback
                traceback.print_exc()
    
    def convert_json_to_db(self, json_path):
        """JSON → DB 변환"""
        print(f"\n{'='*80}")
        print(f"📥 처리 중: {json_path}")
        print(f"{'='*80}\n")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            services = json.load(f)
        
        print(f"서비스 개수: {len(services)}\n")
        
        for idx, service in enumerate(services, 1):
            print(f"[{idx}/{len(services)}] {service['service_name']}")
            benefits = service.get('parsed_data', {}).get('benefits', [])
            print(f"  💰 혜택 {len(benefits)}개")
            
            self.insert_unified(service)
        
        self.conn.commit()
        print(f"\n{'='*80}")
        print(f"✅ 변환 완료!")
        print(f"{'='*80}")
    
    def close(self):
        self.cursor.close()
        self.conn.close()
        print("✅ DB 연결 종료")

if __name__ == "__main__":
    converter = WelfareConverter()
    
    json_files = glob.glob('./정형화데이터/정형화데이터_*.json')
    
    if not json_files:
        print("❌ 정형화데이터 폴더에 JSON 파일이 없습니다!")
        exit(1)
    
    print(f"📂 발견된 파일: {len(json_files)}개")
    
    for json_file in json_files:
        converter.convert_json_to_db(json_file)
    
    converter.close()
    
    print("\n" + "="*80)
    print("🎉 v5.0 변환 완료!")
    print("="*80)