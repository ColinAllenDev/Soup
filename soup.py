import re
from urllib.parse import urljoin
import coloredlogs
import logging
import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from tabulate import tabulate
from dataclasses import dataclass
from overrides import override

@dataclass
class Product:
    model: str
    title: str
    description: str
    category: str
    parent_category: str
    metadata: []
    documents: []
    thumbnails: []


class Page:
    def __init__(self, url):
        self.url = url
        self.soup = Soup.parse_url(url)
        self.category = self._get_category()
        self.tables = self._parse_tables()
        self.data = self._get_data()

    def print(self):
        assert self.category
        log.info(f'Page: {self.category}\n')
        for table in self.tables:
            table.print()

    def _parse_tables(self):
        assert self.soup
        tables = []
        table_titles = []
        for table in self.soup.find_all('table'):
            tables.append(self.Table(table))
        return tables

    def _get_category(self):
        assert self.soup
        return self.soup.find('h1').get_text(strip=True)

    def _get_data(self):
        assert self.tables
        data = []
        for table in self.tables:
            data.append(table.to_dataframe())
        return data

    class Table:
        def __init__(self, soup):
            self.soup = soup
            self.category = self._get_category()
            self.header = self._get_table_header()
            self.rows = self._get_table_rows()
            self.data = self._get_table_data()

        def print(self):
            print(f'{self.category}')
            print(tabulate(self.to_dataframe(), headers='keys', tablefmt='psql', showindex=False))
            print('')

        def to_dataframe(self):
            data_frame = pd.DataFrame(columns=self.header)
            data_frame.style.set_caption(self.category)
            for data in self.data:
                data_frame = data_frame._append(pd.Series(data, index=self.header), ignore_index=True)
            return data_frame

        def _get_category(self):
            assert self.soup
            category = self.soup.find_previous(['h2', 'h3', 'h4', 'strong'])
            if category == None:
                return 'Not Found'
            return category.get_text(strip=True)

        def _get_table_data(self):
            assert len(self.rows) > 0 and len(self.header) > 0
            table_data = []
            for row in self.rows[1:]:
                cells = [cell for cell in row.find_all(['td'])]
                data = [cell.get_text(strip=True) for cell in cells]
                data += [None] * (len(self.header) - len(data))
                table_data.append(data)
            return table_data

        def _get_table_rows(self):
            return self.soup.find_all('tr')

        def _get_table_header(self):
            return [header.get_text(strip=True) for header in self.soup.find_all('th')]

        def _get_table_header_adv(self):
            header_row = [header.get_text(strip=True) for header in self.soup.find_all('th')]
            data_rows = self._get_table_rows()[1:]
            updated_header_row = header_row[:]
            for data_row in data_rows:
                column_index = 0
                for header_element in header_row:
                    if len(data_row) <= column_index:
                        break
                    if len(data_row) > column_index:
                        num_header_elements = min(len(data_row) - column_index, len(header_row))
                        updated_header_element = " ".join(header_row[column_index:column_index + num_header_elements])
                        updated_header_row[column_index] = updated_header_element
                        column_index += num_header_elements
            return updated_header_row

class ProductPage(Page):
    def __init__(self, url):
        super().__init__(url)

    def _parse_tables(self):
        tables = []
        for table in self.soup.find_all('table'):
            if len(table.find_all('table')) == 0:
                tables.append(self.Table(table))
        return tables

    class Table(Page.Table):
        def _get_table_data(self):
            table_data = []
            for row in self._get_table_rows()[1:]:
                cells = [cell for cell in row.find_all(['td']) if 'rowspan' not in cell.attrs]
                data = [cell.get_text(strip=True) for cell in cells]
                data += [None] * (len(self.header) - len(data))
                table_data.append(data)
            return table_data

        def _get_table_rows(self):
            return self.soup.find_all('tr', class_='tabs')

class Soup:
    # Parse an html page using BeautifulSoup
    @staticmethod
    def parse_url(url):
        response = requests.get(url)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        return None

    @staticmethod
    def to_sql(data_frame, db_url, table_name):
        # Create a database connection
        engine = create_engine(db_url)

        # Upload the data frame to the database
        data_frame.to_sql(table_name, con=engine, if_exists='replace', index=False)

# Main Loop
def main():
    # Environment Variables
    root_url = "https://www.diamondantenna.net/products.html"
    endpoints_ignored = ['techno.html', 'accessories.html', 'discontinued.html']
    pattern = r'Product_Catalog/.*\.html'

    # Initialize logger
    global log
    log = logging.getLogger(__name__)
    coloredlogs.install(fmt="[SOUP] %(levelname)s %(message)s")

    # Fetch and parse the main URL
    root_page = Soup.parse_url(root_url)
    assert root_page

    log.info(f'Root Page: {root_url}')
    # Define a regular expression pattern for endpoint links
    endpoint_pattern = re.compile(pattern)

    # Extract links to HTML endpoints matching the pattern above
    endpoint_links = [urljoin(root_url, a['href'])
                      for a in root_page.find_all('a', href=endpoint_pattern)
                      if not any(a['href'].endswith(ignr_endpoint)
                                 for ignr_endpoint in endpoints_ignored)]

    # Track extracted endpoints to avoid repeats
    endpoints_tracked = set()

    # Loop through the endpoint links and fetch/parse each one
    pages = []
    for endpoint_link in endpoint_links:
        # Check if we've already processed this endpoint
        if endpoint_link in endpoints_tracked:
            continue
        # Add endpoint to tracked endpoints
        endpoints_tracked.add(endpoint_link)

        log.info(f'Processing {endpoint_link}')

        # Parse the current endpoint url
        pages.append(ProductPage(endpoint_link))

    for page in pages:
        if page.category == 'Base Station Antennas':
            page.print()

main()
