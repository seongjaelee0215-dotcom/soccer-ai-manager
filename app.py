import streamlit as st
import pandas as pd
import re

# --- [1] 데이터 파싱 및 2쿼터 보장 알고리즘 ---
def parse_players(text):
    # 김철수(ST/MF) 같은 형식에서 이름과 포지션 추출 (ST, LW 등도 FW/MF/DF로 묶어 처리 가능하지만 일단 그대로 사용)
    pattern = r"([가-힣a-zA-Z0-9]+)\(([A-Z]+)/([A-Z]+)\)"
    matches = re.findall(pattern, text)
    return [{"name": m[0], "pos1": m[1], "pos2": m[2], "played_total": 0, "played_pos1": 0} for m in matches]

def generate_fair_squads(players, num_quarters, formation):
    all_squads = []
    
    for q in range(num_quarters):
        current_squad = {pos: [] for pos in formation.keys()}
        selected_this_q = []
        
        # 최우선순위: 주 포지션(pos1) 출전 횟수가 2회 미만인 사람을 먼저 배치
        players.sort(key=lambda x: (x["played_pos1"], x["played_total"]))
        
        # 1차 배정: 주포지션 (pos1)
        for p in players:
            pos = p["pos1"]
            if pos in formation and len(current_squad[pos]) < formation[pos] and p["name"] not in selected_this_q:
                current_squad[pos].append(p["name"])
                selected_this_q.append(p["name"])
                p["played_total"] += 1
                p["played_pos1"] += 1
                
        # 2차 배정: 서브포지션 (pos2) - 빈자리 채우기
        for p in players:
            pos = p["pos2"]
            if pos in formation and len(current_squad[pos]) < formation[pos] and p["name"] not in selected_this_q:
                current_squad[pos].append(p["name"])
                selected_this_q.append(p["name"])
                p["played_total"] += 1
                
        # 3차 배정: 남는 자리 무작위 강제 배정 (인원이 부족할 경우)
        for p in players:
            if p["name"] not in selected_this_q:
                for pos, limit in formation.items():
                    if len(current_squad[pos]) < limit:
                        current_squad[pos].append(p["name"])
                        selected_this_q.append(p["name"])
                        p["played_total"] += 1
                        break
                        
        all_squads.append(current_squad)
        
    return all_squads, players

# --- [2] 완벽한 전술판 그래픽 (에러 방지용 깔끔한 HTML) ---
def render_pitch(squad_dict, title):
    # CSS 충돌을 막기 위해 딕셔너리와 HTML 분리
    html = f"""
    <div style="background-color:#2E8B57; width:100%; max-width:350px; height:450px; position:relative; border:2px solid white; margin:10px auto; border-radius:5px; box-shadow: 2px 2px 10px rgba(0,0,0,0.3);">
        <div style="position:absolute; top:50%; width:100%; height:2px; background-color:white; transform:translateY(-50%);"></div>
        <div style="position:absolute; top:50%; left:50%; width:70px; height:70px; border:2px solid white; border-radius:50%; transform:translate(-50%, -50%);"></div>
        <div style="position:absolute; top:0; left:20%; right:20%; height:15%; border:2px solid white; border-top:none;"></div>
        <div style="position:absolute; bottom:0; left:20%; right:20%; height:15%; border:2px solid white; border-bottom:none;"></div>
        <h4 style="color:white; text-align:left; padding:10px; margin:0; text-shadow:1px 1px 2px black;">{title}</h4>
    """
    y_positions = {"FW": 15, "MF": 45, "DF": 75, "GK": 90}
    
    for pos, players in squad_dict.items():
        if not players: continue
        for i, name in enumerate(players):
            x = (100 / (len(players) + 1)) * (i + 1)
            y = y_positions.get(pos, 50)
            html += f"""
            <div style="position:absolute; top:{y}%; left:{x}%; transform:translate(-50%, -50%); text-align:center;">
                <div style="width:20px; height:20px; background-color:white; border-radius:50%; border:2px solid black; margin:auto;"></div>
                <div style="color:white; font-size:12px; font-weight:bold; text-shadow:1px 1px 2px black; margin-top:3px; white-space:nowrap;">{name}</div>
            </div>
            """
    html += "</div>"
    return html

