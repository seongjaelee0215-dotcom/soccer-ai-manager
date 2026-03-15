import streamlit as st
import pandas as pd
import re
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import datetime

st.set_page_config(page_title="AI Tactical Master", layout="wide", initial_sidebar_state="expanded")

# --- [0. Gemini AI 설정] ---
# Secrets에 등록된 API 키를 가져와 AI를 세팅합니다.
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ai_model = genai.GenerativeModel('gemini-1.5-flash') # 빠르고 똑똑한 최신 모델
except:
    ai_model = None

# --- [1. 구글 시트 연동 설정] ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_settings():
    try:
        df = conn.read(worksheet="Settings")
        return dict(zip(df['setting_name'], df['setting_value']))
    except:
        return {}

def load_data():
    try:
        df = conn.read(worksheet="Sheet1")
        return df['player_info'].dropna().tolist()
    except:
        return ["이성재(CB/DF)", "손흥민(LW/ST)", "이강인(AMF/RW)"]

def load_match_log():
    try:
        df = conn.read(worksheet="MatchLog")
        return df.fillna("") # 빈칸 처리
    except:
        return pd.DataFrame(columns=["Date", "Opponent", "Result", "Score", "Formation", "VideoLink", "AI_Feedback"])

if 'roster' not in st.session_state:
    st.session_state.roster = load_data()

if 'settings' not in st.session_state:
    saved_settings = load_settings()
    st.session_state.team_name = saved_settings.get('team_name', '홍익대학교 경영학부 팀 EINS')
    st.session_state.color_outer = saved_settings.get('color_outer', '#D8BFD8')
    st.session_state.color_inner = saved_settings.get('color_inner', '#000080')
    st.session_state.logo_url = saved_settings.get('logo_url', '')

# --- [2. 사이드바 (V10과 동일)] ---
with st.sidebar:
    st.header("⚙️ 구단 커스텀 설정")
    input_team_name = st.text_input("팀명", st.session_state.team_name)
    input_logo_url = st.text_input("로고 URL", st.session_state.logo_url)
    
    col1, col2 = st.columns(2)
    with col1:
        input_color_outer = st.color_picker("바깥 줄무늬", st.session_state.color_outer) 
    with col2:
        input_color_inner = st.color_picker("안쪽 줄무늬", st.session_state.color_inner)
        
    if st.button("💾 디자인 영구 저장"):
        st.session_state.team_name = input_team_name
        st.session_state.logo_url = input_logo_url
        st.session_state.color_outer = input_color_outer
        st.session_state.color_inner = input_color_inner
        
        settings_df = pd.DataFrame({
            'setting_name': ['team_name', 'logo_url', 'color_outer', 'color_inner'],
            'setting_value': [input_team_name, input_logo_url, input_color_outer, input_color_inner]
        })
        conn.update(worksheet="Settings", data=settings_df)
        st.success("저장 완료!")

