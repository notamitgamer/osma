import os
import csv
import urllib.request
import json
import time

def fetch_and_format_npm_names():
    """
    Fetches the complete list of NPM package names from the community registry mirror
    and formats them for the OSMA Explorer.
    Note: This method is incredibly fast and avoids BigQuery permission issues.
    """
    output_path = "data/npm.csv"
    os.makedirs("data", exist_ok=True)
    
    # We use a reliable, daily-updated JSON mirror of the NPM registry names
    url = "https://raw.githubusercontent.com/nice-registry/all-the-package-names/master/names.json"
    
    print(f"🌐 Fetching master NPM package list...")
    print(f"URL: {url}")
    print("⏳ Downloading (This is usually ~30MB, please wait...)")
    
    try:
        start_time = time.time()
        
        # Download the JSON array of names
        req = urllib.request.Request(url, headers={'User-Agent': 'OSMA-Extractor'})
        with urllib.request.urlopen(req) as response:
            package_names = json.loads(response.read().decode('utf-8'))
            
        fetch_time = time.time() - start_time
        print(f"✅ Download complete in {fetch_time:.2f} seconds!")
        print(f"📦 Found {len(package_names):,} NPM packages.")
        
        print(f"\n📝 Formatting and writing to {output_path}...")
        
        with open(output_path, mode='w', encoding='utf-8', newline='') as outfile:
            writer = csv.writer(outfile)
            # Header matching the HTML explorer's expected format
            writer.writerow(['No.', 'Package Name', 'Version', 'Official Link'])
            
            for i, name in enumerate(package_names, 1):
                # We default version to 'latest' since bulk fetching 3.5M versions 
                # individually would take hours via the NPM API.
                version = "latest" 
                link = f"https://www.npmjs.com/package/{name}"
                
                writer.writerow([i, name, version, link])
                
                if i % 500000 == 0:
                    print(f"   Saved {i:,} packages...")

        print(f"\n🎉 Success! Cleaned file instantly created: {os.path.abspath(output_path)}")
        
    except Exception as e:
        print(f"❌ Error fetching NPM data: {e}")
        print("Please check your internet connection or try again later.")

if __name__ == "__main__":
    fetch_and_format_npm_names()