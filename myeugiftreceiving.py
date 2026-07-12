import streamlit as st
import gspread
import requests
import base64
import io
from PIL import Image
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# --- KẾT NỐI GOOGLE SHEETS TỪ SECRETS ---
@st.cache_resource
def get_credentials():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    return creds

# ID CỦA SHEETS VÀ LINK WEB APP CỦA DRIVE
SHEET_ID = "1ce2iU7qzr9PUoGMorlIaNMYb3KDGizmhiIRquWN8dOE"

# DÁN CÁI LINK WEB APP CỦA GOOGLE APPS SCRIPT VÀO ĐÂY NHA:
LINK_WEB_APP = "https://script.google.com/macros/s/AKfycbw-3bA7lerOMn8anUNs87onotPwcIawgG7660GOVQCi6FhqeKz-7FqyixdvUDX5Z6JA/exec"

# --- HÀM NÉN ẢNH & UPLOAD LÊN GOOGLE DRIVE (QUA APPS SCRIPT) ---
def upload_image_to_gdrive_script(photo_file, filename):
    try:
        # 1. ÉP CÂN ẢNH BẰNG PILLOW
        img = Image.open(photo_file)
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Thu nhỏ ảnh cho nhẹ (tối đa 1024x1024, giữ đúng tỷ lệ gốc)
        img.thumbnail((1024, 1024))
        
        # Lưu vào vùng nhớ đệm, ép chuẩn JPEG, quality 70%
        compressed_io = io.BytesIO()
        img.save(compressed_io, format='JPEG', quality=70)
        compressed_bytes = compressed_io.getvalue()

        # 2. BẮN ẢNH QUA GOOGLE SCRIPT
        encoded_image = base64.b64encode(compressed_bytes).decode('utf-8')
        payload = {
            "fileData": encoded_image,
            "contentType": "image/jpeg",
            "filename": filename
        }
        
        response = requests.post(LINK_WEB_APP, data=payload)
        result = response.text
        
        if result.startswith("http"):
            return result
        else:
            st.error(f"Lỗi từ Google Script: {result}")
            return None
    except Exception as e:
        st.error(f"Lỗi hệ thống khi up hình: {e}")
        return None

# --- CACHE & STATE QUẢN LÝ ĐĂNG NHẬP ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'staff_name' not in st.session_state:
    st.session_state['staff_name'] = ""

# --- CẤU HÌNH GIAO DIỆN & CSS ---
st.set_page_config(page_title="Ghi Nhận Quà Sự Kiện", page_icon="🌻", layout="centered")

css = """
<style>
    @media max-width: 768px {
        .main-title { font-size: 24px !important; line-height: 1.3 !important; white-space: nowrap !important; }
    }
    .main-title {
        background: linear-gradient(to right, #8B0000, #CC7722, #FFB300);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: left; font-size: 32px; font-weight: bold; margin-bottom: 20px;
    }
    .question-text {
        background: linear-gradient(to right, #D81B60, #8E24AA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 18px; font-weight: 600; margin-bottom: 10px;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(to right, #D81B60, #8E24AA) !important;
        color: white !important; border: none !important;
    }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# --- MÀN HÌNH ĐĂNG NHẬP ---
if not st.session_state['logged_in']:
    st.markdown('<div class="main-title">HỆ THỐNG GHI NHẬN<br>NHẬN QUÀ MYÊU SHOW</div>', unsafe_allow_html=True)
    password = st.text_input("Vui lòng nhập mã truy cập của bạn:", type="password")

    # M tạo 1 danh sách các pass hợp lệ ở đây
    danh_sach_pass_hop_le = {
        "PassCuaAn2026": "An",
        "TrangNhanQua!": "Trang",
        "0519": "Phương"
    }

    if st.button("Vào hệ thống", type="primary"):
        # Kiểm tra xem pass nhập vào có nằm trong danh sách không
        if password in danh_sach_pass_hop_le:
            # Lấy tên staff tương ứng với pass đó
            st.session_state['staff_name'] = danh_sach_pass_hop_le[password]
            st.session_state['logged_in'] = True
            st.rerun()
        else:
            st.error("Sai password rồi nha!")

# --- MÀN HÌNH CHÍNH (SAU KHI ĐĂNG NHẬP) ---
else:
    col1, col2 = st.columns([8, 2])
    with col2:
        if st.button("Đăng xuất"):
            st.session_state['logged_in'] = False
            st.session_state['staff_name'] = ""
            st.rerun()

    st.markdown('<div class="main-title">NHẬN QUÀ TỪ 🌻MYÊU🌻</div>', unsafe_allow_html=True)
    st.write(f"Đang trực hệ thống: **{st.session_state['staff_name']}**")
    st.divider()

    st.markdown('<div class="question-text">Mình xin số ghế của bạn nha</div>', unsafe_allow_html=True)
    seat_num = st.text_input("Nhập số ghế (VD: C6)")
    
    # Dùng file_uploader nhưng ép chỉ nhận hình ảnh, trên đt sẽ tự gợi ý bật Camera
    photo = st.file_uploader("Chụp hoặc tải ảnh lên", type=['png', 'jpg', 'jpeg'], accept_multiple_files=False)

    if st.button("Đã nhận quà", type="primary"):
        if not seat_num:
            st.warning("Bạn quên nhập số ghế kìa!")
        elif photo is None:
            st.warning("Vui lòng chụp lại hình làm chứng minh nha!")
        else:
            # Hiển thị loading spinner cho staff biết hệ thống đang xử lý
            with st.spinner("Đang lưu dữ liệu lên hệ thống..."):
                try:
                    # 1. Đặt tên hình trùng với số ghế (VD: C6.jpg)
                    file_name = f"{seat_num.upper()}.jpg"

                    # 2. Truyền thẳng file photo vào hàm nén ảnh và bắn lên Drive
                    img_url = upload_image_to_gdrive_script(photo, file_name)

                    if img_url:
                        # 3. Bắn data vào Google Sheets
                        # Lấy giờ quốc tế (utcnow) cộng thêm 7 tiếng ra giờ Việt Nam
                        timestamp = (datetime.utcnow() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")

                        creds = get_credentials()
                        client = gspread.authorize(creds)
                        sheet = client.open_by_key(SHEET_ID).worksheet("Sheet1")

                        # Dùng append_row để thêm 1 dòng mới tinh
                        sheet.append_row([timestamp, st.session_state['staff_name'], seat_num.upper(), img_url])

                        st.success(f"🎉 Hệ thống đã ghi nhận thành công cho ghế {seat_num.upper()}!")
                    else:
                        st.error("Lỗi khi tải hình ảnh lên server. Vui lòng thử lại!")
                except Exception as e:
                    st.error(f"Có lỗi xảy ra: {e}")
