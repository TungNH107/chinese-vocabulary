from pathlib import Path
import random
import traceback

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# -------------------- Cấu hình --------------------
APP_DIR = Path(__file__).parent
DATA_FILE = APP_DIR / "data" / "vocabulary.csv"
REQUIRED_COLUMNS = [
    "id", "level", "hanzi", "pinyin", "han_viet", "han_viet_chars",
    "meaning", "word_type", "example", "example_pinyin", "example_meaning"
]

st.set_page_config(
    page_title="Chinese Vocabulary",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -------------------- Dữ liệu --------------------
@st.cache_data
def read_vocabulary(file_path: str, modified_time: float):
    frame = pd.read_csv(file_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    for col in REQUIRED_COLUMNS:
        if col not in frame.columns:
            frame[col] = ""
    frame = frame[REQUIRED_COLUMNS].fillna("")
    frame["id"] = frame["id"].astype(str)
    return frame


def get_vocab():
    if not DATA_FILE.exists():
        st.error(f"Không tìm thấy file dữ liệu: {DATA_FILE}")
        st.stop()
    return read_vocabulary(str(DATA_FILE), DATA_FILE.stat().st_mtime)


def init_state():
    defaults = {
        "page": "Học từ",
        "levels": ["HSK 1", "HSK 2"],
        "interval": 10,
        "random_mode": True,
        "avoid_repeat": True,
        "show_pinyin": True,
        "show_hanviet_chars": True,
        "show_examples": True,
        "favorites": [],
        "known_ids": [],
        "seen_ids": [],
        "current_id": None,
        "refresh_count": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def filtered_words(df):
    return df[df["level"].isin(st.session_state.levels)].copy().reset_index(drop=True)


def choose_next(words):
    if words.empty:
        st.session_state.current_id = None
        return
    ids = words["id"].tolist()
    if st.session_state.avoid_repeat:
        pool = [word_id for word_id in ids if word_id not in st.session_state.seen_ids]
        if not pool:
            st.session_state.seen_ids = []
            pool = ids
    else:
        pool = ids

    selected = random.choice(pool) if st.session_state.random_mode else pool[0]
    st.session_state.current_id = selected
    if selected not in st.session_state.seen_ids:
        st.session_state.seen_ids.append(selected)


def get_current_word(words):
    selected = words[words["id"] == str(st.session_state.current_id)]
    if selected.empty:
        choose_next(words)
        selected = words[words["id"] == str(st.session_state.current_id)]
    return None if selected.empty else selected.iloc[0]


# -------------------- Giao diện --------------------
def add_styles():
    st.markdown("""
    <style>
    .block-container {max-width: 850px; padding-top: 2rem; padding-bottom: 3rem;}
    .login-title {font-size: 2.2rem; font-weight: 750; margin-bottom: .15rem;}
    .muted {color: #8993a1; font-size: .82rem; letter-spacing: .08em; margin-bottom: 1.4rem;}
    .word-panel {
        background: linear-gradient(140deg, #172d46 0%, #244766 100%);
        color: #ffffff; padding: 28px; border-radius: 22px;
        margin: 12px 0 18px; box-shadow: 0 10px 30px rgba(15,35,55,.14);
    }
    .level-tag {color:#b9d9ff; font-size: .75rem; font-weight: 700; letter-spacing:.1em;}
    .hanzi {font-size: 3.5rem; font-weight: 750; line-height:1.2; margin: 16px 0 4px;}
    .pinyin {font-size:1.55rem; color:#91c8ff; margin-bottom:14px;}
    .hv {font-size:1.05rem; margin:8px 0;}
    .hvchars {font-size:.9rem; color:#d6e2ef; margin:8px 0;}
    .meaning {font-size:1rem; color:#edf4fb; margin:8px 0;}
    .example {
        background:rgba(255,255,255,.10); border-radius:14px;
        padding:15px; margin-top:18px;
    }
    .example-label {font-size:.72rem; font-weight:700; letter-spacing:.1em; color:#b9d9ff;}
    .example-cn {font-size:1.25rem; margin-top:8px;}
    .example-py {font-size:.92rem; color:#a9d1ff; margin-top:5px;}
    .example-vi {font-size:.92rem; margin-top:5px;}
    </style>
    """, unsafe_allow_html=True)


def render_word(word):
    # Tạo một khối HTML duy nhất, không thụt lề đầu dòng để Markdown
    # không hiểu nhầm HTML thành code block.
    import html

    def safe(value):
        return html.escape(str(value or ""))

    pinyin_html = (
        f"<div class='pinyin'>{safe(word['pinyin'])}</div>"
        if st.session_state.show_pinyin else ""
    )
    chars_html = (
        f"<div class='hvchars'>{safe(word['han_viet_chars'])}</div>"
        if st.session_state.show_hanviet_chars else ""
    )
    example_html = ""
    if st.session_state.show_examples:
        example_html = (
            "<div class='example'>"
            "<div class='example-label'>VÍ DỤ</div>"
            f"<div class='example-cn'>{safe(word['example'])}</div>"
            f"<div class='example-py'>{safe(word['example_pinyin'])}</div>"
            f"<div class='example-vi'>{safe(word['example_meaning'])}</div>"
            "</div>"
        )

    card = (
        "<div class='word-panel'>"
        f"<div class='level-tag'>{safe(word['level']).upper()} · CHINESE VOCABULARY</div>"
        f"<div class='hanzi'>{safe(word['hanzi'])}</div>"
        f"{pinyin_html}"
        f"<div class='hv'>Hán Việt: {safe(word['han_viet'])}</div>"
        f"{chars_html}"
        f"<div class='meaning'>Nghĩa: {safe(word['meaning'])}</div>"
        f"{example_html}"
        "</div>"
    )
    st.markdown(card, unsafe_allow_html=True)


def render_learning(df):
    words = filtered_words(df)
    if words.empty:
        st.warning("Chưa có từ ở cấp độ đang chọn. Vào Cài đặt để chọn cấp độ.")
        return

    try:
        count = st_autorefresh(
            interval=int(st.session_state.interval) * 60 * 1000,
            key="vocab_refresh",
        )
    except Exception:
        count = st.session_state.refresh_count

    if count != st.session_state.refresh_count:
        if st.session_state.refresh_count > 0:
            choose_next(words)
        st.session_state.refresh_count = count

    word = get_current_word(words)
    if word is None:
        st.warning("Không tìm thấy từ phù hợp.")
        return

    st.caption(
        f"Đang học {', '.join(st.session_state.levels)} · "
        f"{len(words)} từ trong bộ lọc"
    )
    render_word(word)

    c1, c2, c3 = st.columns(3)
    is_fav = word["id"] in st.session_state.favorites
    with c1:
        if st.button("★ Đã thích" if is_fav else "☆ Yêu thích", use_container_width=True):
            if is_fav:
                st.session_state.favorites.remove(word["id"])
            else:
                st.session_state.favorites.append(word["id"])
            st.rerun()
    with c2:
        if st.button("✓ Đã thuộc", use_container_width=True):
            if word["id"] not in st.session_state.known_ids:
                st.session_state.known_ids.append(word["id"])
            choose_next(words)
            st.rerun()
    with c3:
        if st.button("Từ tiếp theo ➜", use_container_width=True):
            choose_next(words)
            st.rerun()

    known_count = sum(word_id in set(words["id"]) for word_id in st.session_state.known_ids)
    st.metric("Từ đã đánh dấu đã thuộc", f"{known_count} / {len(words)}")
    st.caption(
        "Tự đổi từ theo chu kỳ khi trang đang mở. Trình duyệt có thể tạm dừng "
        "tự làm mới khi tab ở nền hoặc iPhone khóa màn hình."
    )


def render_list(df):
    st.subheader("Danh sách từ vựng")
    levels = sorted(df["level"].unique().tolist(), key=lambda item: int(item.split()[-1]))
    selected = st.multiselect("Lọc cấp độ", levels, default=[x for x in st.session_state.levels if x in levels])
    query = st.text_input("Tìm chữ Hán, Pinyin, Hán Việt hoặc nghĩa")
    view = df[df["level"].isin(selected)].copy()
    if query.strip():
        q = query.strip().casefold()
        columns = ["hanzi", "pinyin", "han_viet", "meaning", "han_viet_chars"]
        mask = view[columns].apply(
            lambda col: col.astype(str).str.casefold().str.contains(q, regex=False)
        ).any(axis=1)
        view = view[mask]
    st.caption(f"Tìm thấy {len(view)} từ")
    st.dataframe(
        view[["level", "hanzi", "pinyin", "han_viet", "meaning"]],
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "⬇️ Tải danh sách CSV",
        view.to_csv(index=False).encode("utf-8-sig"),
        "vocabulary_export.csv",
        "text/csv",
    )


def render_favorites(df):
    st.subheader("Từ vựng yêu thích")
    favorites = df[df["id"].isin(st.session_state.favorites)]
    if favorites.empty:
        st.info("Bạn chưa lưu từ yêu thích trong phiên học này.")
    else:
        st.dataframe(
            favorites[["level", "hanzi", "pinyin", "han_viet", "meaning"]],
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "⬇️ Xuất từ yêu thích",
            favorites.to_csv(index=False).encode("utf-8-sig"),
            "favorites.csv",
            "text/csv",
        )


def render_settings(df):
    st.subheader("⚙️ Cài đặt")
    levels = sorted(df["level"].unique().tolist(), key=lambda item: int(item.split()[-1]))
    with st.form("settings_form"):
        selected_levels = st.multiselect(
            "Chọn cấp độ HSK muốn học",
            levels,
            default=[x for x in st.session_state.levels if x in levels],
        )
        interval = st.selectbox(
            "Tự đổi từ sau",
            [5, 10, 15, 30, 60],
            index=[5, 10, 15, 30, 60].index(st.session_state.interval),
            format_func=lambda value: f"{value} phút",
        )
        random_mode = st.checkbox("Lấy từ ngẫu nhiên", value=st.session_state.random_mode)
        avoid_repeat = st.checkbox("Không lặp lại đến khi hết danh sách", value=st.session_state.avoid_repeat)
        show_pinyin = st.checkbox("Hiển thị Pinyin", value=st.session_state.show_pinyin)
        show_chars = st.checkbox("Hiển thị Hán Việt từng chữ", value=st.session_state.show_hanviet_chars)
        show_examples = st.checkbox("Hiển thị câu ví dụ", value=st.session_state.show_examples)
        submitted = st.form_submit_button("Lưu cài đặt", type="primary", use_container_width=True)

    if submitted:
        if not selected_levels:
            st.error("Hãy chọn ít nhất một cấp độ.")
        else:
            st.session_state.levels = selected_levels
            st.session_state.interval = interval
            st.session_state.random_mode = random_mode
            st.session_state.avoid_repeat = avoid_repeat
            st.session_state.show_pinyin = show_pinyin
            st.session_state.show_hanviet_chars = show_chars
            st.session_state.show_examples = show_examples
            st.session_state.current_id = None
            st.session_state.seen_ids = []
            st.session_state.refresh_count = 0
            st.success("Đã lưu cài đặt cho phiên sử dụng hiện tại.")
            st.rerun()

    st.divider()
    st.markdown("**Sao lưu dữ liệu cá nhân**")
    backup = {
        "levels": st.session_state.levels,
        "interval": st.session_state.interval,
        "random_mode": st.session_state.random_mode,
        "avoid_repeat": st.session_state.avoid_repeat,
        "show_pinyin": st.session_state.show_pinyin,
        "show_hanviet_chars": st.session_state.show_hanviet_chars,
        "show_examples": st.session_state.show_examples,
        "favorites": st.session_state.favorites,
        "known_ids": st.session_state.known_ids,
    }
    st.download_button(
        "Tải file sao lưu cài đặt",
        pd.Series(backup).to_json(force_ascii=False, indent=2).encode("utf-8"),
        "vocabulary_settings_backup.json",
        "application/json",
    )
    st.caption(
        "Lưu ý: Bản thử nghiệm lưu cài đặt/yêu thích trong phiên trình duyệt. "
        "Tải file sao lưu nếu muốn giữ lại dữ liệu khi phiên bị làm mới."
    )


# -------------------- Chạy ứng dụng --------------------
def main():
    add_styles()
    init_state()
    df = get_vocab()

    st.markdown("# 📚 Vocabulary")
    st.caption("CHINESE LEARNING · HSK 2.0")

    page = st.radio(
        "Điều hướng",
        ["Học từ", "Danh sách", "Yêu thích", "Cài đặt"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if df.empty:
        st.warning("File từ vựng hiện chưa có dữ liệu.")
        return

    if page == "Học từ":
        render_learning(df)
    elif page == "Danh sách":
        render_list(df)
    elif page == "Yêu thích":
        render_favorites(df)
    else:
        render_settings(df)

    st.divider()
    st.caption(f"Vocabulary Web App · Bản thử nghiệm · {len(df)} từ mẫu")


try:
    main()
except Exception as exc:
    st.error("Ứng dụng gặp lỗi khi chạy. Thông tin kỹ thuật:")
    st.exception(exc)
