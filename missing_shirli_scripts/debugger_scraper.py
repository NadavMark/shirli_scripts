"""
Debug script to examine the Google Sheet structure and data
to help identify column mapping and data issues.
"""

import gspread
from google.oauth2.service_account import Credentials


def debug_sheet_structure(credentials_file: str, sheet_name: str):
    """Debug the Google Sheet structure and content."""

    try:
        # Setup connection
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]

        creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
        gc = gspread.authorize(creds)
        worksheet = gc.open(sheet_name).sheet1

        print("╔══════════════════════════════════════════════════════════════════════════════╗")
        print("║                        GOOGLE SHEET DEBUG INFO                              ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝")

        # Basic info
        print(f"📊 Sheet Name: {sheet_name}")
        print(f"📏 Dimensions: {worksheet.row_count} rows × {worksheet.col_count} columns")

        # Headers
        headers = worksheet.row_values(1)
        print(f"\n📋 Column Headers ({len(headers)} columns):")
        for i, header in enumerate(headers, 1):
            print(f"  {chr(64 + i)}: '{header}'")

        # Sample data from first 10 rows
        print(f"\n📝 Sample Data (first 10 rows):")
        print("-" * 80)

        for row_num in range(1, min(11, worksheet.row_count + 1)):
            row_data = worksheet.row_values(row_num)

            if row_num == 1:
                print(f"Row {row_num} (HEADER): {row_data}")
            else:
                # Show only first few columns to avoid clutter
                display_data = row_data[:5] if len(row_data) > 5 else row_data
                if len(row_data) > 5:
                    display_data.append(f"... (+{len(row_data) - 5} more)")

                print(f"Row {row_num}: {display_data}")

                # Check for Hebrew text
                has_hebrew = any(any('\u0590' <= char <= '\u05FF' for char in str(cell))
                                 for cell in row_data if cell)
                if has_hebrew:
                    print(f"      ✡️  Contains Hebrew text")

        # Analyze data patterns
        print(f"\n🔍 Data Analysis:")

        # Count non-empty rows
        non_empty_rows = 0
        hebrew_rows = 0
        english_rows = 0

        all_data = worksheet.get_all_values()
        for i, row in enumerate(all_data[1:], 2):  # Skip header
            if any(cell.strip() for cell in row):
                non_empty_rows += 1

                # Check for Hebrew
                row_text = ' '.join(row)
                if any('\u0590' <= char <= '\u05FF' for char in row_text):
                    hebrew_rows += 1
                elif any(char.isalpha() for char in row_text):
                    english_rows += 1

        print(f"  📊 Non-empty rows: {non_empty_rows}")
        print(f"  🇮🇱 Rows with Hebrew: {hebrew_rows}")
        print(f"  🇺🇸 Rows with English: {english_rows}")

        # Column K status
        print(f"\n📍 Column K (Target column) status:")
        k_values = worksheet.col_values(11)  # Column K
        k_filled = sum(1 for val in k_values[1:] if val.strip())  # Skip header
        print(f"  📝 Already filled: {k_filled} cells")
        print(f"  📄 Empty: {len(k_values) - 1 - k_filled} cells")

        if k_filled > 0:
            print(f"  🔗 Sample filled values:")
            for i, val in enumerate(k_values[1:6], 2):  # Show first 5
                if val.strip():
                    print(f"    Row {i}: {val}")

        print("\n" + "=" * 80)
        print("💡 Recommendations:")

        if hebrew_rows > english_rows:
            print("  • Most data appears to be in Hebrew - ensure proper encoding")

        if len(headers) > 2:
            print("  • Multiple columns detected - verify artist/song column mapping")

        print("  • Check rows 2-3 specifically as they showed warnings")
        print("  • Consider running on a small subset first (5-10 rows)")

    except Exception as e:
        print(f"❌ Error debugging sheet: {e}")


def main():
    """Run the debug analysis."""

    # Configuration - UPDATE THESE PATHS
    CREDENTIALS_FILE = "credentials.json"  # Update this
    SHEET_NAME = "songs"  # Update this

    debug_sheet_structure(CREDENTIALS_FILE, SHEET_NAME)


if __name__ == "__main__":
    main()
