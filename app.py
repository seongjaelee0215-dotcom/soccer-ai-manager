import streamlit as st
import pandas as pd
import re
from streamlit_gsheets import GSheetsConnection

# --- [1. 기본 설정 및 동적 CSS] ---
st.set_page_config(page_title="AI Tactical Master", layout="wide", initial_sidebar_state="expanded")

# 사이드바: 사용자 정의 구단 설정
with st.sidebar:
    st.header("⚙️ 구단 커스텀 설정")
    st.info("우리 팀만의 앱으로 꾸며보세요!")
    
    # 1. 팀명 설정
    team_name = st.text_input("팀명 입력", st.session_state.get('team_name', '홍익대학교 경영학부 팀 EINS'))
    st.session_state.team_name = team_name
    
    # 2. 로고 업로드
    uploaded_logo = st.file_uploader("팀 로고 업로드 (PNG, JPG)", type=['png', 'jpg', 'jpeg'])
    if uploaded_logo is not None:
        st.session_state.logo = uploaded_logo.getvalue()
        
    # 3. 배경 줄무늬 색상 선택
    st.write("🎨 배경 줄무늬 색상")
    col1, col2 = st.columns(2)
    with col1:
        # 연보라색 기본값
        color_outer = st.color_picker("바깥 줄무늬", st.session_state.get('color_outer', '#D8BFD8')) 
    with col2:
        # 남색 기본값
        color_inner = st.color_picker("안쪽 줄무늬", st.session_state.get('color_inner', '#000080'))
        
    st.session_state.color_outer = color_outer
    st.session_state.color_inner = color_inner

