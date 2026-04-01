import os

from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def _get_drive_service(account_index: int):
    """
    account_index (0, 1, 2 ...) အလိုက် Google Drive service account ကို load လုပ်ပေးသည်။
    """
    scopes = ["https://www.googleapis.com/auth/drive.file"]
    credentials_dir = os.path.join(settings.BASE_DIR, "credentials")
    json_path = os.path.join(credentials_dir, f"acc{account_index}.json")

    if not os.path.exists(json_path):
        return None

    creds = service_account.Credentials.from_service_account_file(
        json_path, scopes=scopes
    )
    return build("drive", "v3", credentials=creds)


def upload_to_drive(
    local_path: str, filename: str, account_index: int = 0
) -> str | None:
    """
    Local ဖိုင်တစ်ဖိုင်ကို Google Drive သို့ upload လုပ်၍ file ID ကို ပြန်ပေးမည်။
    credentials/acc{index}.json တွေ သေချာရှိဖို့လိုသည်။
    """
    service = _get_drive_service(account_index)
    if not service:
        return None

    file_metadata = {"name": filename}
    media = MediaFileUpload(local_path, resumable=True)

    request = service.files().create(body=file_metadata, media_body=media, fields="id")
    file = request.execute()
    return file.get("id")
