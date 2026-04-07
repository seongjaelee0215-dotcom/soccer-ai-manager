import streamlit as st
import pandas as pd
import re
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import datetime

st.set_page_config(page_title="AI Tactical Master", layout="wide", initial_sidebar_state="expanded")

# ═══════════════════════════════════════════════════════════════
# [0] Gemini AI 설정
# ═══════════════════════════════════════════════════════════════
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
    AI_AVAILABLE = True
except:
    ai_model = None
    AI_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════
# [1] 구글 시트 & 세션 상태
# ═══════════════════════════════════════════════════════════════
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
        return pd.DataFrame(columns=["Date","Opponent","Result","Score","Formation","VideoLink","AI_Feedback"])

if 'roster' not in st.session_state:
    st.session_state.roster = load_data()
if 'settings' not in st.session_state:
    saved = load_settings()
    st.session_state.team_name   = saved.get('team_name',   '홍익대학교 경영학부 팀 EINS')
    st.session_state.color_outer = saved.get('color_outer', '#D8BFD8')
    st.session_state.color_inner = saved.get('color_inner', '#000080')
    st.session_state.logo_url    = saved.get('logo_url',    '')

# ═══════════════════════════════════════════════════════════════
# [2] 사이드바 & 동적 CSS
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ 구단 커스텀 설정")
    input_team_name  = st.text_input("팀명",     st.session_state.team_name)
    input_logo_url   = st.text_input("로고 URL", st.session_state.logo_url)
    col1, col2 = st.columns(2)
    with col1: input_color_outer = st.color_picker("바깥 줄무늬", st.session_state.color_outer)
    with col2: input_color_inner = st.color_picker("안쪽 줄무늬", st.session_state.color_inner)

    if st.button("💾 디자인 영구 저장"):
        st.session_state.team_name   = input_team_name
        st.session_state.logo_url    = input_logo_url
        st.session_state.color_outer = input_color_outer
        st.session_state.color_inner = input_color_inner
        settings_df = pd.DataFrame({
            'setting_name':  ['team_name','logo_url','color_outer','color_inner'],
            'setting_value': [input_team_name, input_logo_url, input_color_outer, input_color_inner]
        })
        conn.update(worksheet="Settings", data=settings_df)
        st.success("저장 완료!")

    st.divider()
    st.caption("🤖 AI 코치 상태")
    if AI_AVAILABLE:
        st.success("Gemini 연결됨", icon="✅")
    else:
        st.error("API 키 확인 필요", icon="❌")

st.markdown(f"""
<style>
    .stApp {{
        background: linear-gradient(to right,
            {st.session_state.color_outer} 0%,  {st.session_state.color_outer} 3%,
            {st.session_state.color_inner} 3%,  {st.session_state.color_inner} 6%,
            #ffffff 6%, #ffffff 94%,
            {st.session_state.color_inner} 94%, {st.session_state.color_inner} 97%,
            {st.session_state.color_outer} 97%, {st.session_state.color_outer} 100%);
    }}
    .block-container {{
        background-color: rgba(255,255,255,0.88) !important;
        backdrop-filter: blur(4px);
        border-radius: 15px;
        padding: 2rem !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-top: 2rem;
    }}
    div.stButton > button:first-child {{
        background-color: {st.session_state.color_inner};
        color: white; border-radius: 10px; border: none;
    }}
    section[data-testid="stSidebar"] div.stButton > button:first-child {{
        background-color: #2E8B57; width: 100%;
    }}
    /* AI 리포트 카드 */
    .ai-card {{
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid {st.session_state.color_inner};
        border-radius: 12px;
        padding: 20px;
        color: white;
        margin-top: 10px;
    }}
    .ai-section-title {{
        color: {st.session_state.color_outer};
        font-weight: bold;
        font-size: 15px;
        border-bottom: 1px solid rgba(255,255,255,0.2);
        padding-bottom: 6px;
        margin-bottom: 10px;
    }}
    /* 통계 배지 */
    .stat-badge {{
        display:inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: bold;
        margin: 2px;
    }}
</style>
""", unsafe_allow_html=True)

# 헤더
header_col1, header_col2 = st.columns([1, 8])
with header_col1:
    if st.session_state.logo_url:
        try:    st.image(st.session_state.logo_url, use_container_width=True)
        except: st.markdown("⚽")
