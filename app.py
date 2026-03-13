import streamlit as st
import pandas as pd
import re
from streamlit_gsheets import GSheetsConnection

# --- [UI 설정 및 CSS] ---
st.set_page_config(page_title="AI Tactical Master", layout="wide")
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #00BFFF; color: white; border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# [핵심 1] 구글 시트 연결 및 초기 데이터 로드
# ---------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 'Sheet1'에서 데이터를 읽어옵니다. 
        # 첫 번째 컬럼 이름이 'player_info'라고 가정합니다.
        df = conn.read(worksheet="Sheet1")
        return df['player_info'].dropna().tolist()
    except Exception as e:
        # 시트가 비어있거나 연결 전일 경우 기본 샘플 명단 출력
        return ["손흥민(LW/ST)", "조규성(ST/FW)", "이강인(AMF/RW)"]

# 앱 접속 시 딱 한 번만 구글 시트에서 데이터를 가져와 세션에 저장
if 'roster' not in st.session_state:
    st.session_state.roster = load_data()

# --- [기존 전술/파싱 함수들] ---
def parse_players(player_list):
    text = ", ".join(player_list)
    pattern = r"([가-힣a-zA-Z0-9]+)\(([A-Z]+)(?:/([A-Z]+))?\)"
    matches = re.findall(pattern, text)
    return [{"name": m[0], "pos1": m[1], "pos2": m[2] if len(m) > 2 and m[2] else None, "total": 0, "p1_count": 0} for m in matches]

# (generate_squads, coach_voice_db, render_interactive_pitch 함수는 이전과 동일)
# ... [이전 코드의 함수들이 여기에 포함되어 있다고 가정] ...

# ---------------------------------------------------------
# [메인 UI]
# ---------------------------------------------------------
st.title("⚽ AI Tactical Master (Cloud Save)")

tab1, tab2 = st.tabs(["📝 우리 팀 로스터 관리", "🏟️ 매치데이 스쿼드 짜기"])

with tab1:
    st.header("🌐 구글 시트 실시간 동기화")
    st.info("여기서 수정하고 저장하면 구글 스프레드시트에 즉시 반영됩니다.")
    
    # 세션 상태의 명단을 텍스트로 보여줌
    roster_text = st.text_area("전체 명단 편집 (쉼표로 구분)", value=", ".join(st.session_state.roster), height=200)
    
    # ---------------------------------------------------------
    # [핵심 2] 데이터 저장하기 (Update)
    # ---------------------------------------------------------
    if st.button("💾 구글 시트에 영구 저장"):
        new_roster_list = [p.strip() for p in roster_text.split(",") if p.strip()]
        
        # 1. 앱 내부 데이터(세션) 업데이트
        st.session_state.roster = new_roster_list
        
        # 2. 구글 시트 전송용 데이터프레임 생성
        new_df = pd.DataFrame({"player_info": new_roster_list})
        
        # 3. 구글 시트에 덮어쓰기
        conn.update(worksheet="Sheet1", data=new_df)
        
        st.success("✅ 구글 클라우드에 저장이 완료되었습니다! 이제 앱을 껐다 켜도 데이터가 유지됩니다.")

with tab2:
    st.header("오늘의 라인업")
    # 구글 시트에서 불러온 명단(st.session_state.roster)을 그대로 선택지로 사용
    today_players = st.multiselect(
        "출석한 선수를 선택하세요", 
        options=st.session_state.roster,
        default=st.session_state.roster
    )
    
    # (이하 쿼터 설정 및 스쿼드 생성 버튼 로직은 이전과 동일)
    # ...
