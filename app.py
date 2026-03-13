import streamlit as st
import pandas as pd
import re

# 1. 선수 데이터 파싱 및 2쿼터 보장 알고리즘
def parse_players(text):
    pattern = r"([가-힣a-zA-Z0-9]+)\(([A-Z]+)/([A-Z]+)\)"
    matches = re.findall(pattern, text)
    return [{"name": m[0], "pos1": m[1], "pos2": m[2], "total": 0, "p1_count": 0} for m in matches]

def generate_squads(players, quarters, formation):
    all_squads = []
    for q in range(quarters):
        sq = {pos: [] for pos in formation.keys()}
        selected = []
        # 주포지션 출전 적은 순 -> 전체 출전 적은 순 정렬
        players.sort(key=lambda x: (x["p1_count"], x["total"]))
        
        for p in players: # 주포지션 배정
            pos = p["pos1"]
            if pos in formation and len(sq[pos]) < formation[pos] and p["name"] not in selected:
                sq[pos].append(p["name"]); selected.append(p["name"])
                p["total"] += 1; p["p1_count"] += 1
        for p in players: # 서브포지션 배정
            pos = p["pos2"]
            if pos in formation and len(sq[pos]) < formation[pos] and p["name"] not in selected:
                sq[pos].append(p["name"]); selected.append(p["name"])
                p["total"] += 1
        # 빈자리 강제 배정
        players.sort(key=lambda x: x["total"])
        for p in players:
            if p["name"] not in selected:
                for pos, limit in formation.items():
                    if len(sq[pos]) < limit:
                        sq[pos].append(p["name"]); selected.append(p["name"])
                        p["total"] += 1; break
        all_squads.append(sq)
    return all_squads, players

# 2. 전술판 그리기 (절대 안 깨지는 격리형 HTML)
def render_pitch_html(squad, title):
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
    <div style="background:#2E8B57; width:280px; height:380px; position:relative; border:2px solid white; border-radius:10px; overflow:hidden; font-family:sans-serif;">
        <div style="position:absolute; top:50%; width:100%; height:2px; background:white; opacity:0.5;"></div>
        <div style="position:absolute; top:50%; left:50%; width:60px; height:60px; border:2px solid white; border-radius:50%; transform:translate(-50%, -50%); opacity:0.5;"></div>
        <div style="padding:10px; color:white; font-weight:bold; font-size:14px;">{title}</div>
        {player_html}
    </div>"""

# 3. AI 감독 데이터
tactics = {
    "역습형 4-4-2": {"form": {"FW":2, "MF":4, "DF":4, "GK":1}, "desc": "🛡️ 두 줄 수비 후 ⚡ 빠른 역습!"},
    "나폴리식 4-3-3": {"form": {"FW":3, "MF":3, "DF":4, "GK":1}, "desc": "🔥 강한 전방 압박과 유기적인 패스!"}
}

# 4. 앱 화면 구성
st.set_page_config(page_title="AI 감독", layout="wide")
st.title("⚽ AI 동아리 축구 매니저")

with st.sidebar:
    st.header("⚙️ 설정")
    raw = st.text_area("명단 입력 (이름(주/부))", "김철수(FW/MF), 이영희(DF/MF), 박민수(MF/DF), 최지성(GK/DF), 손흥민(FW/MF), 황희찬(FW/MF), 이강인(MF/FW), 김민재(DF/MF), 황인범(MF/DF), 백승호(MF/DF), 설영우(DF/MF), 조규성(FW/MF)")
    num_q = st.slider("쿼터", 1, 6, 4)
    t_name = st.selectbox("전술 선택", list(tactics.keys()))

if st.button("🚀 스쿼드 생성 및 AI 감독 브리핑"):
    ps = parse_players(raw)
    if ps:
        res, updated = generate_squads(ps, num_q, tactics[t_name]["form"])
        st.success(f"🤖 **AI 감독 지시:** {tactics[t_name]['desc']}")
        
        # 전술판 출력 (st.components.v1.html 사용으로 격리)
        cols = st.columns(2)
        for i, sq in enumerate(res):
            with cols[i % 2]:
                st.components.v1.html(render_pitch_html(sq, f"{i+1} 쿼터"), height=400)
        
        st.subheader("📊 출전 통계 (2쿼터 주포지션 보장 확인)")
        df = pd.DataFrame([{"이름": p["name"], "총 출전": p["total"], "주포지션": p["p1_count"]} for p in updated])
        st.table(df.sort_values("주포지션", ascending=False))
