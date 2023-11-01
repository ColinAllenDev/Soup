import re
import logging
from urllib.parse import urljoin
import coloredlogs
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Config
MAIN_URL = "https://www.diamondantenna.net/products.html"
coloredlogs.install()

# Function to fetch and parse a URL
def parse_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        return BeautifulSoup(response.text, 'html.parser')
    else:
        return None

# Function to parse table data
# TODO: Store each table on page in its own DataFrame
def parse_tables(page):
    tables = page.find_all('table')
    # Search all tables on the page for tables without child tables
    for table in tables:
        nested_tables = table.find_all('table')
        if len(nested_tables) == 0:
            column_headers = []
            row_data = []
            for row in table.find_all('tr', class_='tabs'):
                for header in row.find_all('th'):
                    column_headers.append(header.text.strip())
                column_data = []
                for data in row.find_all('td'):
                    if not data.has_attr('rowspan'):
                        column_data.append(data.text.strip())
                row_data.append(column_data)
            data_frame = pd.DataFrame(row_data, columns=column_headers)
            print(data_frame)


def parse_tables_v2(page):
    tables = page.find_all('table')
    for table in tables:
        if len(table.find_all('table')) == 0:
            rows = table.find_all('tr')
            max_columns = max(len([cell for cell in row.find_all(['th', 'td']) if 'rowspan' not in cell.attrs]) for row in rows)
            columns = range(max_columns)
            data_frame = pd.DataFrame(columns=columns)
            for row in table.find_all('tr'):
                cells = [cell for cell in row.find_all(['th', 'td']) if 'rowspan' not in cell.attrs]
                data = [cell.get_text(strip=True) for cell in cells]
                data += [None] * (max_columns - len(data))
                data_frame = data_frame._append(pd.Series(data, index=columns), ignore_index=True)
            print(data_frame)



# Fetch and parse the main URL
main_page = parse_url(MAIN_URL)


if main_page:
    # Define a regular expression pattern for endpoint links
    endpoint_pattern = re.compile(r'Product_Catalog/.*\.html')

    # Extract links to HTML endpoints matching the pattern above
    endpoint_links = [urljoin(MAIN_URL, a['href'])
                      for a in main_page.find_all('a', href=endpoint_pattern)
                      if not a['href'].endswith('techno.html')]

    # Track extracted endpoints to avoid repeats
    endpoints_tracked = set()

    # Loop through the endpoint links and fetch/parse each one
    for endpoint_link in endpoint_links:
        # Check if we've already processed this endpoint
        if endpoint_link in endpoints_tracked:
            continue

        # Add endpoint to tracked endpoints
        endpoints_tracked.add(endpoint_link)

        # Parse the current endpoint url
        endpoint_page = parse_url(endpoint_link)
        if endpoint_page:
            logging.info(f"Parsing Page: {endpoint_link}")
            parse_tables_v2(endpoint_page)
        else:
            logging.error(f"Failed to fetch: {endpoint_link}")
else:
    logging.critical(f"Failed to fetch the main URL: {MAIN_URL}")
