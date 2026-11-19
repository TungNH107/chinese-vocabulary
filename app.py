import json
import random
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
VOCAB_FILE = DATA_DIR / "vocabulary.csv"
USER_FILE = DATA_DIR / "user_data.json"

st.set_page_config(page_title="Vocabulary – Chinese", page_icon="📚", layout="centered")

def check_password():
    try:
        password = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        password = ""
    if not password:
        st.warning("Chưa cấu hình mật khẩu. Hãy tạo .streamlit/secrets.toml theo file mẫu.")
        return True
    if st.session_state.get("authenticated"):
        return True
    st.markdown("## 🔐 Vocabulary")
    entered = st.text_input("Mật khẩu truy cập", type="password")
    if st.button("Đăng nhập", use_container_width=True):
        if entered == password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Mật khẩu chưa đúng.")
    return False

if not check_password():
    st.stop()

def load_vocab():
    df = pd.read_csv(VOCAB_FILE, keep_default_na=False)
    required = ["id","level","hanzi","pinyin","han_viet","han_viet_chars","meaning",
                "word_type","example","example_pinyin","example_meaning"]
    for col in required:
        if col not in df.columns:
            df[col] = ""
    return df[required]

def load_user_data():
    default = {"favorites":[],"selected_levels":["HSK 1","HSK 2"],"interval_minutes":10,
               "random_mode":True,"avoid_repeat":True,"show_hanviet_chars":True,
               "show_examples":True,"show_pinyin":True,"known_ids":[]}
    if USER_FILE.exists():
        try:
            default.update(json.loads(USER_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return default

def save_user_data():
    DATA_DIR.mkdir(exist_ok=True)
    USER_FILE.write_text(json.dumps(st.session_state.user_data, ensure_ascii=False, indent=2),
                         encoding="utf-8")

if "user_data" not in st.session_state:
    st.session_state.user_data = load_user_data()
if "current_id" not in st.session_state:
    st.session_state.current_id = None
if "seen_ids" not in st.session_state:
    st.session_state.seen_ids = []
if "last_refresh_count" not in st.session_state:
    st.session_state.last_refresh_count = 0

df = load_vocab()
ud = st.session_state.user_data

def available_words():
    levels = ud.get("selected_levels", ["HSK 1","HSK 2"])
    return df[df["level"].isin(levels)].copy().reset_index(drop=True)

def choose_next():
    words = available_words()
    if words.empty:
        st.session_state.current_id = None
        return
    ids = words["id"].astype(str).tolist()
    remaining = [x for x in ids if x not in st.session_state.seen_ids] if ud.get("avoid_repeat", True) else ids[:]
    if not remaining:
        st.session_state.seen_ids = []
        remaining = ids[:]
    chosen = random.choice(remaining) if ud.get("random_mode", True) else remaining[0]
    st.session_state.current_id = str(chosen)
    if chosen not in st.session_state.seen_ids:
        st.session_state.seen_ids.append(chosen)

def current_word():
    words = available_words()
    found = words[words["id"].astype(str) == str(st.session_state.current_id)]
    return None if found.empty else found.iloc[0]

def show_word_card(w):
    pinyin_html = f'<div class="word-pinyin">{w["pinyin"]}</div>' if ud.get("show_pinyin", True) else ""
    chars_html = f'<div class="word-chars">{w["han_viet_chars"]}</div>' if ud.get("show_hanviet_chars", True) else ""
    example_html = ""
    if ud.get("show_examples", True):
        example_html = f"""
        <div class="example-box">
          <div class="example-label">VÍ DỤ</div>
          <div class="example-cn">{w["example"]}</div>
          <div class="example-py">{w["example_pinyin"]}</div>
          <div class="example-vi">{w["example_meaning"]}</div>
        </div>
        """
    st.markdown("""
    <style>
    .word-card{background:linear-gradient(145deg,#172D46,#203E5C);color:white;border-radius:22px;padding:25px 23px;margin:8px 0 14px;box-shadow:0 8px 24px rgba(0,0,0,.12)}
    .word-level{color:#B7D8FF;font-size:12px;font-weight:700;letter-spacing:1px}
    .word-hanzi{font-size:54px;line-height:1.15;font-weight:750;margin-top:16px}
    .word-pinyin{color:#8FC5FF;font-size:25px;margin-top:7px}
    .word-hv{color:#fff;font-size:17px;margin-top:14px}
    .word-chars{color:#D2DEEA;font-size:14px;margin-top:7px}
    .word-meaning{color:#DCE8F4;font-size:16px;margin-top:5px}
    .example-box{background:rgba(255,255,255,.09);padding:14px;border-radius:14px;margin-top:20px}
    .example-label{color:#A8CFFF;font-size:11px;font-weight:700;letter-spacing:1px}
    .example-cn{color:#fff;font-size:19px;margin-top:8px}
    .example-py{color:#A8CFFF;font-size:14px;margin-top:5px}
    .example-vi{color:#fff;font-size:14px;margin-top:5px}
    </style>
    """, unsafe_allow_html=True)
    card = f"""
    <div class="word-card">
      <div class="word-level">{w["level"].upper()} · CHINESE VOCABULARY</div>
      <div class="word-hanzi">{w["hanzi"]}</div>
      {pinyin_html}
      <div class="word-hv">Hán Việt: {w["han_viet"]}</div>
      {chars_html}
      <div class="word-meaning">Nghĩa: {w["meaning"]}</div>
      {example_html}
    </div>
    """
    st.markdown(card, unsafe_allow_html=True)

st.markdown("<h1 style='margin-bottom:0'>📚 Vocabulary</h1><div style='color:gray;font-size:13px'>CHINESE LEARNING · HSK 2.0</div>", unsafe_allow_html=True)
page = st.radio("Điều hướng", ["Học từ","Danh sách","Yêu thích","Cài đặt"], horizontal=True, label_visibility="collapsed")

if df.empty:
    st.error("Chưa có dữ liệu từ vựng.")
    st.stop()

if page == "Học từ":
    words = available_words()
    if words.empty:
        st.warning("Chưa có từ ở cấp độ đang chọn. Vào Cài đặt để chọn cấp độ.")
        st.stop()
    interval_ms = int(ud.get("interval_minutes",10))*60*1000
    refresh_count = st_autorefresh(interval=interval_ms, key="vocab_auto_refresh")
    if refresh_count != st.session_state.last_refresh_count:
        if st.session_state.last_refresh_count != 0:
            choose_next()
        st.session_state.last_refresh_count = refresh_count
    if st.session_state.current_id is None or str(st.session_state.current_id) not in words["id"].astype(str).tolist():
        choose_next()
    w = current_word()
    st.caption(f'Đang học {", ".join(ud.get("selected_levels", []))} · {len(words)} từ trong bộ lọc')
    show_word_card(w)
    a,b,c = st.columns(3)
    with a:
        is_fav = str(w["id"]) in [str(x) for x in ud["favorites"]]
        if st.button("★ Đã thích" if is_fav else "☆ Yêu thích", use_container_width=True):
            if is_fav:
                ud["favorites"] = [x for x in ud["favorites"] if str(x) != str(w["id"])]
            else:
                ud["favorites"].append(str(w["id"]))
            save_user_data()
            st.rerun()
    with b:
        if st.button("✓ Đã thuộc", use_container_width=True):
            if str(w["id"]) not in [str(x) for x in ud["known_ids"]]:
                ud["known_ids"].append(str(w["id"]))
                save_user_data()
            choose_next()
            st.rerun()
    with c:
        if st.button("Từ tiếp theo ➜", use_container_width=True):
            choose_next()
            st.rerun()
    st.divider()
    learned = len([x for x in ud["known_ids"] if str(x) in words["id"].astype(str).tolist()])
    st.metric("Từ đã đánh dấu đã thuộc", f"{learned} / {len(words)}")
    st.caption("Tự đổi từ khi trang đang hoạt động. Safari có thể tạm dừng tab nền khi khóa màn hình.")

elif page == "Danh sách":
    st.subheader("Danh sách từ vựng")
    all_levels = sorted(df["level"].unique().tolist())
    selected = st.multiselect("Lọc cấp độ", all_levels, default=ud.get("selected_levels", ["HSK 1","HSK 2"]))
    query = st.text_input("Tìm chữ Hán, Pinyin, Hán Việt hoặc nghĩa")
    view = df[df["level"].isin(selected)].copy()
    if query.strip():
        q = query.strip().lower()
        cols = ["hanzi","pinyin","han_viet","meaning","han_viet_chars"]
        mask = view[cols].astype(str).apply(lambda col: col.str.lower().str.contains(q, regex=False)).any(axis=1)
        view = view[mask]
    st.caption(f"Tìm thấy {len(view)} từ")
    st.dataframe(view[["level","hanzi","pinyin","han_viet","meaning"]], use_container_width=True, hide_index=True)
    st.download_button("⬇️ Tải CSV mở bằng Excel", view.to_csv(index=False).encode("utf-8-sig"), "vocabulary_export.csv", "text/csv")

elif page == "Yêu thích":
    st.subheader("Từ vựng yêu thích")
    fav = df[df["id"].astype(str).isin([str(x) for x in ud["favorites"]])]
    if fav.empty:
        st.info("Bạn chưa lưu từ yêu thích.")
    else:
        st.dataframe(fav[["level","hanzi","pinyin","han_viet","meaning"]], use_container_width=True, hide_index=True)
        st.download_button("⬇️ Xuất từ yêu thích", fav.to_csv(index=False).encode("utf-8-sig"), "favorites.csv", "text/csv")

elif page == "Cài đặt":
    st.subheader("⚙️ Cài đặt")
    st.markdown("**A. Hệ thống từ vựng**")
    st.info("HSK 2.0 · Tiếng Trung giản thể")
    levels = sorted(df["level"].unique().tolist(), key=lambda x: int(x.split()[-1]))
    selected_levels = st.multiselect("Chọn cấp độ muốn học", levels, default=[x for x in ud["selected_levels"] if x in levels])
    st.markdown("**B. Tần suất thay đổi từ**")
    interval_options = [5,10,15,30,60]
    interval = st.selectbox("Chu kỳ (phút)", interval_options, index=interval_options.index(int(ud["interval_minutes"])))
    st.markdown("**C. Phương pháp học**")
    random_mode = st.toggle("Lấy từ ngẫu nhiên", value=ud["random_mode"])
    avoid_repeat = st.toggle("Không lặp lại đến khi hết danh sách", value=ud["avoid_repeat"])
    st.markdown("**D. Nội dung hiển thị**")
    show_pinyin = st.toggle("Hiển thị Pinyin", value=ud["show_pinyin"])
    show_chars = st.toggle("Hiển thị Hán Việt từng chữ", value=ud["show_hanviet_chars"])
    show_examples = st.toggle("Hiển thị ví dụ", value=ud["show_examples"])
    st.markdown("**E. Nhập dữ liệu từ Excel / CSV**")
    st.caption("Cần các cột: id, level, hanzi, pinyin, han_viet, han_viet_chars, meaning, word_type, example, example_pinyin, example_meaning.")
    uploaded = st.file_uploader("Chọn file .xlsx hoặc .csv", type=["xlsx","csv"])
    if uploaded is not None:
        try:
            incoming = pd.read_excel(uploaded, dtype=str) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded, dtype=str)
            st.dataframe(incoming.head(8), use_container_width=True)
            if st.button("Thay bộ dữ liệu hiện tại bằng file đã chọn"):
                missing = [c for c in df.columns if c not in incoming.columns]
                if missing:
                    st.error("Thiếu cột: " + ", ".join(missing))
                else:
                    incoming[df.columns].fillna("").to_csv(VOCAB_FILE, index=False, encoding="utf-8-sig")
                    st.success("Đã cập nhật dữ liệu.")
                    st.rerun()
        except Exception as exc:
            st.error(f"Không đọc được file: {exc}")
    if st.button("💾 Lưu cài đặt", type="primary", use_container_width=True):
        if not selected_levels:
            st.error("Hãy chọn ít nhất một cấp độ.")
        else:
            ud.update({"selected_levels":selected_levels,"interval_minutes":int(interval),
                       "random_mode":random_mode,"avoid_repeat":avoid_repeat,
                       "show_pinyin":show_pinyin,"show_hanviet_chars":show_chars,
                       "show_examples":show_examples})
            save_user_data()
            st.session_state.current_id = None
            st.session_state.seen_ids = []
            st.success("Đã lưu cài đặt.")
            st.rerun()
    st.divider()
    st.download_button("⬇️ Sao lưu cài đặt", json.dumps(ud,ensure_ascii=False,indent=2).encode("utf-8"), "vocabulary_user_backup.json", "application/json")

st.caption("Vocabulary Web App · Prototype V1 · 20 từ mẫu để chạy thử; cần hiệu đính và bổ sung trước khi học chính thức.")
