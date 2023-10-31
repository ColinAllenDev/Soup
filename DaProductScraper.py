import coloredlogs, logging
import numpy as np
import pandas as pd
import math
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Config
main_url = "https://www.diamondantenna.net/products.html"
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
    data_frame = pd.DataFrame()
    for row in page.find_all('tr', class_='tabs'):
        # Process table headers
        column_headers = [header.text.strip() for header in row.find_all('th')]
        # Process table column data
        column_data = [column.text.strip() for column in row.find_all('td') if not column.has_attr('rowspan')]
        # Append these values to the data table
        data_frame = data_frame._append(pd.Series(column_data), ignore_index=True)
    # Print the data frame
    print(data_frame)

# Fetch and parse the main URL
main_page = parse_url(main_url)

if main_page:
    # Define a regular expression pattern for endpoint links
    endpoint_pattern = re.compile(r'Product_Catalog/.*\.html')

    # Extract links to HTML endpoints matching the pattern above (ignore technical info page)
    endpoint_links = [urljoin(main_url, a['href']) for a in main_page.find_all('a', href=endpoint_pattern) if not a['href'].endswith('techno.html')]

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
            parse_tables(endpoint_page)
        else:
            logging.error(f"Failed to fetch: {endpoint_link}")
else:
    logging.critical(f"Failed to fetch the main URL: {main_url}")
