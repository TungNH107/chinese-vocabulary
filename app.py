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
