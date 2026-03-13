import streamlit as st
import pandas as pd
import re
from streamlit_gsheets import GSheetsConnection

# --- [1. UI 및 기본 설정] ---
st.set_page_config(page_title="AI Tactical Master", layout="wide")
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #00BFFF; color: white; border-radius: 10px; border: none;
    }
    /* 탭 디자인 가독성 향상 */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- [2. 구글 시트 연동 로직] ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Sheet1의 player_info 컬럼에서 명단을 가져옴
        df = conn.read(worksheet="Sheet1")
        return df['player_info'].dropna().tolist()
    except:
        # 에러 발생 시(시트 비어있음 등) 기본 샘플 명단
        return ["손흥민(LW/ST)", "이강인(AMF/RW)", "김민재(CB/DF)", "조현우(GK)"]

if 'roster' not in st.session_state:
    st.session_state.roster = load_data()

# --- [3. 핵심 알고리즘 함수들] ---

def parse_players(player_list):
    if not player_list: return []
    text = ", ".join(player_list)
    pattern = r"([가-힣a-zA-Z0-9\s]+)\(([A-Z]+)(?:/([A-Z]+))?\)"
    matches = re.findall(pattern, text)
    return [{"name": m[0].strip(), "pos1": m[1], "pos2": m[2] if m[2] else None, "total": 0, "p1_count": 0} for m in matches]

def can_play(player_pos, target_broad_pos):
    if not player_pos: return False
    if player_pos == "FR" and target_broad_pos != "GK": return True 
    mapping = {"FW": ["FW", "ST", "LW", "RW"], "MF": ["MF", "CM", "CDM", "AMF"], "DF": ["DF", "CB", "RB", "LB"], "GK": ["GK"]}
    return player_pos in mapping.get(target_broad_pos, [])

def generate_squads(players, quarters, formations_selected, tactics):
    all_squads, all_benches = [], []
    for q in range(quarters):
        form_name = formations_selected[q]
        formation = tactics[form_name]["form"]
        sq = {"FW": [], "MF": [], "DF": [], "GK": []}
        selected = []
        
        # 주포지션 우선 배정
        players.sort(key=lambda x: (x["total"], x["p1_count"]))
        for t_pos, limit in formation.items():
            for p in players:
                if len(sq[t_pos]) < limit and p["name"] not in selected and can_play(p["pos1"], t_pos):
                    sq[t_pos].append(p["name"]); selected.append(p["name"]); p["total"] += 1; p["p1_count"] += 1
                        
        # 부포지션 배정
        for t_pos, limit in formation.items():
            for p in players:
                if len(sq[t_pos]) < limit and p["name"] not in selected and p["pos2"] and can_play(p["pos2"], t_pos):
                    sq[t_pos].append(p["name"]); selected.append(p["name"]); p["total"] += 1
                        
        # 빈자리 강제 배정 (GK 제외)
        players.sort(key=lambda x: x["total"])
        for t_pos, limit in formation.items():
            if t_pos == "GK": continue 
            for p in players:
                if len(sq[t_pos]) < limit and p["name"] not in selected and p["pos1"] != "GK":
                    sq[t_pos].append(p["name"]); selected.append(p["name"]); p["total"] += 1
                    
        all_squads.append(sq)
        all_benches.append([p for p in players if p["name"] not in selected])
    return all_squads, all_benches, players

# --- [4. 시각화 및 데이터베이스] ---

coach_voice_db = {
    "4-4-2": {"FW": "⚔️ 포스트 플레이 분담", "MF": "🛡️ 두 줄 수비 조율", "DF": "📦 라인 컨트롤", "GK": "🧤 박스 장악"},
    "4-3-3": {"FW": "⚔️ 윙어 컷인 플레이", "MF": "🛡️ 즉각 재압박", "DF": "📦 오버래핑", "GK": "🧤 스위퍼 키퍼"},
    "4-2-3-1": {"FW": "⚔️ 원톱 고립 주의", "MF": "🛡️ 2선 침투 패스", "DF": "📦 하프스페이스 커버", "GK": "🧤 소통 중심"},
    "5-2-3": {"FW": "⚔️ 역습 속도 유지", "MF": "🛡️ 공간 점유 집중", "DF": "📦 윙백 적극 전진", "GK": "🧤 빠른 빌드업"}
}

