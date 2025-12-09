import requests
import xml.etree.ElementTree as ET
import os

# --- 1. API 및 파일 상수 정의 ---

API_URL = "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations/LcgvWelfaredetailed"
# 사용자 제공 Service Key
# SERVICE_KEY = "a982cc39246fc808d76003ef21e3b0997b4d8f3b2c68b5dc0a304b0ed5004315" # 카카오톡 로그인
SERVICE_KEY = "f1294f00c98f2644b045fdf819708f7aec2efd2d8d5a73b102f92d0130dce6c0" #  회원 로그인

# 입출력 파일 이름 설정
# ⚠️ 중요: 이 변수에 이전 실행 결과 파일(부분적으로 업데이트된 파일) 이름을 지정하세요.
# 예: '지자체 복지 목록 - wantedDtl_추가_완료.xml'
INPUT_FILENAME = "지자체 복지 목록 - wantedDtl_추가_완료.xml"
# 출력을 동일 파일에 덮어씁니다.
OUTPUT_FILENAME = INPUT_FILENAME 

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
        # API에서 오류 코드를 반환해도 예외 발생
        raise Exception(f"API 응답 실패: 코드 {result_code_element.text}, 메시지: {result_message}")

    if wanted_dtl_root.tag != 'wantedDtl':
        raise Exception(f"API 응답 형식 오류: 최상위 태그가 <wantedDtl>이 아닙니다. ({wanted_dtl_root.tag})")
        
    return wanted_dtl_root

# --- 3. XML 수정 메인 로직 함수 ---

def process_xml_updates_resumable(input_path: str, output_path: str):
    """
    XML 파일의 모든 <servList>를 순회하며, 미처리된 항목에 대해서만 API 호출 후 결과를 삽입합니다.
    """
    
    if not os.path.exists(input_path):
        print(f"❌ 오류: 입력 파일 '{input_path}'을(를) 찾을 수 없습니다. 파일 이름을 확인하거나, 이전 실행 결과 파일을 해당 이름으로 변경하세요.")
        return

    try:
        # 1. 메인 XML 파일 로드 및 구문 분석
        tree = ET.parse(input_path)
        root = tree.getroot()
        
        # 모든 <servList> 요소 찾기
        serv_lists = root.findall('servList')
        total_count = len(serv_lists)
        
        print(f"============================================================")
        print(f"✅ 총 {total_count}개의 <servList> 항목에 대한 작업을 시작합니다. (재개 모드)")
        print(f"============================================================")

        # 2. <servList> 순회 및 업데이트
        for i, serv_list_element in enumerate(serv_lists):
            
            serv_id_element = serv_list_element.find('servId')
            
            if serv_id_element is None or not serv_id_element.text:
                print(f"[{i+1}/{total_count}] 경고: <servId>가 없어 해당 항목을 건너뜁니다.")
                continue
                
            serv_id = serv_id_element.text.strip()
            
            # 🌟 핵심 재개 로직: <wantedDtl>이 이미 삽입되어 있는지 확인
            if serv_list_element.find('wantedDtl') is not None:
                print(f"[{i+1}/{total_count}] ServId: {serv_id} (이미 처리됨) -> API 호출을 건너뜁니다.")
                continue
                
            print(f"[{i+1}/{total_count}] ServId: {serv_id} API 호출 및 수정 작업 진행 중...")

            try:
                # 2-1. API 호출 및 <wantedDtl> 요소 획득
                wanted_dtl_element = fetch_wanted_dtl(serv_id)
                
                # 2-2. <wantedDtl> 요소를 해당 <servList>에 삽입
                serv_list_element.append(wanted_dtl_element)
                
                print(f"  > 성공: <wantedDtl>이 <servList>에 성공적으로 삽입되었습니다.")
                
            except requests.exceptions.HTTPError as e:
                # 429 Too Many Requests와 같은 HTTP 오류 발생 시
                print(f"  > ❌ **API HTTP 오류 발생 (작업 중단): {e}**")
                print(f"  > 현재까지의 진행 사항을 저장하고 작업을 종료합니다. 내일 다시 시도하세요.")
                break # 루프를 즉시 종료
            except Exception as e:
                # 기타 연결 오류, XML 파싱 오류, API 응답 실패 등
                print(f"  > ❌ 실패: ServId {serv_id} 처리 중 오류 발생: {e}")
                # 오류가 발생해도 작업을 계속 진행 (다음 항목 시도)
                
        # 3. 수정된 XML 구조를 파일에 저장 (루프가 중단되더라도 현재까지의 진행 사항 저장)
        tree.write(output_path, encoding='UTF-8', xml_declaration=True)
        
        print(f"============================================================")
        print(f"✅ 작업이 완료되거나 중단되었습니다. 최종 결과가 '{output_path}'에 저장되었습니다.")
        print(f"============================================================")

    except ET.ParseError as e:
        print(f"❌ XML 구문 분석 중 오류 발생: 입력 파일 '{input_path}'의 형식을 확인하세요. 오류: {e}")
    except Exception as e:
        print(f"❌ 예기치 않은 심각한 오류 발생: {e}")

# --- 4. 스크립트 실행 ---
# 이 부분이 이전 코드에서 문법 오류를 발생시켰을 가능성이 높으므로, 구조를 명확히 합니다.
if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("❌ 'requests' 라이브러리가 설치되어 있지 않습니다. 'pip install requests' 명령으로 설치해 주세요.")
    else:
        # requests 라이브러리가 존재하면 메인 처리 함수 실행
        process_xml_updates_resumable(INPUT_FILENAME, OUTPUT_FILENAME)