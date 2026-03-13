import streamlit as st
import pandas as pd
import re
from streamlit_gsheets import GSheetsConnection

# --- [1. UI 설정 및 커스텀 디자인] ---
st.set_page_config(page_title="AI Tactical Master", layout="wide")
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #00BFFF; color: white; border-radius: 10px; border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: 0.3s;
    }
    div.stButton > button:first-child:hover { background-color: #009ACD; transform: translateY(-2px); }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- [2. 구글 시트 연동 설정] ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="Sheet1")
        return df['player_info'].dropna().tolist()
    except:
        # 초기 접속자나 오류 시 보여줄 기본 샘플 명단
        return ["이성재(CB/DF)", "손흥민(LW/ST)", "이강인(AMF/RW)", "김민재(CB/DF)", "조현우(GK)"]

if 'roster' not in st.session_state:
    st.session_state.roster = load_data()

# --- [3. 핵심 알고리즘 및 데이터베이스] ---

coach_voice_db = {
    "4-4-2": {
        "FW": "⚔️ 공격: 포스트 플레이와 침투를 분담하세요.<br>🛡️ 수비: 상대 미드필더 패스 길목 차단!",
        "MF": "⚔️ 공격: 윙어는 넓게, 중앙은 패스 보급.<br>🛡️ 수비: 포백 보호를 최우선으로 하세요.",
        "DF": "⚔️ 공격: 전방으로 빠른 롱패스 연결.<br>🛡️ 수비: '두 줄 수비' 라인 조율에 집중!",
        "GK": "🧤 안정적인 박스 장악과 조율이 필수입니다."
    },
    "4-3-3": {
        "FW": "⚔️ 공격: 윙어는 안쪽으로 침투(Cut-in)!<br>🛡️ 수비: 전방 압박의 시작점이 되세요.",
        "MF": "⚔️ 공격: 삼각형 대형 유지하며 패스 게임.<br>🛡️ 수비: 즉각적인 재압박(Gegenpressing) 시도!",
        "DF": "⚔️ 공격: 적극적인 오버래핑으로 측면 지원.<br>🛡️ 수비: 높은 라인의 뒷공간을 주의하세요.",
        "GK": "🧤 스위퍼 키퍼로서 넓은 수비 범위를 가져가세요."
    },
    "4-2-3-1": {
        "FW": "⚔️ 공격: 2선이 올라올 시간을 버는 타겟맨.<br>🛡️ 수비: 상대 센터백을 끈질기게 괴롭히세요.",
        "MF": "⚔️ 공격: 3선은 빌드업, 2선은 킬패스 집중.<br>🛡️ 수비: 더블 볼란치의 단단한 중원 장악!",
        "DF": "⚔️ 공격: 하프스페이스 언더래핑 시도.<br>🛡️ 수비: 수비수는 침투 미리 예측하고 커버!",
        "GK": "🧤 수비형 미드필더와 끊임없이 소통하세요."
    },
    "5-2-3": {
        "FW": "⚔️ 공격: 측면 윙백과의 유기적인 스위칭.<br>🛡️ 수비: 팀 전체 압박을 리드하세요.",
        "MF": "⚔️ 공격: 지체 없는 전방 연결.<br>🛡️ 수비: 미드필더 숫자가 적으니 공간 사수 집중!",
        "DF": "⚔️ 공격: 윙백이 공격의 핵심! 터치라인 지배.<br>🛡️ 수비: 스위퍼가 최후방 라인을 컨트롤하세요.",
        "GK": "🧤 빠른 핸드 스로인으로 역습의 기점을 만드세요."
    }
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

# --- [4. 인터랙티브 전술판 렌더링 함수] ---
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
                <div style="width:20px; height:20px; background:white; border:2px solid #00BFFF; border-radius:50%; margin:0 auto; box-shadow:0 2px 5px rgba(0,0,0,0.5);"></div>
                <div style="color:white; font-size:12px; font-weight:bold; margin-top:3px; white-space:nowrap; text-shadow: 1px 1px 3px black;">{name}</div>
            </div>"""
            
    return f"""
    <div style="background:linear-gradient(180deg, #2E8B57 0%, #226B43 100%); width:100%; max-width:350px; height:440px; position:relative; border:3px solid white; border-radius:15px; overflow:hidden; font-family:sans-serif; margin: 0 auto;">
        <div style="position:absolute; top:50%; width:100%; height:2px; background:white; opacity:0.4;"></div>
        <div style="position:absolute; top:50%; left:50%; width:80px; height:80px; border:2px solid white; border-radius:50%; transform:translate(-50%, -50%); opacity:0.4;"></div>
        {player_html}
        <div id="modal" style="display:none; position:absolute; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:10; padding:20px; color:white; box-sizing:border-box;">
            <div style="text-align:right; cursor:pointer; font-size:24px; color:#00BFFF;" onclick="document.getElementById('modal').style.display='none'">&times;</div>
            <h3 id="m-name" style="margin:0; color:#00BFFF;"></h3>
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

# --- [5. 메인 UI 화면] ---
st.title("⚽ AI Tactical Master")

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
                        
                        # 전술 요약 텍스트 추가 (명당 자리!)
                        with st.expander(f"💡 {forms[i]} 핵심 전술 보기"):
                            data = coach_voice_db[forms[i]]
                            st.markdown(f"**공격:** {data['FW']}\n\n**미드:** {data['MF']}\n\n**수비:** {data['DF']}")
                        
                        bench_str = ", ".join([f"{p['name']}({p['pos1']})" for p in benches[i]])
                        st.info(f"🔄 **교체:** {bench_str if bench_str else '없음'}")
                
                st.write("---")
                st.subheader("📊 매치데이 출전 통계")
                stats_df = pd.DataFrame([{"이름": p["name"], "총 출전": p["total"]} for p in updated])
                st.dataframe(stats_df.sort_values("총 출전", ascending=False), use_container_width=True)
