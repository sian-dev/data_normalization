import requests
import xml.etree.ElementTree as ET
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()
# --- 1. API 및 파일 상수 정의 ---

API_URL = "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfaredetailedV001"
# 사용자 제공 Service Key
# SERVICE_KEY = os.getenv('SERVICE_KEY_KAKAO') #  카카오톡 로그인
SERVICE_KEY = os.getenv('SERVICE_KEY_USER') #  회원 로그인

# 입출력 파일 이름
INPUT_FILENAME = "목록호출/복지목록원본_인천.xml"
OUTPUT_FILENAME = "지자체 복지 목록 - wantedDtl_추가_완료.xml"

# --- 2. API 호출 및 <wantedDtl> 추출 함수 ---

def fetch_wanted_dtl(serv_id: str) -> ET.Element:
    """
    API를 호출하여 특정 servId에 대한 상세 정보(<wantedDtl>) XML 요소를 가져옵니다.
    """
    params = {
        'serviceKey': SERVICE_KEY,
        'servId': serv_id
    }
    
    # API 호출
    response = requests.get(API_URL, params=params, timeout=10)
    response.raise_for_status() # 4xx, 5xx 에러 시 예외 발생
    
    api_response_xml = response.text
    
    # XML 응답 파싱
    wanted_dtl_root = ET.fromstring(api_response_xml)

    # API 결과 코드 확인 (0이 성공)
    result_code_element = wanted_dtl_root.find('resultCode')
    if result_code_element is not None and result_code_element.text != '0':
        result_message = wanted_dtl_root.find('resultMessage').text if wanted_dtl_root.find('resultMessage') is not None else "메시지 없음"
        raise Exception(f"API 호출 실패: 코드 {result_code_element.text}, 메시지: {result_message}")

    # API 응답의 최상위 요소는 <wantedDtl>이어야 함 (사용자 제공 예시 기준)
    if wanted_dtl_root.tag != 'wantedDtl':
        raise Exception(f"API 응답 형식 오류: 최상위 태그가 <wantedDtl>이 아닙니다. ({wanted_dtl_root.tag})")
        
    return wanted_dtl_root

# --- 3. XML 수정 메인 로직 함수 ---

def process_xml_updates(input_path: str, output_path: str):
    """
    XML 파일의 모든 <servList>를 순회하며 API 호출 결과를 삽입하고 저장합니다.
    """
    
    if not os.path.exists(input_path):
        print(f"❌ 오류: 입력 파일 '{input_path}'을(를) 찾을 수 없습니다. 파일이 스크립트와 같은 경로에 있는지 확인하세요.")
        return

    try:
        # 1. 메인 XML 파일 로드 및 구문 분석
        tree = ET.parse(input_path)
        root = tree.getroot()
        
        # 모든 <servList> 요소 찾기
        serv_lists = root.findall('servList')
        total_count = len(serv_lists)
        
        print(f"============================================================")
        print(f"✅ 총 {total_count}개의 <servList> 항목에 대한 작업을 시작합니다.")
        print(f"============================================================")

        # 2. <servList> 순회 및 업데이트
        for i, serv_list_element in enumerate(serv_lists):
            serv_id_element = serv_list_element.find('servId')
            
            if serv_id_element is None or not serv_id_element.text:
                print(f"[{i+1}/{total_count}] 경고: <servId>가 없어 해당 항목을 건너뜁니다.")
                continue
                
            serv_id = serv_id_element.text.strip()
            print(f"[{i+1}/{total_count}] ServId: {serv_id} API 호출 및 수정 작업 진행 중...")

            try:
                # 2-1. API 호출 및 <wantedDtl> 요소 획득
                wanted_dtl_element = fetch_wanted_dtl(serv_id)
                
                # 2-2. <wantedDtl> 요소를 해당 <servList>에 삽입
                # (기존 XML 선언은 <servList> 내에 삽입될 때 자동으로 제거됨)
                serv_list_element.append(wanted_dtl_element)
                
                print(f"  > 성공: <wantedDtl>이 <servList>에 성공적으로 삽입되었습니다.")
                
            except Exception as e:
                print(f"  > ❌ 실패: ServId {serv_id} 처리 중 오류 발생: {e}")
                
        # 3. 수정된 XML 구조를 새 파일에 저장
        # write()를 사용하여 수정된 내용을 파일에 씁니다.
        # encoding='UTF-8'을 사용하고, pretty_print 기능을 사용하여 가독성을 높입니다.
        
        # ElementTree 기본 write는 들여쓰기를 지원하지 않아 tostring/parse를 통해 포매팅합니다.
        # 그러나 간단하게는 tree.write()를 사용하겠습니다. (필요 시 lxml 사용 권장)
        tree.write(output_path, encoding='UTF-8', xml_declaration=True)
        
        print(f"============================================================")
        print(f"🎉 모든 작업이 완료되었습니다! 수정된 XML 파일이 '{output_path}'에 저장되었습니다.")
        print(f"============================================================")

    except ET.ParseError as e:
        print(f"❌ XML 구문 분석 중 오류 발생: 입력 파일 '{input_path}'의 형식을 확인하세요. 오류: {e}")
    except Exception as e:
        print(f"❌ 예기치 않은 심각한 오류 발생: {e}")

# --- 4. 스크립트 실행 ---
if __name__ == "__main__":
    # 요청 라이브러리가 있는지 확인 (없으면 설치를 안내했으므로 pass)
    try:
        import requests
    except ImportError:
        print("❌ 'requests' 라이브러리가 설치되어 있지 않습니다. 'pip install requests' 명령으로 설치해 주세요.")
    else:
        # 실제 파일 이름을 사용하여 함수 실행
        process_xml_updates(INPUT_FILENAME, OUTPUT_FILENAME)