import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys

# --- Configuration ---
# Define the scope for Google Sheets API access
# This scope allows read/write access to all your Google Sheets files
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


# --- Authentication Function ---
def authenticate_gspread():
    """
    Authenticates with Google Sheets API using either a service account or OAuth 2.0.
    Prompts the user to choose the authentication method.

    Returns:
        gspread.Client: An authenticated gspread client object.
    """
    print("\n--- Google Sheets Authentication ---")
    print("Choose your authentication method:")
    print("1. Service Account (Recommended for automation, requires a JSON key file)")
    print("2. OAuth 2.0 (Recommended for personal use, requires browser interaction)")

    while True:
        auth_choice = input("Enter your choice (1 or 2): ").strip()
        if auth_choice == '1':
            return authenticate_service_account()
        elif auth_choice == '2':
            return authenticate_oauth2()
        else:
            print("Invalid choice. Please enter '1' or '2'.")


def authenticate_service_account():
    """
    Authenticates using a service account JSON key file.

    Returns:
        gspread.Client: An authenticated gspread client object.
    """
    while True:
        json_key_path = input("Enter the path to your service account JSON key file: ").strip()
        if not os.path.exists(json_key_path):
            print(f"Error: File not found at '{json_key_path}'. Please check the path.")
            continue
        try:
            # Use ServiceAccountCredentials to create credentials from the JSON key file
            creds = ServiceAccountCredentials.from_json_keyfile_name(json_key_path, SCOPES)
            # Authorize the gspread client with the obtained credentials
            client = gspread.authorize(creds)
            print("Service account authentication successful!")
            return client
        except Exception as e:
            print(f"Service account authentication failed: {e}")
            print("Please ensure the JSON key file is valid and has the correct permissions.")
            # If authentication fails, prompt again or exit
            sys.exit(1)  # Exit if service account auth fails


def authenticate_oauth2():
    """
    Authenticates using OAuth 2.0, opening a browser for user consent.
    Stores credentials in 'token.json' for future use.

    Returns:
        gspread.Client: An authenticated gspread client object.
    """
    # Import necessary modules for OAuth 2.0 here to avoid unnecessary imports
    # if service account is chosen.
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Ensure 'credentials.json' (client_secret.json renamed) is present
            if not os.path.exists('credentials.json'):
                print("Error: 'credentials.json' not found. Please download your OAuth 2.0 client configuration.")
                print("Refer to the instructions on how to get 'credentials.json' for OAuth 2.0.")
                sys.exit(1)  # Exit if credentials.json is missing

            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    client = gspread.authorize(creds)
    print("OAuth 2.0 authentication successful!")
    return client


# --- Get Sheet Data Function ---
def get_sheet_data(client):
    """
    Prompts the user for Google Sheet ID and sheet name, then reads data.

    Args:
        client (gspread.Client): Authenticated gspread client.

    Returns:
        tuple: A tuple containing (gspread.Worksheet object, list of lists representing all data).
               Returns (None, None) if the sheet or worksheet is not found.
    """
    while True:
        sheet_id = input("Enter the Google Sheet ID (from the URL): ").strip()
        sheet_name = input("Enter the specific sheet name (tab name): ").strip()

        try:
            # Open the spreadsheet by its ID
            spreadsheet = client.open_by_key(sheet_id)
            # Select the specific worksheet by name
            worksheet = spreadsheet.worksheet(sheet_name)
            # Get all values from the worksheet
            all_data = worksheet.get_all_values()
            print(f"Successfully read data from '{sheet_name}' in spreadsheet ID '{sheet_id}'.")
            return worksheet, all_data
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"Error: Spreadsheet with ID '{sheet_id}' not found. Please check the ID.")
        except gspread.exceptions.WorksheetNotFound:
            print(f"Error: Worksheet '{sheet_name}' not found in the spreadsheet. Please check the sheet name.")
        except Exception as e:
            print(f"An unexpected error occurred while accessing the sheet: {e}")

        retry = input("Do you want to try again? (yes/no): ").strip().lower()
        if retry != 'yes':
            return None, None