with header_col2:
    st.title(st.session_state.team_name)
st.divider()

# ═══════════════════════════════════════════════════════════════
# [3] 전술 데이터베이스 & 알고리즘
# ═══════════════════════════════════════════════════════════════
# 각 포메이션·포지션별 코치 지시사항 (공격/수비 분리)
coach_voice_db = {
    "4-4-2": {
        "FW": "⚔️ <b>[공격]</b> 두 스트라이커의 역할 분담이 핵심입니다. 한 명은 포스트 플레이로 공을 받고, 다른 한 명은 뒷공간 침투를 노리세요. 항상 상대 센터백 사이 간격을 벌려두세요.<br>🛡️ <b>[수비]</b> 전방 압박의 시작점! 상대 수비형 미드필더의 패스 길목을 적극 차단하고, 두 명이 함께 몰아붙이는 '더블 프레스'를 적극 활용하세요.",
        "MF": "⚔️ <b>[공격]</b> 좌우 윙어는 터치라인 근처로 넓게 벌려 상대 수비를 분산시키고, 중앙 두 명은 빠른 원터치 패스로 공을 전방으로 연결하세요.<br>🛡️ <b>[수비]</b> 두 줄(4-4) 수비 블록의 핵심! FW와의 간격 15m, DF와의 간격 15m를 유지하며 콤팩트한 수비 블록을 형성하세요.",
        "DF": "⚔️ <b>[공격]</b> 사이드백은 적극적인 오버래핑으로 윙어와 2:1 상황을 만드세요. 센터백은 정확한 롱패스로 FW에게 직접 연결하는 '롱킥 빌드업'도 활용하세요.<br>🛡️ <b>[수비]</b> 오프사이드 트랩 타이밍이 중요합니다. 주장 또는 지정된 선수의 신호에 맞춰 일사불란하게 라인을 올리세요.",
        "GK": "🧤 <b>[코치 지시]</b> 페널티박스 내 공중볼은 두려움 없이 장악하세요. 수비 라인이 낮을 때는 짧은 패스, 라인이 높을 때는 빠른 롱킥으로 전환을 유도하세요."
    },
    "4-3-3": {
        "FW": "⚔️ <b>[공격]</b> 윙 포워드는 안쪽으로 파고드는 '컷인'으로 슈팅 기회를 만드세요. 센터 FW는 뒤로 내려와 미드필더와 연결고리 역할을 하며 '하프스페이스'를 공략하세요.<br>🛡️ <b>[수비]</b> 3명이 상대 수비를 동시에 압박하는 '프론트3 하이프레스'! 상대 빌드업의 시작 자체를 끊어내는 것이 목표입니다.",
        "MF": "⚔️ <b>[공격]</b> 삼각형 포지션을 항상 유지하며 '패스 앤 무브'를 반복하세요. 공을 주고 나서 바로 움직여 받을 공간을 직접 만드는 것이 핵심입니다.<br>🛡️ <b>[수비]</b> 공을 잃는 순간 3초 안에 즉각 재압박! '게겐프레싱'으로 상대의 역습 루트 자체를 차단하세요. 단 한 명도 멍하니 있으면 안 됩니다.",
        "DF": "⚔️ <b>[공격]</b> 풀백은 이 전술의 숨겨진 핵심 병기입니다. 윙어가 안으로 파고들 때, 풀백은 비어있는 사이드 공간을 과감하게 오버래핑하세요.<br>🛡️ <b>[수비]</b> 풀백이 올라간 뒤 생기는 뒷공간은 반대편 센터백이 커버해야 합니다. '스위칭 커버링'을 항상 염두에 두세요.",
        "GK": "🧤 <b>[코치 지시]</b> 높은 수비 라인을 보조하는 '스위퍼 키퍼'가 되어야 합니다. 페널티박스 밖으로 나와 뒷공간 처리를 적극적으로 하고, 발로 빌드업에 참여하는 것도 중요합니다."
    },
    "4-2-3-1": {
        "FW": "⚔️ <b>[공격]</b> 혼자서 상대 수비 2명을 상대하는 타겟맨의 역할입니다. 공중볼 경합과 등지기 플레이로 2선 미드필더들이 올라올 시간을 벌어주는 것이 첫 번째 임무입니다.<br>🛡️ <b>[수비]</b> 상대 센터백이 공을 잡으면 즉시 압박해 빌드업을 방해하세요. 불필요하게 체력을 소모하지 말고 '스마트한 압박'을 하세요.",
        "MF": "⚔️ <b>[공격]</b> 더블 볼란치(2명의 수비형 미드필더)는 안전한 빌드업의 기점입니다. 2선의 공격형 미드필더 3명은 자유롭게 움직이며 킬패스와 슈팅 찬스를 노리세요.<br>🛡️ <b>[수비]</b> 더블 볼란치가 중원을 완벽하게 장악하는 것이 이 전술의 핵심입니다. 공격 전환 시에는 2선 3명이 즉시 내려와 5미드필더처럼 수비하세요.",
        "DF": "⚔️ <b>[공격]</b> 측면 사이드백은 '언더래핑(윙어 안쪽으로 파고들기)'을 시도해 상대 수비를 혼란에 빠뜨리세요.<br>🛡️ <b>[수비]</b> 사이드백이 올라갔을 때 생기는 '하프스페이스'는 반드시 센터백과 볼란치가 협력해서 커버해야 합니다.",
        "GK": "🧤 <b>[코치 지시]</b> 더블 볼란치와 끊임없이 소통하세요. 짧은 패스 배급으로 후방 빌드업에 적극 참여하고, 위험 지역의 크로스볼은 과감하게 걷어내세요."
    },
    "5-2-3": {
        "FW": "⚔️ <b>[공격]</b> 3명의 공격수는 좌-중-우 넓게 벌려 상대 5백을 분산시키세요. 윙백의 오버래핑 타이밍에 맞춰 스위칭 플레이로 상대 수비를 무너뜨리세요.<br>🛡️ <b>[수비]</b> 역습 상황을 항상 대비하세요. 공을 잃는 순간 최소 1명의 FW는 즉시 역습 저지를 위해 미드필더 라인 쪽으로 이동하세요.",
        "MF": "⚔️ <b>[공격]</b> 미드필더 2명은 전방으로 빠른 전환 패스에 집중하세요. 기회가 생기면 과감하게 전진해 공격에 가담하되, 뒷공간 관리를 잊지 마세요.<br>🛡️ <b>[수비]</b> 미드필더가 2명 뿐이라 공간이 넓습니다. '공간 점유'와 '위치 선정'이 매우 중요합니다. 무분별하게 따라가지 말고 지역 방어를 하세요.",
        "DF": "⚔️ <b>[공격]</b> 윙백은 이 전술의 공격 엔진입니다! 과감하게 전진해 상대 진영 깊숙이 파고들고 크로스와 슈팅을 시도하세요. 윙백이 적극적일수록 팀 공격이 살아납니다.<br>🛡️ <b>[수비]</b> 스위퍼 역할의 중앙 센터백이 최종 라인을 컨트롤합니다. 5명이 촘촘한 수비 블록을 형성해 상대 공격의 중앙 침투를 원천 봉쇄하세요.",
        "GK": "🧤 <b>[코치 지시]</b> 역습이 이 전술의 핵심 무기입니다. 공을 잡는 순간 빠른 핸드 스로인 또는 롱킥으로 즉시 역습의 기점이 되어주세요."
    }
}

