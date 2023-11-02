import re
import logging
from urllib.parse import urljoin
import coloredlogs
import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from tabulate import tabulate

class Soup:
    # Member Variables
    def __init__(self, url, ignored):
        self.root_url = url
        self.endpoints_ignored = ignored

        coloredlogs.install()

    def parse_url(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        return None


    def parse_tables(self, page):
        page_frames = []
        tables = page.find_all('table')
        for table in tables:
            if len(table.find_all('table')) == 0:
                column_headers = [header.get_text(strip=True) for header in table.find_all('th')]
                data_frame = pd.DataFrame(columns=column_headers)
                for row in table.find_all('tr', class_='tabs')[1:]:
                    cells = [cell for cell in row.find_all(['th', 'td']) if 'rowspan' not in cell.attrs]
                    data = [cell.get_text(strip=True) for cell in cells]
                    data += [None] * (len(column_headers) - len(data))
                    data_frame = data_frame._append(pd.Series(data, index=column_headers), ignore_index=True)
                page_frames.append(data_frame)
        return page_frames


    def get_data_tables(self, url=None):
        # Determine if we're using the member variable or arg
        url = self.root_url if url is None else url
        # Fetch and parse the main URL
        main_page = self.parse_url(url)

        if main_page:
            # Define a regular expression pattern for endpoint links
            endpoint_pattern = re.compile(r'Product_Catalog/.*\.html')

            # Extract links to HTML endpoints matching the pattern above
            endpoint_links = [urljoin(self.root_url, a['href'])
                              for a in main_page.find_all('a', href=endpoint_pattern)
                              if not any(a['href'].endswith(inv_endpoint)
                                         for inv_endpoint in self.endpoints_ignored)]

            # Track extracted endpoints to avoid repeats
            endpoints_tracked = set()

            # Loop through the endpoint links and fetch/parse each one
            page_tables = []
            for endpoint_link in endpoint_links:
                # Check if we've already processed this endpoint
                if endpoint_link in endpoints_tracked:
                    continue
                # Add endpoint to tracked endpoints
                endpoints_tracked.add(endpoint_link)
                # Parse the current endpoint url
                endpoint_page = self.parse_url(endpoint_link)
                if endpoint_page:
                    logging.info(f"Parsing Page: {endpoint_link}")
                    # Gather data tables from endpoint page
                    page_tables.append(self.parse_tables(endpoint_page))
                else:
                    logging.error(f"Failed to fetch: {endpoint_link}")
            return page_tables
        else:
            logging.critical("Failed to fetch the main URL %s:", self.root_url)


    def to_sql(self, data_frame, db_url, table_name):
        # Create a database connection
        engine = create_engine(db_url)

        # Upload the data frame to the database
        data_frame.to_sql(table_name, con=engine, if_exists='replace', index=False)

ROOT_URL = "https://www.diamondantenna.net/products.html"
ENDPOINTS_IGNORED = ['techno.html', 'accessories.html', 'discontinued.html']

product_parser = Soup(ROOT_URL, ENDPOINTS_IGNORED)
page_tables = product_parser.get_data_tables()
for page in page_tables:
    for table in page:
        print(tabulate(table, headers='keys', tablefmt='psql', showindex=False))
