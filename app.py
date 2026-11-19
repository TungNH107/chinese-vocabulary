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