tactics_form = {
    "4-4-2": {"form": {"FW":2, "MF":4, "DF":4, "GK":1}},
    "4-3-3": {"form": {"FW":3, "MF":3, "DF":4, "GK":1}},
    "4-2-3-1": {"form": {"FW":1, "MF":5, "DF":4, "GK":1}},
    "5-2-3": {"form": {"FW":3, "MF":2, "DF":5, "GK":1}}
}

def render_interactive_pitch(squad, form_name):
    y_map = {"FW": "15%", "MF": "45%", "DF": "75%", "GK": "90%"}
    player_html = ""
    instr = coach_voice_db.get(form_name, coach_voice_db["4-4-2"])
    for pos, names in squad.items():
        if not names: continue 
        for i, name in enumerate(names):
            x = (100 / (len(names) + 1)) * (i + 1)
            player_html += f"""
            <div style="position:absolute; top:{y_map[pos]}; left:{x}%; transform:translate(-50%, -50%); text-align:center;">
                <div style="width:16px; height:16px; background:white; border:2px solid #00BFFF; border-radius:50%; margin:0 auto;"></div>
                <div style="color:white; font-size:11px; font-weight:bold; margin-top:2px; text-shadow:1px 1px 2px black;">{name}</div>
            </div>"""
    return f"""
    <div style="background:#226B43; width:100%; height:380px; position:relative; border:2px solid white; border-radius:10px; overflow:hidden;">
        <div style="position:absolute; top:50%; width:100%; height:1px; background:white; opacity:0.5;"></div>
        <div style="position:absolute; top:50%; left:50%; width:60px; height:60px; border:1px solid white; border-radius:50%; transform:translate(-50%, -50%); opacity:0.5;"></div>
        {player_html}
    </div>"""

# --- [5. 메인 앱 화면] ---

st.title("⚽ AI Tactical Master (Cloud)")

tab1, tab2 = st.tabs(["📝 우리 팀 로스터 관리", "🏟️ 매치데이 스쿼드 짜기"])

with tab1:
    st.header("🌐 구글 시트 동기화")
    current_roster = ", ".join(st.session_state.roster)
    roster_input = st.text_area("명단 편집 (이름(포지션) 형식, 쉼표 구분)", value=current_roster, height=200)
    
    if st.button("💾 구글 시트에 영구 저장"):
        new_list = [p.strip() for p in roster_input.split(",") if p.strip()]
        st.session_state.roster = new_list
        conn.update(worksheet="Sheet1", data=pd.DataFrame({"player_info": new_list}))
        st.success("✅ 저장이 완료되었습니다!")

with tab2:
    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.header("오늘의 라인업")
        today_players = st.multiselect("참석자 선택", options=st.session_state.roster, default=st.session_state.roster)
        num_q = st.slider("쿼터 수", 1, 6, 4)
        forms = [st.selectbox(f"{i+1}Q 전술", list(tactics_form.keys()), key=f"q_{i}") for i in range(num_q)]
        generate_btn = st.button("🚀 AI 스쿼드 자동 생성")

    with col_r:
        if generate_btn:
            players_data = parse_players(today_players)
            if not players_data:
                st.warning("선수를 선택해주세요.")
            else:
                res, benches, updated = generate_squads(players_data, num_q, forms, tactics_form)
                cols = st.columns(2)
                for i in range(num_q):
                    with cols[i % 2]:
                        st.markdown(f"**{i+1}쿼터 ({forms[i]})**")
                        # 핵심: st.components.v1.html을 사용해야 HTML이 렌더링됩니다.
                        st.components.v1.html(render_interactive_pitch(res[i], forms[i]), height=400)
                
                st.write("---")
                st.subheader("📊 출전 통계")
                stats_df = pd.DataFrame([{"이름": p["name"], "총 출전": p["total"]} for p in updated])
                st.dataframe(stats_df.sort_values("총 출전", ascending=False), use_container_width=True)