tactics_form = {
    "4-4-2":  {"form": {"FW":2, "MF":4, "DF":4, "GK":1}},
    "4-3-3":  {"form": {"FW":3, "MF":3, "DF":4, "GK":1}},
    "4-2-3-1":{"form": {"FW":1, "MF":5, "DF":4, "GK":1}},
    "5-2-3":  {"form": {"FW":3, "MF":2, "DF":5, "GK":1}},
}

# ─── 파싱 & 배정 로직 ────────────────────────────────────────
def parse_players(player_list):
    text = ", ".join(player_list)
    return [
        {"name": m[0].strip(), "pos1": m[1], "pos2": m[2] if m[2] else None,
         "total": 0, "p1_count": 0}
        for m in re.findall(r"([가-힣a-zA-Z0-9\s]+)\(([A-Z]+)(?:/([A-Z]+))?\)", text)
    ]

def can_play(player_pos, target_broad_pos):
    if not player_pos: return False
    if player_pos == "FR" and target_broad_pos != "GK": return True
    mapping = {
        "FW": ["FW","ST","LW","RW","AMF"],
        "MF": ["MF","CM","CDM","AMF","RW","LW"],
        "DF": ["DF","CB","RB","LB"],
        "GK": ["GK"],
    }
    return player_pos in mapping.get(target_broad_pos, [])

