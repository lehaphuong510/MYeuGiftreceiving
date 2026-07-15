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

SHEET_ID = "1ce2iU7qzr9PUoGMorlIaNMYb3KDGizmhiIRquWN8dOE"
LINK_WEB_APP = "https://script.google.com/macros/s/AKfycbw-3bA7lerOMn8anUNs87onotPwcIawgG7660GOVQCi6FhqeKz-7FqyixdvUDX5Z6JA/exec"

# --- HÀM NÉN ẢNH & UPLOAD LÊN DRIVE ---
def upload_image_to_gdrive_script(photo_file, filename):
    try:
        img = Image.open(photo_file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        img.thumbnail((1024, 1024))
        compressed_io = io.BytesIO()
        img.save(compressed_io, format='JPEG', quality=70)
        compressed_bytes = compressed_io.getvalue()

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

# --- CACHE & STATE QUẢN LÝ ĐĂNG NHẬP VÀ FORM UI ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'staff_name' not in st.session_state:
    st.session_state['staff_name'] = ""
if 'form_key' not in st.session_state:
    st.session_state['form_key'] = 0
if 'success_msg' not in st.session_state:
    st.session_state['success_msg'] = ""
if 'error_msg' not in st.session_state:
    st.session_state['error_msg'] = ""

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
    st.markdown('<div class="main-title">Đăng nhập Trạm Nhận Quà</div>', unsafe_allow_html=True)
    password = st.text_input("Vui lòng nhập mã truy cập của bạn:", type="password")

    danh_sach_pass_hop_le = {
        "PassCuaAn2026": "An",
        "TrangNhanQua!": "Trang",
        "0519": "Lê Phương"
    }

    if st.button("Vào hệ thống", type="primary"):
        if password in danh_sach_pass_hop_le:
            st.session_state['staff_name'] = danh_sach_pass_hop_le[password]
            st.session_state['logged_in'] = True
            st.rerun()
        else:
            st.error("Sai password rồi nha!")

# --- MÀN HÌNH CHÍNH ---
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

    if st.session_state['success_msg']:
        st.success(st.session_state['success_msg'])
        st.session_state['success_msg'] = "" 
        
    if st.session_state['error_msg']:
        st.error(st.session_state['error_msg'])
        st.session_state['error_msg'] = ""

    st.markdown('<div class="question-text">Mình xin số ghế của bạn nha</div>', unsafe_allow_html=True)
    seat_num = st.text_input("Nhập số ghế (VD: C6) hoặc SĐT (VD: 09xxxx)", key=f"seat_{st.session_state['form_key']}")
    
    st.markdown('<div style="font-size: 14px; margin-top: -10px; margin-bottom: 5px; color: gray;">Email (chỉ bắt buộc trong trường hợp khách vãng lai)</div>', unsafe_allow_html=True)
    user_email = st.text_input("Nhập email", key=f"email_{st.session_state['form_key']}")
    
    photo = st.file_uploader("Chụp hoặc tải ảnh lên", type=['png', 'jpg', 'jpeg'], accept_multiple_files=False, key=f"photo_{st.session_state['form_key']}")

    if st.button("Đã nhận quà", type="primary"):
        is_sdt = len(seat_num.strip()) >= 9 
        
        if not seat_num:
            st.warning("Bạn quên nhập số ghế/SĐT kìa!")
        elif is_sdt and not user_email.strip():
            st.warning("Trường hợp nhập SĐT khách vãng lai, vui lòng điền thêm Email vào ô phía dưới nha!")
        elif photo is None:
            st.warning("Vui lòng chụp lại hình làm chứng minh nha!")
        else:
            with st.spinner("Đang lưu dữ liệu lên hệ thống..."):
                try:
                    seat_normalized = seat_num.upper().strip()
                    email_normalized = user_email.strip()
                    
                    safe_filename = seat_normalized.replace("/", "_").replace("\\", "_")
                    file_name = f"{safe_filename}.jpg"

                    img_url = upload_image_to_gdrive_script(photo, file_name)

                    if img_url:
                        timestamp = (datetime.utcnow() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")

                        creds = get_credentials()
                        client = gspread.authorize(creds)
                        sheet = client.open_by_key(SHEET_ID).worksheet("Sheet1")

                        seat_for_sheet = f"'{seat_normalized}"
                        sheet.append_row([timestamp, st.session_state['staff_name'], seat_for_sheet, email_normalized, img_url, "", ""])

                        st.session_state['success_msg'] = f"🎉 Hệ thống đã ghi nhận thành công cho: {seat_normalized}!"
                        st.session_state['form_key'] += 1 
                        st.rerun() 
                    else:
                        st.session_state['error_msg'] = "Lỗi khi tải hình ảnh lên server. Vui lòng thử lại!"
                        st.rerun()
                except Exception as e:
                    st.session_state['error_msg'] = f"Có lỗi xảy ra: {e}"
                    st.rerun()
