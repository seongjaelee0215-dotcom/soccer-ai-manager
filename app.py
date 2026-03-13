import streamlit as st
import pandas as pd
import re

# 1. 포지션 판별 도우미
def can_play(player_pos, target_broad_pos):
    if not player_pos: return False
    # FR은 골키퍼 빼고 다 가능
    if player_pos == "FR" and target_broad_pos != "GK": return True 
    
    mapping = {
        "FW": ["FW", "ST", "LW", "RW"],
        "MF": ["MF", "CM", "CDM", "AMF"],
        "DF": ["DF", "CB", "RB", "LB"],
        "GK": ["GK"]
    }
    return player_pos in mapping.get(target_broad_pos, [])

# 2. 명단 파싱
def parse_players(text):
    if not text: return []
    pattern = r"([가-힣a-zA-Z0-9]+)\(([A-Z]+)(?:/([A-Z]+))?\)"
    matches = re.findall(pattern, text)
    parsed = []
    for m in matches:
        parsed.append({"name": m[0], "pos1": m[1], "pos2": m[2] if len(m) > 2 and m[2] else None, "total": 0, "p1_count": 0})
    return parsed

# 3. 3쿼터 이상 보장 + 골키퍼 예외 처리 알고리즘
def generate_squads(players, quarters, formations_selected, tactics):
    all_squads = []
    all_benches = []
    
    for q in range(quarters):
        form_name = formations_selected[q]
        formation = tactics[form_name]["form"]
        sq = {"FW": [], "MF": [], "DF": [], "GK": []}
        selected = []
        
        # [핵심] 4쿼터 몰빵 방지: '전체 출전 횟수'가 가장 적은 사람부터 무조건 우선순위 부여
        players.sort(key=lambda x: (x["total"], x["p1_count"]))
        
        # 1차 배정: 주포지션
        for t_pos, limit in formation.items():
            for p in players:
                if len(sq[t_pos]) < limit and p["name"] not in selected:
                    if can_play(p["pos1"], t_pos):
                        sq[t_pos].append(p["name"]); selected.append(p["name"])
                        p["total"] += 1; p["p1_count"] += 1
                        
        # 2차 배정: 부포지션
        for t_pos, limit in formation.items():
            for p in players:
                if len(sq[t_pos]) < limit and p["name"] not in selected:
                    if p["pos2"] and can_play(p["pos2"], t_pos):
                        sq[t_pos].append(p["name"]); selected.append(p["name"])
                        p["total"] += 1
                        
        # 3차 배정: 빈자리 강제 배정 (출전 횟수 적은 순)
        players.sort(key=lambda x: x["total"])
        for t_pos, limit in formation.items():
            # [핵심] 골키퍼 자리는 빈자리 땜빵에서 완전히 제외합니다. (필드 플레이어 강제 배정 금지)
            if t_pos == "GK": continue 
            
            for p in players:
                if len(sq[t_pos]) < limit and p["name"] not in selected:
                    # 골키퍼 전용 선수가 필드에 나가는 것도 방지
                    if p["pos1"] != "GK":
                        sq[t_pos].append(p["name"]); selected.append(p["name"])
                        p["total"] += 1
                    
        all_squads.append(sq)
        bench = [p for p in players if p["name"] not in selected]
        all_benches.append(bench)
        
    return all_squads, all_benches, players

