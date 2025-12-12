-- ================================================================================
-- 복지 DB 스키마 v4.1 (children_min/max 추가)
-- ⭐⭐⭐ 핵심: Benefits 중심 구조 + 자녀 수 조건 추가
-- ================================================================================
-- v4.1 변경사항:
--   1. children_min, children_max 필드 명확화
--   2. False 값 방지를 위한 주석 추가
-- ================================================================================
-- 기존 테이블 삭제 (있다면)
DROP TABLE IF EXISTS welfare_benefits;

DROP TABLE IF EXISTS welfare_services;

-- ================================================================================
-- 1. welfare_services (서비스 기본 정보 + 지역)
-- ================================================================================
CREATE TABLE
    welfare_services (
        service_id VARCHAR(50) PRIMARY KEY COMMENT '서비스 고유 ID (복지로 제공)',
        service_name VARCHAR(200) NOT NULL COMMENT '서비스명',
        detail_url TEXT COMMENT '상세 정보 URL',
        -- ⭐ 지역 (서비스 레벨만!)
        sido VARCHAR(50) COMMENT '시도 (예: 울산광역시, 서울특별시)',
        sigungu VARCHAR(50) COMMENT '시군구 (예: 울주군, 강남구)',
        source VARCHAR(100) COMMENT '데이터 출처 (예: 울산광역시)',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
        INDEX idx_sido (sido),
        INDEX idx_sigungu (sigungu),
        INDEX idx_sido_sigungu (sido, sigungu)
    ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '복지 서비스 기본 정보 (지역 포함)';

-- ================================================================================
-- 2. welfare_benefits (혜택 + 모든 조건)
-- ================================================================================
CREATE TABLE
    welfare_benefits (
        benefit_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '혜택 고유 ID (자동 생성)',
        service_id VARCHAR(50) NOT NULL COMMENT '서비스 ID (FK)',
        -- ====================================
        -- 혜택 정보
        -- ====================================
        amount DECIMAL(15, 2) COMMENT '지원 금액 (원 단위, 예: 1000000 = 100만원)',
        amount_type VARCHAR(50) COMMENT '금액 유형 (일시금/월/년/회)',
        amount_unit VARCHAR(20) COMMENT '금액 단위 (원/포인트)',
        benefit_type VARCHAR(50) NOT NULL COMMENT '혜택 유형 (현금/서비스/물품/감면/포인트)',
        payment_cycle VARCHAR(50) COMMENT '지급 주기 (일시금/5회분할/매월)',
        payment_method VARCHAR(100) COMMENT '지급 방법 (계좌입금/카드/현장지급)',
        payment_timing VARCHAR(100) COMMENT '지급 시기 (신청 후 다음달/즉시)',
        description TEXT NOT NULL COMMENT '혜택 설명',
        -- ====================================
        -- ⭐ AND 조건 (모두 충족 필요)
        -- ====================================
        -- 나이
        age_min_months INT COMMENT '최소 나이 (개월, 예: 0 = 신생아, 12 = 만1세)',
        age_max_months INT COMMENT '최대 나이 (개월, 예: 11 = 0세, 23 = 1세, 96 = 만8세)',
        -- 소득
        income_type VARCHAR(50) COMMENT '소득 유형 (기준중위소득/차상위계층/기초생활수급자)',
        income_max_percent INT COMMENT '소득 상한 (%, 예: 150 = 기준중위소득 150% 이하)',
        -- 가구
        household_type VARCHAR(100) COMMENT '가구 형태 (한부모/조손/다문화/맞벌이)',
        household_members_min INT COMMENT '최소 가구원 수 (본인+자녀+동거가족)',
        household_members_max INT COMMENT '최대 가구원 수',
        -- ⭐ 자녀 (v4.1 추가 명확화)
        children_min INT COMMENT '최소 자녀 수 (예: 2 = 2자녀 이상)',
        children_max INT COMMENT '최대 자녀 수 (예: 2 = 2자녀까지)',
        birth_order INT COMMENT '출생순서 (1=첫째, 2=둘째, 3=셋째이상)',
        -- 거주
        residence_min_months INT COMMENT '최소 거주 기간 (개월, 예: 6 = 6개월 이상)',
        -- 양육
        childcare_type VARCHAR(50) COMMENT '양육 방식 (가정/어린이집/유치원)',
        requires_grandparent_care BOOLEAN COMMENT '조부모 양육 필요 여부 (true 또는 NULL만, false 금지!)',
        requires_dual_income BOOLEAN COMMENT '맞벌이 필요 여부 (true 또는 NULL만, false 금지!)',
        -- 장애
        requires_disability BOOLEAN COMMENT '아동 장애 필요 여부 (true 또는 NULL만, false 금지!)',
        requires_parent_disability BOOLEAN COMMENT '부모 장애 필요 여부 (true 또는 NULL만, false 금지!)',
        disability_level VARCHAR(20) COMMENT '장애 정도 (경증/중증)',
        -- 질환 (아동)
        child_has_serious_disease BOOLEAN COMMENT '아동 중증질환 여부 (true 또는 NULL만, false 금지!)',
        child_has_rare_disease BOOLEAN COMMENT '아동 희귀질환 여부 (true 또는 NULL만, false 금지!)',
        child_has_chronic_disease BOOLEAN COMMENT '아동 난치질환 여부 (true 또는 NULL만, false 금지!)',
        child_has_cancer BOOLEAN COMMENT '아동 암/백혈병 여부 (true 또는 NULL만, false 금지!)',
        -- 질환 (부모)
        parent_has_serious_disease BOOLEAN COMMENT '부모 중증질환 여부 (true 또는 NULL만, false 금지!)',
        parent_has_rare_disease BOOLEAN COMMENT '부모 희귀질환 여부 (true 또는 NULL만, false 금지!)',
        parent_has_chronic_disease BOOLEAN COMMENT '부모 난치질환 여부 (true 또는 NULL만, false 금지!)',
        parent_has_cancer BOOLEAN COMMENT '부모 암 여부 (true 또는 NULL만, false 금지!)',
        parent_has_infertility BOOLEAN COMMENT '부모 난임 여부 (true 또는 NULL만, false 금지!)',
        -- 특수 상황
        is_violence_victim BOOLEAN COMMENT '폭력 피해 여부 (true 또는 NULL만, false 금지!)',
        is_abuse_victim BOOLEAN COMMENT '학대 피해 여부 (true 또는 NULL만, false 금지!)',
        is_defector BOOLEAN COMMENT '탈북민 여부 (true 또는 NULL만, false 금지!)',
        is_national_merit BOOLEAN COMMENT '국가유공자 여부 (true 또는 NULL만, false 금지!)',
        is_foster_child BOOLEAN COMMENT '위탁아동 여부 (true 또는 NULL만, false 금지!)',
        is_single_mother BOOLEAN COMMENT '미혼모 여부 (true 또는 NULL만, false 금지!)',
        is_low_income BOOLEAN COMMENT '저소득층 여부 (true 또는 NULL만, false 금지!)',
        -- 임신/출산
        pregnancy_weeks_min INT COMMENT '최소 임신 주수',
        pregnancy_weeks_max INT COMMENT '최대 임신 주수',
        birth_within_months INT COMMENT '출산 후 경과 개월 (예: 12 = 출산 후 1년 이내)',
        -- 교육
        education_level VARCHAR(20) COMMENT '교육 단계 (초등/중등/고등)',
        is_enrolled BOOLEAN COMMENT '재학 여부 (true 또는 NULL만, false 금지!)',
        -- 주거
        housing_type VARCHAR(50) COMMENT '주거 형태 (자가/전세/월세/무상)',
        -- ====================================
        -- ⭐ OR 조건 (하나만 충족) - JSON
        -- ====================================
        or_conditions JSON COMMENT 'OR 조건 (JSON, 예: {"household_type": ["맞벌이", "한부모"]})',
        -- ====================================
        -- 메타 정보
        -- ====================================
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
        -- ====================================
        -- 인덱스 (검색 최적화)
        -- ====================================
        INDEX idx_service (service_id),
        INDEX idx_age (age_min_months, age_max_months),
        INDEX idx_income (income_type, income_max_percent),
        INDEX idx_birth_order (birth_order),
        INDEX idx_children (children_min, children_max),
        INDEX idx_household_members (household_members_min, household_members_max),
        INDEX idx_childcare_type (childcare_type),
        INDEX idx_benefit_type (benefit_type),
        INDEX idx_amount (amount),
        -- 복합 인덱스 (자주 사용하는 조합)
        INDEX idx_age_income (age_max_months, income_max_percent),
        INDEX idx_age_birth (age_max_months, birth_order),
        INDEX idx_children_birth (children_min, birth_order),
        FOREIGN KEY (service_id) REFERENCES welfare_services (service_id) ON DELETE CASCADE
    ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '복지 혜택 정보 (모든 조건 포함)';

-- ================================================================================
-- 검색 쿼리 예시
-- ================================================================================
-- 예시 1: 기본 검색 (0세, 울산광역시, 기준중위소득 100%)
/*
SELECT 
s.service_id,
s.service_name,
s.sido,
s.sigungu,
b.benefit_id,
b.amount,
b.amount_type,
b.benefit_type,
b.description
FROM welfare_services s
INNER JOIN welfare_benefits b ON s.service_id = b.service_id
WHERE
-- 지역 (서비스 레벨)
(s.sido = '울산광역시' OR s.sido IS NULL OR s.sido = '')
AND (s.sigungu = '울주군' OR s.sigungu IS NULL OR s.sigungu = '')

-- 나이 (혜택 레벨)
AND (b.age_min_months IS NULL OR b.age_min_months <= 6)
AND (b.age_max_months IS NULL OR b.age_max_months >= 6)

-- 소득 (혜택 레벨)
AND (b.income_type IS NULL 
OR (b.income_type = '기준중위소득' AND b.income_max_percent >= 100))

-- 출생순서 (혜택 레벨)
AND (b.birth_order IS NULL OR b.birth_order = 1)

ORDER BY b.amount DESC;
 */
-- 예시 2: 자녀 수 조건 검색 (2자녀 이상)
/*
SELECT 
s.service_name,
b.amount,
b.description
FROM welfare_services s
INNER JOIN welfare_benefits b ON s.service_id = b.service_id
WHERE
-- 자녀 수 (2명 이상)
(b.children_min IS NULL OR b.children_min <= 2)
AND (b.children_max IS NULL OR b.children_max >= 2)

ORDER BY b.amount DESC;
 */
-- 예시 3: 다자녀 가정 (children_min 활용)
/*
SELECT 
s.service_name,
b.amount,
b.children_min,
b.description
FROM welfare_services s
INNER JOIN welfare_benefits b ON s.service_id = b.service_id
WHERE
-- 다자녀 (2자녀 이상)
b.children_min >= 2

ORDER BY s.service_name;
 */
-- ================================================================================
-- 데이터 검증 쿼리
-- ================================================================================
-- 1. 서비스별 혜택 개수
/*
SELECT 
s.service_name,
COUNT(b.benefit_id) AS benefit_count
FROM welfare_services s
LEFT JOIN welfare_benefits b ON s.service_id = b.service_id
GROUP BY s.service_id, s.service_name
ORDER BY benefit_count DESC;
 */
-- 2. 자녀 수 조건 사용 통계
/*
SELECT 
children_min,
children_max,
COUNT(*) AS count
FROM welfare_benefits
WHERE children_min IS NOT NULL OR children_max IS NOT NULL
GROUP BY children_min, children_max
ORDER BY children_min, children_max;
 */
-- 3. Boolean 필드 False 값 검증 (있으면 안 됨!)
/*
SELECT 
service_id,
benefit_id,
'requires_grandparent_care' AS field_name
FROM welfare_benefits
WHERE requires_grandparent_care = FALSE

UNION ALL

SELECT 
service_id,
benefit_id,
'requires_disability' AS field_name
FROM welfare_benefits
WHERE requires_disability = FALSE

UNION ALL

SELECT 
service_id,
benefit_id,
'is_abuse_victim' AS field_name
FROM welfare_benefits
WHERE is_abuse_victim = FALSE;

-- 결과가 0건이어야 정상!
 */
-- ================================================================================
-- 완료!
-- ================================================================================
-- v4.1 스키마 생성 완료
-- 
-- 변경사항:
--   - children_min, children_max 명확화 및 인덱스 추가
--   - Boolean 필드 주석에 false 금지 명시
--   - 자녀 수 검색 쿼리 예시 추가
-- ================================================================================