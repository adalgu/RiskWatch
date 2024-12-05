import csv
from database import Database
from datetime import datetime

def migrate_events(csv_file_path):
    db = Database()
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date_str = row['date']
            description = row['description']
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                db.add_event(date=date, description=description)
                print(f"Added event: {date} - {description}")
            except Exception as e:
                print(f"Error adding event: {row} - {e}")

if __name__ == "__main__":
    migrate_events('news_collector/ui/modules/eventdb.csv')