# 4. Coach's Voice 기반 딥러닝 AI 코칭 데이터 (마인드셋 & 역할)
coach_voice_db = {
    "4-4-2": {
        "FW": "⚔️ 공격: 투톱 중 한 명은 포스트 플레이로 수비를 끌고, 다른 한 명은 그 뒷공간으로 직선적인 침투를 가져갑니다.<br>🛡️ 수비: 전방 압박보다는 상대 미드필더에게 향하는 패스 길목을 차단하는 데 집중하세요.",
        "MF": "⚔️ 공격: 측면 윙어는 터치라인을 밟고 넓게 서서 아이솔레이션(1대1) 기회를 창출하세요.<br>🛡️ 수비: 중앙 미드필더 2명은 서포터가 원딜을 보호하듯, 상대의 역습 동선을 미리 읽고 포백을 든든하게 보호하는 위치 선정이 핵심입니다.",
        "DF": "⚔️ 공격: 볼을 탈취하면 지체 없이 전방의 열린 공간으로 롱 킥을 시도하세요.<br>🛡️ 수비: 클래식한 '두 줄 수비'입니다. 센터백은 라인 주도권을 잃지 않도록 상대 공격수를 타이트하게 마크하세요.",
        "GK": "안정적인 박스 장악력이 필수입니다. 크로스가 올라올 때 펀칭과 캐칭 판단을 확실히 하세요."
    },
    "4-3-3": {
        "FW": "⚔️ 공격: 윙어는 과감하게 안쪽으로 컷인(Cut-in)하며 슈팅 각도를 만들고, 펄스나인(가짜 9번)은 미드필드로 내려와 수비를 끌어냅니다.<br>🛡️ 수비: 전방 압박의 트리거입니다. 라인 주도권을 쥐기 위해 상대 풀백을 향해 커브 런으로 강하게 압박하세요.",
        "MF": "⚔️ 공격: 후방 빌드업의 코어로서 끊임없이 고개를 돌려 시야를 장악(Head-checking)하세요. 트라이앵글 대형을 유지하며 윤활유 역할을 해야 합니다.<br>🛡️ 수비: 공수 전환 시 즉각적인 재압박(Gegenpressing)으로 상대의 카운터를 지연시키세요.",
        "DF": "⚔️ 공격: 윙어가 안쪽으로 파고들면 측면으로 오버래핑하여 공격의 폭을 넓히세요.<br>🛡️ 수비: 상대 공격수가 등지고 받을 때, 물러서지 않고 과감하게 전진하여 볼을 탈취하는 능동적인 예측 수비가 필요합니다.",
        "GK": "스위퍼 키퍼로서 수비 라인 뒷공간을 넓게 커버하고, 빌드업 시에는 11번째 필드 플레이어처럼 짧은 패스의 시작점이 되어주세요."
    },
    "4-2-3-1": {
        "FW": "⚔️ 공격: 홀로 적진에 남겨지더라도 볼을 키핑하며 2선 공격수들이 올라올 시간을 벌어주는 타겟맨 역할을 수행하세요.<br>🛡️ 수비: 상대 센터백이 편하게 전진 패스를 하지 못하도록 지속적으로 괴롭혀야 합니다.",
        "MF": "⚔️ 공격: 공격형 미드필더(AMF)는 3선의 더블 볼란치(2명의 수비형 미드필더)로부터 공을 이어받아 창의적인 킬패스를 찔러 넣으세요.<br>🛡️ 수비: 3선 미드필더들은 라인을 내리고 위험 지역의 시야를 장악하며 상대의 컷백을 차단하세요.",
        "DF": "⚔️ 공격: 풀백은 상황에 따라 하프스페이스로 언더래핑하여 중앙 수적 우위를 만들어주세요.<br>🛡️ 수비: 4백 대형을 견고하게 유지하고, 중앙 수비수는 상대 공격수의 침투를 미리 예측하고 커버해야 합니다.",
        "GK": "수비형 미드필더와 적극적으로 소통하며 수비 라인의 간격을 조율하세요."
    },
    "5-2-3": {
        "FW": "⚔️ 공격: 전방 스리톱은 서로 스위칭하며 상대 3백 사이의 하프스페이스 틈새를 적극적으로 공략하세요.<br>🛡️ 수비: 상대 수비가 빌드업을 할 때 한쪽 측면으로 몰아넣는 팀 압박을 지휘하세요.",
        "MF": "⚔️ 공격: 단 2명으로 중원을 감당해야 하므로, 볼을 잡았을 때 지체 없이 측면 윙백이나 전방으로 연결하는 간결함이 필요합니다.<br>🛡️ 수비: 중원에서 수적 열세에 놓이기 쉬우므로 무리한 전진 압박보다는 공간을 지키는 데 집중하세요.",
        "DF": "⚔️ 공격: 양쪽 윙백(LWB, RWB)이 사실상의 측면 공격수입니다. 체력을 갈아 넣어 터치라인을 지배하세요.<br>🛡️ 수비: 5백이 되면서 중앙은 단단해집니다. 센터백 중 한 명은 스위퍼 역할을 하며 라인을 컨트롤하세요.",
        "GK": "페널티 박스 안으로 들어오는 롱패스를 차단하고, 빠른 스로인으로 윙백에게 역습 찬스를 열어주세요."
    }
}