def generate_squads(players, quarters, formations_selected, tactics):
    for p in players:
        p["field_play_count"] = 0
        p["gk_play_count"]    = 0
        p["history"]          = []

    all_squads = []
    for q in range(quarters):
        form_name = formations_selected[q]
        formation = tactics[form_name]["form"]
        sq = {"FW": [], "MF": [], "DF": [], "GK": []}
        selected_in_q = set()

        # STEP 1: 전문 GK 우선 배정
        for p in players:
            if len(sq["GK"]) >= formation.get("GK", 1): break
            if (p["pos1"] == "GK" or p["pos2"] == "GK") and p["name"] not in selected_in_q:
                sq["GK"].append(p["name"])
                selected_in_q.add(p["name"])
                p["gk_play_count"] += 1
                p["history"].append(q)

        # STEP 2: 필드 포지션 배정
        for t_pos in ["FW", "MF", "DF"]:
            limit = formation.get(t_pos, 0)
            while len(sq[t_pos]) < limit:
                best_candidate, best_score = None, -9999
                for p in players:
                    if p["name"] in selected_in_q: continue
                    score = 0
                    if p["pos1"] == "GK": score -= 300
                    if   can_play(p["pos1"], t_pos): score += 100
                    elif can_play(p["pos2"], t_pos): score += 50
                    f = p["field_play_count"]
                    if   f < 2:  score += 500
                    elif f == 2: score += 100
                    else:        score -= 1000
                    if q > 0 and (q-1) not in p["history"]:
                        score += 250
                        if q > 1 and (q-2) not in p["history"]: score += 500
                    if score > best_score:
                        best_score, best_candidate = score, p
                if best_candidate:
                    sq[t_pos].append(best_candidate["name"])
                    selected_in_q.add(best_candidate["name"])
                    best_candidate["field_play_count"] += 1
                    best_candidate["history"].append(q)
                else: break

        # STEP 3: GK 공백 시 임시 키퍼
        while len(sq["GK"]) < formation.get("GK", 1):
            best_volunteer, min_fp = None, 999
            for p in players:
                if p["name"] not in selected_in_q and p["field_play_count"] < min_fp:
                    min_fp, best_volunteer = p["field_play_count"], p
            if best_volunteer:
                sq["GK"].append(best_volunteer["name"])
                selected_in_q.add(best_volunteer["name"])
                best_volunteer["gk_play_count"] += 1
                best_volunteer["history"].append(q)
            else: break

        all_squads.append(sq)

    for p in players:
        p["total"]    = p["field_play_count"]
        p["p1_count"] = p["gk_play_count"]
    return all_squads, players

