import json
import os
import time

def main():
    os.makedirs("stats", exist_ok=True)
    
    global_stats = {
        "generated_at": time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "ecosystems": {}
    }

    total_pkgs = 0

    for eco in ["npm", "pypi"]:
        manifest_path = f"data/{eco}/manifest.json"
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                data = json.load(f)
                global_stats["ecosystems"][eco] = {
                    "total_packages": data.get("total_packages", 0),
                    "total_chunks": data.get("total_chunks", 0),
                    "last_updated": data.get("last_etl_run", "")
                }
                total_pkgs += data.get("total_packages", 0)

    global_stats["grand_total_packages"] = total_pkgs

    with open("stats/global_stats.json", "w") as f:
        json.dump(global_stats, f, indent=2)

    print(f"[Stats] Synced global stats. Grand total: {total_pkgs} packages.")

if __name__ == "__main__":
    main()