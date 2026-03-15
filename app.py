import streamlit as st
import pandas as pd
import re
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import datetime

st.set_page_config(page_title="AI Tactical Master", layout="wide", initial_sidebar_state="expanded")

# --- [0. Gemini AI 설정] ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
except:
    ai_model = None

# --- [1. 구글 시트 및 세션 상태 설정] ---
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
        return ["이성재(CB/DF)", "손흥민(LW/ST)", "이강인(AMF/RW)", "김민재(CB/DF)", "조현우(GK)"]

def load_match_log():
    try:
        df = conn.read(worksheet="MatchLog")
        return df.fillna("")
    except:
        return pd.DataFrame(columns=["Date", "Opponent", "Result", "Score", "Formation", "VideoLink", "AI_Feedback"])

if 'roster' not in st.session_state: st.session_state.roster = load_data()
if 'settings' not in st.session_state:
    saved_settings = load_settings()
    st.session_state.team_name = saved_settings.get('team_name', '홍익대학교 경영학부 팀 EINS')
    st.session_state.color_outer = saved_settings.get('color_outer', '#D8BFD8')
    st.session_state.color_inner = saved_settings.get('color_inner', '#000080')
    st.session_state.logo_url = saved_settings.get('logo_url', '')

# --- [2. 사이드바 및 동적 CSS] ---
with st.sidebar:
    st.header("⚙️ 구단 커스텀 설정")
    input_team_name = st.text_input("팀명", st.session_state.team_name)
    input_logo_url = st.text_input("로고 URL", st.session_state.logo_url)
    
    col1, col2 = st.columns(2)
    with col1: input_color_outer = st.color_picker("바깥 줄무늬", st.session_state.color_outer) 
    with col2: input_color_inner = st.color_picker("안쪽 줄무늬", st.session_state.color_inner)
        
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

