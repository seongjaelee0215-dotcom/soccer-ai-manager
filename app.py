import streamlit as st
import pandas as pd
import re

# 1. 포지션 판별 도우미 (세부 포지션을 4대 포지션으로 변환)
def can_play(player_pos, target_broad_pos):
    if not player_pos: return False
    if player_pos == "FR" and target_broad_pos != "GK": return True # FR은 골키퍼 빼고 다 가능
    
    mapping = {
        "FW": ["FW", "ST", "LW", "RW"],
        "MF": ["MF", "CM", "CDM", "AMF"],
        "DF": ["DF", "CB", "RB", "LB"],
        "GK": ["GK"]
    }
    return player_pos in mapping.get(target_broad_pos, [])

# 2. 명단 파싱 (포지션 1개, 2개 모두 지원)
def parse_players(text):
    if not text: return []
    pattern = r"([가-힣a-zA-Z0-9]+)\(([A-Z]+)(?:/([A-Z]+))?\)"
    matches = re.findall(pattern, text)
    parsed = []
    for m in matches:
        name = m[0]
        pos1 = m[1]
        pos2 = m[2] if len(m) > 2 and m[2] else None
        parsed.append({"name": name, "pos1": pos1, "pos2": pos2, "total": 0, "p1_count": 0})
    return parsed

# 3. 2쿼터 보장 + 쿼터별 포메이션 알고리즘
def generate_squads(players, quarters, formations_selected, tactics):
    all_squads = []
    all_benches = []
    
    for q in range(quarters):
        form_name = formations_selected[q]
        formation = tactics[form_name]["form"]
        sq = {"FW": [], "MF": [], "DF": [], "GK": []}
        selected = []
        
        # 주포지션 출전 적은 순 -> 전체 출전 적은 순 정렬
        players.sort(key=lambda x: (x["p1_count"], x["total"]))
        
        # 1차 배정: 주포지션(pos1) 일치
        for t_pos, limit in formation.items():
            for p in players:
                if len(sq[t_pos]) < limit and p["name"] not in selected:
                    if can_play(p["pos1"], t_pos):
                        sq[t_pos].append(p["name"]); selected.append(p["name"])
                        p["total"] += 1; p["p1_count"] += 1
                        
        # 2차 배정: 부포지션(pos2) 일치
        for t_pos, limit in formation.items():
            for p in players:
                if len(sq[t_pos]) < limit and p["name"] not in selected:
                    if p["pos2"] and can_play(p["pos2"], t_pos):
                        sq[t_pos].append(p["name"]); selected.append(p["name"])
                        p["total"] += 1
                        
        # 3차 배정: 빈자리 발생 시, 출전 횟수가 적은 사람부터 아무나 땜빵
        players.sort(key=lambda x: x["total"])
        for t_pos, limit in formation.items():
            for p in players:
                if len(sq[t_pos]) < limit and p["name"] not in selected:
                    sq[t_pos].append(p["name"]); selected.append(p["name"])
                    p["total"] += 1
                    
        all_squads.append(sq)
        
        # 벤치(교체) 명단 정리
        bench = [p for p in players if p["name"] not in selected]
        all_benches.append(bench)
        
    return all_squads, all_benches, players

# 4. 전술판 그리기 (격리형 HTML - 깨짐 방지)
def render_pitch_html(squad):
    y_map = {"FW": "15%", "MF": "45%", "DF": "75%", "GK": "90%"}
    player_html = ""
    for pos, names in squad.items():
        for i, name in enumerate(names):
            x = (100 / (len(names) + 1)) * (i + 1)
            player_html += f"""
            <div style="position:absolute; top:{y_map[pos]}; left:{x}%; transform:translate(-50%, -50%); text-align:center;">
                <div style="width:14px; height:14px; background:white; border:2px solid black; border-radius:50%; margin:0 auto;"></div>
                <div style="color:white; font-size:11px; font-weight:bold; margin-top:2px; white-space:nowrap; text-shadow: 1px 1px 2px black;">{name}</div>
            </div>"""
    
    return f"""
    <div style="background:#2E8B57; width:280px; height:360px; position:relative; border:2px solid white; border-radius:10px; overflow:hidden; font-family:sans-serif; margin-bottom:10px;">
        <div style="position:absolute; top:50%; width:100%; height:2px; background:white; opacity:0.5;"></div>
        <div style="position:absolute; top:50%; left:50%; width:60px; height:60px; border:2px solid white; border-radius:50%; transform:translate(-50%, -50%); opacity:0.5;"></div>
        {player_html}
    </div>"""

