"""
Quick script to check your Google Sheet structure
This will show you exactly what's in each column
"""

import gspread
from google.oauth2.service_account import Credentials

# Configuration
CREDS_FILE = 'credentials.json'
SHEET_NAME = 'songs'
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive'
]


def check_sheet_structure():
    """Check and display the structure of your Google Sheet."""

    try:
        print("🔍 Checking Google Sheet structure...")
        print("=" * 50)

        # Connect to Google Sheets
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=GOOGLE_SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1

        # Get first 5 rows to analyze structure
        rows = sheet.get_all_values()[:5]

        if not rows:
            print("❌ Sheet is empty")
            return

        print(f"📊 Sheet '{SHEET_NAME}' has {len(sheet.get_all_values())} total rows")
        print("\n📋 Column Structure:")

        # Show headers
        headers = rows[0]
        for i, header in enumerate(headers):
            column_letter = chr(65 + i)  # A, B, C, etc.
            print(f"   Column {column_letter}: '{header}'")

        print("\n📝 Sample Data (first 3 rows):")
        for row_num, row in enumerate(rows[1:4], 2):
            print(f"\n   Row {row_num}:")
            for i, value in enumerate(row):
                column_letter = chr(65 + i)
                print(f"     {column_letter}: '{value}'")

        print("\n" + "=" * 50)
        print("✅ Analysis complete!")

        # Provide recommendations
        print("\n💡 Based on your sheet structure:")
        if len(headers) >= 2:
            print(f"   - Column A ('{headers[0]}') appears to be: Artist")
            print(f"   - Column B ('{headers[1]}') appears to be: Song Title")
            if len(headers) >= 3:
                print(f"   - Column C ('{headers[2]}') appears to be: {headers[2]}")

        print("\n🔧 For the music automation script:")
        print("   - Make sure Column A = Artist names")
        print("   - Make sure Column B = Song titles")
        print("   - Links will be added to columns F and G")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    check_sheet_structure()
    input("\nPress Enter to exit...")