custom_css = f"""
<style>
    .stApp {{ background: linear-gradient(to right, {st.session_state.color_outer} 0%, {st.session_state.color_outer} 3%, {st.session_state.color_inner} 3%, {st.session_state.color_inner} 6%, #ffffff 6%, #ffffff 94%, {st.session_state.color_inner} 94%, {st.session_state.color_inner} 97%, {st.session_state.color_outer} 97%, {st.session_state.color_outer} 100%); }}
    .block-container {{ background-color: rgba(255, 255, 255, 0.85) !important; backdrop-filter: blur(4px); border-radius: 15px; padding: 2rem !important; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-top: 2rem; }}
    div.stButton > button:first-child {{ background-color: {st.session_state.color_inner}; color: white; border-radius: 10px; border: none; }}
    section[data-testid="stSidebar"] div.stButton > button:first-child {{ background-color: #2E8B57; width: 100%; }}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

header_col1, header_col2 = st.columns([1, 8])
with header_col1:
    if st.session_state.logo_url:
        try: st.image(st.session_state.logo_url, use_container_width=True)
        except: st.markdown("⚽")
with header_col2: st.title(st.session_state.team_name)
st.divider()

# --- [3. 핵심 알고리즘 및 팝업 렌더링 (복구 완료!)] ---
coach_voice_db = {
    "4-4-2": {"FW": "⚔️ 포스트 플레이 분담 및 침투<br>🛡️ 수비형 미드필더 패스 길목 차단", "MF": "⚔️ 윙어는 넓게 벌리고, 중앙은 볼 배급<br>🛡️ 두 줄 수비 조율 및 간격 유지", "DF": "⚔️ 후방 빌드업 및 롱패스<br>🛡️ 오프사이드 라인 컨트롤", "GK": "🧤 박스 장악 및 안정적인 캐칭"},
    "4-3-3": {"FW": "⚔️ 윙어 컷인 플레이 및 하프스페이스 공략<br>🛡️ 전방 압박의 시작점", "MF": "⚔️ 삼각형 대형 유지 및 패스 앤 무브<br>🛡️ 공을 잃으면 즉각 재압박(게겐프레싱)", "DF": "⚔️ 풀백 적극적 오버래핑<br>🛡️ 뒷공간 커버 필수", "GK": "🧤 높은 라인을 보조하는 스위퍼 키퍼"},
    "4-2-3-1": {"FW": "⚔️ 2선이 올라올 시간을 버는 타겟맨<br>🛡️ 상대 센터백 지속적 견제", "MF": "⚔️ 3선 빌드업, 2선 킬패스 집중<br>🛡️ 더블 볼란치의 중원 완벽 장악", "DF": "⚔️ 측면 언더래핑 시도<br>🛡️ 하프스페이스 커버", "GK": "🧤 수비형 미드필더와 끊임없는 소통"},
    "5-2-3": {"FW": "⚔️ 측면 윙백과의 유기적 스위칭<br>🛡️ 역습 속도 유지를 위한 준비", "MF": "⚔️ 전방으로 빠른 롱볼 전환<br>🛡️ 미드필더 숫자 부족, 공간 점유 집중", "DF": "⚔️ 윙백이 공격의 핵심! 적극 전진<br>🛡️ 스위퍼의 최종 라인 컨트롤", "GK": "🧤 빠른 핸드 스로인으로 역습 기점 마련"}
}

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
    all_squads = []
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
    return all_squads, players

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
    <div style="background:linear-gradient(180deg, #2E8B57 0%, #226B43 100%); width:100%; max-width:350px; height:440px; position:relative; border:3px solid white; border-radius:15px; overflow:hidden; font-family:sans-serif; margin: 0 auto; box-shadow:0 8px 16px rgba(0,0,0,0.2);">
        <div style="position:absolute; top:50%; width:100%; height:2px; background:white; opacity:0.4;"></div>
        <div style="position:absolute; top:50%; left:50%; width:80px; height:80px; border:2px solid white; border-radius:50%; transform:translate(-50%, -50%); opacity:0.4;"></div>
        {player_html}
        <div id="modal" style="display:none; position:absolute; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.9); z-index:10; padding:20px; color:white; box-sizing:border-box;">
            <div style="text-align:right; cursor:pointer; font-size:24px; color:{st.session_state.color_outer};" onclick="document.getElementById('modal').style.display='none'">&times;</div>
            <h3 id="m-name" style="margin:0; color:{st.session_state.color_outer};"></h3>
            <p id="m-pos" style="font-size:12px; color:#aaa; margin-bottom:15px;"></p>
            <p id="m-text" style="font-size:14px; line-height:1.6;"></p>
            <p style="font-size:11px; color:#666; margin-top:30px;">(화면을 클릭하면 닫힙니다)</p>
        </div>
    </div>
    <script>
    function showCoach(name, pos, text) {{
        document.getElementById('m-name').innerText = name;
        document.getElementById('m-pos').innerText = "포지션: " + pos;
        document.getElementById('m-text').innerHTML = text;
        document.getElementById('modal').style.display = 'block';
    }}
    </script>
    """

# --- [4. 메인 탭 UI] ---
tab1, tab2, tab3 = st.tabs(["📝 로스터 관리", "🏟️ 스쿼드 짜기 및 수정", "📈 경기 일지 및 AI 분석"])

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
        
        if st.button("🚀 AI 1차 스쿼드 자동 생성"):
            players_data = parse_players(today_players)
            res, updated = generate_squads(players_data, num_q, forms, tactics_form)
            # 세션 상태에 저장하여 수동 수정 시에도 날아가지 않도록 고정
            st.session_state.ai_squads = res
            st.session_state.players_data = players_data
            st.session_state.today_names = [p["name"] for p in players_data]

    with col_r:
        if 'ai_squads' in st.session_state and st.session_state.ai_squads:
            board_cols = st.columns(2)
            for i in range(num_q):
                with board_cols[i % 2]:
                    st.markdown(f"### 🎯 {i+1}Q ({forms[i]})")
                    
                    # 수동 조정 UI (Expander 내부에 배치)
                    with st.expander("⚙️ 포지션 수동 조정 (클릭)"):
                        st.caption("원하는 선수를 직접 골라 배치하세요. 선발명단 외의 선수는 자동으로 벤치로 이동합니다.")
                        new_fw = st.multiselect("FW 공격수", st.session_state.today_names, default=st.session_state.ai_squads[i]["FW"], key=f"fw_edit_{i}")
                        new_mf = st.multiselect("MF 미드필더", st.session_state.today_names, default=st.session_state.ai_squads[i]["MF"], key=f"mf_edit_{i}")
                        new_df = st.multiselect("DF 수비수", st.session_state.today_names, default=st.session_state.ai_squads[i]["DF"], key=f"df_edit_{i}")
                        new_gk = st.multiselect("GK 골키퍼", st.session_state.today_names, default=st.session_state.ai_squads[i]["GK"], key=f"gk_edit_{i}")
                    
                    # 수동 조정된 데이터로 현재 스쿼드 구성
                    current_squad = {"FW": new_fw, "MF": new_mf, "DF": new_df, "GK": new_gk}
                    assigned_players = set(new_fw + new_mf + new_df + new_gk)
                    current_bench = [name for name in st.session_state.today_names if name not in assigned_players]
                    
                    # 렌더링 (팝업 기능 포함)
                    st.components.v1.html(render_interactive_pitch(current_squad, forms[i]), height=470)
                    
                    # 벤치 표시
                    st.info(f"🔄 **교체 대기:** {', '.join(current_bench) if current_bench else '없음'}")

