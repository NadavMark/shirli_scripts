"""
Test script to verify the fixes work correctly
"""

import logging
from ultimate_scraper import UltimateGuitarScraper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_google_sheets_update():
    """Test Google Sheets update functionality"""
    try:
        CREDENTIALS_PATH = "path/to/your/service-account-key.json"  # Update this
        SHEET_URL = "your_google_sheet_url_here"  # Update this

        scraper = UltimateGuitarScraper(CREDENTIALS_PATH, SHEET_URL)

        # Test updating a cell (use a test row)
        test_row = 100  # Use a row that won't interfere with your data
        test_url = "https://test-url.com"

        print("Testing Google Sheets update...")
        scraper.update_chord_cell(test_row, test_url)

        # Verify the update
        cell_value = scraper.sheet.cell(test_row, 6).value
        if cell_value == test_url:
            print("✅ Google Sheets update test PASSED")
        else:
            print(f"❌ Google Sheets update test FAILED. Expected: {test_url}, Got: {cell_value}")

        # Clean up test
        scraper.sheet.update_cell(test_row, 6, "")
        scraper.cleanup()

    except Exception as e:
        print(f"❌ Google Sheets test failed: {e}")


def test_webdriver_connection():
    """Test WebDriver connection and search"""
    try:
        CREDENTIALS_PATH = "path/to/your/service-account-key.json"  # Update this
        SHEET_URL = "your_google_sheet_url_here"  # Update this

        scraper = UltimateGuitarScraper(CREDENTIALS_PATH, SHEET_URL)

        print("Testing WebDriver search...")
        result = scraper.search_ultimate_guitar("Nat King Cole", "Unforgettable")

        if result:
            print(f"✅ WebDriver search test PASSED. Found: {result}")
        else:
            print("⚠️ WebDriver search test completed but no results found (this might be normal)")

        scraper.cleanup()

    except Exception as e:
        print(f"❌ WebDriver test failed: {e}")


if __name__ == "__main__":
    print("Running fix verification tests...\n")

    print("1. Testing Google Sheets update fix:")
    test_google_sheets_update()

    print("\n2. Testing WebDriver connection fix:")
    test_webdriver_connection()

    print("\nTest completed!")