# 사용자가 선택한 색상으로 전체 배경 CSS 동적 생성
custom_css = f"""
<style>
    /* 전체 배경 양쪽 줄무늬 패턴 */
    .stApp {{
        background: linear-gradient(to right, 
            {st.session_state.color_outer} 0%, {st.session_state.color_outer} 3%, 
            {st.session_state.color_inner} 3%, {st.session_state.color_inner} 6%, 
            #ffffff 6%, #ffffff 94%, 
            {st.session_state.color_inner} 94%, {st.session_state.color_inner} 97%, 
            {st.session_state.color_outer} 97%, {st.session_state.color_outer} 100%);
    }}
    /* 중앙 컨텐츠 영역이 잘 보이도록 반투명 흰색 박스 추가 */
    .block-container {{
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 2rem !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-top: 2rem;
    }}
    /* 버튼 디자인 */
    div.stButton > button:first-child {{
        background-color: {st.session_state.color_inner}; color: white; border-radius: 10px; border: none;
    }}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- [2. 헤더: 구단 로고 및 팀명 표시] ---
header_col1, header_col2 = st.columns([1, 8])
with header_col1:
    if 'logo' in st.session_state:
        st.image(st.session_state.logo, use_container_width=True)
    else:
        st.markdown("<h1 style='text-align:center;'>⚽</h1>", unsafe_allow_html=True)
with header_col2:
    st.title(st.session_state.team_name)
st.divider()


# --- [3. 구글 시트 연동 로직] ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="Sheet1")
        return df['player_info'].dropna().tolist()
    except:
        return ["이성재(CB/DF)", "손흥민(LW/ST)", "이강인(AMF/RW)", "김민재(CB/DF)", "조현우(GK)"]

if 'roster' not in st.session_state:
    st.session_state.roster = load_data()


# --- [4. 핵심 알고리즘 및 데이터베이스 (V8과 동일)] ---
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
        players.sort(key=lambda x: (x["total"], x["p1_count"]))
        for t_pos, limit in formation.items():
            for p in players:
                if len(sq[t_pos]) < limit and p["name"] not in selected and can_play(p["pos1"], t_pos):
                    sq[t_pos].append(p["name"]); selected.append(p["name"]); p["total"] += 1; p["p1_count"] += 1
        for t_pos, limit in formation.items():
            for p in players:
                if len(sq[t_pos]) < limit and p["name"] not in selected and p["pos2"] and can_play(p["pos2"], t_pos):
                    sq[t_pos].append(p["name"]); selected.append(p["name"]); p["total"] += 1
        players.sort(key=lambda x: x["total"])
        for t_pos, limit in formation.items():
            if t_pos == "GK": continue 
            for p in players:
                if len(sq[t_pos]) < limit and p["name"] not in selected and p["pos1"] != "GK":
                    sq[t_pos].append(p["name"]); selected.append(p["name"]); p["total"] += 1
        all_squads.append(sq)
        all_benches.append([p for p in players if p["name"] not in selected])
    return all_squads, all_benches, players

def render_interactive_pitch(squad, form_name):
    y_map = {"FW": "15%", "MF": "45%", "DF": "75%", "GK": "90%"}
    player_html = ""
    coach_data = coach_voice_db.get(form_name, coach_voice_db["4-4-2"])
    
    for pos, names in squad.items():
        if not names: continue 
        instruction = coach_data.get(pos, "기본 전술 지침을 따릅니다.")
        for i, name in enumerate(names):
            x = (100 / (len(names) + 1)) * (i + 1)
            player_html += f"""
            <div onclick="showCoach('{name}', '{pos}', '{instruction}')" style="position:absolute; top:{y_map[pos]}; left:{x}%; transform:translate(-50%, -50%); text-align:center; cursor:pointer; z-index:5;">
                <div style="width:20px; height:20px; background:white; border:2px solid {st.session_state.color_inner}; border-radius:50%; margin:0 auto; box-shadow:0 2px 5px rgba(0,0,0,0.5);"></div>
                <div style="color:white; font-size:12px; font-weight:bold; margin-top:3px; white-space:nowrap; text-shadow: 1px 1px 3px black;">{name}</div>
            </div>"""
            
    return f"""
    <div style="background:linear-gradient(180deg, #2E8B57 0%, #226B43 100%); width:100%; max-width:350px; height:440px; position:relative; border:3px solid white; border-radius:15px; overflow:hidden; font-family:sans-serif; margin: 0 auto;">
        <div style="position:absolute; top:50%; width:100%; height:2px; background:white; opacity:0.4;"></div>
        <div style="position:absolute; top:50%; left:50%; width:80px; height:80px; border:2px solid white; border-radius:50%; transform:translate(-50%, -50%); opacity:0.4;"></div>
        {player_html}
        <div id="modal" style="display:none; position:absolute; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:10; padding:20px; color:white; box-sizing:border-box;">
            <div style="text-align:right; cursor:pointer; font-size:24px; color:{st.session_state.color_outer};" onclick="document.getElementById('modal').style.display='none'">&times;</div>
            <h3 id="m-name" style="margin:0; color:{st.session_state.color_outer};"></h3>
            <p id="m-pos" style="font-size:12px; color:#aaa; margin-bottom:15px;"></p>
            <p id="m-text" style="font-size:14px; line-height:1.6;"></p>
            <p style="font-size:11px; color:#666; margin-top:30px;">(클릭하여 닫기)</p>
        </div>
    </div>
    <script>
    function showCoach(name, pos, text) {{
        document.getElementById('m-name').innerText = name;
        document.getElementById('m-pos').innerText = "Position: " + pos;
        document.getElementById('m-text').innerHTML = text;
        document.getElementById('modal').style.display = 'block';
    }}
    </script>
    """


# --- [5. 메인 탭 UI] ---
tab1, tab2 = st.tabs(["📝 우리 팀 로스터 관리", "🏟️ 매치데이 스쿼드 짜기"])

with tab1:
    st.header("🌐 구글 시트 동기화")
    roster_input = st.text_area("전체 명단 (이름(주포/부포) 형식, 쉼표 구분)", value=", ".join(st.session_state.roster), height=200)
    if st.button("💾 구글 시트에 영구 저장"):
        new_list = [p.strip() for p in roster_input.split(",") if p.strip()]
        st.session_state.roster = new_list
        conn.update(worksheet="Sheet1", data=pd.DataFrame({"player_info": new_list}))
        st.success("✅ 저장이 완료되었습니다!")

with tab2:
    col_l, col_r = st.columns([1, 2.5])
    with col_l:
        st.subheader("오늘의 설정")
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
                board_cols = st.columns(2)
                for i in range(num_q):
                    with board_cols[i % 2]:
                        st.markdown(f"### 🎯 {i+1}Q ({forms[i]})")
                        st.components.v1.html(render_interactive_pitch(res[i], forms[i]), height=450)
                        
                        with st.expander(f"💡 {forms[i]} 핵심 전술 보기"):
                            data = coach_voice_db[forms[i]]
                            st.markdown(f"**공격:** {data['FW']}\n\n**미드:** {data['MF']}\n\n**수비:** {data['DF']}")
                        
                        bench_str = ", ".join([f"{p['name']}({p['pos1']})" for p in benches[i]])
                        st.info(f"🔄 **교체:** {bench_str if bench_str else '없음'}")
                
                st.write("---")
                st.subheader("📊 매치데이 출전 통계")
                stats_df = pd.DataFrame([{"이름": p["name"], "총 출전": p["total"]} for p in updated])
                st.dataframe(stats_df.sort_values("총 출전", ascending=False), use_container_width=True)
