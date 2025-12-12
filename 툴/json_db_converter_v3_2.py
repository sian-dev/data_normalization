"""
JSON → DB 컨버터 v2
- and_conditions / or_conditions 분리
"""
import json
import pymysql

class JSONtoDBConverterV2:
    def __init__(self, host, user, password, database):
        """DB 연결 초기화"""
        self.conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        self.cursor = self.conn.cursor()
    
    def insert_service(self, item):
        """서비스 기본 정보 삽입"""
        sql = """
        INSERT INTO welfare_services (service_id, service_name, detail_url, sido, sigungu, source)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          service_name = VALUES(service_name),
          detail_url = VALUES(detail_url),
          sido = VALUES(sido),
          sigungu = VALUES(sigungu),
          source = VALUES(source)
        """
        
        self.cursor.execute(sql, (
            item['service_id'],
            item['service_name'],
            item.get('detail_url'),
            item.get('sido'),
            item.get('sigungu'),
            item.get('source', '중앙부처')
        ))
    
    def insert_and_conditions(self, service_id, and_cond):
        """AND 조건 삽입"""
        sql = """
        INSERT INTO welfare_and_conditions (
          service_id, age_min_months, age_max_months, income_max_percent, income_type,
          residence_min_months, household_type, children_min, children_max,
          pregnancy_weeks_min, pregnancy_weeks_max, birth_within_months,
          requires_dual_income, requires_grandparent_care, requires_disability,
          disability_level, requires_parent_disability, parent_disability_level,
          birth_special, housing_type, other_conditions
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          age_min_months = VALUES(age_min_months),
          age_max_months = VALUES(age_max_months),
          income_max_percent = VALUES(income_max_percent),
          income_type = VALUES(income_type),
          residence_min_months = VALUES(residence_min_months),
          household_type = VALUES(household_type),
          children_min = VALUES(children_min),
          children_max = VALUES(children_max),
          pregnancy_weeks_min = VALUES(pregnancy_weeks_min),
          pregnancy_weeks_max = VALUES(pregnancy_weeks_max),
          birth_within_months = VALUES(birth_within_months),
          requires_dual_income = VALUES(requires_dual_income),
          requires_grandparent_care = VALUES(requires_grandparent_care),
          requires_disability = VALUES(requires_disability),
          disability_level = VALUES(disability_level),
          requires_parent_disability = VALUES(requires_parent_disability),
          parent_disability_level = VALUES(parent_disability_level),
          birth_special = VALUES(birth_special),
          housing_type = VALUES(housing_type),
          other_conditions = VALUES(other_conditions)
        """
        
        # 배열을 JSON 문자열로 변환
        income_type = json.dumps(and_cond.get('income_type'), ensure_ascii=False) if isinstance(and_cond.get('income_type'), list) else and_cond.get('income_type')
        household_type = json.dumps(and_cond.get('household_type'), ensure_ascii=False) if isinstance(and_cond.get('household_type'), list) else and_cond.get('household_type')
        
        self.cursor.execute(sql, (
            service_id,
            and_cond.get('age_min_months'),
            and_cond.get('age_max_months'),
            and_cond.get('income_max_percent'),
            income_type,
            and_cond.get('residence_min_months'),
            household_type,
            and_cond.get('children_min'),
            and_cond.get('children_max'),
            and_cond.get('pregnancy_weeks_min'),
            and_cond.get('pregnancy_weeks_max'),
            and_cond.get('birth_within_months'),
            and_cond.get('requires_dual_income'),
            and_cond.get('requires_grandparent_care'),
            and_cond.get('requires_disability'),
            and_cond.get('disability_level'),
            and_cond.get('requires_parent_disability'),
            and_cond.get('parent_disability_level'),
            and_cond.get('birth_special'),
            and_cond.get('housing_type'),
            and_cond.get('other_conditions')
        ))
    
    def insert_or_conditions(self, service_id, or_cond):
        """OR 조건 삽입"""
        # OR 조건이 모두 None이면 삽입하지 않음
        has_condition = any(or_cond.get(key) is not None for key in [
            'age_max_months', 'requires_disability', 'household_type', 
            'children_min', 'birth_within_months', 'description'
        ])
        
        if not has_condition:
            return
        
        sql = """
        INSERT INTO welfare_or_conditions (
          service_id, age_max_months, requires_disability, disability_level,
          household_type, children_min, pregnancy_weeks_min, pregnancy_weeks_max,
          birth_within_months, requires_parent_disability, parent_disability_level,
          birth_special, description
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          age_max_months = VALUES(age_max_months),
          requires_disability = VALUES(requires_disability),
          disability_level = VALUES(disability_level),
          household_type = VALUES(household_type),
          children_min = VALUES(children_min),
          pregnancy_weeks_min = VALUES(pregnancy_weeks_min),
          pregnancy_weeks_max = VALUES(pregnancy_weeks_max),
          birth_within_months = VALUES(birth_within_months),
          requires_parent_disability = VALUES(requires_parent_disability),
          parent_disability_level = VALUES(parent_disability_level),
          birth_special = VALUES(birth_special),
          description = VALUES(description)
        """
        
        # 배열을 JSON 문자열로 변환
        household_type = json.dumps(or_cond.get('household_type'), ensure_ascii=False) if isinstance(or_cond.get('household_type'), list) else or_cond.get('household_type')
        
        self.cursor.execute(sql, (
            service_id,
            or_cond.get('age_max_months'),
            or_cond.get('requires_disability'),
            or_cond.get('disability_level'),
            household_type,
            or_cond.get('children_min'),
            or_cond.get('pregnancy_weeks_min'),
            or_cond.get('pregnancy_weeks_max'),
            or_cond.get('birth_within_months'),
            or_cond.get('requires_parent_disability'),
            or_cond.get('parent_disability_level'),
            or_cond.get('birth_special'),
            or_cond.get('description')
        ))
    
    def insert_benefits(self, service_id, benefits):
        """혜택 정보 삽입"""
        sql = """
        INSERT INTO welfare_benefits (
          service_id, amount, amount_type, support_count, support_period,
          max_amount_per_child, max_amount_total, birth_order, support_type, support_description
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        for benefit in benefits:
            self.cursor.execute(sql, (
                service_id,
                benefit.get('amount'),
                benefit.get('amount_type'),
                benefit.get('support_count'),
                benefit.get('support_period'),
                benefit.get('max_amount_per_child'),
                benefit.get('max_amount_total'),
                benefit.get('birth_order'),
                benefit.get('support_type'),
                benefit.get('support_description')
            ))
    
    def batch_insert_from_json(self, json_path):
        """JSON 파일에서 일괄 삽입"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n총 {len(data)}개 데이터 삽입 시작...\n")
        
        for idx, item in enumerate(data, 1):
            try:
                service_id = item['service_id']
                service_name = item['service_name']
                source = item.get('source', '중앙부처')
                sido = item.get('sido', '')
                sigungu = item.get('sigungu', '')
                
                # 지역 표시
                if source == '중앙부처':
                    location = '[중앙부처]'
                elif sigungu:
                    location = f'[{sido}/{sigungu}]'
                elif sido:
                    location = f'[{sido}]'
                else:
                    location = '[지역미상]'
                
                print(f"[{idx}/{len(data)}] {location} {service_name[:40]}")
                
                # 서비스 정보 삽입
                self.insert_service(item)
                
                # 조건 정보 삽입
                parsed = item['parsed_data']
                self.insert_and_conditions(service_id, parsed['and_conditions'])
                self.insert_or_conditions(service_id, parsed['or_conditions'])
                
                # 혜택 정보 삽입
                self.insert_benefits(service_id, parsed['benefits'])
                
            except Exception as e:
                print(f"  ⚠️  오류: {e}")
                continue
        
        self.conn.commit()
        print(f"\n✅ 완료: {len(data)}개 처리")
    
    def batch_insert_multiple_files(self, json_paths):
        """여러 JSON 파일을 한번에 처리"""
        total_count = 0
        
        for json_path in json_paths:
            print(f"\n{'='*60}")
            print(f"📂 파일: {json_path}")
            print(f"{'='*60}")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"총 {len(data)}개 데이터 처리 중...\n")
            
            for idx, item in enumerate(data, 1):
                try:
                    service_id = item['service_id']
                    service_name = item['service_name']
                    source = item.get('source', '중앙부처')
                    sido = item.get('sido', '')
                    sigungu = item.get('sigungu', '')
                    
                    # 지역 표시
                    if source == '중앙부처':
                        location = '[중앙부처]'
                    elif sigungu:
                        location = f'[{sido}/{sigungu}]'
                    elif sido:
                        location = f'[{sido}]'
                    else:
                        location = '[지역미상]'
                    
                    print(f"[{idx}/{len(data)}] {location} {service_name[:40]}")
                    
                    # 서비스 정보 삽입
                    self.insert_service(item)
                    
                    # 조건 정보 삽입
                    parsed = item['parsed_data']
                    self.insert_and_conditions(service_id, parsed['and_conditions'])
                    self.insert_or_conditions(service_id, parsed['or_conditions'])
                    
                    # 혜택 정보 삽입
                    self.insert_benefits(service_id, parsed['benefits'])
                    
                    total_count += 1
                    
                except Exception as e:
                    print(f"  ⚠️  오류: {e}")
                    continue
            
            self.conn.commit()
            print(f"✅ 파일 완료: {len(data)}개 처리\n")
        
        print(f"\n{'='*60}")
        print(f"🎉 전체 완료: 총 {total_count}개 복지 데이터 저장됨")
        print(f"{'='*60}\n")
    
    def close(self):
        """연결 종료"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    converter = JSONtoDBConverterV2(
        host='192.168.56.82',
        user='work',
        password='1111',
        database='work_local'
    )
    
    # ⭐ 여러 파일 한번에 처리
    converter.batch_insert_multiple_files([
        '정형화데이터_중앙부.json',  # 중앙부처
        '정형화데이터_울산.json'     # 울산
    ])
    
    converter.close()