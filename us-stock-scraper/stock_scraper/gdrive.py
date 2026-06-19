"""
Google Drive 上傳模組。
Google Drive upload helper.

支援兩種驗證方式 / Supports two auth methods:
  1. OAuth 使用者授權 (預設)  -> 需要 credentials.json，第一次會開瀏覽器登入
  2. Service Account         -> 設定環境變數 GOOGLE_SERVICE_ACCOUNT=service_account.json

上傳時若 Drive 中已存在同名檔案 (同一資料夾)，會自動更新而非新增重複檔。
If a file with the same name already exists in the folder, it is updated
in place instead of creating a duplicate.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

# 只需要建立/管理本程式建立的檔案即可
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def _get_service(credentials_file: str, token_file: str):
    """建立並回傳已驗證的 Google Drive service。"""
    # 優先嘗試 Service Account (適合自動化/伺服器排程)
    sa_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT")
    if sa_path:
        from google.oauth2 import service_account

        logger.info("使用 Service Account 驗證: %s", sa_path)
        creds = service_account.Credentials.from_service_account_file(
            sa_path, scopes=SCOPES
        )
        return build("drive", "v3", credentials=creds)

    # 否則使用 OAuth 使用者授權流程
    creds: Optional[Credentials] = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("權杖過期，嘗試更新...")
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                raise FileNotFoundError(
                    f"找不到 OAuth 憑證檔 {credentials_file}。\n"
                    "請到 Google Cloud Console 建立 OAuth 用戶端並下載 credentials.json，"
                    "或設定環境變數 GOOGLE_SERVICE_ACCOUNT。\n"
                    "See README for how to obtain credentials.json."
                )
            logger.info("第一次使用，開啟瀏覽器進行授權...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w", encoding="utf-8") as fh:
            fh.write(creds.to_json())
        logger.info("已將授權權杖儲存到 %s", token_file)

    return build("drive", "v3", credentials=creds)


def _find_existing_file(service, name: str, folder_id: str) -> Optional[str]:
    """在指定資料夾中尋找同名檔案，回傳 file id 或 None。"""
    safe_name = name.replace("'", "\\'")
    query = f"name = '{safe_name}' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    resp = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)", pageSize=1)
        .execute()
    )
    files = resp.get("files", [])
    return files[0]["id"] if files else None


def upload_json(
    local_path: str,
    folder_id: str = "",
    credentials_file: str = "credentials.json",
    token_file: str = "token.json",
) -> str:
    """
    將本地 JSON 檔上傳到 Google Drive。
    Upload a local JSON file to Google Drive.

    Returns:
        Google Drive 上的檔案連結 (webViewLink)。
    """
    service = _get_service(credentials_file, token_file)
    file_name = os.path.basename(local_path)
    media = MediaFileUpload(local_path, mimetype="application/json", resumable=True)

    existing_id = _find_existing_file(service, file_name, folder_id)
    if existing_id:
        logger.info("更新已存在的檔案 %s ...", file_name)
        file = (
            service.files()
            .update(fileId=existing_id, media_body=media, fields="id, webViewLink")
            .execute()
        )
    else:
        logger.info("上傳新檔案 %s ...", file_name)
        metadata: dict = {"name": file_name}
        if folder_id:
            metadata["parents"] = [folder_id]
        file = (
            service.files()
            .create(body=metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )

    link = file.get("webViewLink", f"https://drive.google.com/file/d/{file.get('id')}")
    logger.info("上傳完成: %s", link)
    return link
