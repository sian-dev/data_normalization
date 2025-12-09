"""
JSON → MariaDB 변환기 (개선 버전)
- AI가 생성한 JSON 파일을 MariaDB에 저장
- 지원 횟수, 최대 금액, 링크 포함
"""
import mysql.connector
import json
from datetime import datetime

class JSONToDBConverter:
    def __init__(self, host='localhost', user='root', password='', database='welfare_db'):
        """
        MariaDB 연결
        """
        self.conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        self.cursor = self.conn.cursor()
    
    def load_json(self, json_path):
        """
        JSON 파일 로드
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n📂 JSON 로드: {len(data)}개 복지")
        return data
    
    def insert_service_from_json(self, item):
        """
        JSON 데이터를 DB에 삽입
        
        Args:
            item: JSON 아이템 (service_id, service_name, sido, sigungu, source, parsed_data 포함)
        """
        service_id = item['service_id']
        service_name = item['service_name']
        detail_url = item.get('detail_url', '')
        
        # JSON에서 지역 정보 가져오기
        sido = item.get('sido')
        sigungu = item.get('sigungu')
        source = item.get('source')
        
        original = item.get('original_data', {})
        parsed = item['parsed_data']
        
        # 1. welfare_services 삽입
        self.cursor.execute('''
        INSERT INTO welfare_services 
        (service_id, service_name, source, sido, sigungu, 
         description, support_content, department, contact, detail_url,
         application_method, application_period)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        service_name = VALUES(service_name),
        detail_url = VALUES(detail_url)
        ''', (
            service_id,
            service_name,
            source,
            sido,
            sigungu,
            original.get('target_text', '')[:500],  # description
            original.get('support_text', '')[:1000],  # support_content
            None,  # department (XML에서 별도 추출)
            None,  # contact
            detail_url,
            None,  # application_method
            None   # application_period
        ))
        
        # 2. welfare_conditions 삽입
        cond = parsed['conditions']
        self.cursor.execute('''
        INSERT INTO welfare_conditions 
        (service_id, age_min_months, age_max_months, income_max_percent, income_type,
         residence_min_months, household_type, children_min, children_max,
         pregnancy_weeks_min, pregnancy_weeks_max, birth_within_months,
         requires_dual_income, requires_grandparent_care, requires_disability,
         disability_level, requires_parent_disability, parent_disability_level,
         birth_special, housing_type, other_conditions)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            service_id,
            cond.get('age_min_months'),
            cond.get('age_max_months'),
            cond.get('income_max_percent'),
            cond.get('income_type'),
            cond.get('residence_min_months'),
            cond.get('household_type'),
            cond.get('children_min'),
            cond.get('children_max'),
            cond.get('pregnancy_weeks_min'),
            cond.get('pregnancy_weeks_max'),
            cond.get('birth_within_months'),
            cond.get('requires_dual_income'),
            cond.get('requires_grandparent_care'),
            cond.get('requires_disability'),
            cond.get('disability_level'),
            cond.get('requires_parent_disability'),
            cond.get('parent_disability_level'),
            ','.join(cond['birth_special']) if cond.get('birth_special') else None,
            cond.get('housing_type'),
            cond.get('other_conditions')
        ))
        
        # 3. welfare_benefits 삽입 (개선 버전)
        for benefit in parsed.get('benefits', []):
            self.cursor.execute('''
            INSERT INTO welfare_benefits 
            (service_id, amount, amount_type, 
             support_count, support_period,
             max_amount_per_child, max_amount_total,
             birth_order, benefit_sigungu, 
             support_type, support_description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                service_id,
                benefit.get('amount'),
                benefit.get('amount_type'),
                benefit.get('support_count'),          # NEW
                benefit.get('support_period'),         # NEW
                benefit.get('max_amount_per_child'),   # NEW
                benefit.get('max_amount_total'),       # NEW
                benefit.get('birth_order'),
                sigungu,  # 지역별 차등
                benefit.get('support_type', '서비스'),
                benefit.get('support_description', '')[:200]
            ))
        
        # 4. welfare_tags 삽입 (기본 태그)
        self.insert_default_tags(service_id, service_name, cond)
    
    def insert_default_tags(self, service_id, service_name, conditions):
        """
        기본 태그 생성 (서비스명 기반)
        """
        tags = []
        
        # 나이 기반 생애주기 태그
        if conditions.get('age_max_months'):
            max_months = conditions['age_max_months']
            if max_months <= 72:
                tags.append(('생애주기', '영유아'))
            elif max_months <= 144:
                tags.append(('생애주기', '아동'))
        
        # 임신/출산 태그
        if conditions.get('pregnancy_weeks_min') or conditions.get('birth_within_months'):
            tags.append(('생애주기', '임신·출산'))
        
        # 가구형태 태그
        if conditions.get('household_type'):
            household = conditions['household_type']
            if '한부모' in household:
                tags.append(('대상자', '한부모'))
            if '조손' in household:
                tags.append(('대상자', '조손'))
            if '다문화' in household:
                tags.append(('대상자', '다문화'))
        
        # 서비스명 기반 태그
        if '출산' in service_name:
            tags.append(('관심사', '출산'))
        if '급식' in service_name:
            tags.append(('관심사', '급식'))
        if '교육' in service_name or '학비' in service_name:
            tags.append(('관심사', '교육'))
        
        # 태그 삽입
        for tag_type, tag_value in tags:
            self.cursor.execute('''
            INSERT INTO welfare_tags (service_id, tag_type, tag_value)
            VALUES (%s, %s, %s)
            ''', (service_id, tag_type, tag_value))
    
    def batch_insert_from_json(self, json_path):
        """
        JSON 파일 일괄 변환
        
        Args:
            json_path: JSON 파일 경로
        """
        data = self.load_json(json_path)
        
        print(f"\n{'='*80}")
        print(f"JSON → DB 변환 시작: {len(data)}개")
        print(f"{'='*80}\n")
        
        for idx, item in enumerate(data, 1):
            try:
                service_name = item['service_name']
                sido = item.get('sido', '정보없음')
                sigungu = item.get('sigungu', '전체')
                source = item.get('source', '정보없음')
                
                print(f"[{idx:3d}/{len(data)}] [{source}/{sido or '전국'}/{sigungu or '전체'}] {service_name[:30]:<30}", end=' ')
                
                self.insert_service_from_json(item)
                
                print("✓")
                
                if idx % 10 == 0:
                    self.conn.commit()
                    
            except Exception as e:
                print(f"✗ 오류: {e}")
        
        self.conn.commit()
        
        print(f"\n{'='*80}")
        print(f"✅ 변환 완료: {len(data)}개")
        print(f"{'='*80}\n")
    
    def get_statistics(self):
        """DB 통계"""
        print("\n" + "="*80)
        print("DB 통계")
        print("="*80)
        
        self.cursor.execute('SELECT COUNT(*) FROM welfare_services')
        total = self.cursor.fetchone()[0]
        print(f"\n총 복지 서비스: {total}개")
        
        self.cursor.execute('''
        SELECT source, COUNT(*) as cnt
        FROM welfare_services
        GROUP BY source
        ''')
        print("\n출처별:")
        for row in self.cursor.fetchall():
            print(f"  {row[0]:15s}: {row[1]}개")
        
        # 최대 지원금액이 있는 복지 수
        self.cursor.execute('''
        SELECT COUNT(DISTINCT service_id)
        FROM welfare_benefits
        WHERE max_amount_per_child IS NOT NULL OR max_amount_total IS NOT NULL
        ''')
        max_amount_count = self.cursor.fetchone()[0]
        print(f"\n최대 지원금액 명시: {max_amount_count}개")
        
        # 지원 횟수가 있는 복지 수
        self.cursor.execute('''
        SELECT COUNT(DISTINCT service_id)
        FROM welfare_benefits
        WHERE support_count IS NOT NULL
        ''')
        support_count = self.cursor.fetchone()[0]
        print(f"지원 횟수 명시: {support_count}개")
    
    def close(self):
        """연결 종료"""
        self.conn.commit()
        self.cursor.close()
        self.conn.close()


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == '__main__':
    # MariaDB 연결
    config = {
        'host': '192.168.56.82',
        'user': 'work',
        'password': '1111',
        'database': 'work_local'
    }
    
    converter = JSONToDBConverter(**config)
    
    print("="*80)
    print("JSON → DB 변환 프로세스")
    print("="*80)
    
    # 중앙부처 JSON → DB
    print("\n[1단계] 중앙부처 복지 변환")
    converter.batch_insert_from_json(
        json_path='parsed_strict_gpt중앙부.json'
    )
    
    # 울산시 JSON → DB
    print("\n[2단계] 울산시 복지 변환")
    converter.batch_insert_from_json(
        json_path='parsed_strict_gpt울산.json'
    )
    
    # 통계
    converter.get_statistics()
    
    converter.close()
    
    print("\n✅ JSON → DB 변환 완료!")
    print("\n💡 프로세스:")
    print("  1. AI로 XML → JSON 파싱 (strict_gpt_parser.py)")
    print("  2. JSON → DB 변환 (json_to_db_converter.py) ← 현재 단계")
    print("  3. DB 검색 (mariadb_search_engine.py)")