# --- [5. 매치 로그 및 AI 분석 탭 (V11과 동일)] ---
with tab3:
    st.header("📈 경기 기록 & AI 코치 분석")
    with st.expander("➕ 새 경기 기록하기", expanded=False):
        with st.form("match_form"):
            m_date = st.date_input("경기 날짜", datetime.date.today())
            m_opp = st.text_input("상대팀 이름")
            c1, c2, c3 = st.columns(3)
            with c1: m_res = st.selectbox("결과", ["승리", "무승부", "패배"])
            with c2: m_score = st.text_input("스코어 (예: 3-1)", "0-0")
            with c3: m_form = st.selectbox("메인 포메이션", list(tactics_form.keys()))
            m_video = st.text_input("경기 영상/하이라이트 링크")
            m_memo = st.text_area("감독의 짧은 메모 (우리 팀의 문제점이나 잘한 점을 적어주시면 AI가 참고합니다)")
            submit_match = st.form_submit_button("기록 저장하기")
            if submit_match:
                old_df = load_match_log()
                new_row = pd.DataFrame([{"Date": str(m_date), "Opponent": m_opp, "Result": m_res, "Score": m_score, "Formation": m_form, "VideoLink": m_video, "AI_Feedback": m_memo}])
                updated_df = pd.concat([old_df, new_row], ignore_index=True)
                conn.update(worksheet="MatchLog", data=updated_df)
                st.success("✅ 경기 기록이 클라우드에 저장되었습니다!")
                st.rerun()

    st.divider()
    match_df = load_match_log()
    if not match_df.empty:
        for index, row in match_df[::-1].iterrows(): 
            with st.container():
                rc1, rc2 = st.columns([3, 1])
                with rc1:
                    res_emoji = "🔥" if row['Result'] == "승리" else "🤝" if row['Result'] == "무승부" else "💔"
                    st.subheader(f"{res_emoji} {row['Date']} vs {row['Opponent']} ({row['Score']})")
                    if row['VideoLink']: st.markdown(f"[▶️ 경기 영상 보러가기]({row['VideoLink']})")
                with rc2:
                    if st.button("🤖 AI 심층 전술 피드백", key=f"ai_btn_{index}"):
                        if ai_model is None:
                            st.error("API 키가 설정되지 않았습니다.")
                        else:
                            with st.spinner("AI가 분석 중입니다..."):
                                prompt = f"당신은 세계 최고의 축구 전술가입니다. 대학 축구팀 '{st.session_state.team_name}'의 경기 결과를 바탕으로 피드백을 주세요. 상대팀: {row['Opponent']}, 결과: {row['Result']}({row['Score']}), 포메이션: {row['Formation']}, 메모: {row['AI_Feedback']}. 잘한 점, 보완점, 유명 감독의 철학 인용, 다음 경기를 위한 3줄 요약을 포함해 열정적인 어조로 작성해주세요."
                                try:
                                    response = ai_model.generate_content(prompt)
                                    st.markdown(f"> **AI 전술 코치의 리포트**\n\n{response.text}")
                                except Exception as e: st.error(f"오류가 발생했습니다: {e}")
            st.write("---")
