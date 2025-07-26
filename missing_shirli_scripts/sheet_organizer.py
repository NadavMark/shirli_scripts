import gspread
import pandas as pd
from collections import defaultdict
import re

# --- Configuration ---
# Updated names as requested
SPREADSHEET_NAME = 'songs'
WORKSHEET_NAME = 'songs'
OUTPUT_WORKSHEET_NAME = 'Cleaned_Songs_Data'  # New tab name for cleaned data

# --- Google Sheets API Authentication ---
try:
    # Authenticate with Google Sheets using the service account key file
    # Changed filename to 'credentials.json' as requested
    gc = gspread.service_account(filename='credentials.json')
    spreadsheet = gc.open(SPREADSHEET_NAME)
    worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    print(f"Successfully connected to spreadsheet '{SPREADSHEET_NAME}' and worksheet '{WORKSHEET_NAME}'.")
except gspread.exceptions.SpreadsheetNotFound:
    print(f"Error: Spreadsheet '{SPREADSHEET_NAME}' not found. Please check the name.")
    exit()
except gspread.exceptions.WorksheetNotFound:
    print(f"Error: Worksheet '{WORKSHEET_NAME}' not found in spreadsheet '{SPREADSHEET_NAME}'. Please check the name.")
    exit()
except Exception as e:
    print(f"An error occurred during Google Sheets authentication or connection: {e}")
    print("Please ensure 'credentials.json' is in the same directory and has the correct permissions.")
    exit()

# Fetch all values from the worksheet
all_values = worksheet.get_all_values()

if not all_values:
    print("No data found in the worksheet. Exiting.")
    exit()

# The first row is assumed to be headers.
# We'll create unique headers if there are duplicates or blanks.
original_headers = [header.strip() if header.strip() != '' else f'Unnamed_Col_{i}' for i, header in
                    enumerate(all_values[0])]

# Ensure headers are unique even if they were named the same
unique_headers = []
counts = defaultdict(int)
for header in original_headers:
    original_name = header
    temp_header = header
    while temp_header in unique_headers:  # If this header name already exists
        counts[original_name] += 1
        temp_header = f"{original_name}_{counts[original_name]}"
    unique_headers.append(temp_header)

# Create DataFrame from the rest of the values with our unique headers
# Ensure there are rows beyond headers, otherwise df will be empty
if len(all_values) > 1:
    df = pd.DataFrame(all_values[1:], columns=unique_headers)
else:
    print("No data rows found beyond the header. Exiting.")
    exit()

print("\n--- Original DataFrame Head ---")
print(df.head())
print("\nOriginal Columns (after initial processing):", df.columns.tolist())

# --- 1. Standardize Column Names and Consolidate Data ---
# Map possible column names to their desired unified names
column_mapping = {
    'title': 'שם השיר', 'שם השיר': 'שם השיר',
    'artist': 'אמן', 'אמן': 'אמן',
    'tags': 'תגיות', 'תגיות': 'תגיות', 'subject': 'תגיות',
    'youtube': 'קישור YouTube',  # Explicit YouTube column
    'spotify': 'קישור Spotify',  # Explicit Spotify column
    'הערות': 'הערות/לביקורת', 'needs review': 'הערות/לביקורת'
    # 'links' will be handled contextually based on content
}

# Regex patterns for link detection
YOUTUBE_PATTERN = r'(youtube\.com|youtu\.be)'
SPOTIFY_PATTERN = r'(spotify\.com)'

# Using a dictionary to store temporary consolidated data, mapping (artist, title) to consolidated row data
consolidated_rows = defaultdict(lambda: {
    'אמן': None,
    'שם השיר': None,
    'תגיות': set(),
    'קישור YouTube': set(),
    'קישור Spotify': set(),
    'הערות/לביקורת': set(),
    'other_cols': defaultdict(set)  # To store data from columns not explicitly mapped
})

