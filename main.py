import pygame
import threading
import requests
import time
import xml.etree.ElementTree as ET
import sys
import os

# ==========================================
# 1. API 및 기본 설정 (사용자 커스텀 옵션)
# ==========================================
def load_stn():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    key_file_path = os.path.join(base_path, "stn_to_show.txt")
    
    if not os.path.exists(key_file_path):
        with open(key_file_path, "w", encoding="utf-8") as f:
            f.write("")
            
    # 💡 여러 인코딩 형식을 순차적으로 시도하여 파일 읽기
    key = ""
    encodings = ['utf-8', 'cp949', 'utf-8-sig', 'utf-16']
    
    for enc in encodings:
        try:
            with open(key_file_path, "r", encoding=enc) as f:
                key = f.read().strip()
            break  # 성공적으로 읽으면 반복문 탈출
        except UnicodeDecodeError:
            continue  # 현재 인코딩으로 실패하면 다음 인코딩 시도
            
    if not key or key == "" or key == "sample":
        sys.exit()
        
    return key

def load_api_key():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    key_file_path = os.path.join(base_path, "api_key.txt")
    
    if not os.path.exists(key_file_path):
        with open(key_file_path, "w", encoding="utf-8") as f:
            f.write("")
            
    # 💡 여러 인코딩 형식을 순차적으로 시도하여 파일 읽기
    key = ""
    encodings = ['utf-8', 'cp949', 'utf-8-sig', 'utf-16']
    
    for enc in encodings:
        try:
            with open(key_file_path, "r", encoding=enc) as f:
                key = f.read().strip()
            break  # 성공적으로 읽으면 반복문 탈출
        except UnicodeDecodeError:
            continue  # 현재 인코딩으로 실패하면 다음 인코딩 시도
            
    if not key or key == "" or key == "sample":
        sys.exit()
        
    return key

API_KEY = load_api_key()         # 발급받은 실제 API 키
STATION_NAME = load_stn()    # 조회할 역 이름 (API 호출 및 당역 종착 판별에 사용)
TARGET_SUBWAY_ID = "1001"  # 특정 노선만 필터링 (1호선)

# 💡 URL 정의 (수정 완료)
URL = f"http://swopenAPI.seoul.go.kr/api/subway/{API_KEY}/xml/realtimeStationArrival/1/5/{STATION_NAME}"

# 💡 급행열차 표시 여부 선택 (True: 급행 포함 / False: 급행 제외)
INCLUDE_EXPRESS = False

CUSTOM_STATION_NAMES = {
    "동대문역사문화공원": "DDP",
    "디지털미디어시티": "DMC",
    "가산디지털단지": "가산Digi.",
    "평택지제": "지  제",
    "서울": "서울역",
    # 필요에 따라 추가하세요: "원래이름": "바꿀이름"
}

# 영어 행선지 (이외의 행선지는 "undefined" 처리)
DEST_EN = {
    "광운대": "Kwangwoon Univ.",
    "청량리": "Cheongnyangni",
    "구로": "Guro",
    "병점": "Byeongjeom",
    "연천": "Yeoncheon",
    "인천": "Incheon",
    "동인천": "Dongincheon",
    "서울역": "Seoul Station",
    "동묘앞": "Dongmyo",
    "서동탄": "Seodongtan",
    "용산": "Yongsan",
    "광명": "Gwangmyeong",
    "의정부": "Uijeongbu"
}

latest_trains = []
current_interval = 15

# ==========================================
# 2. Pygame 설정 및 폰트 로드
# ==========================================
WIDTH, HEIGHT = 1200, 300
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SubwayPlatform")

BLACK  = (10, 10, 10)
YELLOW = (235, 175, 30)
GREEN  = (20, 220, 40)
RED    = (230, 30, 30)

# 메인 LED 폰트 로드
try:
    font = pygame.font.Font("led_font.ttf", 60)
    font_large = pygame.font.Font("led_font.ttf", 90)
except:
    print("경고: led_font.ttf 파일을 찾을 수 없어 시스템 기본 폰트를 사용합니다.")
    font = pygame.font.SysFont("malgungothic", 60)
    font_large = pygame.font.SysFont("malgungothic", 90)

# 시계 숫자용 바탕체 로드
try:
    font_batang = pygame.font.SysFont("batang", 120, bold=False)
except:
    font_batang = font_large

# ==========================================
# 3. 데이터 파싱 및 수집 스레드
# ==========================================
def parse_train_info(msg2, msg3):
    status = "출발"
    if "도착" in msg2:
        status = "도착"
    elif "진입" in msg2 or "접근" in msg2:
        status = "접근"
        
    rem_stations = ""
    if "[" in msg2 and "]" in msg2:
        num = msg2.split("[")[1].split("]")[0]
        rem_stations = f"{num}전 역"
    elif "전역" in msg2:
        rem_stations = "전 역"
    else:
        rem_stations = msg2.split()[0]
        
    current_station = msg3 if msg3 else "정보없음"
    return current_station, rem_stations, status

