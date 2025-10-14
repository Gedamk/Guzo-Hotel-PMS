from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError

# 🔑 Path to your service account key
creds_path = r"C:\Users\Gedan\Desktop\Guzo\guzo_booking_bot\creds\guzo_service_account.json"

# 🔒 Define API scope (read-only Drive access)
scopes = ["https://www.googleapis.com/auth/drive.readonly"]

try:
    # ✅ Build the credentials
    creds = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=scopes
    )

    # ✅ Build the Drive API service
    service = build("drive", "v3", credentials=creds)

    print("🔍 Testing Drive API connection...")

    # ✅ Make a small test query
    results = service.files().list(pageSize=5).execute()
    files = results.get("files", [])

    if not files:
        print("⚠️ No files found or access restricted.")
    else:
        print(f"✅ Drive API working! Found {len(files)} files:")
        for f in files:
            print("   -", f["name"])

except FileNotFoundError:
    print("❌ Error: Service account JSON file not found at this path:")
    print(f"   {creds_path}")
    print("   → Please verify the path is correct.")
except HttpError as error:
    print("❌ Google API returned an error:")
    print(error)
    print("\n👉 Tip: If it says 'API has not been used in project before', open:")
    print("   https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=662408224209")
    print("   Enable the Drive API for this project, wait 1–2 minutes, and retry.")
except Exception as e:
    print("⚠️ Unexpected error occurred:")
    print(e)
