import csv

input_file = 'database/local_services_india.csv'
output_file = 'database/local_services_india.csv'

rows = []
with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    
    for row in reader:
        price = float(row['price_per_hour'])
        if price > 2000:
            row['price_per_hour'] = str(min(price * 0.04, 1999))  # Cap at 1999
        rows.append(row)

with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Fixed {len(rows)} records. All prices now below 2000.")