# Iterate through each row of the original DataFrame
for index, row in df.iterrows():
    # Convert row to dictionary for easier access, and normalize keys
    row_dict = {k.strip().lower(): v for k, v in row.items()}

    current_artist = None
    current_title = None

    # Try to identify primary keys (artist, title) first from explicitly named columns
    for potential_artist_col in ['artist', 'אמן']:
        if potential_artist_col in row_dict and pd.notna(row_dict[potential_artist_col]) and str(
                row_dict[potential_artist_col]).strip() != '':
            current_artist = str(row_dict[potential_artist_col]).strip()
            break

    for potential_title_col in ['title', 'שם השיר']:
        if potential_title_col in row_dict and pd.notna(row_dict[potential_title_col]) and str(
                row_dict[potential_title_col]).strip() != '':
            current_title = str(row_dict[potential_title_col]).strip()
            break

    # Fallback for artist/title from first two columns if not found by explicit names
    # This addresses 'שם האמן' being in column A or B, etc.
    if current_artist is None and len(unique_headers) > 0:
        val_col0 = row_dict.get(unique_headers[0].lower())
        if pd.notna(val_col0) and str(val_col0).strip() != '':
            current_artist = str(val_col0).strip()  # Assume first col might be artist

    if current_title is None and len(unique_headers) > 1:
        val_col1 = row_dict.get(unique_headers[1].lower())
        if pd.notna(val_col1) and str(val_col1).strip() != '' and str(val_col1).strip() != current_artist:
            current_title = str(val_col1).strip()  # Assume second col might be title, if not identical to artist

    # Handle missing essential details and add a note
    row_notes = []
    if not current_artist:
        current_artist = "UNKNOWN ARTIST"
        row_notes.append("Missing Artist details.")
    if not current_title:
        current_title = "UNKNOWN TITLE"
        row_notes.append("Missing Title details.")

    # Use a unique key for consolidation, even with placeholders
    key = (current_artist, current_title)

    # Consolidate data for the current row
    for col_name, value in row_dict.items():
        if pd.notna(value) and str(value).strip() != '':
            value = str(value).strip()

            # --- Link Handling (Columns D, E, F - general links and named link columns) ---
            # Explicitly check for common 'links' or 'unnamed_col_X' which might contain links
            if col_name == 'links' or col_name.startswith('unnamed_col_'):  # Covers columns D,E,F if unnamed
                if re.search(YOUTUBE_PATTERN, value, re.IGNORECASE):
                    consolidated_rows[key]['קישור YouTube'].add(value)
                elif re.search(SPOTIFY_PATTERN, value, re.IGNORECASE):
                    consolidated_rows[key]['קישור Spotify'].add(value)
                else:  # It's a link, but not YouTube/Spotify, or just other text
                    consolidated_rows[key]['other_cols'][col_name].add(value)  # Keep it in its original column

            # Map known columns (if not already handled as specific links)
            elif col_name in column_mapping:
                mapped_name = column_mapping[col_name]
                if mapped_name == 'תגיות':
                    consolidated_rows[key][mapped_name].update(
                        [t.strip() for t in re.split(r'[,\n;]', value) if t.strip()])
                elif mapped_name == 'קישור YouTube':
                    consolidated_rows[key][mapped_name].add(value)
                elif mapped_name == 'קישור Spotify':
                    consolidated_rows[key][mapped_name].add(value)
                elif mapped_name == 'הערות/לביקורת':
                    consolidated_rows[key][mapped_name].add(value)
                # Artist and Title are set initially, avoiding overwrite by general mapping if already set
                elif mapped_name == 'אמן' and consolidated_rows[key]['אמן'] is None:
                    consolidated_rows[key]['אמן'] = value
                elif mapped_name == 'שם השיר' and consolidated_rows[key]['שם השיר'] is None:
                    consolidated_rows[key]['שם השיר'] = value
            else:
                # Add to other_cols if not explicitly mapped and not handled as a link
                consolidated_rows[key]['other_cols'][col_name].add(value)

    # Add notes for missing details
    if row_notes:
        consolidated_rows[key]['הערות/לביקורת'].add('; '.join(row_notes))

    # Ensure artist and title are set on the consolidated row object from the key
    consolidated_rows[key]['אמן'] = current_artist
    consolidated_rows[key]['שם השיר'] = current_title

