#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
복지 JSON → DB 변환 스크립트 v4.5
- 27개 OR 조건 완전 지원
- danz_welfare_* 테이블 사용
- fd_ 접두사 사용
"""

import pymysql
import json
import glob
import os

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
        """값을 쉼표 구분 문자열로 변환 (빈 배열은 NULL)"""
        if not value:
            return None  # 빈 값은 NULL로
        
        # Boolean 처리
        if isinstance(value, bool):
            return None if not value else 'true'  # True만 'true', False는 NULL
        
        # 리스트 처리
        if isinstance(value, list):
            if len(value) == 0:
                return None  # 빈 배열은 NULL
            # Boolean 배열 처리
            if all(isinstance(x, bool) for x in value):
                return 'true' if any(value) else None  # 하나라도 True면 'true'
            # 문자열 배열 처리 → 쉼표 구분
            return ','.join(str(v) for v in value)
        
        # 단일 문자열
        return str(value)
    
    def insert_service(self, service):
        """서비스 삽입 (fd_ 접두사)"""
        sql = """
        INSERT INTO danz_welfare_services (
          fd_service_id, fd_service_name, fd_detail_url,
          fd_sido, fd_sigungu, fd_source,
          fd_target_text, fd_criteria_text, fd_support_text
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          fd_service_name=VALUES(fd_service_name),
          fd_detail_url=VALUES(fd_detail_url),
          fd_sido=VALUES(fd_sido),
          fd_sigungu=VALUES(fd_sigungu),
          fd_source=VALUES(fd_source),
          fd_target_text=VALUES(fd_target_text),
          fd_criteria_text=VALUES(fd_criteria_text),
          fd_support_text=VALUES(fd_support_text)
        """
        
        original = service.get('original_data', {})
        
        try:
            self.cursor.execute(sql, (
                service['service_id'],
                service['service_name'],
                service.get('detail_url'),
                service.get('sido'),
                service.get('sigungu'),
                service.get('source'),
                original.get('target_text'),
                original.get('criteria_text'),
                original.get('support_text')
            ))
        except Exception as e:
            print(f"❌ 서비스 삽입 오류: {e}")
            print(f"   Service ID: {service['service_id']}")
    
    def insert_benefit(self, service_id, benefit):
        """혜택 삽입 (27개 OR 조건, fd_ 접두사)"""
        
        # and_conditions 추출
        and_cond = benefit.get('and_conditions', {})
        
        # False 값 필터링
        for key, value in list(and_cond.items()):
            if value is False:
                and_cond[key] = None
        
        # ⭐ or_conditions 27개 처리
        or_cond = benefit.get('or_conditions', {})
        
        # 27개 OR 조건 JSON 배열 생성
        or_income_json = self.to_json(or_cond.get('income_type'))
        or_household_json = self.to_json(or_cond.get('household_type'))
        or_childcare_json = self.to_json(or_cond.get('childcare_type'))
        
        or_requires_grandparent_json = self.to_json(or_cond.get('requires_grandparent_care'))
        or_requires_dual_income_json = self.to_json(or_cond.get('requires_dual_income'))
        
        or_requires_disability_json = self.to_json(or_cond.get('requires_disability'))
        or_requires_parent_disability_json = self.to_json(or_cond.get('requires_parent_disability'))
        or_disability_level_json = self.to_json(or_cond.get('disability_level'))
        
        or_child_serious_json = self.to_json(or_cond.get('child_has_serious_disease'))
        or_child_rare_json = self.to_json(or_cond.get('child_has_rare_disease'))
        or_child_chronic_json = self.to_json(or_cond.get('child_has_chronic_disease'))
        or_child_cancer_json = self.to_json(or_cond.get('child_has_cancer'))
        
        or_parent_serious_json = self.to_json(or_cond.get('parent_has_serious_disease'))
        or_parent_rare_json = self.to_json(or_cond.get('parent_has_rare_disease'))
        or_parent_chronic_json = self.to_json(or_cond.get('parent_has_chronic_disease'))
        or_parent_cancer_json = self.to_json(or_cond.get('parent_has_cancer'))
        or_parent_infertility_json = self.to_json(or_cond.get('parent_has_infertility'))
        
        or_violence_json = self.to_json(or_cond.get('is_violence_victim'))
        or_abuse_json = self.to_json(or_cond.get('is_abuse_victim'))
        or_defector_json = self.to_json(or_cond.get('is_defector'))
        or_merit_json = self.to_json(or_cond.get('is_national_merit'))
        or_foster_json = self.to_json(or_cond.get('is_foster_child'))
        or_single_json = self.to_json(or_cond.get('is_single_mother'))
        or_low_income_json = self.to_json(or_cond.get('is_low_income'))
        
        or_education_json = self.to_json(or_cond.get('education_level'))
        or_enrolled_json = self.to_json(or_cond.get('is_enrolled'))
        or_housing_json = self.to_json(or_cond.get('housing_type'))
        
        sql = """
        INSERT INTO danz_welfare_benefits (
          fd_service_id,
          fd_amount, fd_amount_type, fd_amount_unit, fd_benefit_type,
          fd_payment_cycle, fd_payment_method, fd_payment_timing, fd_description,
          fd_age_min_months, fd_age_max_months,
          fd_income_type, fd_income_max_percent,
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
          fd_education_level, fd_is_enrolled, fd_housing_type,
          
          -- 27개 OR 조건
          fd_or_income_type, fd_or_household_type, fd_or_childcare_type,
          fd_or_requires_grandparent_care, fd_or_requires_dual_income,
          fd_or_requires_disability, fd_or_requires_parent_disability, fd_or_disability_level,
          fd_or_child_has_serious_disease, fd_or_child_has_rare_disease,
          fd_or_child_has_chronic_disease, fd_or_child_has_cancer,
          fd_or_parent_has_serious_disease, fd_or_parent_has_rare_disease,
          fd_or_parent_has_chronic_disease, fd_or_parent_has_cancer, fd_or_parent_has_infertility,
          fd_or_is_violence_victim, fd_or_is_abuse_victim, fd_or_is_defector,
          fd_or_is_national_merit, fd_or_is_foster_child, fd_or_is_single_mother, fd_or_is_low_income,
          fd_or_education_level, fd_or_is_enrolled, fd_or_housing_type
        ) VALUES (
          %s,
          %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s
        )
        """
        
        try:
            self.cursor.execute(sql, (
                service_id,
                benefit.get('amount'), benefit.get('amount_type'),
                benefit.get('amount_unit'), benefit.get('benefit_type'),
                benefit.get('payment_cycle'), benefit.get('payment_method'),
                benefit.get('payment_timing'), benefit.get('description'),
                
                and_cond.get('age_min_months'), and_cond.get('age_max_months'),
                and_cond.get('income_type'), and_cond.get('income_max_percent'),
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
                and_cond.get('education_level'), and_cond.get('is_enrolled'),
                and_cond.get('housing_type'),
                
                # 27개 OR 조건
                or_income_json, or_household_json, or_childcare_json,
                or_requires_grandparent_json, or_requires_dual_income_json,
                or_requires_disability_json, or_requires_parent_disability_json,
                or_disability_level_json,
                or_child_serious_json, or_child_rare_json,
                or_child_chronic_json, or_child_cancer_json,
                or_parent_serious_json, or_parent_rare_json,
                or_parent_chronic_json, or_parent_cancer_json, or_parent_infertility_json,
                or_violence_json, or_abuse_json, or_defector_json,
                or_merit_json, or_foster_json, or_single_json, or_low_income_json,
                or_education_json, or_enrolled_json, or_housing_json
            ))
        except Exception as e:
            print(f"❌ 혜택 삽입 오류: {e}")
            print(f"   Service ID: {service_id}")
            print(f"   Benefit: {benefit.get('description', 'N/A')[:50]}")
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
            
            # 서비스 삽입
            self.insert_service(service)
            
            # 혜택 삽입
            benefits = service.get('parsed_data', {}).get('benefits', [])
            print(f"  💰 혜택 {len(benefits)}개")
            
            for benefit in benefits:
                self.insert_benefit(service['service_id'], benefit)
        
        self.conn.commit()
        print(f"\n{'='*80}")
        print(f"✅ 변환 완료!")
        print(f"{'='*80}")
        print(f"총 서비스: {len(services)}개")
        total_benefits = sum(len(s.get('parsed_data', {}).get('benefits', [])) for s in services)
        print(f"총 혜택: {total_benefits}개")
        if len(services) > 0:
            print(f"평균 혜택/서비스: {total_benefits/len(services):.1f}개")
    
    def close(self):
        """연결 종료"""
        self.cursor.close()
        self.conn.close()
        print("✅ DB 연결 종료")

if __name__ == "__main__":
    converter = WelfareConverter()
    
    # JSON 파일 찾기
    json_files = glob.glob('./정형화데이터/정형화데이터_*.json')
    
    if not json_files:
        print("❌ 정형화데이터 폴더에 JSON 파일이 없습니다!")
        exit(1)
    
    print(f"📂 발견된 파일: {len(json_files)}개")
    for i, f in enumerate(json_files, 1):
        print(f"  [{i}] {f}")
    
    # 변환 실행
    for json_file in json_files:
        converter.convert_json_to_db(json_file)
    
    converter.close()
    
    print("\n" + "="*80)
    print("🎉 v4.5 변환 완료!")
    print(f"총 {len(json_files)}개 파일 처리 완료")
    print("변경사항:")
    print("  - fd_ 접두사 사용")
    print("  - 27개 OR 조건 완전 지원")
    print("  - 쉼표 구분 형식")
    print("="*80)