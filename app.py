from pathlib import Path
import html
import random

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

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

def init_state():
    defaults = {
        "level": "HSK 1",
        "current_id": None,
        "favorites": [],
        "known_ids": [],
        "seen_ids": [],
        "random_mode": False,
        "interval": 10,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def choose_next(words):
    if words.empty:
        st.session_state.current_id = None
        return
    ids = words["id"].tolist()
    unseen = [x for x in ids if x not in st.session_state.seen_ids]
    if not unseen:
        st.session_state.seen_ids = []
        unseen = ids
    selected = random.choice(unseen) if st.session_state.random_mode else unseen[0]
    st.session_state.current_id = selected
    st.session_state.seen_ids.append(selected)

def get_current(words):
    if st.session_state.current_id is None or st.session_state.current_id not in words["id"].tolist():
        choose_next(words)
    row = words[words["id"] == str(st.session_state.current_id)]
    if row.empty:
        return None
    return row.iloc[0]

# ==================== STYLE ====================
def add_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Ma+Shan+Zheng&display=swap');
    html, body, [class*="css"], .stApp {
        font-family: 'Be Vietnam Pro', 'Noto Sans SC', sans-serif;
    }
    .stApp {
        background:
          radial-gradient(circle at 8% 8%, rgba(49,112,220,.28), transparent 28%),
          radial-gradient(circle at 92% 92%, rgba(37,89,154,.24), transparent 30%),
          #f4f7fc;
    }
    .block-container {max-width: 960px; padding-top: .55rem; padding-bottom: 1rem;}
    [data-testid="stHeader"] {background: transparent;}
    .study-card {
        display:grid;
        grid-template-columns: minmax(0, .92fr) minmax(0, 1.08fr);
        gap: 10px;
        background: rgba(255,255,255,.97);
        border: 1px solid rgba(210,220,236,.8);
        border-radius: 18px;
        padding: 10px;
        box-shadow: 0 18px 48px rgba(25,55,100,.13);
        color:#101827;
        min-height: 315px;
    }
    .left-col {
        padding: 1px 10px 1px 1px;
        border-right: 2px solid #dce5f3;
        display:flex; flex-direction:column; justify-content:center;
    }
    .right-col {display:flex; flex-direction:column; gap:8px; justify-content:center;}
    .topline {display:flex; align-items:center; gap:14px; margin-bottom:9px; flex-wrap:wrap;}
    .level-pill {background:#1264ed; color:white; padding:5px 10px; border-radius:18px; font-size:14px; font-weight:800;}
    .counter {font-size:14px; font-weight:800; color:#15233c;}
    .heart {margin-left:auto; color:#ed3345; font-size:20px; background:#fff0f3; border-radius:50%; padding:4px 8px;}
    .hanzi {font-family:'Ma Shan Zheng','KaiTi','STKaiti',serif; font-size:clamp(48px, 5.8vw, 76px); line-height:1.2; font-weight:700; letter-spacing:2px; text-align:center; margin:8px 0 10px; color:#101010;}
    .pinyin {font-size:clamp(20px, 2.3vw, 28px); color:#1671ee; font-weight:700; letter-spacing:.2px; text-align:center; margin:0 0 20px;}
    .sound {display:inline-block; color:#1264ed; background:#e5efff; border-radius:50%; padding:8px 13px; font-size:16px; vertical-align:middle; margin-left:10px;}
    .info-pill {border-radius:22px; padding:4px 8px; margin:3px 0; font-size:14px; text-align:center;}
    .hanviet {background:#e5efff;}
    .meaning {background:#fff2d9;}
    .example-vi {background:#f0eaff; font-size:13px; font-style:italic;}
    .info-label {color:#1264ed; font-weight:800; margin-right:12px;}
    .lang-panel {border-radius:17px; padding:9px 11px; min-height:105px; display:flex; flex-direction:column; justify-content:center;}
    .english {background:linear-gradient(120deg,#edf4ff,#e4edff);}
    .vietnamese {background:linear-gradient(120deg,#fff0f5,#fde5ef);}
    .lang-head {display:flex; align-items:center; gap:18px; flex-wrap:wrap; margin-bottom:12px;}
    .lang-tag {color:white; font-weight:900; font-size:16px; border-radius:14px; padding:8px 17px;}
    .en-tag {background:#1264ed;}
    .vi-tag {background:#ed2638;}
    .gloss {font-size:clamp(18px,2vw,25px); font-weight:850; color:#101827;}
    .part {font-size:13px; font-style:italic; color:#28364d;}
    .quote {font-size:clamp(14px,1.45vw,19px); font-style:italic; color:#10264e; padding:7px 0 7px 20px; border-left:8px solid #1264ed; margin:8px 0 12px;}
    .vietnamese .quote {border-left-color:#ed2638; font-style:normal;}
    .meta {display:inline-block; background:rgba(255,255,255,.62); border-radius:24px; padding:4px 8px; font-size:13px; color:#172b4d; margin-top:4px;}
    .meta b {margin-right:10px;}
    @media(max-width:760px) {
      .study-card {grid-template-columns:1fr; padding:9px; gap:8px; min-height:0;}
      .left-col {border-right:0; border-bottom:2px solid #dce5f3; padding:0 0 18px;}
      .right-col {gap:12px;}
      .lang-panel {min-height:95px; padding:9px;}
      .hanzi {font-size:56px;}
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
    init_state()
    add_css()

    st.markdown("<h2 style='text-align:center;color:#152c4d;margin-bottom:0'>📚 CHINESE VOCABULARY</h2>", unsafe_allow_html=True)
    st.caption("HỌC TỪ VỰNG TIẾNG TRUNG · HSK")

    try:
        df, source = load_data()
    except Exception as exc:
        st.error("Không tải được file dữ liệu vocabulary.csv.")
        st.code(str(exc))
        st.info("Kiểm tra file data/vocabulary.csv trong GitHub hoặc nhánh main.")
        st.stop()

    if df.empty:
        st.warning("File từ vựng chưa có dữ liệu.")
        st.stop()

    levels = sorted(df["level"].dropna().unique().tolist(),
                    key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 999)
    if st.session_state.level not in levels:
        st.session_state.level = levels[0]

    with st.container():
        nav1, nav2, nav3, nav4 = st.columns([1.3, 1, 1, 1])
        with nav1:
            st.session_state.level = st.selectbox("Cấp độ", levels, index=levels.index(st.session_state.level))
        with nav2:
            page = st.selectbox("Chức năng", ["Học từ", "Danh sách", "Yêu thích", "Cài đặt"])
        with nav3:
            st.caption(f"Tổng dữ liệu: {len(df)} từ")
        with nav4:
            st.caption(f"Nguồn: {'GitHub' if source == 'github' else 'Repository'}")

    words = df[df["level"] == st.session_state.level].reset_index(drop=True)

    if page == "Học từ":
        try:
            count = st_autorefresh(interval=int(st.session_state.interval) * 60 * 1000, key="vocab_auto_refresh")
        except Exception:
            count = 0
        if count > 0 and st.session_state.get("last_refresh", 0) != count:
            if st.session_state.current_id is not None:
                choose_next(words)
            st.session_state.last_refresh = count

        current = get_current(words)
        if current is None:
            st.warning("Không tìm thấy từ phù hợp.")
            return

        render_card(current, words)
        a, b, c = st.columns(3)
        is_fav = current["id"] in st.session_state.favorites
        with a:
            if st.button("♥ Bỏ yêu thích" if is_fav else "♡ Yêu thích", use_container_width=True):
                if is_fav:
                    st.session_state.favorites.remove(current["id"])
                else:
                    st.session_state.favorites.append(current["id"])
                st.rerun()
        with b:
            if st.button("✓ Đã thuộc", use_container_width=True):
                if current["id"] not in st.session_state.known_ids:
                    st.session_state.known_ids.append(current["id"])
                choose_next(words)
                st.rerun()
        with c:
            if st.button("Từ tiếp theo ➜", use_container_width=True):
                choose_next(words)
                st.rerun()

        known = sum(x in set(words["id"]) for x in st.session_state.known_ids)
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
        fav = df[df["id"].isin(st.session_state.favorites)]
        if fav.empty:
            st.info("Bạn chưa có từ yêu thích.")
        else:
            st.dataframe(fav[COLUMNS], use_container_width=True, hide_index=True)

    else:
        st.subheader("Cài đặt")
        st.session_state.interval = st.selectbox("Tự đổi từ sau", [5, 10, 15, 30, 60],
                                                 index=[5, 10, 15, 30, 60].index(st.session_state.interval))
        st.session_state.random_mode = st.checkbox("Lấy từ ngẫu nhiên", value=st.session_state.random_mode)
        if st.button("Áp dụng cài đặt"):
            st.session_state.current_id = None
            st.session_state.seen_ids = []
            st.success("Đã cập nhật cài đặt.")
            st.rerun()

if __name__ == "__main__":
    main()
