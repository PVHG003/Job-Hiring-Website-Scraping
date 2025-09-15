import requests
from bs4 import BeautifulSoup

USER_AGENT = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Make request with user agent
response = requests.get(
    "https://vi.wikipedia.org/w/index.php?title=T%E1%BB%89nh_(Vi%E1%BB%87t_Nam)&oldid=69606850",
    headers=USER_AGENT
)

print(f"Status code: {response.status_code}")
soup = BeautifulSoup(response.text, "html.parser")

province_tables = soup.find_all("table", class_="wikitable")
print(f"Found {len(province_tables)} tables")

# Correct way to navigate the table
table_body = province_tables[0].find('tbody')  # Use find() method
table_rows = table_body.find_all('tr')  # Get all rows, not just first
first_row = table_rows[0]  # Get first row
table_data = first_row.find_all('td')  # Get all cells in first row

print("First row data:")
for i, cell in enumerate(table_data):
    print(f"Cell {i}: {cell.get_text().strip()}")

# Extract province names from all rows
print("\nAll provinces:")
with open("provinces.txt", "w", encoding="utf-8") as f:
    for i, row in enumerate(table_rows):
        cells = row.find_all('td')
        if len(cells) >= 2:  # Make sure row has enough cells
            # Province name is typically in the second cell (index 1)
            province_cell = cells[1]
            province_link = province_cell.find('a')

            if province_link:
                province_name = province_link.get('title') or province_link.get_text().strip()
                print(f"{province_name}")
                f.write(f"{province_name}\n")  # Write to file