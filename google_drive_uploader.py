#!/usr/bin/env python3
import os
import sys
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(base_dir, 'token_drive.pickle')
    client_secrets_path = os.path.join(base_dir, 'client_secrets.json')
    
    creds = None
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed, re-authenticating: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists(client_secrets_path):
                print(f"ERROR: Google Auth client_secrets.json missing at {client_secrets_path}")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            # Run local server with open_browser=False to display authorization URL in headless environments
            print("\n" + "="*80)
            print("GOOGLE DRIVE OAUTH CONFIGURATION")
            print("="*80)
            print("Click the link below, authorize the Google App, and paste the code back:")
            try:
                creds = flow.run_local_server(port=8080, open_browser=False)
            except Exception:
                creds = flow.run_local_server(port=0, open_browser=False)
            
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
            
    return build('drive', 'v3', credentials=creds)

def find_or_create_folder(service, folder_name, parent_id=None):
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']
    else:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        folder = service.files().create(body=file_metadata, fields='id').execute()
        print(f"Created folder '{folder_name}' with ID {folder.get('id')}")
        return folder.get('id')

def upload_file_to_drive(service, local_path, filename, mime_type, parent_id):
    file_metadata = {
        'name': filename,
        'parents': [parent_id]
    }
    media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"Uploaded file '{filename}' with ID {file.get('id')}")
    return file.get('id')

def push_folder_to_drive(local_folder_path):
    """Uploads the local post folder and its assets directly to Google Drive."""
    if not os.path.exists(local_folder_path):
        print(f"ERROR: Local folder not found: {local_folder_path}")
        return False
        
    print(f"Initializing Google Drive upload for: {local_folder_path}")
    service = get_drive_service()
    if not service:
        print("ERROR: Google Drive API could not be initialized.")
        return False
        
    try:
        # 1. Ensure root folder "Automatische Posts" exists
        root_folder_id = find_or_create_folder(service, "Automatische Posts")
        
        # 2. Create the specific subfolder for the post
        folder_name = os.path.basename(local_folder_path)
        post_folder_id = find_or_create_folder(service, folder_name, root_folder_id)
        
        # 3. Upload all files from the local folder
        for file in os.listdir(local_folder_path):
            local_file_path = os.path.join(local_folder_path, file)
            if os.path.isfile(local_file_path):
                ext = os.path.splitext(file)[1].lower()
                mime = "image/png"
                if ext == ".mp4":
                    mime = "video/mp4"
                elif ext == ".txt":
                    mime = "text/plain"
                elif ext == ".jpg" or ext == ".jpeg":
                    mime = "image/jpeg"
                    
                upload_file_to_drive(service, local_file_path, file, mime, post_folder_id)
                
        print(f"Google Drive Upload completed successfully for {folder_name}!")
        return True
    except Exception as e:
        print(f"ERROR during Google Drive upload: {e}")
        return False

if __name__ == "__main__":
    # Test execution / one-time authentication
    print("Testing Google Drive connection...")
    service = get_drive_service()
    if service:
        print("SUCCESS: Google Drive service connected!")
        try:
            folder_id = find_or_create_folder(service, "Automatische Posts")
            print(f"Active Root Folder ID: {folder_id}")
        except Exception as e:
            print(f"Query failed: {e}")
    else:
        print("FAILED to connect.")