# ─── 피치 렌더러 ─────────────────────────────────────────────
def render_interactive_pitch(squad, form_name):
    y_map   = {"FW": "15%", "MF": "42%", "DF": "72%", "GK": "90%"}
    pos_label = {"FW": "공격수", "MF": "미드필더", "DF": "수비수", "GK": "골키퍼"}
    coach_data = coach_voice_db.get(form_name, coach_voice_db["4-4-2"])
    player_html = ""
    for pos, names in squad.items():
        if not names: continue
        instruction = coach_data.get(pos, "감독 지시에 따르세요.")
        for i, name in enumerate(names):
            x = (100 / (len(names) + 1)) * (i + 1)
            color = {"FW":"#FF6B6B","MF":"#4ECDC4","DF":"#45B7D1","GK":"#96CEB4"}.get(pos, "white")
            player_html += f"""
            <div onclick="showCoach('{name}', '{pos_label[pos]}', `{instruction}`)"
                 style="position:absolute; top:{y_map[pos]}; left:{x}%;
                        transform:translate(-50%,-50%); text-align:center;
                        cursor:pointer; z-index:5; transition:transform 0.15s;">
                <div style="width:24px; height:24px; background:{color};
                            border:2px solid white; border-radius:50%;
                            margin:0 auto; box-shadow:0 2px 8px rgba(0,0,0,0.6);"></div>
                <div style="color:white; font-size:11px; font-weight:bold;
                            margin-top:3px; white-space:nowrap;
                            text-shadow:1px 1px 3px black;">{name}</div>
            </div>"""

    return f"""
    <div style="background:linear-gradient(180deg,#2E8B57 0%,#1a5c35 100%);
                width:100%; max-width:350px; height:460px;
                position:relative; border:3px solid white; border-radius:15px;
                overflow:hidden; font-family:sans-serif; margin:0 auto;
                box-shadow:0 8px 20px rgba(0,0,0,0.3);">
        <!-- 필드 라인 -->
        <div style="position:absolute;top:50%;width:100%;height:1px;background:rgba(255,255,255,0.4);"></div>
        <div style="position:absolute;top:50%;left:50%;width:70px;height:70px;
                    border:1px solid rgba(255,255,255,0.4);border-radius:50%;
                    transform:translate(-50%,-50%);"></div>
        <div style="position:absolute;top:0;left:25%;width:50%;height:18%;
                    border:1px solid rgba(255,255,255,0.3);border-top:none;box-sizing:border-box;"></div>
        <div style="position:absolute;bottom:0;left:25%;width:50%;height:18%;
                    border:1px solid rgba(255,255,255,0.3);border-bottom:none;box-sizing:border-box;"></div>
        <!-- 포메이션 라벨 -->
        <div style="position:absolute;top:4px;right:8px;color:rgba(255,255,255,0.6);
                    font-size:11px;font-weight:bold;">{form_name}</div>
        {player_html}
        <!-- 코치 모달 -->
        <div id="modal" style="display:none;position:absolute;top:0;left:0;
                                width:100%;height:100%;
                                background:rgba(0,0,0,0.93);z-index:10;
                                padding:18px;color:white;box-sizing:border-box;
                                overflow-y:auto;">
            <div onclick="document.getElementById('modal').style.display='none'"
                 style="text-align:right;cursor:pointer;font-size:22px;color:#D8BFD8;">&times;</div>
            <div style="font-size:11px;color:#888;margin-bottom:4px;" id="m-pos"></div>
            <div style="font-size:16px;font-weight:bold;color:#D8BFD8;
                        margin-bottom:12px;border-bottom:1px solid #333;
                        padding-bottom:8px;" id="m-name"></div>
            <div style="font-size:13px;line-height:1.8;color:#ddd;" id="m-text"></div>
            <div style="font-size:10px;color:#555;margin-top:20px;text-align:center;">
                선수 아이콘을 탭하면 이 창이 닫힙니다</div>
        </div>
    </div>
    <script>
    function showCoach(name, pos, text) {{
        document.getElementById('m-name').innerText = name;
        document.getElementById('m-pos').innerText  = "포지션: " + pos;
        document.getElementById('m-text').innerHTML = text;
        document.getElementById('modal').style.display = 'block';
    }}
    </script>
    """

# ═══════════════════════════════════════════════════════════════
# [4] AI 헬퍼 함수
# ═══════════════════════════════════════════════════════════════
def ai_query(prompt: str) -> str:
    """Gemini API 호출 공통 헬퍼."""
    if not AI_AVAILABLE:
        return "⚠️ AI 모델을 사용할 수 없습니다. Gemini API 키를 확인해주세요."
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI 오류: {e}"

def build_match_analysis_prompt(row: pd.Series) -> str:
    return f"""당신은 20년 경력의 전문 축구 전술 코치입니다. 아래 경기 데이터를 분석해 구체적이고 실용적인 피드백을 제공하세요.

[경기 정보]
- 상대팀: {row['Opponent']}
- 결과: {row['Result']} ({row['Score']})
- 우리 포메이션: {row['Formation']}
- 감독 메모: {row['AI_Feedback']}

다음 4가지 항목으로 나눠 분석해주세요. 각 항목을 마크다운 헤더(###)로 구분하고, 각 항목마다 구체적인 전술 용어와 실전 조언을 포함하세요.

### ✅ 이번 경기 잘한 점
### ⚠️ 개선이 필요한 점
### 🎯 다음 경기 전술 포인트 (3가지)
### 💬 코치 한마디 (동기부여 메시지)

한국어로 작성하고, 각 항목을 2~4문장으로 간결하게 작성하세요."""

