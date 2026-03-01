import os
import logging
import argparse
from pathlib import Path
from typing import List, Set

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_csv_files(data_dir: str = "data", mode: str = "trim", 
                    count: int = 50, position: str = "last", stock_id: str = None):
    """
    Processes CSV files in data_dir based on the selected mode.
    Modes:
        - trim: Removes first or last N records.
        - dedup: Removes duplicate date entries.
        - sort: Sorts records by date chronologically.
        - check: Scans for malformed rows (for debugging).
    """
    path = Path(data_dir)
    if not path.is_dir():
        logging.error(f"Directory {data_dir} not found.")
        return

    if stock_id:
        csv_files = [path / f"{stock_id}.csv"]
    else:
        csv_files = sorted(list(path.glob("*.csv")))
        
    logging.info(f"Found {len(csv_files)} files. Mode: {mode.upper()}")

    processed_count = 0
    modified_count = 0

    for file_path in csv_files:
        if not file_path.exists():
            continue
        try:
            with file_path.open("r", encoding="utf-8") as f:
                lines = f.readlines()

            if not lines:
                continue

            header = lines[0]
            data_rows = lines[1:]
            
            new_lines = [header]
            has_changes = False

            if mode == "trim":
                if position == "last":
                    new_data = data_rows[:-count] if len(data_rows) > count else []
                else: # position == "first"
                    new_data = data_rows[count:] if len(data_rows) > count else []
                
                if len(new_data) != len(data_rows):
                    new_lines.extend(new_data)
                    has_changes = True
                else:
                    new_lines.extend(data_rows)

            elif mode == "dedup":
                seen_dates: Set[str] = set()
                deduped_data = []
                for line in data_rows:
                    parts = line.split(",")
                    if not parts or len(parts) < 1: continue
                    date_val = parts[0].strip()
                    if date_val not in seen_dates:
                        seen_dates.add(date_val)
                        deduped_data.append(line)
                    else:
                        has_changes = True
                new_lines.extend(deduped_data)

            elif mode == "sort":
                # Assuming Date is the first column in YYYY-MM-DD format
                data_records = []
                for line in data_rows:
                    if not line.strip(): continue
                    parts = line.split(",")
                    if not parts: continue
                    data_records.append(line)
                
                # Sort by date string (alphabetical sort works for YYYY-MM-DD)
                sorted_data = sorted(data_records, key=lambda x: x.split(",")[0].strip())
                if sorted_data != data_rows:
                    new_lines.extend(sorted_data)
                    has_changes = True
                else:
                    new_lines.extend(data_rows)

            elif mode == "check":
                # Generic malformed detection
                for i, line in enumerate(data_rows):
                    if "--" in line or ",0," in line or not line.strip():
                        logging.warning(f"Malformed at {file_path.name}:{i+2} -> {line.strip()}")

            # Save if changes were made
            if has_changes:
                with file_path.open("w", encoding="utf-8", newline="") as f:
                    f.writelines(new_lines)
                modified_count += 1
            
            processed_count += 1
            if processed_count % 100 == 0:
                logging.info(f"Processed {processed_count} files...")

        except Exception as e:
            logging.error(f"Error processing {file_path.name}: {e}")

    logging.info(f"Operation complete. Processed {processed_count} files, Modified {modified_count} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KDTrace Data Repair Tool")
    parser.add_argument("--dir", default="data", help="Target directory (default: data)")
    parser.add_argument("--sid", help="Specific stock ID to process")
    parser.add_argument("--mode", choices=["trim", "dedup", "sort", "check"], default="trim", help="Action mode")
    parser.add_argument("--count", type=int, default=50, help="[Trim mode] Records to remove")
    parser.add_argument("--pos", choices=["first", "last"], default="last", help="[Trim mode] Position")
    
    args = parser.parse_args()
    process_csv_files(data_dir=args.dir, mode=args.mode, count=args.count, position=args.pos, stock_id=args.sid)
