from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import os

# Configuration
CREDENTIALS_FILE = "credentials.json"
DOC_ID = "1N23617Z17RR8UUZ7qg_dnVWR9Uevl8ks6n3J-Bt28uw"

def read_google_doc(doc_id):
    if not os.path.exists(CREDENTIALS_FILE):
        print("❌ Credentials file not found.")
        return

    scope = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/documents.readonly"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    service = build('docs', 'v1', credentials=creds)

    try:
        document = service.documents().get(documentId=doc_id).execute()
        content = ""
        for element in document.get('body').get('content'):
            if 'paragraph' in element:
                for run in element.get('paragraph').get('elements'):
                    if 'textRun' in run:
                        content += run.get('textRun').get('content')
        print("✅ Document Content Retrieved:")
        print(content)
        return content
    except Exception as e:
        print(f"❌ Error reading document: {e}")

if __name__ == "__main__":
    read_google_doc(DOC_ID)
