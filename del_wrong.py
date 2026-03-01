import os
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def trim_csv_files(data_dir: str = "data", count: int = 50, position: str = "last"):
    """Removes the first or last N records from all CSV files in data_dir, preserving the header."""
    if not os.path.isdir(data_dir):
        logging.error(f"Directory {data_dir} not found.")
        return

    csv_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    logging.info(f"Found {len(csv_files)} files in {data_dir}. Trimming {count} records from the {position}...")

    processed_count = 0
    for file_name in csv_files:
        file_path = os.path.join(data_dir, file_name)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if not lines:
                continue

            header = lines[0]
            data = lines[1:]
            
            # Trimming logic
            if position == "last":
                if len(data) > count:
                    new_data = data[:-count]
                else:
                    new_data = []
            else: # position == "first"
                if len(data) > count:
                    new_data = data[count:]
                else:
                    new_data = []

            # Combine header back with remaining data
            final_content = [header] + new_data
            
            with open(file_path, "w", encoding="utf-8", newline="") as f:
                f.writelines(final_content)
            
            processed_count += 1
            if processed_count % 100 == 0:
                logging.info(f"Processed {processed_count} files...")

        except Exception as e:
            logging.error(f"Error processing {file_name}: {e}")

    logging.info(f"Operation complete. Successfully trimmed {processed_count} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch trim CSV records from files in a directory.")
    parser.add_argument("--dir", default="data", help="Directory containing CSV files (default: data)")
    parser.add_argument("--count", type=int, default=50, help="Number of records to remove (default: 50)")
    parser.add_argument("--pos", choices=["first", "last"], default="last", help="Remove records from the 'first' or 'last' (default: last)")
    
    args = parser.parse_args()
    trim_csv_files(data_dir=args.dir, count=args.count, position=args.pos)
