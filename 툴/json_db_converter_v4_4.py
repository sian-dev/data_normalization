"""
복지 DB 컨버터 v4.2 (OR 조건 개별 컬럼)
- ⭐ v4.2 변경: or_conditions → or_household_type, or_income_type 분리
- JSON → DB INSERT
"""
import json
import pymysql
from datetime import datetime
import glob
import os
from dotenv import load_dotenv

class WelfareDBConverterV4_2:
    def __init__(self, db_config):
        """DB 설정 초기화"""
        self.db_config = db_config
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """DB 연결"""
        try:
            self.conn = pymysql.connect(
                host=self.db_config['host'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                charset='utf8mb4'
            )
            self.cursor = self.conn.cursor()
            print("✅ DB 연결 성공!")
        except Exception as e:
            print(f"❌ DB 연결 실패: {e}")
            raise
    
    def close(self):
        """DB 연결 종료"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✅ DB 연결 종료")
    
    def insert_service(self, service):
        """서비스 삽입"""
        sql = """
        INSERT INTO welfare_services (
          service_id, service_name, detail_url, sido, sigungu, source,
          target_text, criteria_text, support_text
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
          service_name = VALUES(service_name),
          detail_url = VALUES(detail_url),
          sido = VALUES(sido),
          sigungu = VALUES(sigungu),
          source = VALUES(source)
        """
        
        try:
            original = service.get('original_data', {})
            
            self.cursor.execute(sql, (
                service['service_id'],
                service['service_name'],
                service['detail_url'],
                service['sido'] if service.get('sido') else None,
                service['sigungu'] if service.get('sigungu') else None,
                service['source'],
                original.get('target_text', ''),
                original.get('criteria_text', ''),
                original.get('support_text', '')
            ))
        except Exception as e:
            print(f"❌ 서비스 삽입 오류 ({service['service_name']}): {e}")
    
    def insert_benefit(self, service_id, benefit):
        """혜택 삽입 (OR 조건 개별 컬럼)"""
        
        # and_conditions 추출
        and_cond = benefit.get('and_conditions', {})
        
        # False 값 필터링 (False → None)
        for key, value in list(and_cond.items()):
            if value is False:
                and_cond[key] = None
        
        # ⭐ or_conditions 분리 (household_type, income_type)
        or_cond = benefit.get('or_conditions', {})
        
        # or_household_type JSON 배열
        or_household = or_cond.get('household_type', [])
        or_household_json = json.dumps(or_household, ensure_ascii=False) if or_household else '[]'
        
        # or_income_type JSON 배열
        or_income = or_cond.get('income_type', [])
        or_income_json = json.dumps(or_income, ensure_ascii=False) if or_income else '[]'
        
        sql = """
        INSERT INTO welfare_benefits (
          service_id,
          
          -- 혜택 정보
          amount, amount_type, amount_unit, benefit_type,
          payment_cycle, payment_method, payment_timing, description,
          
          -- AND 조건
          age_min_months, age_max_months,
          income_type, income_max_percent,
          household_type, household_members_min, household_members_max,
          children_min, children_max, birth_order,
          residence_min_months,
          childcare_type, requires_grandparent_care, requires_dual_income,
          requires_disability, requires_parent_disability, disability_level,
          child_has_serious_disease, child_has_rare_disease, child_has_chronic_disease, child_has_cancer,
          parent_has_serious_disease, parent_has_rare_disease, parent_has_chronic_disease, parent_has_cancer, parent_has_infertility,
          is_violence_victim, is_abuse_victim, is_defector, is_national_merit, is_foster_child, is_single_mother, is_low_income,
          pregnancy_weeks_min, pregnancy_weeks_max, birth_within_months,
          education_level, is_enrolled,
          housing_type,
          
          -- OR 조건 (개별 컬럼)
          or_household_type, or_income_type
        ) VALUES (
          %s,
          %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s,
          %s, %s
        )
        """
        
        try:
            self.cursor.execute(sql, (
                service_id,
                
                # 혜택 정보
                benefit.get('amount'),
                benefit.get('amount_type'),
                benefit.get('amount_unit'),
                benefit.get('benefit_type'),
                benefit.get('payment_cycle'),
                benefit.get('payment_method'),
                benefit.get('payment_timing'),
                benefit.get('description'),
                
                # AND 조건
                and_cond.get('age_min_months'),
                and_cond.get('age_max_months'),
                and_cond.get('income_type'),
                and_cond.get('income_max_percent'),
                and_cond.get('household_type'),
                and_cond.get('household_members_min'),
                and_cond.get('household_members_max'),
                and_cond.get('children_min'),
                and_cond.get('children_max'),
                and_cond.get('birth_order'),
                and_cond.get('residence_min_months'),
                and_cond.get('childcare_type'),
                and_cond.get('requires_grandparent_care'),
                and_cond.get('requires_dual_income'),
                and_cond.get('requires_disability'),
                and_cond.get('requires_parent_disability'),
                and_cond.get('disability_level'),
                and_cond.get('child_has_serious_disease'),
                and_cond.get('child_has_rare_disease'),
                and_cond.get('child_has_chronic_disease'),
                and_cond.get('child_has_cancer'),
                and_cond.get('parent_has_serious_disease'),
                and_cond.get('parent_has_rare_disease'),
                and_cond.get('parent_has_chronic_disease'),
                and_cond.get('parent_has_cancer'),
                and_cond.get('parent_has_infertility'),
                and_cond.get('is_violence_victim'),
                and_cond.get('is_abuse_victim'),
                and_cond.get('is_defector'),
                and_cond.get('is_national_merit'),
                and_cond.get('is_foster_child'),
                and_cond.get('is_single_mother'),
                and_cond.get('is_low_income'),
                and_cond.get('pregnancy_weeks_min'),
                and_cond.get('pregnancy_weeks_max'),
                and_cond.get('birth_within_months'),
                and_cond.get('education_level'),
                and_cond.get('is_enrolled'),
                and_cond.get('housing_type'),
                
                # OR 조건 (개별 컬럼)
                or_household_json,
                or_income_json
            ))
        except Exception as e:
            print(f"❌ 혜택 삽입 오류: {e}")
            print(f"   Service ID: {service_id}")
            print(f"   Benefit: {benefit.get('description', 'N/A')[:50]}")
            import traceback
            traceback.print_exc()
    
    def convert_json_to_db(self, json_path):
        """JSON → DB 변환 (v4.2)"""
        print(f"\n{'='*80}")
        print(f"📥 JSON 파일 읽기: {json_path}")
        print(f"{'='*80}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            services = json.load(f)
        
        total_services = len(services)
        total_benefits = 0
        
        print(f"서비스 개수: {total_services}")
        
        for idx, service in enumerate(services, 1):
            service_id = service['service_id']
            service_name = service['service_name']
            
            print(f"\n[{idx}/{total_services}] {service_name[:60]}")
            
            # 1. 서비스 삽입
            self.insert_service(service)
            
            # 2. 혜택 삽입
            parsed_data = service.get('parsed_data', {})
            benefits = parsed_data.get('benefits', [])
            
            if not benefits:
                print(f"  ⚠️ 혜택 없음")
                continue
            
            print(f"  💰 혜택 {len(benefits)}개")
            
            for benefit_idx, benefit in enumerate(benefits, 1):
                self.insert_benefit(service_id, benefit)
                total_benefits += 1
                
                # 진행 상황 출력
                desc = benefit.get('description', 'N/A')[:40]
                amount = benefit.get('amount')
                amount_str = f"{amount:,}원" if amount else "금액없음"
                
                # OR 조건 확인
                or_cond = benefit.get('or_conditions', {})
                or_household = or_cond.get('household_type', [])
                or_income = or_cond.get('income_type', [])
                or_info = ""
                if or_household:
                    or_info += f" [OR 가구: {','.join(or_household)}]"
                if or_income:
                    or_info += f" [OR 소득: {','.join(or_income)}]"
                
                print(f"    [{benefit_idx}] {desc}... ({amount_str}){or_info}")
        
        # 커밋
        self.conn.commit()
        
        print(f"\n{'='*80}")
        print(f"✅ 변환 완료!")
        print(f"{'='*80}")
        print(f"총 서비스: {total_services}개")
        print(f"총 혜택: {total_benefits}개")
        print(f"평균 혜택/서비스: {total_benefits / total_services:.1f}개")

# 사용 예시
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    import glob
    
    # .env 파일에서 환경 변수 로드
    load_dotenv()
    
    # DB 설정
    db_config = {
        'host': os.getenv('DB_HOST', '192.168.56.82'),
        'user': os.getenv('DB_USER', 'work'),
        'password': os.getenv('DB_PASSWORD', '1111'),
        'database': os.getenv('DB_NAME', 'work_local')
    }
    
    # JSON 파일 찾기
    json_patterns = [
        './정형화데이터/정형화데이터_울산.json',
        # './정형화데이터/정형화데이터_중앙부.json'
    ]
    
    json_files = []
    for pattern in json_patterns:
        if os.path.exists(pattern):
            json_files.append(pattern)
    
    if not json_files:
        print("❌ 정형화데이터 파일을 찾을 수 없습니다!")
        exit(1)
    
    print(f"📂 발견된 파일: {len(json_files)}개")
    for i, f in enumerate(json_files, 1):
        print(f"  [{i}] {f}")
    
    converter = WelfareDBConverterV4_2(db_config)
    
    try:
        # DB 연결
        converter.connect()
        
        # 모든 파일 처리
        for json_file in json_files:
            print(f"\n{'='*80}")
            print(f"📥 처리 중: {json_file}")
            print(f"{'='*80}")
            
            # JSON → DB 변환
            converter.convert_json_to_db(json_file)
        
    finally:
        converter.close()
    
    print("\n" + "="*80)
    print("🎉 v4.2 변환 완료!")
    print(f"총 {len(json_files)}개 파일 처리 완료")
    print("변경사항:")
    print("  1. or_conditions → or_household_type, or_income_type 분리")
    print("  2. OR 조건 JSON 배열로 저장")
    print("  3. False 값 자동 필터링")
    print("="*80)