def fetch_api_thread():
    global latest_trains, current_interval
    while True:
        try:
            res = requests.get(URL)
            res.encoding = 'utf-8'
            root = ET.fromstring(res.text)
            
            up_trains = []
            for row in root.findall('row'):
                current_subway_id = row.find('subwayId').text
                train_status = row.find('btrainSttus').text
                
                # 급행 포함 여부 판별
                is_target_status = True if INCLUDE_EXPRESS else (train_status != "급행")
                
                if current_subway_id == TARGET_SUBWAY_ID and row.find('updnLine').text == "상행" and is_target_status:
                    
                    raw_bstatnNm = row.find('bstatnNm').text
                    raw_msg3 = row.find('arvlMsg3').text
                    
                    clean_bstatnNm = CUSTOM_STATION_NAMES.get(
                        raw_bstatnNm, raw_bstatnNm.split('(')[0] if raw_bstatnNm else "정보없음"
                    )
                    clean_msg3 = CUSTOM_STATION_NAMES.get(
                        raw_msg3, raw_msg3.split('(')[0] if raw_msg3 else "정보없음"
                    )
                    
                    msg2 = row.find('arvlMsg2').text
                    cur_sta, rem_sta, stat = parse_train_info(msg2, clean_msg3)
                    
                    # 💡 정렬을 위한 ordkey 데이터 추가 추출
                    ordkey = row.find('ordkey').text
                    
                    up_trains.append({
                        'bstatnNm': clean_bstatnNm,
                        'arvlCd': row.find('arvlCd').text,
                        'current_station': cur_sta,
                        'remaining_stations': rem_sta,
                        'status': stat,
                        'train_status': train_status,
                        'ordkey': ordkey  # 딕셔너리에 추가
                    })
            
            # 💡 [핵심] ordkey 값을 기준으로 리스트를 오름차순 정렬 (가장 가까운 열차가 0번 인덱스로)
            up_trains.sort(key=lambda x: x['ordkey'])
            
            latest_trains = up_trains
            
            # 가변 주기 적용 (가장 가까운 열차 기준)
            if up_trains and up_trains[0]['arvlCd'] in ["0", "1", "2", "3", "4"]:
                current_interval = 20
            else:
                current_interval = 10
                
        except Exception as e:
            print(f"API 에러: {e}")
            current_interval = 20
            
        time.sleep(current_interval)

# ==========================================
# 4. 정밀 텍스트 렌더링 헬퍼 함수
# ==========================================
def draw_colored_segments_center(segments, y, default_font=font):
    """여러 색상과 폰트가 섞인 텍스트를 가로 중앙에 렌더링"""
    surfaces = []
    for seg in segments:
        text, color = seg[0], seg[1]
        seg_font = seg[2] if len(seg) >= 3 else default_font
        surfaces.append(seg_font.render(text, True, color))
        
    total_w = sum(s.get_width() for s in surfaces)
    start_x = (WIDTH - total_w) // 2
    
    curr_x = start_x
    for s in surfaces:
        screen.blit(s, s.get_rect(midleft=(curr_x, y)))
        curr_x += s.get_width()

def draw_4_columns(col1, col2, col3, col4, y, col2_color=YELLOW):
    """
    1, 2번 평시 화면용 4단 격자 배치 
    col2_color 옵션을 추가하여 급행 시 빨간색 반영
    """
    t1 = font.render(col1, True, YELLOW)
    screen.blit(t1, t1.get_rect(midleft=(WIDTH * 0.08, y)))
    
    t2 = font.render(col2, True, col2_color)
    screen.blit(t2, t2.get_rect(midleft=(WIDTH * 0.33, y)))
    
    t4 = font.render(col4, True, RED)
    screen.blit(t4, t4.get_rect(midright=(WIDTH * 0.92, y)))
    
    t3 = font.render(col3, True, GREEN)
    screen.blit(t3, t3.get_rect(midright=(WIDTH * 0.72, y)))