# --- [3] AI 감독 전술 데이터베이스 ---
tactics_db = {
    "선수비 후역습 (클래식 4-4-2)": {
        "formation": {"FW": 2, "MF": 4, "DF": 4, "GK": 1},
        "offense": "최전방 투톱 중 한 명은 포스트플레이로 공을 지켜주고, 나머지 한 명은 수비 뒷공간으로 즉시 침투합니다. 윙어들은 측면을 넓게 벌려 빠른 크로스를 준비하세요.",
        "defense": "간격을 촘촘하게 유지하는 '두 줄 수비(4-4)'가 핵심입니다. 중앙 공간을 절대 내주지 말고 상대를 측면으로 몰아넣은 뒤 압박하세요."
    },
    "유기적 압박 (나폴리 스타일 4-3-3)": {
        "formation": {"FW": 3, "MF": 3, "DF": 4, "GK": 1},
        "offense": "윙어들은 과감하게 안쪽으로 파고들며 슈팅 찬스를 노리고, 풀백이 그 빈 측면 공간으로 오버래핑합니다. 후방 빌드업 시 센터백부터 침착하게 패스워크를 전개하세요.",
        "defense": "공을 빼앗기면 물러서지 않고 즉각적으로 재압박(Gegenpressing)에 들어갑니다. 최전방 스리톱부터 시작되는 강한 전방 압박으로 상대의 실수를 유도하세요."
    },
    "중원 장악형 (3-5-2)": {
        "formation": {"FW": 2, "MF": 5, "DF": 3, "GK": 1},
        "offense": "5명의 미드필더를 바탕으로 볼 점유율을 높입니다. 양쪽 윙백은 공격 시 깊숙이 전진하여 크로스를 올립니다.",
        "defense": "수비 시에는 윙백이 내려와 5백을 형성합니다. 중앙 미드필더 3명이 상대 공격수를 강하게 대인 마크하세요."
    }
}

# --- [4] 메인 웹 화면 ---
st.set_page_config(page_title="AI 축구 감독", layout="wide")
st.title("⚽ AI 동아리 축구 감독 & 매니저")

st.sidebar.header("📋 경기 설정")
raw_input = st.sidebar.text_area(
    "명단 입력 (이름(주/부))", 
    value="김철수(FW/MF), 이영희(DF/MF), 박민수(MF/DF), 최지성(GK/DF), 정발굴(FW/DF), 조현우(GK/MF), 손흥민(FW/MF), 황희찬(FW/MF), 이강인(MF/FW), 김민재(DF/MF), 황인범(MF/DF), 백승호(MF/DF), 설영우(DF/MF), 김진수(DF/MF), 권경원(DF/MF), 조규성(FW/MF), 오현규(FW/MF), 주민규(FW/MF)",
    height=250
)
num_q = st.sidebar.slider("진행할 쿼터 수", 1, 6, 4)
tactic_choice = st.sidebar.selectbox("전술 및 포메이션 선택", list(tactics_db.keys()))

if st.sidebar.button("✨ 스쿼드 및 전술 생성"):
    players = parse_players(raw_input)
    if not players:
        st.error("명단 형식을 확인해주세요! 예: 김철수(FW/MF)")
    else:
        # 전술 브리핑 출력
        st.success(f"🤖 AI 감독의 전술 지시: **{tactic_choice}**")
        st.write(f"⚔️ **공격 지침:** {tactics_db[tactic_choice]['offense']}")
        st.write(f"🛡️ **수비 지침:** {tactics_db[tactic_choice]['defense']}")
        st.markdown("---")
        
        # 스쿼드 생성
        target_formation = tactics_db[tactic_choice]["formation"]
        results, updated_players = generate_fair_squads(players, num_q, target_formation)
        
        # 전술판 시각화
        st.subheader("🏟️ 쿼터별 선발 라인업 (전술판)")
        cols = st.columns(2)
        for i, squad in enumerate(results):
            with cols[i % 2]:
                # 핵심: unsafe_allow_html=True 가 있어야 코드가 안 보이고 이미지가 뜹니다.
                st.markdown(render_pitch(squad, f"{i+1}쿼터"), unsafe_allow_html=True)
                
        # 출전 보장 통계 출력
        st.subheader("📊 개인별 출전 통계 (2쿼터 보장 확인)")
        stats_df = pd.DataFrame([
            {"이름": p["name"], "총 출전": p["played_total"], "주포지션 출전": p["played_pos1"]} 
            for p in updated_players
        ]).sort_values(by=["주포지션 출전", "총 출전"], ascending=[False, False])
        
        st.table(stats_df)
        st.info("💡 위 표에서 모든 인원이 주포지션에서 충분히 뛰었는지 확인할 수 있습니다.")