# --- Find Duplicates Logic ---
def find_duplicates(data, case_sensitive=False):
    """
    Identifies duplicate rows based on Column A and Column B, keeping the first occurrence.

    Args:
        data (list of lists): The data from the Google Sheet.
        case_sensitive (bool): If True, comparisons are case-sensitive. Default is False.

    Returns:
        tuple: A tuple containing:
               - list: Indices of rows to be deleted (0-indexed).
               - int: Total number of duplicate entries found.
               - list of lists: The data with duplicates removed.
    """
    if not data:
        return [], 0, []

    # Assuming Column A is index 0 and Column B is index 1
    col_a_idx = 0
    col_b_idx = 1

    unique_combinations = set()
    rows_to_keep = []
    rows_to_delete_indices = []
    duplicate_count = 0

    # Iterate through data starting from the second row if there's a header (all_values includes header)
    # If your sheet has no header, adjust this logic.
    # For simplicity, we'll assume the first row is data or header and start checking from there.
    for i, row in enumerate(data):
        # Ensure row has at least two columns
        if len(row) < 2:
            rows_to_keep.append(row)  # Keep rows that don't have enough columns
            continue

        # Get values from Column A and B
        val_a = str(row[col_a_idx]).strip()
        val_b = str(row[col_b_idx]).strip()

        # Apply case sensitivity logic
        if not case_sensitive:
            val_a = val_a.lower()
            val_b = val_b.lower()

        # Create a tuple for the combination to use in the set
        combination = (val_a, val_b)

        if combination in unique_combinations:
            # This is a duplicate, mark for deletion
            rows_to_delete_indices.append(i)
            duplicate_count += 1
        else:
            # This is a unique combination, add to set and keep the row
            unique_combinations.add(combination)
            rows_to_keep.append(row)

    return rows_to_delete_indices, duplicate_count, rows_to_keep


# --- Main Execution ---
def main():
    """
    Main function to orchestrate the duplicate deletion process.
    """
    print("--- Google Sheet Duplicate Deleter ---")

    # 1. Authenticate
    client = authenticate_gspread()
    if not client:
        print("Authentication failed. Exiting.")
        return

    # 2. Get Sheet Data
    worksheet, all_data = get_sheet_data(client)
    if not worksheet or not all_data:
        print("Could not retrieve sheet data. Exiting.")
        return

    if not all_data:
        print("The sheet is empty. No duplicates to check.")
        return

    # Determine if the first row is a header
    has_header = False
    header_choice = input("Does your sheet have a header row? (yes/no): ").strip().lower()
    if header_choice == 'yes':
        has_header = True
        header_row = all_data[0]
        data_to_process = all_data[1:]  # Exclude header for duplicate checking
    else:
        header_row = []  # No header
        data_to_process = all_data  # Process all rows

    # 3. Case sensitivity option
    case_sensitive_choice = input(
        "Perform case-sensitive comparison for columns A and B? (yes/no, default is no): ").strip().lower()
    case_sensitive = True if case_sensitive_choice == 'yes' else False

    # 4. Find Duplicates
    # The indices returned here are relative to `data_to_process`
    rows_to_delete_relative_indices, duplicate_count, cleaned_data_rows = find_duplicates(data_to_process,
                                                                                          case_sensitive)

    if duplicate_count == 0:
        print("\nNo duplicate entries found in Column A and Column B.")
        return

    print(f"\nFound {duplicate_count} duplicate row(s) based on Column A and Column B.")

    # 5. User Confirmation
    while True:
        confirmation = input("Do you want to proceed with deleting these duplicate rows? (yes/no): ").strip().lower()
        if confirmation == 'yes':
            break
        elif confirmation == 'no':
            print("Deletion cancelled by user. No changes were made to the sheet.")
            return
        else:
            print("Invalid input. Please type 'yes' or 'no'.")

    # 6. Perform Deletion (Efficiently)
    try:
        print("\nDeleting duplicate rows...")

        # If there's a header, prepend it to the cleaned data
        final_data_to_write = []
        if has_header:
            final_data_to_write.append(header_row)
        final_data_to_write.extend(cleaned_data_rows)

        # Clear the entire sheet and then write the cleaned data back.
        # This is generally more robust and efficient than deleting rows one by one,
        # especially for larger sheets or many deletions, as it avoids indexing issues.
        worksheet.clear()  # Clears all cells in the worksheet
        worksheet.update(final_data_to_write)  # Writes the new data back

        print(f"Successfully deleted {duplicate_count} duplicate row(s).")
        print("The sheet has been updated with unique entries.")

    except Exception as e:
        print(f"An error occurred during deletion: {e}")
        print("Please check your permissions and try again.")


if __name__ == "__main__":
    main()
