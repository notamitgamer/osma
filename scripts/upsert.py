import json
import os
import time

CHUNK_SIZE = 2000

def ensure_data_dirs():
    os.makedirs("data/npm", exist_ok=True)
    os.makedirs("data/pypi", exist_ok=True)

def load_json(filepath, default):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return default

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def get_chunk_filename(package_no):
    chunk_index = (package_no - 1) // CHUNK_SIZE
    start = chunk_index * CHUNK_SIZE + 1
    end = (chunk_index + 1) * CHUNK_SIZE
    return f"chunk_{start:06d}_{end:06d}.jsonl"

def update_ecosystem(ecosystem_name, extract_file):
    print(f"[Upsert] Processing {ecosystem_name}...")
    
    data_dir = f"data/{ecosystem_name}"
    manifest_file = os.path.join(data_dir, "manifest.json")
    index_file = os.path.join(data_dir, "index.json")

    manifest = load_json(manifest_file, {
        "total_packages": 0,
        "total_chunks": 0,
        "chunk_size": CHUNK_SIZE,
        "last_etl_run": "",
        "chunk_url_pattern": f"data/{ecosystem_name}/{{chunk_name}}"
    })
    
    pkg_index = load_json(index_file, {})
    
    # Save base files immediately so stats sync can read them even if empty
    manifest["last_etl_run"] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    save_json(manifest_file, manifest)
    save_json(index_file, pkg_index)

    if not os.path.exists(extract_file):
        print(f"[Upsert] No extraction file for {ecosystem_name}, skipping updates.")
        return

    extracted_data = load_json(extract_file, [])

    if not extracted_data:
        print(f"[Upsert] {ecosystem_name} extract is empty.")
        return

    # Group updates by chunk to minimize file IO
    chunk_updates = {}

    for pkg in extracted_data:
        pkg_name = pkg["package_name"]
        index_key = f"{ecosystem_name}:{pkg_name}"
        
        is_new = False
        if index_key in pkg_index:
            package_no = pkg_index[index_key]
        else:
            manifest["total_packages"] += 1
            package_no = manifest["total_packages"]
            pkg_index[index_key] = package_no
            is_new = True

        pkg["package_no"] = package_no
        chunk_file = get_chunk_filename(package_no)
        chunk_path = os.path.join(data_dir, chunk_file)

        if chunk_path not in chunk_updates:
            # Load existing chunk
            existing_rows = {}
            if os.path.exists(chunk_path):
                with open(chunk_path, "r") as f:
                    for line in f:
                        if line.strip():
                            row = json.loads(line)
                            existing_rows[row["package_no"]] = row
            chunk_updates[chunk_path] = existing_rows

        if not is_new and package_no in chunk_updates[chunk_path]:
            # Retain original first_seen
            pkg["first_seen"] = chunk_updates[chunk_path][package_no].get("first_seen", pkg["first_seen"])

        # Upsert into memory chunk
        chunk_updates[chunk_path][package_no] = pkg

    # Write modified chunks back to disk
    for chunk_path, rows_dict in chunk_updates.items():
        sorted_rows = [rows_dict[k] for k in sorted(rows_dict.keys())]
        with open(chunk_path, "w") as f:
            for row in sorted_rows:
                f.write(json.dumps(row) + "\n")

    manifest["total_chunks"] = (manifest["total_packages"] + CHUNK_SIZE - 1) // CHUNK_SIZE
    manifest["last_etl_run"] = time.strftime('%Y-%m-%dT%H:%M:%SZ')

    save_json(manifest_file, manifest)
    save_json(index_file, pkg_index)
    
    print(f"[Upsert] {ecosystem_name} complete. Total packages: {manifest['total_packages']}. Modified {len(chunk_updates)} chunks.")

def main():
    ensure_data_dirs()
    update_ecosystem("npm", "state/npm_extract.json")
    update_ecosystem("pypi", "state/pypi_extract.json")

if __name__ == "__main__":
    main()