# ==========================================
# 5. 메인 루프
# ==========================================
def main():
    threading.Thread(target=fetch_api_thread, daemon=True).start()
    clock = pygame.time.Clock()
    
    idle_sequence = [1, 3, 2, 3]
    idle_index = 0
    last_switch_time = pygame.time.get_ticks()
    SCREEN_DURATION = 5000
    
    ROW_Y = [55, 150, 245]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill(BLACK)
        current_time_ms = pygame.time.get_ticks()
        
        if current_time_ms - last_switch_time > SCREEN_DURATION:
            idle_index = (idle_index + 1) % len(idle_sequence)
            last_switch_time = current_time_ms

        active_screen = idle_sequence[idle_index]
        event_train = None
        
        if latest_trains:
            t = latest_trains[0]
            if t['arvlCd'] == "3":
                active_screen = 4
                event_train = t
            elif t['arvlCd'] in ["4", "0"]:
                active_screen = 5 if idle_index % 2 == 0 else 6
                event_train = t
            elif t['arvlCd'] == "1":
                active_screen = 7
                event_train = t
            elif t['arvlCd'] == "2":
                active_screen = 8
                event_train = t

        # ==================================
        # 화면별 정밀 렌더링
        # ==================================
        if active_screen == 1 or active_screen == 2:
            for i, t in enumerate(latest_trains[:3]):
                # 당역 종착 / 급행 / 일반 판별 로직
                dest_text = t['bstatnNm']
                suffix_text = "행"
                suffix_color = YELLOW
                
                if dest_text == STATION_NAME:
                    dest_text = "당역    종착"
                    suffix_text = ""
                elif t['train_status'] == "급행":
                    suffix_text = "급행"
                    suffix_color = RED
                
                # 1번 화면은 현재역, 2번 화면은 남은역 표시
                info_text = t['current_station'] if active_screen == 1 else t['remaining_stations']
                
                draw_4_columns(dest_text, suffix_text, info_text, t['status'], ROW_Y[i], suffix_color)
                    
        elif active_screen == 3:
            t_title = font.render("현재시간", True, GREEN)
            screen.blit(t_title, t_title.get_rect(midleft=(WIDTH * 0.08, ROW_Y[0])))
            
            h_str, m_str = time.strftime("%H"), time.strftime("%M")
            draw_colored_segments_center([
                (f"{h_str} ", YELLOW, font_batang),
                ("시  ", RED, font),
                (f"{m_str} ", YELLOW, font_batang),
                ("분", RED, font)
            ], ROW_Y[1] + 25)
            
        elif active_screen in [4, 5, 7, 8] and event_train:
            # 이벤트 화면 당역종착/급행 판별
            if event_train['bstatnNm'] == STATION_NAME:
                e_dest = "당역  종착"
                e_suf = ""
                e_suf_c = GREEN
            elif event_train['train_status'] == "급행":
                e_dest = event_train['bstatnNm']
                e_suf = "급행"
                e_suf_c = RED
            else:
                e_dest = event_train['bstatnNm']
                e_suf = "행"
                e_suf_c = GREEN

            if active_screen == 4:
                draw_colored_segments_center([("이번열차 :  ", GREEN), (e_dest, YELLOW), (f"  {e_suf}", e_suf_c)], ROW_Y[0])
                draw_colored_segments_center([(e_dest, YELLOW), (f"  {e_suf}  ", e_suf_c), ("열차가", GREEN)], ROW_Y[1])
                draw_colored_segments_center([("전  역 을  ", RED), ("출발하였습니다", GREEN)], ROW_Y[2])
                
            elif active_screen == 5:
                draw_colored_segments_center([("이번열차 :  ", GREEN), (e_dest, YELLOW), (f"  {e_suf}", e_suf_c)], ROW_Y[0])
                draw_colored_segments_center([("열차가  ", GREEN), ("잠시후", RED), ("  도착합니다", GREEN)], ROW_Y[1] + 25)
                
            elif active_screen == 7:
                draw_colored_segments_center([("이번열차 :  ", GREEN), (e_dest, YELLOW), (f"  {e_suf}", e_suf_c)], ROW_Y[0])
                draw_colored_segments_center([("질서있게  ", YELLOW), ("승차하여", RED)], ROW_Y[1])
                draw_colored_segments_center([("주시기 바랍니다", GREEN)], ROW_Y[2])
                
            elif active_screen == 8:
                draw_colored_segments_center([("이번열차 :  ", GREEN), (e_dest, YELLOW), (f"  {e_suf}", e_suf_c)], ROW_Y[1])

        elif active_screen == 6 and event_train:
            dest_kr = event_train['bstatnNm']
            dest_en = DEST_EN.get(dest_kr, "undefined")
            if dest_kr == STATION_NAME:
                dest_en = "This Station" # 당역 종착일 경우 영문 표기
                
            draw_colored_segments_center([("The train for", GREEN)], ROW_Y[0])
            draw_colored_segments_center([(dest_en, YELLOW)], ROW_Y[1])
            draw_colored_segments_center([("will be arriving shortly", RED)], ROW_Y[2])

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()