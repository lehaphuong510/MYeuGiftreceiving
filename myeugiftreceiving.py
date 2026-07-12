import streamlit as st
import gspread
import requests
import base64
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- KẾT NỐI GOOGLE SHEETS TỪ SECRETS ---
@st.cache_resource
def get_credentials():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return creds

SHEET_ID = "1ce2iU7qzr9PUoGMorlIaNMYb3KDGizmhiIRquWN8dOE"

# DÁN CÁI LINK WEB APP CỦA GOOGLE APPS SCRIPT VÀO ĐÂY NHA:
LINK_WEB_APP = "https://script.google.com/macros/s/AKfycbwLjSkMD-1tufo1nJ_Ec_tZ9NMCBQdR1pEp-xBDvfnqVEtMHlO4fW27YeLILjOLpqxT/exec"

# --- HÀM UPLOAD ẢNH BẰNG GOOGLE APPS SCRIPT ---
def upload_image_to_gdrive_script(image_bytes, filename):
    try:
        # Chuyển hình thành chuỗi mã hóa để bắn qua mạng dễ dàng
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        payload = {
            "fileData": encoded_image,
            "contentType": "image/jpeg",
            "filename": filename
        }
        # Bắn dữ liệu đi
        response = requests.post(LINK_WEB_APP, data=payload)
        result = response.text
        
        # Nếu link trả về có chữ http nghĩa là thành công
        if result.startswith("http"):
            return result
        else:
            print("Lỗi từ Google Script:", result)
            return None
    except Exception as e:
        print(f"Lỗi hệ thống: {e}")
        return None

# --- CACHE & STATE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'staff_name' not in st.session_state:
    st.session_state['staff_name'] = ""

# --- CẤU HÌNH GIAO DIỆN & CSS ---
st.set_page_config(page_title="Ghi Nhận Quà Sự Kiện", page_icon="🌻", layout="centered")

css = """

"""
st.markdown(css, unsafe_allow_html=True)

# --- MÀN HÌNH ĐĂNG NHẬP ---
if not st.session_state['logged_in']:
    st.markdown('HỆ THỐNG GHI NHẬNNHẬN QUÀ TẶNG MYÊU SHOW', unsafe_allow_html=True)
    password = st.text_input("Vui lòng nhập mã truy cập của bạn:", type="password")

    danh_sach_pass_hop_le = {
        "PassCuaAn2026": "An",
        "TrangNhanQua!": "Trang",
        "0519": "Phương"
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

    st.markdown('NHẬN QUÀ TỪ 🌻MYÊU🌻', unsafe_allow_html=True)
    st.write(f"Đang trực hệ thống: **{st.session_state['staff_name']}**")
    st.divider()

    st.markdown('Mình xin số ghế của bạn nha', unsafe_allow_html=True)
    seat_num = st.text_input("Nhập số ghế (VD: C6)")
    photo = st.camera_input("Chụp lại tấm hình")

    if st.button("Đã nhận quà", type="primary"):
        if not seat_num:
            st.warning("Bạn quên nhập số ghế kìa!")
        elif photo is None:
            st.warning("Vui lòng chụp lại hình làm chứng minh nha!")
        else:
            with st.spinner("Đang lưu dữ liệu lên hệ thống..."):
                try:
                    file_name = f"{seat_num.upper()}.jpg"

                    # 1. Bắn hình lên Drive qua link Apps Script
                    img_url = upload_image_to_gdrive_script(photo.getvalue(), file_name)

                    if img_url:
                        # 2. Ghi data vào Google Sheets
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        creds = get_credentials()
                        client = gspread.authorize(creds)
                        sheet = client.open_by_key(SHEET_ID).worksheet("Sheet1")
                        sheet.append_row([timestamp, st.session_state['staff_name'], seat_num.upper(), img_url])

                        st.success(f"🎉 Hệ thống đã ghi nhận thành công cho ghế {seat_num.upper()}!")
                    else:
                        st.error("Lỗi khi up hình lên Drive. Có thể do nghẽn mạng, m thử lại xíu nha!")
                except Exception as e:
                    st.error(f"Lỗi: {e}")