# Prepare data for final DataFrame
final_data = []
for key, data in consolidated_rows.items():
    row_dict = {
        'אמן': data['אמן'],
        'שם השיר': data['שם השיר'],
        'תגיות': ', '.join(sorted(list(data['תגיות']))),
        'קישור YouTube': ', '.join(sorted(list(data['קישור YouTube']))),
        'קישור Spotify': ', '.join(sorted(list(data['קישור Spotify']))),
        'הערות/לביקורת': ', '.join(sorted(list(data['הערות/לביקורת'])))
    }
    # Add other columns from 'other_cols'
    for col_name, values_set in data['other_cols'].items():
        if col_name not in ['links', 'youtube', 'spotify', 'title', 'artist', 'tags', 'subject', 'הערות',
                            'needs review', 'קישורים']:
            row_dict[col_name] = ', '.join(sorted(list(values_set)))

    final_data.append(row_dict)

# Create the cleaned DataFrame
cleaned_df = pd.DataFrame(final_data)

# --- 2. Sort and Reorder Columns ---
# Define the desired order of columns
desired_column_order = [
    'אמן',
    'שם השיר',
    'תגיות',
    'קישור YouTube',
    'קישור Spotify',
    'הערות/לביקורת'
]

# Get existing columns from the cleaned DataFrame
existing_columns = cleaned_df.columns.tolist()

# Filter desired_column_order to only include columns that actually exist in the DataFrame
final_columns = [col for col in desired_column_order if col in existing_columns]

# Add any other columns that were not explicitly mapped but existed in the original data,
# placing them after the defined core columns.
for col in existing_columns:
    if col not in final_columns:
        # Avoid re-adding original names if their content was consolidated
        # This list ensures columns that were sources for main fields don't reappear as 'other_cols'
        if col not in column_mapping.keys() and not col.startswith(
                'unnamed_col_'):  # Don't add if it's an original mapped col or a generic unnamed (which should have been processed)
            final_columns.append(col)

cleaned_df = cleaned_df[final_columns]

print("\n--- Cleaned DataFrame Head ---")
print(cleaned_df.head())
print("\nCleaned Columns:", cleaned_df.columns.tolist())
print(f"\nOriginal rows: {len(df)} | Cleaned rows: {len(cleaned_df)}")

# --- 3. Write Cleaned Data Back to Google Sheet ---
try:
    # Create a new worksheet for cleaned data, or clear existing if it exists
    try:
        output_worksheet = spreadsheet.worksheet(OUTPUT_WORKSHEET_NAME)
        # Clear existing content (optional, but good for reruns)
        output_worksheet.clear()
        print(f"Cleared existing worksheet '{OUTPUT_WORKSHEET_NAME}'.")
    except gspread.exceptions.WorksheetNotFound:
        output_worksheet = spreadsheet.add_worksheet(title=OUTPUT_WORKSHEET_NAME, rows=str(len(cleaned_df) + 100),
                                                     cols=str(len(cleaned_df.columns) + 5))
        print(f"Created new worksheet '{OUTPUT_WORKSHEET_NAME}'.")

    # Convert DataFrame to a list of lists (including header)
    data_to_write = [cleaned_df.columns.tolist()] + cleaned_df.values.tolist()

    # Update the worksheet with the cleaned data
    output_worksheet.update(data_to_write, range_name='A1')
    print(
        f"\nSuccessfully wrote cleaned data to worksheet '{OUTPUT_WORKSHEET_NAME}' in Google Sheet '{SPREADSHEET_NAME}'.")

except Exception as e:
    print(f"An error occurred while writing data back to Google Sheet: {e}")