import streamlit as st
import pandas as pd
import re
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- [1] 선수 데이터 처리 및 2쿼터 보장 알고리즘 ---
def parse_players(text):
    pattern = r"([가-힣a-zA-Z0-9]+)\(([A-Z]+)/([A-Z]+)\)"
    matches = re.findall(pattern, text)
    return [{"name": m[0], "pos1": m[1], "pos2": m[2], "total": 0, "p1_count": 0} for m in matches]

def generate_fair_squads(players, num_quarters, formation_needs):
    all_quarters = []
    for q in range(num_quarters):
        current_squad = {pos: [] for pos in formation_needs.keys()}
        selected_this_q = []
        
        # 주포지션(pos1) 2회 미만 출전자에게 최우선권 부여
        players.sort(key=lambda x: (x["p1_count"] >= 2, x["total"]))
        
        # 1차: 주포지션 배정
        for p in players:
            pos = p["pos1"]
            if pos in current_squad and len(current_squad[pos]) < formation_needs[pos] and p["name"] not in selected_this_q:
                current_squad[pos].append(p["name"])
                selected_this_q.append(p["name"])
                p["total"] += 1
                p["p1_count"] += 1
        
        # 2차: 서브포지션 배정
        for p in players:
            pos = p["pos2"]
            if pos in current_squad and len(current_squad[pos]) < formation_needs[pos] and p["name"] not in selected_this_q:
                current_squad[pos].append(p["name"])
                selected_this_q.append(p["name"])
                p["total"] += 1
                
        # 3차: 빈자리 강제 배정 (출전 적은 순)
        players.sort(key=lambda x: x["total"])
        for p in players:
            if p["name"] not in selected_this_q:
                for pos, limit in formation_needs.items():
                    if len(current_squad[pos]) < limit:
                        current_squad[pos].append(p["name"])
                        selected_this_q.append(p["name"])
                        p["total"] += 1
                        break
        all_quarters.append(current_squad)
    return all_quarters, players

# --- [2] 축구 전술판 이미지 생성 함수 (Matplotlib) ---
def draw_pitch_image(squad_dict, title):
    fig, ax = plt.subplots(figsize=(6, 8))
    ax.set_facecolor('#2E8B57')
    
    # 경기장 선 그리기
    plt.plot([0, 100, 100, 0, 0], [0, 0, 120, 120, 0], color="white", lw=2)
    plt.plot([0, 100], [60, 60], color="white", lw=2)
    ax.add_patch(patches.Circle((50, 60), 10, color='white', fill=False, lw=2))
    ax.add_patch(patches.Rectangle((20, 0), 60, 18, color='white', fill=False, lw=2))
    ax.add_patch(patches.Rectangle((20, 102), 60, 18, color='white', fill=False, lw=2))
    
    # 포지션별 Y좌표 설정 (상대적 위치)
    y_map = {"FW": 105, "MF": 65, "DF": 25, "GK": 7}
    
    for pos, names in squad_dict.items():
        for i, name in enumerate(names):
            x = (100 / (len(names) + 1)) * (i + 1)
            y = y_map.get(pos, 60)
            # 선수 아이콘
            ax.add_patch(patches.Circle((x, y), 3, color='white', ec='black', lw=1.5, zorder=3))
            # 선수 이름
            ax.text(x, y-5, name, color='white', fontweight='bold', ha='center', 
                    bbox=dict(facecolor='black', alpha=0.5, edgecolor='none', pad=1))
            
    plt.title(title, color='white', fontsize=18, fontweight='bold', pad=15)
    plt.xlim(-5, 105)
    plt.ylim(-5, 125)
    plt.axis('off')
    return fig

# --- [3] AI 감독 전술 지침 데이터 ---
tactic_data = {
    "역습형 4-4-2": {
        "needs": {"FW": 2, "MF": 4, "DF": 4, "GK": 1},
        "ai_coach": "🛡️ **수비:** 촘촘한 두 줄 수비로 공간을 지우세요. \n\n ⚡ **공격:** 공을 뺏자마자 투톱의 침투를 향해 롱패스를 찌르세요!"
    },
    "압박형 4-3-3": {
        "needs": {"FW": 3, "MF": 3, "DF": 4, "GK": 1},
        "ai_coach": "🔥 **수비:** 최전방부터 숨 막히는 압박을 가하세요. \n\n ⚽ **공격:** 윙어들이 안쪽으로 파고들고 풀백이 높은 위치까지 전진합니다."
    }
}

# --- [4] Streamlit UI ---
st.set_page_config(page_title="AI Soccer Manager", layout="wide")
st.title("⚽ AI 동아리 축구 매니저")

with st.sidebar:
    st.header("⚙️ 설정")
    raw_input = st.text_area("명단 입력 (이름(주/부))", 
                             value="손흥민(FW/MF), 김민재(DF/MF), 이강인(MF/FW), 조현우(GK/DF), 황희찬(FW/MF), 황인범(MF/DF), 설영우(DF/MF), 백승호(MF/DF), 조규성(FW/MF), 정승현(DF/MF), 박용우(MF/DF)", 
                             height=200)
    num_q = st.slider("쿼터 수", 1, 6, 4)
    choice = st.selectbox("AI 전술 선택", list(tactic_data.keys()))

if st.button("🚀 스쿼드 및 AI 전술 생성"):
    players = parse_players(raw_input)
    if not players:
        st.error("입력 형식을 확인해 주세요! 예: 홍길동(FW/MF)")
    else:
        # AI 감독 지시사항
        st.info(f"🤖 **AI 감독의 지시:** \n\n {tactic_data[choice]['ai_coach']}")
        
        # 알고리즘 실행
        res, updated = generate_fair_squads(players, num_q, tactic_data[choice]["needs"])
        
        # 전술판 이미지 출력
        st.subheader("🏟️ 쿼터별 라인업 (이미지 저장 가능)")
        cols = st.columns(2)
        for i, squad in enumerate(res):
            with cols[i % 2]:
                fig = draw_pitch_image(squad, f"{i+1} QUARTER")
                st.pyplot(fig)
        
        # 통계표
        st.subheader("📊 개인별 출전 통계")
        stats_df = pd.DataFrame([{"이름": p["name"], "총 출전": p["total"], "주포지션(보장)": p["p1_count"]} for p in updated])
        st.table(stats_df.sort_values("주포지션(보장)", ascending=False))