def build_season_analysis_prompt(match_df: pd.DataFrame) -> str:
    records = []
    for _, r in match_df.iterrows():
        records.append(f"- {r['Date']} vs {r['Opponent']}: {r['Result']} ({r['Score']}, 전술:{r['Formation']})")
    records_str = "\n".join(records)
    return f"""당신은 데이터 기반 축구 수석 코치입니다. 아래 시즌 전체 경기 기록을 분석해 종합 보고서를 작성하세요.

[시즌 경기 기록]
{records_str}

다음 항목으로 분석하세요:

### 📊 시즌 총평
### 💪 팀의 강점 패턴
### 🔧 반복되는 약점
### 🏆 남은 경기 전략 제언

한국어로 작성하고 전문적이면서도 선수들이 이해하기 쉽게 작성하세요."""

def build_formation_recommendation_prompt(players_info: list, quarters: int) -> str:
    player_summary = ", ".join(players_info)
    return f"""당신은 축구 전술 전문가입니다. 오늘 참석한 선수 명단과 포지션을 보고 {quarters}개 쿼터에 최적의 포메이션을 추천하세요.

[오늘 참석 선수]
{player_summary}

사용 가능한 포메이션: 4-4-2, 4-3-3, 4-2-3-1, 5-2-3

각 쿼터별로 추천 포메이션과 그 이유를 간략히 설명하세요. 선수 수, 포지션 분포, 전술적 밸런스를 고려하세요.

형식:
- 1쿼터: [포메이션] - [이유 1~2문장]
- 2쿼터: ...

마지막에 오늘 경기 전체 전술 키워드 3개를 제시하세요. 한국어로 답변하세요."""

# ═══════════════════════════════════════════════════════════════
# [5] 메인 탭 UI
# ═══════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs(["📝 로스터 관리", "🏟️ 스쿼드 & AI 전술", "📈 경기 일지 & AI 분석"])

# ───────────────────────────────────────────
# TAB 1: 로스터 관리
# ───────────────────────────────────────────
with tab1:
    st.subheader("👥 선수 명단 관리")
    st.caption("형식: 이름(주포지션/부포지션)  예) 손흥민(ST/LW), 이강인(AMF/RW)")
    roster_input = st.text_area(
        "전체 명단", value=", ".join(st.session_state.roster), height=200
    )

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("💾 명단 저장"):
            new_list = [p.strip() for p in roster_input.split(",") if p.strip()]
            st.session_state.roster = new_list
            conn.update(worksheet="Sheet1", data=pd.DataFrame({"player_info": new_list}))
            st.success("✅ 저장 완료!")

    # 현재 등록 선수 현황 표
    if st.session_state.roster:
        parsed = parse_players(st.session_state.roster)
        if parsed:
            st.divider()
            st.subheader("📋 등록 선수 현황")
            roster_df = pd.DataFrame([
                {"이름": p["name"], "주 포지션": p["pos1"], "부 포지션": p["pos2"] or "-"}
                for p in parsed
            ])
            st.dataframe(roster_df, use_container_width=True, hide_index=True)

