import streamlit as st
import pandas as pd
import re

# --- [UI 부드럽게 만들기 (커스텀 CSS)] ---
st.set_page_config(page_title="AI Tactical Master", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
    <style>
    /* 전체적인 폰트와 버튼 디자인을 둥글고 부드럽게(스카이블루 톤) 변경 */
    div.stButton > button:first-child {
        background-color: #00BFFF;
        color: white;
        border-radius: 10px;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: #009ACD;
        transform: translateY(-2px);
    }
    </style>
""", unsafe_allow_html=True)

# --- [데이터 보존 로직 (Session State)] ---
# 새로고침해도 임시로 명단을 기억하도록 세션 초기화
if 'roster' not in st.session_state:
    st.session_state.roster = [
        "손흥민(LW/ST)", "조규성(ST/FW)", "황희찬(RW/FW)", 
        "이강인(AMF/RW)", "황인범(CM/CDM)", "백승호(CM/MF)", "박용우(CDM/DF)", 
        "김민재(CB/DF)", "정승현(CB/DF)", "설영우(RB/LB)", "김진수(LB/MF)", 
        "조현우(GK)", "유상철(FR)"
    ]

# --- [1. 포지션 판별 및 파싱 알고리즘] ---
def can_play(player_pos, target_broad_pos):
    if not player_pos: return False
    if player_pos == "FR" and target_broad_pos != "GK": return True 
    mapping = {
        "FW": ["FW", "ST", "LW", "RW"],
        "MF": ["MF", "CM", "CDM", "AMF"],
        "DF": ["DF", "CB", "RB", "LB"],
        "GK": ["GK"]
    }
    return player_pos in mapping.get(target_broad_pos, [])

def parse_players(player_list):
    if not player_list: return []
    # 리스트를 하나의 문자열로 합친 뒤 기존 정규식으로 안전하게 추출
    text = ", ".join(player_list)
    pattern = r"([가-힣a-zA-Z0-9]+)\(([A-Z]+)(?:/([A-Z]+))?\)"
    matches = re.findall(pattern, text)
    return [{"name": m[0], "pos1": m[1], "pos2": m[2] if len(m) > 2 and m[2] else None, "total": 0, "p1_count": 0} for m in matches]

# --- [2. 3쿼터 보장 + 스쿼드 생성 알고리즘] ---
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

# --- [3. Coach's Voice 전술 데이터] ---
coach_voice_db = {
    "4-4-2": {
        "FW": "⚔️ 공격: 포스트 플레이와 침투를 분담하세요.<br>🛡️ 수비: 상대 미드필더로 향하는 패스 길목을 차단하세요.",
        "MF": "⚔️ 공격: 윙어는 넓게 서고, 중앙은 패스를 뿌려줍니다.<br>🛡️ 수비: 포백을 든든하게 보호하는 위치 선정이 핵심입니다.",
        "DF": "⚔️ 공격: 롱 킥으로 전방에 빠르게 연결하세요.<br>🛡️ 수비: 클래식한 '두 줄 수비'로 라인을 조율하세요.",
        "GK": "안정적인 박스 장악력이 필수입니다."
    },
    "4-3-3": {
        "FW": "⚔️ 공격: 윙어는 컷인(Cut-in), 톱은 펄스나인 움직임을 가져가세요.<br>🛡️ 수비: 전방 압박의 트리거 역할을 수행하세요.",
        "MF": "⚔️ 공격: 트라이앵글 대형을 유지하며 윤활유 역할을 하세요.<br>🛡️ 수비: 즉각적인 재압박(Gegenpressing)을 시도하세요.",
        "DF": "⚔️ 공격: 적극적으로 오버래핑하여 폭을 넓히세요.<br>🛡️ 수비: 능동적인 예측 수비가 필요합니다.",
        "GK": "스위퍼 키퍼로서 수비 라인 뒷공간을 넓게 커버하세요."
    },
    "4-2-3-1": {
        "FW": "⚔️ 공격: 2선이 올라올 시간을 벌어주는 타겟맨 역할을 하세요.<br>🛡️ 수비: 상대 센터백을 괴롭혀주세요.",
        "MF": "⚔️ 공격: 3선에서 2선으로 창의적인 킬패스를 찔러 넣으세요.<br>🛡️ 수비: 3선은 라인을 내리고 위험 지역을 장악하세요.",
        "DF": "⚔️ 공격: 하프스페이스로 언더래핑을 시도하세요.<br>🛡️ 수비: 중앙 수비수는 침투를 미리 예측하고 커버하세요.",
        "GK": "수비형 미드필더와 적극적으로 소통하세요."
    },
    "5-2-3": {
        "FW": "⚔️ 공격: 서로 스위칭하며 상대 하프스페이스를 공략하세요.<br>🛡️ 수비: 팀 압박을 지휘하세요.",
        "MF": "⚔️ 공격: 지체 없이 측면이나 전방으로 연결하세요.<br>🛡️ 수비: 공간을 지키는 데 집중하세요.",
        "DF": "⚔️ 공격: 윙백이 사실상 공격수입니다. 터치라인을 지배하세요.<br>🛡️ 수비: 스위퍼 한 명이 라인을 컨트롤하세요.",
        "GK": "빠른 스로인으로 윙백에게 역습 찬스를 열어주세요."
    }
}

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
                <div style="width:18px; height:18px; background:white; border:2px solid #00BFFF; border-radius:50%; margin:0 auto; transition:0.2s; box-shadow:0 2px 5px rgba(0,0,0,0.5);" onmouseover="this.style.transform='scale(1.3)'" onmouseout="this.style.transform='scale(1)'"></div>
                <div style="color:white; font-size:12px; font-weight:bold; margin-top:3px; white-space:nowrap; text-shadow: 1px 1px 3px black, 0 0 5px black;">{name}</div>
            </div>"""
    return f"""
    <div style="background:linear-gradient(180deg, #2E8B57 0%, #226B43 100%); width:100%; max-width:320px; height:420px; position:relative; border:3px solid rgba(255,255,255,0.8); border-radius:15px; overflow:hidden; font-family:'Helvetica Neue', sans-serif; margin: 0 auto; box-shadow: 0 10px 20px rgba(0,0,0,0.3);">
        <div style="position:absolute; top:50%; width:100%; height:2px; background:white; opacity:0.6;"></div>
        <div style="position:absolute; top:50%; left:50%; width:70px; height:70px; border:2px solid white; border-radius:50%; transform:translate(-50%, -50%); opacity:0.6;"></div>
        <div style="position:absolute; top:0; left:20%; width:60%; height:15%; border:2px solid white; border-top:none; opacity:0.6;"></div>
        <div style="position:absolute; bottom:0; left:20%; width:60%; height:15%; border:2px solid white; border-bottom:none; opacity:0.6;"></div>
        {player_html}
        <div id="modal" style="display:none; position:absolute; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.9); z-index:10; padding:20px; box-sizing:border-box; color:white; border-radius:12px;">
            <div style="text-align:right; cursor:pointer; font-size:24px; font-weight:bold; color:#00BFFF;" onclick="document.getElementById('modal').style.display='none'">&times;</div>
            <h2 id="m-name" style="margin:0 0 5px 0; color:#00BFFF; border-bottom:1px solid #444; padding-bottom:10px;"></h2>
            <div id="m-pos" style="font-size:13px; color:#ccc; margin-bottom:15px; font-weight:bold;"></div>
            <div id="m-text" style="font-size:14px; line-height:1.6;"></div>
        </div>
    </div>
    <script>
    function showCoach(name, pos, text) {{
        document.getElementById('m-name').innerText = name;
        document.getElementById('m-pos').innerText = "Role: " + pos;
        document.getElementById('m-text').innerHTML = text;
        document.getElementById('modal').style.display = 'block';
    }}
    </script>
    """

tactics_form = {
    "4-4-2": {"form": {"FW":2, "MF":4, "DF":4, "GK":1}},
    "4-3-3": {"form": {"FW":3, "MF":3, "DF":4, "GK":1}},
    "4-2-3-1": {"form": {"FW":1, "MF":5, "DF":4, "GK":1}},
    "5-2-3": {"form": {"FW":3, "MF":2, "DF":5, "GK":1}}
}

# --- [4. 메인 화면 UI (Tabs 활용)] ---
st.title("⚽ AI Tactical Master")
st.markdown("동아리 및 아마추어 축구팀을 위한 **스마트 로스터 & 전술 코칭 보드**입니다.")

# 탭으로 화면 분리
tab1, tab2 = st.tabs(["📝 우리 팀 로스터 관리", "🏟️ 매치데이 스쿼드 짜기"])

with tab1:
    st.header("팀 전체 선수 명단")
    st.markdown("팀원들을 한 번만 등록해두면 매번 입력할 필요가 없습니다. (형식: `이름(주/부)`)")
    
    # 명단을 편하게 관리할 수 있는 텍스트 에어리어 (세션과 동기화)
    roster_text = st.text_area("명단 편집", value=", ".join(st.session_state.roster), height=150)
    
    if st.button("💾 로스터 저장하기"):
        # 입력된 텍스트를 리스트로 변환하여 세션에 저장
        new_roster = [p.strip() for p in roster_text.split(",") if p.strip()]
        st.session_state.roster = new_roster
        st.success("✅ 로스터가 성공적으로 저장되었습니다! '매치데이 스쿼드 짜기' 탭으로 이동하세요.")

with tab2:
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.header("오늘의 라인업 설정")
        # 저장된 로스터를 불러와서 오늘 온 사람만 체크박스 형태로 선택
        today_players = st.multiselect(
            "✅ 오늘 참석한 선수 선택 (기본적으로 모두 선택됨)", 
            options=st.session_state.roster,
            default=st.session_state.roster
        )
        
        st.markdown("---")
        num_q = st.slider("총 쿼터 수", 1, 6, 4)
        formations_selected = []
        for i in range(num_q):
            f = st.selectbox(f"{i+1}쿼터 전술", list(tactics_form.keys()), key=f"q_{i}")
            formations_selected.append(f)
            
        generate_btn = st.button("🚀 AI 전술 보드 생성")

    with col_right:
        if generate_btn:
            ps = parse_players(today_players)
            if not ps:
                st.error("참석한 선수를 1명 이상 선택해 주세요!")
            else:
                res, benches, updated = generate_squads(ps, num_q, formations_selected, tactics_form)
                
                # 2열로 전술판 예쁘게 배치
                board_cols = st.columns(2)
                for i in range(num_q):
                    with board_cols[i % 2]:
                        st.markdown(f"#### 🎯 {i+1}Q ({formations_selected[i]})")
                        st.components.v1.html(render_interactive_pitch(res[i], formations_selected[i]), height=440)
                        
                        bench_str = ", ".join([f"{p['name']}({p['pos1']})" for p in benches[i]])
                        st.info(f"🔄 **교체:** {bench_str if bench_str else '없음'}")
                
                st.markdown("---")
                st.subheader("📊 매치데이 출전 통계")
                df = pd.DataFrame([{"이름": p["name"], "총 출전": p["total"], "주포지션": p["p1_count"]} for p in updated])
                st.dataframe(df.sort_values(by=["총 출전", "주포지션"], ascending=[False, False]), use_container_width=True)