# 5. 전술 데이터 (확장)
tactics = {
    "4-4-2": {"form": {"FW":2, "MF":4, "DF":4, "GK":1}},
    "4-3-3": {"form": {"FW":3, "MF":3, "DF":4, "GK":1}},
    "4-2-3-1": {"form": {"FW":1, "MF":5, "DF":4, "GK":1}},
    "5-2-3": {"form": {"FW":3, "MF":2, "DF":5, "GK":1}}
}

# 6. 앱 화면 구성
st.set_page_config(page_title="AI 감독", layout="wide")
st.title("⚽ AI 동아리 축구 매니저")

with st.sidebar:
    st.header("📋 명단 입력")
    fw_in = st.text_area("공격수 (FW, ST, LW, RW)", "손흥민(LW/ST), 조규성(ST/FW), 황희찬(RW/FW)")
    mf_in = st.text_area("미드필더 (MF, CM, CDM, AMF)", "이강인(AMF/RW), 황인범(CM/CDM), 백승호(CM/MF), 박용우(CDM/DF), 이재성(AMF/CM)")
    df_in = st.text_area("수비수 (DF, CB, RB, LB)", "김민재(CB/DF), 정승현(CB/DF), 설영우(RB/LB), 김진수(LB/MF)")
    gk_in = st.text_area("골키퍼 (GK)", "조현우(GK), 김승규(GK)")
    fr_in = st.text_area("올라운더 (FR - 골키퍼 제외 전지역)", "유상철(FR)")
    
    st.markdown("---")
    st.header("⚙️ 쿼터별 전술 설정")
    num_q = st.slider("총 쿼터 수", 1, 6, 4)
    
    # 쿼터별로 각각 포메이션을 선택할 수 있는 기능 추가
    formations_selected = []
    for i in range(num_q):
        f = st.selectbox(f"{i+1}쿼터 포메이션", list(tactics.keys()), key=f"q_{i}")
        formations_selected.append(f)

# 실행 버튼
if st.button("🚀 스쿼드 생성 및 교체 명단 확인"):
    # 5개의 텍스트 박스 내용을 하나로 합쳐서 파싱
    raw_total = f"{fw_in}, {mf_in}, {df_in}, {gk_in}, {fr_in}"
    ps = parse_players(raw_total)
    
    if ps:
        res, benches, updated = generate_squads(ps, num_q, formations_selected, tactics)
        st.success("🤖 각 쿼터별 맞춤형 스쿼드 배치가 완료되었습니다!")
        
        cols = st.columns(2)
        for i in range(num_q):
            with cols[i % 2]:
                st.markdown(f"### 🎯 {i+1}쿼터 ({formations_selected[i]})")
                st.components.v1.html(render_pitch_html(res[i]), height=380)
                
                # 교체 명단 문자열 만들기
                bench_str = ", ".join([f"{p['name']}({p['pos1']}{'/' + p['pos2'] if p['pos2'] else ''})" for p in benches[i]])
                if not bench_str: bench_str = "없음"
                
                st.info(f"🔄 **교체 대기:** {bench_str}")
        
        st.markdown("---")
        st.subheader("📊 전체 출전 통계 (2쿼터 주포지션 보장 확인)")
        df = pd.DataFrame([{"이름": p["name"], "총 출전": p["total"], "주포지션": p["p1_count"]} for p in updated])
        st.table(df.sort_values(by=["주포지션", "총 출전"], ascending=[False, False]))
    else:
        st.error("명단을 입력해 주세요!")