# 5. 전술판 + 팝업 코칭 인터페이스 (HTML/JS/CSS 통합)
def render_interactive_pitch(squad, form_name):
    y_map = {"FW": "15%", "MF": "45%", "DF": "75%", "GK": "90%"}
    player_html = ""
    coach_data = coach_voice_db.get(form_name, coach_voice_db["4-4-2"])
    
    for pos, names in squad.items():
        if not names: continue # 골키퍼 공란 시 렌더링 생략
        instruction = coach_data.get(pos, "기본 전술 지침을 따릅니다.")
        
        for i, name in enumerate(names):
            x = (100 / (len(names) + 1)) * (i + 1)
            # 클릭 이벤트 주입
            player_html += f"""
            <div onclick="showCoach('{name}', '{pos}', '{instruction}')" style="position:absolute; top:{y_map[pos]}; left:{x}%; transform:translate(-50%, -50%); text-align:center; cursor:pointer; z-index:5;">
                <div style="width:18px; height:18px; background:white; border:2px solid black; border-radius:50%; margin:0 auto; transition:0.2s; box-shadow:0 2px 5px rgba(0,0,0,0.5);" onmouseover="this.style.transform='scale(1.3)'" onmouseout="this.style.transform='scale(1)'"></div>
                <div style="color:white; font-size:12px; font-weight:bold; margin-top:3px; white-space:nowrap; text-shadow: 1px 1px 3px black, 0 0 5px black;">{name}</div>
            </div>"""
    
    # 팝업(Modal) UI 및 경기장 포함
    return f"""
    <div style="background:#2E8B57; width:100%; max-width:320px; height:420px; position:relative; border:2px solid white; border-radius:10px; overflow:hidden; font-family:'Helvetica Neue', sans-serif; margin: 0 auto;">
        <div style="position:absolute; top:50%; width:100%; height:2px; background:white; opacity:0.6;"></div>
        <div style="position:absolute; top:50%; left:50%; width:70px; height:70px; border:2px solid white; border-radius:50%; transform:translate(-50%, -50%); opacity:0.6;"></div>
        <div style="position:absolute; top:0; left:20%; width:60%; height:15%; border:2px solid white; border-top:none; opacity:0.6;"></div>
        <div style="position:absolute; bottom:0; left:20%; width:60%; height:15%; border:2px solid white; border-bottom:none; opacity:0.6;"></div>
        
        {player_html}
        
        <div id="modal" style="display:none; position:absolute; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:10; padding:20px; box-sizing:border-box; color:white; border-radius:10px;">
            <div style="text-align:right; cursor:pointer; font-size:24px; font-weight:bold; color:#ff4b4b;" onclick="document.getElementById('modal').style.display='none'">&times;</div>
            <h2 id="m-name" style="margin:0 0 5px 0; color:#4CAF50; border-bottom:1px solid #555; padding-bottom:10px;"></h2>
            <div id="m-pos" style="font-size:13px; color:#aaa; margin-bottom:15px; font-weight:bold;"></div>
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

# 6. 전술 데이터 뼈대
tactics_form = {
    "4-4-2": {"form": {"FW":2, "MF":4, "DF":4, "GK":1}},
    "4-3-3": {"form": {"FW":3, "MF":3, "DF":4, "GK":1}},
    "4-2-3-1": {"form": {"FW":1, "MF":5, "DF":4, "GK":1}},
    "5-2-3": {"form": {"FW":3, "MF":2, "DF":5, "GK":1}}
}

# 7. 앱 화면
st.set_page_config(page_title="AI Coach's Voice", layout="wide")
st.title("⚽ 동아리 매니저 & AI 코칭 시스템")
st.markdown("💡 **Tip:** 전술판에 배치된 선수의 동그라미를 클릭하면, Coach's Voice 기반의 디테일한 역할 코칭 브리핑을 확인할 수 있습니다.")

with st.sidebar:
    st.header("📋 명단 입력")
    fw_in = st.text_area("공격수 (FW, ST, LW, RW)", "손흥민(LW/ST), 조규성(ST/FW), 황희찬(RW/FW)")
    mf_in = st.text_area("미드필더 (MF, CM, CDM, AMF)", "이강인(AMF/RW), 황인범(CM/CDM), 백승호(CM/MF), 박용우(CDM/DF), 이재성(AMF/CM)")
    df_in = st.text_area("수비수 (DF, CB, RB, LB)", "김민재(CB/DF), 정승현(CB/DF), 설영우(RB/LB), 김진수(LB/MF)")
    gk_in = st.text_area("골키퍼 (GK) *공란 시 비워둡니다", "") # 골키퍼 비워두기 테스트용
    fr_in = st.text_area("올라운더 (FR - 필드 전지역)", "유상철(FR)")
    
    st.markdown("---")
    st.header("⚙️ 쿼터별 전술 설정")
    num_q = st.slider("총 쿼터 수", 1, 6, 4)
    
    formations_selected = []
    for i in range(num_q):
        f = st.selectbox(f"{i+1}쿼터 포메이션", list(tactics_form.keys()), key=f"q_{i}")
        formations_selected.append(f)

if st.button("🚀 스쿼드 생성 및 AI 코칭 시작"):
    raw_total = f"{fw_in}, {mf_in}, {df_in}, {gk_in}, {fr_in}"
    ps = parse_players(raw_total)
    
    if ps:
        res, benches, updated = generate_squads(ps, num_q, formations_selected, tactics_form)
        
        cols = st.columns(2)
        for i in range(num_q):
            with cols[i % 2]:
                st.markdown(f"### 🎯 {i+1}쿼터 ({formations_selected[i]})")
                # 팝업 기능이 들어간 새로운 HTML 컴포넌트 호출
                st.components.v1.html(render_interactive_pitch(res[i], formations_selected[i]), height=450)
                
                bench_str = ", ".join([f"{p['name']}({p['pos1']}{'/' + p['pos2'] if p['pos2'] else ''})" for p in benches[i]])
                st.info(f"🔄 **대기:** {bench_str if bench_str else '없음'}")
        
        st.markdown("---")
        st.subheader("📊 전체 출전 통계 (최소 3쿼터 보장 확인용)")
        st.markdown("알고리즘이 특정 소수의 4쿼터 독식을 막고, 하위권 출전자의 기회를 강제로 끌어올렸습니다. *(골키퍼 공란 시 필드 플레이어 기록 제외됨)*")
        df = pd.DataFrame([{"이름": p["name"], "총 출전": p["total"], "주포지션": p["p1_count"]} for p in updated])
        st.table(df.sort_values(by=["총 출전", "주포지션"], ascending=[False, False]))
    else:
        st.error("명단을 입력해 주세요!")