# ───────────────────────────────────────────
# TAB 2: 스쿼드 & AI 전술
# ───────────────────────────────────────────
with tab2:
    col_l, col_r = st.columns([1, 2.8])

    with col_l:
        st.subheader("⚙️ 경기 설정")
        today_players = st.multiselect(
            "오늘 참석자 선택",
            options=st.session_state.roster,
            default=st.session_state.roster
        )
        num_q = st.slider("쿼터 수", 1, 6, 4)

        st.divider()
        # AI 포메이션 추천
        st.markdown("**🤖 AI 포메이션 추천**")
        if st.button("✨ AI에게 오늘 전술 물어보기", use_container_width=True):
            if not today_players:
                st.warning("참석자를 먼저 선택해주세요.")
            else:
                with st.spinner("AI 코치 분석 중..."):
                    prompt = build_formation_recommendation_prompt(today_players, num_q)
                    result = ai_query(prompt)
                st.markdown(result)

        st.divider()
        # 쿼터별 포메이션 수동 선택
        st.markdown("**📋 쿼터별 포메이션 선택**")
        forms = [
            st.selectbox(f"{i+1}쿼터 포메이션", list(tactics_form.keys()), key=f"q_{i}")
            for i in range(num_q)
        ]

        st.divider()
        if st.button("🚀 스쿼드 자동 생성", use_container_width=True):
            if not today_players:
                st.error("참석자를 선택해주세요.")
            else:
                players_data = parse_players(today_players)
                res, updated = generate_squads(players_data, num_q, forms, tactics_form)
                st.session_state.ai_squads     = res
                st.session_state.players_data  = players_data
                st.session_state.today_names   = [p["name"] for p in players_data]
                st.success("✅ 스쿼드 생성 완료!")

    with col_r:
        if 'ai_squads' in st.session_state and st.session_state.ai_squads:
            st.subheader("🏟️ 쿼터별 전술 보드")
            board_cols = st.columns(2)

            for i in range(num_q):
                with board_cols[i % 2]:
                    st.markdown(f"#### 🎯 {i+1}Q  `{forms[i]}`")

                    with st.expander("⚙️ 수동 조정"):
                        names = st.session_state.today_names
                        new_fw = st.multiselect("FW 공격수",  names, default=st.session_state.ai_squads[i]["FW"], key=f"fw_edit_{i}")
                        new_mf = st.multiselect("MF 미드필더", names, default=st.session_state.ai_squads[i]["MF"], key=f"mf_edit_{i}")
                        new_df = st.multiselect("DF 수비수",  names, default=st.session_state.ai_squads[i]["DF"], key=f"df_edit_{i}")
                        new_gk = st.multiselect("GK 골키퍼",  names, default=st.session_state.ai_squads[i]["GK"], key=f"gk_edit_{i}")

                    current_squad = {
                        "FW": st.session_state.get(f"fw_edit_{i}", st.session_state.ai_squads[i]["FW"]),
                        "MF": st.session_state.get(f"mf_edit_{i}", st.session_state.ai_squads[i]["MF"]),
                        "DF": st.session_state.get(f"df_edit_{i}", st.session_state.ai_squads[i]["DF"]),
                        "GK": st.session_state.get(f"gk_edit_{i}", st.session_state.ai_squads[i]["GK"]),
                    }
                    assigned = set(sum(current_squad.values(), []))
                    bench    = [n for n in st.session_state.today_names if n not in assigned]

                    st.components.v1.html(render_interactive_pitch(current_squad, forms[i]), height=480)
                    if bench:
                        st.info(f"🔄 교체 대기: **{', '.join(bench)}**")
                    else:
                        st.success("전원 배치 완료")

            # ── 출전 통계 ──────────────────────────────────
            st.divider()
            st.subheader("📊 실시간 출전 통계")
            stats_list = []
            for name in st.session_state.today_names:
                count = 0
                gk_count = 0
                for i in range(num_q):
                    fw = st.session_state.get(f"fw_edit_{i}", st.session_state.ai_squads[i]["FW"])
                    mf = st.session_state.get(f"mf_edit_{i}", st.session_state.ai_squads[i]["MF"])
                    df = st.session_state.get(f"df_edit_{i}", st.session_state.ai_squads[i]["DF"])
                    gk = st.session_state.get(f"gk_edit_{i}", st.session_state.ai_squads[i]["GK"])
                    if name in (fw + mf + df): count += 1
                    if name in gk:             gk_count += 1
                total_q = count + gk_count
                bar = "🟩" * total_q + "⬜" * (num_q - total_q)
                stats_list.append({
                    "선수명": name,
                    "필드": f"{count}Q",
                    "GK": f"{gk_count}Q",
                    "합계": f"{total_q}/{num_q}",
                    "출전 현황": bar,
                })
            st.dataframe(
                pd.DataFrame(stats_list),
                use_container_width=True,
                hide_index=True
            )

