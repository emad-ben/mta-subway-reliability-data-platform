import requests
import time
import csv
from pathlib import Path

def bucket_rows_by_date(data):
    grouped_by_date = {}

    for row in data:
        current_timestamp = row["transit_timestamp"]
        current_date = current_timestamp[:10]

        if current_date not in grouped_by_date:
            grouped_by_date[current_date] = []
        
        grouped_by_date[current_date].append(row)
    
    return grouped_by_date


def append_to_partition(date_string, rows, output_directory):
    file_path = Path(output_directory)
    file_path = file_path / f"dt={date_string}" / "ridership.csv"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["transit_timestamp", "transit_mode", "station_complex_id", 
                                                "station_complex", "borough", "payment_method", 
                                                "fare_class_category", "ridership", "transfers", 
                                                "latitude", "longitude", "georeference"])
        if file.tell() == 0:
            writer.writeheader()
        
        for row in rows:
            writer.writerow(row)
    
    return file_path

"""
I get the number of riders at a certain station for a certain fare type every hour.
"""

def get_data(start_date, end_date, output_directory):
    offset = 0
    limit = 50_000
    where_clause = f"transit_timestamp between '{start_date}' and '{end_date}'"

    response_empty = False
    while not response_empty:
        url = f"https://data.ny.gov/resource/5wq4-mkjj.json?$limit={limit}&$offset={offset}&$where={where_clause}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=60)
                break
            except requests.exceptions.RequestException as error:
                if (attempt == max_retries - 1):
                    raise RuntimeError(f"Failed request after {max_retries} attempts at offset {offset}") from error
                time.sleep(2)
                continue

        data = response.json()
        print(len(data))

        if not data:
            response_empty = True
            break

        grouped_by_date = bucket_rows_by_date(data)

        for date in grouped_by_date:
            directory_string = append_to_partition(date, grouped_by_date[date], output_directory)

        offset += len(data)

if __name__ == "__main__":
    get_data(
        start_date="2025-05-01T00:00:00",
        end_date="2025-05-31T23:59:59",
        output_directory="data/raw/ridership"
    )
