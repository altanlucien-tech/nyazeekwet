import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django.conf import settings

BASE_DIR = settings.BASE_DIR

# JSON ဖိုင်လမ်းကြောင်းများ
SERVICE_ACCOUNT_FILES = [
    os.path.join(BASE_DIR, 'credentials', 'acc0.json'), # Index 0
    os.path.join(BASE_DIR, 'credentials', 'acc1.json'), # Index 1
    os.path.join(BASE_DIR, 'credentials', 'acc2.json')  # Index 2
]

# --- အရေးကြီးသည်- Folder ID များကို အကောင့်အလိုက် ဖြည့်ပေးပါ ---
# အကောင့်တစ်ခုချင်းစီရဲ့ Drive ထဲမှာ Folder တစ်ခုစီဆောက်ပြီး Service Account ကို Share ပေးရပါမယ်
DRIVE_FOLDER_IDS = {
    0: '10ga4LyUF3KP7wzCv5cAt6fe4LlnC4ttE', # Books အတွက်
    1: '1XG2rTuZKmDAQZgtM7wtXa9I4AsWwOVmf', # Manga အတွက်
    2: '1mOKYxjXnRkIRM6FllhY7enU8-m-dqWlz'  # Audiobook အတွက်
}

def get_drive_service(account_index):
    SCOPES = ['https://www.googleapis.com/auth/drive']
    if account_index >= len(SERVICE_ACCOUNT_FILES): return None
    
    json_path = SERVICE_ACCOUNT_FILES[account_index]
    if not os.path.exists(json_path): return None

    creds = service_account.Credentials.from_service_account_file(json_path, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file_path, file_name, account_index):
    service = get_drive_service(account_index)
    if not service: return None
    
    folder_id = DRIVE_FOLDER_IDS.get(account_index)
    
    # MIME Type သတ်မှတ်ချက်ကို ပိုတိကျအောင် ပြင်ဆင်ခြင်း
    mimetype = 'application/octet-stream'
    if file_name.lower().endswith('.pdf'):
        mimetype = 'application/pdf'
    elif file_name.lower().endswith('.mp3'):
        mimetype = 'audio/mpeg'
    elif file_name.lower().endswith('.m4a'):
        mimetype = 'audio/mp4'
    elif file_name.lower().endswith(('.jpg', '.jpeg')):
        mimetype = 'image/jpeg'

    file_metadata = {
        'name': file_name,
        'parents': [folder_id] if folder_id else []
    }
    media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')