# --- [3. 동적 CSS (V10과 동일)] ---
custom_css = f"""
<style>
    .stApp {{
        background: linear-gradient(to right, 
            {st.session_state.color_outer} 0%, {st.session_state.color_outer} 3%, 
            {st.session_state.color_inner} 3%, {st.session_state.color_inner} 6%, 
            #ffffff 6%, #ffffff 94%, 
            {st.session_state.color_inner} 94%, {st.session_state.color_inner} 97%, 
            {st.session_state.color_outer} 97%, {st.session_state.color_outer} 100%);
    }}
    .block-container {{
        background-color: rgba(255, 255, 255, 0.85) !important;
        backdrop-filter: blur(4px); border-radius: 15px; padding: 2rem !important; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-top: 2rem;
    }}
    div.stButton > button:first-child {{
        background-color: {st.session_state.color_inner}; color: white; border-radius: 10px; border: none;
    }}
    section[data-testid="stSidebar"] div.stButton > button:first-child {{
        background-color: #2E8B57; width: 100%;
    }}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- [4. 헤더 (V10과 동일)] ---
header_col1, header_col2 = st.columns([1, 8])
with header_col1:
    if st.session_state.logo_url:
        try:
            st.image(st.session_state.logo_url, use_container_width=True)
        except:
            st.markdown("⚽")
with header_col2:
    st.title(st.session_state.team_name)
st.divider()

# --- [5. 핵심 알고리즘 (V10과 동일 - 생략 없이 포함됨)] ---
coach_voice_db = {"4-4-2": {"FW": "⚔️ 포스트 플레이 분담", "MF": "🛡️ 두 줄 수비 조율", "DF": "📦 라인 컨트롤", "GK": "🧤 박스 장악"},"4-3-3": {"FW": "⚔️ 윙어 컷인 플레이", "MF": "🛡️ 즉각 재압박", "DF": "📦 오버래핑", "GK": "🧤 스위퍼 키퍼"},"4-2-3-1": {"FW": "⚔️ 원톱 고립 주의", "MF": "🛡️ 2선 침투 패스", "DF": "📦 하프스페이스 커버", "GK": "🧤 소통 중심"},"5-2-3": {"FW": "⚔️ 역습 속도 유지", "MF": "🛡️ 공간 점유 집중", "DF": "📦 윙백 적극 전진", "GK": "🧤 빠른 빌드업"}}
tactics_form = {"4-4-2": {"form": {"FW":2, "MF":4, "DF":4, "GK":1}},"4-3-3": {"form": {"FW":3, "MF":3, "DF":4, "GK":1}},"4-2-3-1": {"form": {"FW":1, "MF":5, "DF":4, "GK":1}},"5-2-3": {"form": {"FW":3, "MF":2, "DF":5, "GK":1}}}
def parse_players(player_list):
    text = ", ".join(player_list)
    return [{"name": m[0].strip(), "pos1": m[1], "pos2": m[2] if m[2] else None, "total": 0, "p1_count": 0} for m in re.findall(r"([가-힣a-zA-Z0-9\s]+)\(([A-Z]+)(?:/([A-Z]+))?\)", text)]
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
    for pos, names in squad.items():
        if not names: continue 
        for i, name in enumerate(names):
            x = (100 / (len(names) + 1)) * (i + 1)
            player_html += f"""<div style="position:absolute; top:{y_map[pos]}; left:{x}%; transform:translate(-50%, -50%); text-align:center; z-index:5;"><div style="width:20px; height:20px; background:white; border:2px solid {st.session_state.color_inner}; border-radius:50%; margin:0 auto; box-shadow:0 2px 5px rgba(0,0,0,0.5);"></div><div style="color:white; font-size:12px; font-weight:bold; margin-top:3px; white-space:nowrap; text-shadow: 1px 1px 3px black;">{name}</div></div>"""
    return f"""<div style="background:linear-gradient(180deg, #2E8B57 0%, #226B43 100%); width:100%; max-width:350px; height:440px; position:relative; border:3px solid white; border-radius:15px; overflow:hidden; font-family:sans-serif; margin: 0 auto; box-shadow:0 8px 16px rgba(0,0,0,0.2);"><div style="position:absolute; top:50%; width:100%; height:2px; background:white; opacity:0.4;"></div><div style="position:absolute; top:50%; left:50%; width:80px; height:80px; border:2px solid white; border-radius:50%; transform:translate(-50%, -50%); opacity:0.4;"></div>{player_html}</div>"""

# --- [6. 메인 탭 UI (새로운 경기 일지 탭 추가)] ---
tab1, tab2, tab3 = st.tabs(["📝 로스터 관리", "🏟️ 스쿼드 짜기", "📈 경기 일지 및 AI 분석"])

with tab1:
    roster_input = st.text_area("전체 명단 (이름(주포/부포) 형식, 쉼표 구분)", value=", ".join(st.session_state.roster), height=200)
    if st.button("💾 명단 저장"):
        new_list = [p.strip() for p in roster_input.split(",") if p.strip()]
        st.session_state.roster = new_list
        conn.update(worksheet="Sheet1", data=pd.DataFrame({"player_info": new_list}))
        st.success("✅ 저장 완료!")

with tab2:
    col_l, col_r = st.columns([1, 2.5])
    with col_l:
        today_players = st.multiselect("참석자 선택", options=st.session_state.roster, default=st.session_state.roster)
        num_q = st.slider("쿼터 수", 1, 6, 4)
        forms = [st.selectbox(f"{i+1}Q 전술", list(tactics_form.keys()), key=f"q_{i}") for i in range(num_q)]
        generate_btn = st.button("🚀 스쿼드 자동 생성")
    with col_r:
        if generate_btn and today_players:
            players_data = parse_players(today_players)
            res, benches, updated = generate_squads(players_data, num_q, forms, tactics_form)
            board_cols = st.columns(2)
            for i in range(num_q):
                with board_cols[i % 2]:
                    st.markdown(f"### 🎯 {i+1}Q ({forms[i]})")
                    st.components.v1.html(render_interactive_pitch(res[i], forms[i]), height=470)
                    bench_str = ", ".join([f"{p['name']}({p['pos1']})" for p in benches[i]])
                    st.info(f"🔄 **교체:** {bench_str if bench_str else '없음'}")

# --- [7. 매치 로그 및 AI 분석 탭 (신규)] ---
with tab3:
    st.header("📈 EINS 경기 기록 & AI 코치 분석")
    st.markdown("경기 기록을 남기고, 최신 축구 전술 이론에 입각한 AI 코치의 상세 피드백을 받아보세요.")
    
    # 경기 기록 입력 폼
    with st.expander("➕ 새 경기 기록하기", expanded=False):
        with st.form("match_form"):
            m_date = st.date_input("경기 날짜", datetime.date.today())
            m_opp = st.text_input("상대팀 이름")
            c1, c2, c3 = st.columns(3)
            with c1: m_res = st.selectbox("결과", ["승리", "무승부", "패배"])
            with c2: m_score = st.text_input("스코어 (예: 3-1)", "0-0")
            with c3: m_form = st.selectbox("메인 포메이션", list(tactics_form.keys()))
            m_video = st.text_input("경기 영상/하이라이트 링크 (유튜브/구글드라이브 등)")
            m_memo = st.text_area("감독의 짧은 메모 (우리 팀의 문제점이나 잘한 점을 적어주시면 AI가 참고합니다)")
            
            submit_match = st.form_submit_button("기록 저장하기")
            
            if submit_match:
                # 새 데이터를 기존 데이터프레임에 추가하고 구글 시트에 업데이트
                old_df = load_match_log()
                new_row = pd.DataFrame([{
                    "Date": str(m_date), "Opponent": m_opp, "Result": m_res, 
                    "Score": m_score, "Formation": m_form, "VideoLink": m_video, "AI_Feedback": m_memo
                }])
                updated_df = pd.concat([old_df, new_row], ignore_index=True)
                conn.update(worksheet="MatchLog", data=updated_df)
                st.success("✅ 경기 기록이 클라우드에 저장되었습니다!")
                st.rerun()

    # 기록된 경기 리스트 보기
    st.divider()
    match_df = load_match_log()
    
    if match_df.empty:
        st.info("아직 기록된 경기가 없습니다. 위에서 첫 경기를 기록해 보세요!")
    else:
        for index, row in match_df[::-1].iterrows(): # 최신순으로 보여줌
            with st.container():
                rc1, rc2 = st.columns([3, 1])
                with rc1:
                    res_emoji = "🔥" if row['Result'] == "승리" else "🤝" if row['Result'] == "무승부" else "💔"
                    st.subheader(f"{res_emoji} {row['Date']} vs {row['Opponent']} ({row['Score']})")
                    st.write(f"**사용 포메이션:** {row['Formation']}")
                    if row['VideoLink']:
                        st.markdown(f"[▶️ 경기 영상 보러가기]({row['VideoLink']})")
                
                with rc2:
                    # AI 피드백 생성 버튼
                    if st.button("🤖 AI 심층 전술 피드백", key=f"ai_btn_{index}"):
                        if ai_model is None:
                            st.error("API 키가 설정되지 않았습니다. Secrets에 GEMINI_API_KEY를 등록해주세요.")
                        else:
                            with st.spinner("AI가 현대 축구 전술 이론을 바탕으로 경기를 분석 중입니다..."):
                                prompt = f"""
                                당신은 펩 과르디올라, 카를로 안첼로티급의 세계 최고의 축구 전술가입니다.
                                홍익대학교 경영학부 축구팀 'EINS'의 경기 결과를 바탕으로 전문적이고 날카로운 전술 피드백을 제공해주세요.
                                
                                [경기 정보]
                                - 상대팀: {row['Opponent']}
                                - 결과: {row['Result']} ({row['Score']})
                                - 사용 포메이션: {row['Formation']}
                                - 감독의 메모: {row['AI_Feedback']}
                                
                                [요청 사항]
                                1. 이 포메이션과 결과, 감독 메모를 종합하여 우리 팀이 잘했을 부분과 보완해야 할 점을 전술적으로 분석해 주세요.
                                2. 현대 축구 논문이나 유명 감독의 철학을 한 가지 인용해서 조언해 주세요.
                                3. 다음 경기를 위한 포지션별(공격/중원/수비) 구체적인 훈련 또는 전술 지침을 3줄로 요약해 주세요.
                                4. 전문적이면서도 대학 축구팀에 맞는 열정적인 어조를 사용하세요.
                                """
                                try:
                                    response = ai_model.generate_content(prompt)
                                    st.success("분석 완료!")
                                    st.markdown(f"> **AI 전술 코치의 리포트**\n\n{response.text}")
                                except Exception as e:
                                    st.error(f"분석 중 오류가 발생했습니다: {e}")
            st.write("---")
