import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- KẾT NỐI GOOGLE CLOUD TỪ SECRETS ---
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

# ID CỦA SHEETS VÀ FOLDER DRIVE
SHEET_ID = "1ce2iU7qzr9PUoGMorlIaNMYb3KDGizmhiIRquWN8dOE"
FOLDER_ID = "1ue0GEah5v-YRwFlciQ54UBpfrXDI0eeC"

# --- HÀM UPLOAD ẢNH LÊN GOOGLE DRIVE ---
def upload_image_to_gdrive(image_bytes, filename):
    try:
        creds = get_credentials()
        drive_service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {
            'name': filename,
            'parents': [FOLDER_ID]
        }
        media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype='image/jpeg', resumable=True)
        
        # Upload file lên Drive
        file = drive_service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id, webViewLink'
        ).execute()
        
        file_id = file.get('id')
        
        # Cấp quyền cho ai có link cũng xem được
        drive_service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        return file.get('webViewLink')
    except Exception as e:
        print(f"Lỗi khi up Drive: {e}")
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

    st.markdown('<div class="main-title">NHẬN QUÀ ANH THIÊN MINH<br>TỪ 🌻🤍 MYÊU 🤍🌻</div>', unsafe_allow_html=True)
    st.write(f"Đang trực hệ thống: **{st.session_state['staff_name']}**")
    st.divider()

    st.markdown('<div class="question-text">Mình xin số ghế của bạn nha</div>', unsafe_allow_html=True)
    seat_num = st.text_input("Nhập số ghế (VD: C6)")
    photo = st.camera_input("Chụp lại tấm hình")

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

                    # 2. Bắn hình lên Google Drive lấy link
                    img_url = upload_image_to_gdrive(photo.getvalue(), file_name)

                    if img_url:
                        # 3. Bắn data vào Google Sheets
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
