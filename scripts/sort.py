import os

def sort_and_reindex_csv():
    input_file = "F:\OSMA\data\pypi.csv"
    output_file = "F:\OSMA\data\pypi_sorted.csv"

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    print(f"Reading {input_file} for processing...")
    
    data_rows = []
    header = ""

    # Read the file and separate the ID from the content
    with open(input_file, mode='r', encoding='utf-8') as f:
        header = f.readline() # Capture the header
        for line in f:
            if line.strip():
                try:
                    # Split into [original_id, the_rest_of_the_line]
                    parts = line.split(',', 1)
                    pkg_no = int(parts[0].strip())
                    content = parts[1].lstrip() # Keep the rest of the line (package name, version, etc.)
                    data_rows.append((pkg_no, content))
                except (ValueError, IndexError):
                    continue

    if not data_rows:
        print("No data found to process.")
        return

    # 1. Sort based on the original ID to maintain correct order
    print(f"Sorting {len(data_rows)} rows...")
    data_rows.sort(key=lambda x: x[0])

    # 2. Write back with NEW sequential numbers (1, 2, 3...)
    print(f"Re-indexing and writing to {output_file}...")
    with open(output_file, mode='w', encoding='utf-8') as f:
        f.write(header) # Write original header
        for i, (old_id, content) in enumerate(data_rows, 1):
            # i is our new sequential number
            f.write(f"{i}, {content}")

    total_input = data_rows[-1][0] if data_rows else 0
    total_output = len(data_rows)
    gaps_closed = total_input - total_output

    print(f"✅ Success! Sorted and re-indexed file created.")
    print(f"📊 Summary:")
    print(f"   - Total packages saved: {total_output}")
    print(f"   - Gaps/Missing packages removed: {gaps_closed}")

if __name__ == "__main__":
    sort_and_reindex_csv()
