import urllib.request
import xmlrpc.client
import json
import csv
import os
import time

OUTPUT_FILE = "data/pypi.csv"
MAX_PACKAGES = 1000 # Adjust this to get more or less data
PYPI_RPC_URL = "https://pypi.org/pypi"

def extract_pypi_to_csv():
    os.makedirs("data", exist_ok=True)
    
    headers = [
        "Package Name", 
        "Version", 
        "Official Link", 
        "Creator", 
        "Creator Profile Link", 
        "Description"
    ]

    print("[PyPI] Connecting to XML-RPC to get package list...")
    try:
        client = xmlrpc.client.ServerProxy(PYPI_RPC_URL)
        # Gets ALL 500k+ package names in one go!
        all_packages = client.list_packages() 
    except Exception as e:
        print(f"[PyPI] Error getting package list: {e}")
        return

    print(f"[PyPI] Total packages found: {len(all_packages)}. Will extract metadata for top {MAX_PACKAGES}.")

    total_fetched = 0

    with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)

        # Iterate through the massive list, up to our safe MAX limit
        for pkg_name in all_packages[:MAX_PACKAGES]:
            url = f"https://pypi.org/pypi/{pkg_name}/json"
            
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'OSMA-Bulk-Bot'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                    
                info = data.get("info", {})
                
                version = info.get("version", "")
                desc = info.get("summary", "").replace("\n", " ")
                official_link = info.get("package_url", f"https://pypi.org/project/{pkg_name}/")
                
                # PyPI API usually returns author name and email, but no direct "profile URL"
                # So we link to their email or their listed project url as a fallback
                creator_name = info.get("author", "Unknown")
                if not creator_name or creator_name == "UNKNOWN":
                    creator_name = info.get("maintainer", "Unknown")
                    
                creator_link = info.get("author_email", "N/A")
                if creator_link != "N/A":
                    creator_link = f"mailto:{creator_link}"
                
                writer.writerow([
                    pkg_name,
                    version,
                    official_link,
                    creator_name,
                    creator_link,
                    desc
                ])
                total_fetched += 1
                
            except urllib.error.HTTPError as e:
                # 404s happen occasionally if a package was deleted but still listed
                pass
            except Exception as e:
                print(f"[PyPI] Error processing {pkg_name}: {e}")
            
            # Print progress every 100 items
            if total_fetched % 100 == 0:
                print(f"[PyPI] Processed {total_fetched} / {MAX_PACKAGES}...")
                
            time.sleep(0.1) # Be gentle to PyPI's API

    print(f"[PyPI] Successfully wrote {total_fetched} packages to {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_pypi_to_csv()
