from pathlib import Path
import html
import random

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager
from datetime import datetime, timezone

# ==================== CONFIG ====================
APP_DIR = Path(__file__).parent
LOCAL_DATA_FILE = APP_DIR / "data" / "vocabulary.csv"
CSV_URL = "https://raw.githubusercontent.com/TungNH107/chinese-vocabulary/main/data/vocabulary.csv"

COLUMNS = [
    "id", "level", "hanzi", "pinyin", "han_viet", "han_viet_chars",
    "meaning_vi", "meaning_en", "word_type_vi", "word_type_en",
    "example_en", "example_en_ipa", "example_zh", "example_zh_pinyin",
    "example_vi"
]

st.set_page_config(
    page_title="Chinese Vocabulary",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==================== DATA ====================
@st.cache_data(ttl=300)
def load_data():
    if LOCAL_DATA_FILE.exists():
        df = pd.read_csv(LOCAL_DATA_FILE, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        source = "local"
    else:
        df = pd.read_csv(CSV_URL, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        source = "github"

    # Keep the new 15-column schema. Missing columns are shown as blank,
    # rather than silently mapping old English fields into Vietnamese fields.
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS].fillna("")
    df["id"] = df["id"].astype(str)
    df["level"] = df["level"].astype(str).str.strip()
    return df, source

def esc(value):
    return html.escape(str(value or "").strip())


# ==================== SUPABASE + AUTH ====================
cookies = EncryptedCookieManager(
    prefix="chinese_vocab/",
    password=st.secrets.get("COOKIE_PASSWORD", "change-this-cookie-password-in-streamlit-secrets"),
)

def supabase_config():
    cfg = st.secrets.get("supabase", {})
    return cfg.get("url"), cfg.get("anon_key")

def sb_client(access_token=None):
    url, key = supabase_config()
    if not url or not key:
        return None
    client = create_client(url, key)
    if access_token:
        client.postgrest.auth(access_token)
    return client

def auth_ui():
    st.title("📚 Chinese Vocabulary")
    st.caption("Đăng nhập để đồng bộ cài đặt và tiến độ học giữa Web và iPhone.")
    url, key = supabase_config()
    if not url or not key:
        st.error("Chưa cấu hình Supabase trong Streamlit Secrets.")
        st.code('[supabase]\\nurl = "https://YOUR_PROJECT.supabase.co"\\nanon_key = "YOUR_SUPABASE_PUBLISHABLE_KEY"\\nCOOKIE_PASSWORD = "a-long-random-secret-string"')
        st.stop()

    client = sb_client()
    tab_login, tab_signup = st.tabs(["Đăng nhập", "Tạo tài khoản"])
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Mật khẩu", type="password")
            submit = st.form_submit_button("Đăng nhập", use_container_width=True)
        if submit:
            try:
                response = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
                cookies["access_token"] = response.session.access_token
                cookies["refresh_token"] = response.session.refresh_token
                cookies["user_email"] = response.user.email or email.strip()
                cookies.save()
                st.rerun()
            except Exception as exc:
                st.error(f"Đăng nhập thất bại: {exc}")
    with tab_signup:
        with st.form("signup_form"):
            email = st.text_input("Email đăng ký", key="signup_email")
            password = st.text_input("Mật khẩu (ít nhất 8 ký tự)", type="password", key="signup_password")
            submit = st.form_submit_button("Tạo tài khoản", use_container_width=True)
        if submit:
            try:
                response = client.auth.sign_up({"email": email.strip(), "password": password})
                if response.session:
                    cookies["access_token"] = response.session.access_token
                    cookies["refresh_token"] = response.session.refresh_token
                    cookies["user_email"] = response.user.email or email.strip()
                    cookies.save()
                    st.rerun()
                else:
                    st.success("Đã tạo tài khoản. Hãy xác nhận email rồi đăng nhập.")
            except Exception as exc:
                st.error(f"Không tạo được tài khoản: {exc}")

def authenticated_client():
    if not cookies.ready():
        st.stop()
    access = cookies.get("access_token")
    refresh = cookies.get("refresh_token")
    if not access:
        auth_ui()
        st.stop()

    client = sb_client()
    try:
        refreshed = client.auth.set_session(access, refresh)
        if refreshed and refreshed.session:
            access = refreshed.session.access_token
            cookies["access_token"] = access
            cookies["refresh_token"] = refreshed.session.refresh_token
            cookies.save()
        client.postgrest.auth(access)
        user = client.auth.get_user(access).user
        return client, user
    except Exception:
        cookies["access_token"] = ""
        cookies["refresh_token"] = ""
        cookies["user_email"] = ""
        cookies.save()
        auth_ui()
        st.stop()

def sign_out():
    for key in ["access_token", "refresh_token", "user_email"]:
        cookies[key] = ""
    cookies.save()
    st.rerun()

def load_settings(client, user_id):
    result = client.table("user_settings").select("*").eq("user_id", user_id).limit(1).execute()
    if result.data:
        return result.data[0]
    payload = {
        "user_id": user_id,
        "level": "HSK 1",
        "random_mode": True,
        "interval_minutes": 10,
        "current_word_id": None,
        "seen_ids": [],
        "next_change_at": None,
    }
    return client.table("user_settings").insert(payload).execute().data[0]

def save_settings(client, user_id, values):
    values = {**values, "updated_at": datetime.now(timezone.utc).isoformat()}
    client.table("user_settings").update(values).eq("user_id", user_id).execute()

def load_progress(client, user_id):
    result = client.table("word_progress").select("*").eq("user_id", user_id).execute()
    return {str(row["word_id"]): row for row in (result.data or [])}

def save_progress(client, user_id, word_id, **values):
    payload = {
        "user_id": user_id,
        "word_id": str(word_id),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **values,
    }
    client.table("word_progress").upsert(payload, on_conflict="user_id,word_id").execute()

def init_state(settings, progress):
    st.session_state.level = settings.get("level") or "HSK 1"
    st.session_state.random_mode = bool(settings.get("random_mode", True))
    st.session_state.interval = int(settings.get("interval_minutes", 10))
    st.session_state.current_id = str(settings.get("current_word_id") or "") or None
    st.session_state.seen_ids = [str(x) for x in (settings.get("seen_ids") or [])]
    st.session_state.favorites = [wid for wid, p in progress.items() if p.get("is_favorite")]
    st.session_state.known_ids = [wid for wid, p in progress.items() if p.get("is_known")]

def persist_settings(client, user_id):
    save_settings(client, user_id, {
        "level": st.session_state.level,
        "random_mode": bool(st.session_state.random_mode),
        "interval_minutes": int(st.session_state.interval),
        "current_word_id": st.session_state.current_id,
        "seen_ids": st.session_state.seen_ids,
    })

def choose_next(words, client=None, user_id=None):
    if words.empty:
        st.session_state.current_id = None
        return
    ids = words["id"].astype(str).tolist()
    seen = set(st.session_state.seen_ids)
    unseen = [x for x in ids if x not in seen]
    if not unseen:
        seen = set()
        unseen = ids
    selected = random.choice(unseen) if st.session_state.random_mode else unseen[0]
    st.session_state.current_id = str(selected)
    st.session_state.seen_ids = list(seen | {str(selected)})
    if client and user_id:
        persist_settings(client, user_id)
        save_settings(client, user_id, {
            "next_change_at": datetime.now(timezone.utc).timestamp() + int(st.session_state.interval) * 60
        })

def get_current(words, client=None, user_id=None):
    ids = words["id"].astype(str).tolist()
    if st.session_state.current_id is None or str(st.session_state.current_id) not in ids:
        choose_next(words, client, user_id)
    row = words[words["id"].astype(str) == str(st.session_state.current_id)]
    return None if row.empty else row.iloc[0]

# ==================== STYLE ====================
def add_css():
    st.markdown("""
    <style>
    .stApp {
        background:
          radial-gradient(circle at 8% 8%, rgba(49,112,220,.28), transparent 28%),
          radial-gradient(circle at 92% 92%, rgba(37,89,154,.24), transparent 30%),
          #f4f7fc;
    }
    .block-container {max-width: 1180px; padding-top: .8rem; padding-bottom: 1.5rem;}
    [data-testid="stHeader"] {background: transparent;}
    .study-card {
        display:grid;
        grid-template-columns: minmax(0, .92fr) minmax(0, 1.08fr);
        gap: 14px;
        background: rgba(255,255,255,.97);
        border: 1px solid rgba(210,220,236,.8);
        border-radius: 22px;
        padding: 16px;
        box-shadow: 0 12px 32px rgba(25,55,100,.11);
        color:#101827;
        height: 420px;
        min-height: 420px;
        max-height: 420px;
        box-sizing: border-box;
        overflow: hidden;
    }
    .left-col { min-width:0; overflow:hidden;
        padding: 4px 22px 4px 4px;
        border-right: 2px solid #dce5f3;
        display:flex; flex-direction:column; justify-content:center;
    }
    .right-col {display:flex; min-width:0; min-height:0; flex-direction:column; gap:12px; justify-content:center; overflow:hidden;}
    .topline {display:flex; align-items:center; gap:14px; margin-bottom:22px; flex-wrap:wrap;}
    .level-pill {background:#1264ed; color:white; padding:10px 20px; border-radius:28px; font-size:16px; font-weight:800;}
    .counter {font-size:16px; font-weight:800; color:#15233c;}
    .heart {margin-left:auto; color:#ed3345; font-size:24px; background:#fff0f3; border-radius:50%; padding:8px 15px;}
    .hanzi {font-size:clamp(52px, 5.5vw, 76px); line-height:1.12; font-weight:800; text-align:center; margin:5px 0 6px; color:#101010; overflow-wrap:anywhere;}
    .pinyin {font-size:clamp(21px, 2.2vw, 28px); color:#1671ee; font-weight:800; text-align:center; margin:0 0 10px;}
    .sound {display:inline-block; color:#1264ed; background:#e5efff; border-radius:50%; padding:8px 13px; font-size:18px; vertical-align:middle; margin-left:10px;}
    .info-pill {border-radius:22px; padding:7px 11px; margin:4px 0; font-size:14px; text-align:center; overflow:hidden;}
    .hanviet {background:#e5efff;}
    .meaning {background:#fff2d9;}
    .example-vi {background:#f0eaff; font-size:13px; font-style:italic; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;}
    .info-label {color:#1264ed; font-weight:800; margin-right:12px;}
    .lang-panel {border-radius:22px; padding:14px 16px; height:176px; min-height:176px; max-height:176px; box-sizing:border-box; display:flex; flex-direction:column; justify-content:center; overflow:hidden;}
    .english {background:linear-gradient(120deg,#edf4ff,#e4edff);}
    .vietnamese {background:linear-gradient(120deg,#fff0f5,#fde5ef);}
    .lang-head {display:flex; align-items:center; gap:18px; flex-wrap:wrap; margin-bottom:12px;}
    .lang-tag {color:white; font-weight:900; font-size:18px; border-radius:15px; padding:8px 17px;}
    .en-tag {background:#1264ed;}
    .vi-tag {background:#ed2638;}
    .gloss {font-size:clamp(18px,2vw,25px); font-weight:850; color:#101827; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
    .part {font-size:15px; font-style:italic; color:#28364d;}
    .quote {font-size:clamp(14px,1.45vw,18px); line-height:1.4; font-style:italic; color:#10264e; padding:5px 0 5px 13px; border-left:5px solid #1264ed; margin:4px 0 6px; min-height:2.8em; max-height:2.8em; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow-wrap:anywhere;}
    .vietnamese .quote {border-left-color:#ed2638; font-style:normal;}
    .meta {display:inline-block; background:rgba(255,255,255,.62); border-radius:20px; padding:6px 11px; font-size:13px; color:#172b4d; margin-top:3px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
    .meta b {margin-right:10px;}
    @media(max-width:760px) {
      .study-card {grid-template-columns:1fr; padding:18px; gap:15px;}
      .left-col { min-width:0; overflow:hidden;border-right:0; border-bottom:2px solid #dce5f3; padding:0 0 18px;}
      .right-col {gap:12px;}
      .lang-panel {min-height:150px; padding:18px;}
      .hanzi {font-size:66px;}
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== RENDER ====================
def render_card(w, words):
    level_words = words[words["level"] == w["level"]].reset_index(drop=True)
    positions = level_words.index[level_words["id"] == w["id"]].tolist()
    position = positions[0] + 1 if positions else 1
    total = len(level_words)
    favorite = w["id"] in st.session_state.favorites
    heart = "♥" if favorite else "♡"

    card = f"""
    <div class="study-card">
      <div class="left-col">
        <div class="topline">
          <span class="level-pill">{esc(w['level'])}</span>
          <span class="counter">{position} / {total}</span>
          <span class="heart">{heart}</span>
        </div>
        <div class="hanzi">{esc(w['hanzi'])}</div>
        <div class="pinyin">{esc(w['pinyin'])}<span class="sound">🔊</span></div>
        <div class="info-pill hanviet"><span class="info-label">Hán Việt:</span><b>{esc(w['han_viet'])}</b></div>
        <div class="info-pill meaning"><span class="info-label">Nghĩa:</span><b>{esc(w['meaning_vi'])}</b></div>
        <div class="info-pill example-vi"><span class="info-label">Ví dụ:</span>{esc(w['example_vi'])}</div>
      </div>
      <div class="right-col">
        <div class="lang-panel english">
          <div class="lang-head">
            <span class="lang-tag en-tag">EN</span>
            <span class="gloss">{esc(w['meaning_en'])}</span>
            <span class="part">({esc(w['word_type_en'])})</span>
          </div>
          <div class="quote">“{esc(w['example_en'])}”</div>
          <div class="meta"><b>IPA:</b> {esc(w['example_en_ipa'])}</div>
        </div>
        <div class="lang-panel vietnamese">
          <div class="lang-head">
            <span class="lang-tag vi-tag">VI</span>
            <span class="gloss">{esc(w['meaning_vi'])}</span>
            <span class="part">({esc(w['word_type_vi'])})</span>
          </div>
          <div class="quote">“{esc(w['example_zh'])}”</div>
          <div class="meta"><b>Pinyin:</b> {esc(w['example_zh_pinyin'])}</div>
        </div>
      </div>
    </div>
    """
    st.markdown(card, unsafe_allow_html=True)


def main():
    if not cookies.ready():
        st.stop()
    client, user = authenticated_client()
    user_id = str(user.id)

    try:
        df, source = load_data()
        settings = load_settings(client, user_id)
        progress = load_progress(client, user_id)
    except Exception as exc:
        st.error("Không tải được dữ liệu đồng bộ từ Supabase.")
        st.code(str(exc))
        st.info("Kiểm tra SQL schema, Supabase URL và Publishable Key trong Streamlit Secrets.")
        st.stop()

    init_state(settings, progress)
    add_css()

    st.markdown("<h2 style='text-align:center;color:#152c4d;margin-bottom:0'>📚 CHINESE VOCABULARY</h2>", unsafe_allow_html=True)
    st.caption(f"Xin chào {user.email or ''} · Web và iPhone dùng chung dữ liệu học.")

    with st.sidebar:
        st.subheader("Tài khoản")
        st.write(user.email or "")
        if st.button("Đăng xuất"):
            sign_out()

    if df.empty:
        st.warning("File từ vựng chưa có dữ liệu.")
        st.stop()

    levels = sorted(df["level"].dropna().unique().tolist(),
                    key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 999)
    if st.session_state.level not in levels:
        st.session_state.level = levels[0]
        persist_settings(client, user_id)

    nav1, nav2, nav3, nav4 = st.columns([1.3, 1, 1, 1])
    with nav1:
        selected_level = st.selectbox("Cấp độ", levels, index=levels.index(st.session_state.level), key="level_select")
    with nav2:
        page = st.selectbox("Chức năng", ["Học từ", "Danh sách", "Yêu thích", "Cài đặt"])
    with nav3:
        st.caption(f"Tổng dữ liệu: {len(df)} từ")
    with nav4:
        st.caption(f"Nguồn: {'GitHub' if source == 'github' else 'Repository'}")

    if selected_level != st.session_state.level:
        st.session_state.level = selected_level
        st.session_state.current_id = None
        st.session_state.seen_ids = []
        persist_settings(client, user_id)

    words = df[df["level"] == st.session_state.level].reset_index(drop=True)

    if page == "Học từ":
        try:
            count = st_autorefresh(interval=int(st.session_state.interval) * 60 * 1000, key="vocab_auto_refresh")
        except Exception:
            count = 0
        due = settings.get("next_change_at")
        now = datetime.now(timezone.utc).timestamp()
        if due and float(due) <= now and count > 0:
            choose_next(words, client, user_id)

        current = get_current(words, client, user_id)
        if current is None:
            st.warning("Không tìm thấy từ phù hợp.")
            return

        render_card(current, words)
        a, b, c = st.columns(3)
        is_fav = bool(progress.get(str(current["id"]), {}).get("is_favorite"))
        is_known = bool(progress.get(str(current["id"]), {}).get("is_known"))
        with a:
            if st.button("♥ Bỏ yêu thích" if is_fav else "♡ Yêu thích", use_container_width=True):
                save_progress(client, user_id, current["id"], is_favorite=not is_fav, is_known=is_known)
                st.rerun()
        with b:
            if st.button("✓ Đã thuộc" if not is_known else "✓ Đã thuộc", use_container_width=True):
                save_progress(client, user_id, current["id"], is_favorite=is_fav, is_known=True)
                choose_next(words, client, user_id)
                st.rerun()
        with c:
            if st.button("Từ tiếp theo ➜", use_container_width=True):
                choose_next(words, client, user_id)
                st.rerun()

        progress = load_progress(client, user_id)
        known = sum(1 for wid, p in progress.items() if p.get("is_known") and wid in set(words["id"].astype(str)))
        st.progress(known / len(words) if len(words) else 0)
        st.caption(f"Đã thuộc {known}/{len(words)} từ {st.session_state.level}. Tự đổi từ sau {st.session_state.interval} phút khi trang đang mở.")

    elif page == "Danh sách":
        query = st.text_input("Tìm chữ Hán, Pinyin, Hán Việt hoặc nghĩa")
        view = words.copy()
        if query.strip():
            q = query.strip().casefold()
            cols = ["hanzi", "pinyin", "han_viet", "meaning_vi", "meaning_en"]
            mask = view[cols].apply(lambda col: col.str.casefold().str.contains(q, regex=False)).any(axis=1)
            view = view[mask]
        st.dataframe(view[COLUMNS], use_container_width=True, hide_index=True)
        st.download_button("Tải CSV", view.to_csv(index=False).encode("utf-8-sig"),
                           "vocabulary_export.csv", "text/csv")

    elif page == "Yêu thích":
        fav_ids = [wid for wid, p in progress.items() if p.get("is_favorite")]
        fav = df[df["id"].astype(str).isin(fav_ids)]
        if fav.empty:
            st.info("Bạn chưa có từ yêu thích.")
        else:
            st.dataframe(fav[COLUMNS], use_container_width=True, hide_index=True)

    else:
        st.subheader("Cài đặt")
        with st.form("settings_form"):
            interval = st.selectbox("Tự đổi từ sau", [5, 10, 15, 30, 60],
                                    index=[5, 10, 15, 30, 60].index(int(st.session_state.interval)))
            random_mode = st.checkbox("Lấy từ ngẫu nhiên", value=bool(st.session_state.random_mode))
            apply = st.form_submit_button("Áp dụng cài đặt")
        if apply:
            st.session_state.interval = int(interval)
            st.session_state.random_mode = bool(random_mode)
            st.session_state.current_id = None
            st.session_state.seen_ids = []
            persist_settings(client, user_id)
            save_settings(client, user_id, {"next_change_at": None})
            st.success("Đã lưu cài đặt lên Supabase. iPhone sẽ nhận ở lần widget làm mới tiếp theo.")
            st.rerun()

if __name__ == "__main__":
    main()