import urllib.request
import json
import csv
import os
import time

OUTPUT_FILE = "data/npmjs.csv"
MAX_PACKAGES = 1000  # Adjust this to get more or less data

# Changed 'not:deprecated' to 'javascript' to guarantee tens of thousands of results
SEARCH_API = "https://registry.npmjs.org/-/v1/search?text=javascript&size=250&from={}"

def extract_npm_to_csv():
    os.makedirs("data", exist_ok=True)
    
    # Define CSV Headers
    headers = [
        "Package Name", 
        "Version", 
        "Official Link", 
        "Creator", 
        "Creator Profile Link", 
        "Description"
    ]

    print(f"[NPM] Starting extraction of up to {MAX_PACKAGES} packages...")

    total_fetched = 0
    offset = 0

    with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)

        while total_fetched < MAX_PACKAGES:
            url = SEARCH_API.format(offset)
            print(f"[NPM] Fetching offset {offset}...")
            
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'OSMA-Bulk-Bot'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
            except Exception as e:
                print(f"[NPM] API Error: {e}")
                time.sleep(5)
                break # Stop on error

            objects = data.get("objects", [])
            if not objects:
                print("[NPM] No more results found.")
                break # No more results

            for item in objects:
                if total_fetched >= MAX_PACKAGES:
                    break
                    
                pkg = item.get("package", {})
                
                name = pkg.get("name", "")
                version = pkg.get("version", "")
                desc = pkg.get("description", "").replace("\n", " ") # Clean newlines
                
                official_link = pkg.get("links", {}).get("npm", f"https://www.npmjs.com/package/{name}")
                
                # Try to safely extract creator data
                creator_name = "Unknown"
                creator_link = "N/A"
                author = pkg.get("author")
                
                if isinstance(author, dict) and "name" in author:
                    creator_name = author["name"]
                    creator_link = f"https://www.npmjs.com/~{author.get('username', creator_name.replace(' ', ''))}"
                elif "publisher" in pkg:
                    creator_name = pkg["publisher"].get("username", "Unknown")
                    creator_link = f"https://www.npmjs.com/~{creator_name}"

                writer.writerow([
                    name,
                    version,
                    official_link,
                    creator_name,
                    creator_link,
                    desc
                ])
                
                total_fetched += 1
                
            offset += 250
            time.sleep(0.5) # Be gentle to the API

    print(f"[NPM] Successfully wrote {total_fetched} packages to {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_npm_to_csv()
