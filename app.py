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
