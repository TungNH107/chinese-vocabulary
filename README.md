# Vocabulary Web App V1

Ứng dụng học từ vựng tiếng Trung bằng Python + Streamlit, tối ưu để thử nghiệm trên máy tính và iPhone.

## Tính năng
- Chữ Hán, Pinyin, Hán Việt, Hán Việt từng chữ, nghĩa và ví dụ.
- Lọc theo cấp độ HSK.
- Tự làm mới theo chu kỳ cấu hình khi trang đang hoạt động.
- Chọn từ tiếp theo, ngẫu nhiên và tránh lặp trong một vòng.
- Đánh dấu yêu thích và đã thuộc.
- Tìm kiếm, xuất CSV, nhập Excel/CSV.
- Cổng mật khẩu cơ bản cho mục đích cá nhân.

## Quan trọng về dữ liệu
`data/vocabulary.csv` hiện chỉ có **20 từ mẫu** để kiểm tra giao diện và luồng hoạt động. Đây chưa phải danh sách HSK 1–2 đầy đủ hoặc bộ dữ liệu đã được hiệu đính học thuật. Cần đối chiếu danh sách HSK 2.0 và kiểm tra Hán Việt, ví dụ trước khi dùng làm tài liệu học chính thức.

## Chạy trên Windows
1. Cài Python 3.11 hoặc 3.12: https://www.python.org/downloads/
2. Giải nén ZIP, ví dụ vào `C:\Vocabulary`.
3. Mở PowerShell tại thư mục dự án.
4. Tạo môi trường ảo:
   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   Nếu PowerShell chặn kích hoạt:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```
5. Cài thư viện:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
6. Sao chép `.streamlit\secrets.toml.example` thành `.streamlit\secrets.toml`, rồi thay mật khẩu.
7. Chạy:
   ```powershell
   streamlit run app.py
   ```
8. Mở `http://localhost:8501`.

## Đưa lên Internet bằng Streamlit Community Cloud
1. Tạo tài khoản GitHub và Streamlit Community Cloud.
2. Tạo repository GitHub chứa mã nguồn.
3. Upload các file dự án. **Không upload `secrets.toml` hoặc mật khẩu.**
4. Trên Streamlit Community Cloud, chọn New app, kết nối repository và chọn `app.py`.
5. Trong App settings → Secrets, thêm:
   ```toml
   APP_PASSWORD = "MAT_KHAU_RIENG_CUA_BAN"
   ```
6. Deploy, mở URL được cấp trên iPhone bằng Safari.
7. Trong Safari chọn Share → Add to Home Screen.

## Lưu ý quan trọng
- Cổng mật khẩu trong app là lớp bảo vệ cơ bản, không thay thế xác thực chuyên dụng. Không lưu thông tin nhạy cảm.
- Streamlit Community Cloud có thể khởi động lại; hệ thống tệp cục bộ không được đảm bảo lưu trữ bền vững. Dữ liệu người dùng và file CSV sửa trực tiếp trên máy chủ có thể mất khi app ngủ, khởi động lại hoặc redeploy.
- Nếu muốn giữ mã nguồn riêng tư và dữ liệu bền vững, cần chọn hosting hỗ trợ repository riêng tư và ổ đĩa/database bền vững hoặc bổ sung Supabase.
- Safari có thể tạm dừng tab nền; không đảm bảo đổi từ đúng 10 phút khi khóa màn hình.

## Cấu trúc file
```text
vocabulary_webapp_v1/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── secrets.toml.example
└── data/
    └── vocabulary.csv
```

## Cấu trúc cột Excel/CSV
`id, level, hanzi, pinyin, han_viet, han_viet_chars, meaning, word_type, example, example_pinyin, example_meaning`

`level` dùng định dạng `HSK 1`, `HSK 2`... `id` phải duy nhất.
