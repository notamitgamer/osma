import os
import csv
import re
import urllib.request
import json

def normalize_pypi_name(name):
    """
    Normalizes PyPI package names according to PEP 503.
    (e.g. 'Django-Auth' == 'django.auth' == 'django_auth' == 'django-auth')
    """
    return re.sub(r"[-_.]+", "-", str(name)).lower()

def filter_deleted_packages(input_csv):
    """
    Cross-references the local CSV against PyPI's active master list.
    Removes packages that have been deleted from PyPI.
    """
    # Temporary file to stream the kept records into
    temp_output = "data/pypi_temp_active.csv"
    
    print("\n🌐 [PyPI Simple API] Fetching master list of active packages...")
    try:
        req = urllib.request.Request(
            'https://pypi.org/simple/', 
            headers={'Accept': 'application/vnd.pypi.simple.v1+json'}
        )
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
            # Create a set of normalized active package names for O(1) instant lookup
            print("⏳ Indexing active packages into memory...")
            active_projects = {normalize_pypi_name(proj["name"]) for proj in data.get("projects", [])}
            
        print(f"✅ Found {len(active_projects):,} currently active packages on PyPI.")
        
    except Exception as e:
        print(f"❌ Failed to fetch PyPI active list: {e}")
        return

    print(f"\n📖 Reading local database: {input_csv}")
    print("⏳ Filtering out deleted packages...")

    kept_count = 0
    deleted_count = 0

    try:
        with open(input_csv, mode='r', encoding='utf-8') as infile, \
             open(temp_output, mode='w', encoding='utf-8', newline='') as outfile:
            
            reader = csv.DictReader(infile)
            writer = csv.writer(outfile)
            
            # Write headers
            writer.writerow(['No.', 'Package Name', 'Version', 'Official Link'])
            
            for row in reader:
                original_name = row.get('Package Name')
                if not original_name:
                    continue
                    
                normalized = normalize_pypi_name(original_name)
                
                # Check if the package is in the active master list
                if normalized in active_projects:
                    kept_count += 1
                    # Re-number the "No." column so it stays sequential
                    writer.writerow([kept_count, original_name, row.get('Version', ''), row.get('Official Link', '')])
                else:
                    deleted_count += 1
                    
        # Replace the old file with the new cleaned file safely
        os.replace(temp_output, input_csv)
        
        print(f"\n🎉 Deletion filter complete!")
        print(f"   🟢 Kept (Active):   {kept_count:,}")
        print(f"   🔴 Removed (Del):   {deleted_count:,}")
        print(f"📂 Updated file saved at: {input_csv}")

    except Exception as e:
        print(f"❌ Error during filtering: {e}")
        # Clean up temp file if something goes wrong
        if os.path.exists(temp_output):
            os.remove(temp_output)

if __name__ == "__main__":
    # Ensure the script looks for the CSV in the 'data' folder
    FORMATTED_CSV_PATH = "data/pypi.csv"
    
    if os.path.exists(FORMATTED_CSV_PATH):
        filter_deleted_packages(FORMATTED_CSV_PATH)
    else:
        print(f"❌ Cannot filter: '{FORMATTED_CSV_PATH}' does not exist.")
        print("Please ensure your CSV is located at data/pypi.csv relative to this script.")