# ───────────────────────────────────────────
# TAB 3: 경기 일지 & AI 분석
# ───────────────────────────────────────────
with tab3:
    st.header("📈 경기 기록 & AI 코치 분석")

    # ── 새 경기 기록 ──────────────────────────
    with st.expander("➕ 새 경기 기록하기", expanded=False):
        with st.form("match_form"):
            m_date = st.date_input("경기 날짜", datetime.date.today())
            m_opp  = st.text_input("상대팀 이름")
            c1, c2, c3 = st.columns(3)
            with c1: m_res   = st.selectbox("결과", ["승리", "무승부", "패배"])
            with c2: m_score = st.text_input("스코어 (예: 3-1)", "0-0")
            with c3: m_form  = st.selectbox("포메이션", list(tactics_form.keys()))
            m_video = st.text_input("영상/하이라이트 링크")
            m_memo  = st.text_area("감독 메모 (상세할수록 AI 분석이 정확해집니다)")
            if st.form_submit_button("기록 저장하기"):
                old_df  = load_match_log()
                new_row = pd.DataFrame([{
                    "Date": str(m_date), "Opponent": m_opp,
                    "Result": m_res, "Score": m_score,
                    "Formation": m_form, "VideoLink": m_video, "AI_Feedback": m_memo
                }])
                conn.update(worksheet="MatchLog", data=pd.concat([old_df, new_row], ignore_index=True))
                st.success("✅ 저장 완료!")
                st.rerun()

    match_df = load_match_log()

    if match_df.empty:
        st.info("아직 기록된 경기가 없습니다. 위에서 첫 경기를 기록해보세요! ⚽")
    else:
        # ── 시즌 요약 카드 ──────────────────────
        st.subheader("🏆 시즌 요약")
        total = len(match_df)
        wins  = len(match_df[match_df["Result"] == "승리"])
        draws = len(match_df[match_df["Result"] == "무승부"])
        losses= len(match_df[match_df["Result"] == "패배"])
        win_rate = round(wins / total * 100) if total else 0

        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("총 경기", total)
        s2.metric("승리 🔥", wins)
        s3.metric("무승부 🤝", draws)
        s4.metric("패배 💔", losses)
        s5.metric("승률", f"{win_rate}%")

        # ── AI 시즌 종합 분석 ───────────────────
        if st.button("🤖 AI 시즌 종합 분석 보고서 생성", use_container_width=True):
            with st.spinner("AI 코치가 시즌 전체를 분석하고 있습니다..."):
                prompt = build_season_analysis_prompt(match_df)
                result = ai_query(prompt)
            st.markdown(result)

        st.divider()

        # ── 경기별 리스트 ────────────────────────
        st.subheader("📋 경기별 기록")
        for index, row in match_df[::-1].iterrows():
            res_emoji = {"승리": "🔥", "무승부": "🤝", "패배": "💔"}.get(row['Result'], "⚽")
            with st.container(border=True):
                rc1, rc2, rc3 = st.columns([3, 1, 1])
                with rc1:
                    st.markdown(
                        f"**{res_emoji} {row['Date']} vs {row['Opponent']}** &nbsp; "
                        f"`{row['Score']}` &nbsp; `{row['Formation']}`"
                    )
                    if row['AI_Feedback']:
                        st.caption(f"📝 {row['AI_Feedback'][:60]}{'...' if len(str(row['AI_Feedback'])) > 60 else ''}")
                with rc2:
                    if row.get('VideoLink'):
                        st.link_button("🎬 영상", row['VideoLink'])
                with rc3:
                    ai_btn = st.button("🤖 AI 분석", key=f"ai_btn_{index}", use_container_width=True)

                # AI 분석 결과 (버튼 클릭 시)
                if ai_btn:
                    with st.spinner("AI 코치 분석 중..."):
                        prompt = build_match_analysis_prompt(row)
                        result = ai_query(prompt)

                    # 구조화된 AI 리포트 렌더링
                    st.markdown(result)

                    # 추가: 다음 경기 상대 맞춤 질문
                    st.divider()
                    st.markdown("##### 🗣️ AI 코치에게 추가 질문하기")
                    follow_up = st.text_input(
                        "예) '상대팀 압박에 대응하는 방법은?'",
                        key=f"followup_{index}"
                    )
                    if st.button("질문 전송", key=f"followup_btn_{index}"):
                        if follow_up:
                            with st.spinner("답변 생성 중..."):
                                fq_prompt = (
                                    f"축구 전술 코치로서 다음 경기 상황({row['Opponent']} 전, {row['Formation']} 포메이션)에 대한 질문에 답하세요:\n\n"
                                    f"질문: {follow_up}\n\n한국어로 구체적이고 실용적으로 답하세요."
                                )
                                st.markdown(ai_query(fq_prompt))
