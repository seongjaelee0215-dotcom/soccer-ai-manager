import streamlit as st
import pandas as pd
import re

# 1. 선수 배정 알고리즘
def parse_players(text):
    pattern = r"([가-힣a-zA-Z0-9]+)\(([A-Z]+)/([A-Z]+)\)"
    matches = re.findall(pattern, text)
    return [{"name": m[0], "pos1": m[1], "pos2": m[2], "total": 0, "p1_count": 0} for m in matches]

def generate_squads(players, quarters, formation):
    all_squads = []
    for q in range(quarters):
        sq = {pos: [] for pos in formation.keys()}
        selected = []
        
        # 1순위: 주포지션 출전 적은 순 -> 2순위: 전체 출전 적은 순 정렬
        players.sort(key=lambda x: (x["p1_count"], x["total"]))
        
        # 주포지션(pos1) 우선 배정
        for p in players:
            pos = p["pos1"]
            if pos in formation and len(sq[pos]) < formation[pos] and p["name"] not in selected:
                sq[pos].append(p["name"])
                selected.append(p["name"])
                p["total"] += 1
                p["p1_count"] += 1
                
        # 서브포지션(pos2) 배정
        for p in players:
            pos = p["pos2"]
            if pos in formation and len(sq[pos]) < formation[pos] and p["name"] not in selected:
                sq[pos].append(p["name"])
                selected.append(p["name"])
                p["total"] += 1
                
        # 인원이 모자랄 경우 남는 자리 무작위 강제 배정
        players.sort(key=lambda x: x["total"])
        for p in players:
            if p["name"] not in selected:
                for pos, limit in formation.items():
                    if len(sq[pos]) < limit:
                        sq[pos].append(p["name"])
                        selected.append(p["name"])
                        p["total"] += 1
                        break
                        
        all_squads.append(sq)
    return all_squads, players

# 2. 전술판 시각화 (HTML)
def draw_pitch(squad, title):
    html = f"""
    <div style="background-color:#2E8B57; width:100%; max-width:320px; height:400px; position:relative; border:2px solid white; margin:10px auto; border-radius:10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.5);">
        <div style="position:absolute; top:50%; width:100%; height:2px; background-color:white;"></div>
        <div style="position:absolute; top:50%; left:50%; width:60px; height:60px; border:2px solid white; border-radius:50%; transform:translate(-50%, -50%);"></div>
        <h4 style="color:white; padding:10px; margin:0; text-shadow:1px 1px 2px black;">{title}</h4>
    """
    y_map = {"FW": 15, "MF": 45, "DF": 75, "GK": 92}
    
    for pos, names in squad.items():
        for i, name in enumerate(names):
            x = (100 / (len(names) + 1)) * (i + 1)
            y = y_map.get(pos, 50)
            html += f"""
            <div style="position:absolute; top:{y}%; left:{x}%; transform:translate(-50%, -50%); text-align:center;">
                <div style="width:16px; height:16px; background-color:white; border-radius:50%; border:2px solid black; margin:auto;"></div>
                <div style="color:white; font-size:12px; font-weight:bold; text-shadow:1px 1px 2px black; margin-top:3px; white-space:nowrap;">{name}</div>
            </div>
            """
    return html + "</div>"

# 3. AI 전술 데이터
tactics = {
    "역습형 4-4-2": {
        "form": {"FW":2, "MF":4, "DF":4, "GK":1}, 
        "desc": "공격 시 윙어들이 직선적으로 돌파하고, 수비 시에는 촘촘한 두 줄 수비를 유지하세요."
    },
    "점유율형 4-3-3": {
        "form": {"FW":3, "MF":3, "DF":4, "GK":1}, 
        "desc": "짧은 패스로 경기를 조립하고, 공을 뺏기면 즉시 전방 압박을 가하세요."
    }
}

# 4. Streamlit UI 구성
st.set_page_config(page_title="AI 감독", layout="wide")
st.title("⚽ AI 동아리 축구 매니저")

raw = st.sidebar.text_area("명단 (이름(주/부))", "김철수(FW/MF), 이영희(DF/MF), 박민수(MF/DF), 최지성(GK/DF), 손흥민(FW/MF), 황희찬(FW/MF), 이강인(MF/FW), 김민재(DF/MF), 황인범(MF/DF), 백승호(MF/DF), 설영우(DF/MF), 권경원(DF/MF)")
num_q = st.sidebar.slider("쿼터", 1, 6, 4)
t_name = st.sidebar.selectbox("전술 선택", list(tactics.keys()))

if st.sidebar.button("스쿼드 생성"):
    ps = parse_players(raw)
    if not ps:
        st.error("명단 형식을 맞춰주세요! 예: 김철수(FW/MF)")
    else:
        res, updated = generate_squads(ps, num_q, tactics[t_name]["form"])
        
        st.success(f"🤖 **AI 감독 지시:** {tactics[t_name]['desc']}")
        
        cols = st.columns(2)
        for i, sq in enumerate(res):
            with cols[i % 2]:
                st.markdown(draw_pitch(sq, f"{i+1}쿼터"), unsafe_allow_html=True)
                
        st.subheader("📊 출전 통계 (2쿼터 주포지션 보장 확인)")
        stats_df = pd.DataFrame([
            {"이름": p["name"], "총 출전": p["total"], "주포지션(보장)": p["p1_count"]} 
            for p in updated
        ]).sort_values(by=["주포지션(보장)", "총 출전"], ascending=[False, False])
        
        st.table(stats_df)
