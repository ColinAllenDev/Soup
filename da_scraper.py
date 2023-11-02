import re
import logging
from urllib.parse import urljoin
import coloredlogs
import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from tabulate import tabulate
from dataclasses import dataclass

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
        self.tables = self._parse_tables()
        self.data = self._get_data()

    def _parse_tables(self):
        assert self.soup
        for table in self.soup.find_all('table'):
            self.tables.append(self.Table(table))

    def _get_data(self):
        assert self.tables
        for table in self.tables():
            self.data.append(table.to_dataframe())


    class Table:
        def __init__(self, soup):
            self.soup = soup
            self.header = self._get_table_header()
            self.rows = self._get_table_rows()
            self.data = self._get_table_data()

        def to_dataframe(self):
            assert self.data and len(self.header) > 0
            data_frame = pd.DataFrame(columns=self.header)
            for data in self.data:
                data_frame._append(pd.Series(data, index=self.header), ignore_index=True)
            return data_frame

        def _get_table_data(self):
            assert len(self.rows) > 0 and len(self.header) > 0
            table_data = []
            for row in self.rows[1:]:
                cells = [cell for cell in row.find_all('td')]
                data = [cell.get_text(strip=True) for cell in cells]
                data += [None] * (len(self.header) - len(data))
                table_data.append(data)
            return table_data

        def _get_table_rows(self):
            return self.soup.find_all('tr')

        def _get_table_header(self):
            return [header.get_text(strip=True) for header in self.soup.find_all('th')]



class DAProductPage(Page):
    @overrides(Page)
    def __init__(self, url, category = '', parent_category = ''):
        super().__init__(url)
        self.category = category
        self.parent_category = parent_category

    @overrides(Page)
    def _parse_tables(self):
        for table in self.soup.find_all('table'):
            if len(soup.find_all('table')) == 0:
                self.tables.append(self.Tables(soup))

    class Table(Page.Table):
        @overrides(Page.Table)
        def _get_table_data(self):
            table_data = []
            for row in self.get_table_rows[1:]:
                cells = [cell for cell in row.find_all('td') if 'rowspan' not in cell.attrs]
                data = [cell.get_text(strip=True) for cell in cells]
                data += [None] * (len(self.headers) - len(data))
                table_data.append(data)
            return table_data

        @override(Page.Table)
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

    # Get all data tables at a given endpoint
    @staticmethod
    def get_endpoint_data(url):
        # Fetch and parse the main URL
        main_page = Page(url)

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


    def to_product(self, table_data):


    def to_sql(self, data_frame, db_url, table_name):
        # Create a database connection
        engine = create_engine(db_url)

        # Upload the data frame to the database
        data_frame.to_sql(table_name, con=engine, if_exists='replace', index=False)

# Main Loop
def main():
    ROOT_URL = "https://www.diamondantenna.net/products.html"
    ENDPOINTS_IGNORED = ['techno.html', 'accessories.html', 'discontinued.html']

    product_parser = Soup(ROOT_URL, ENDPOINTS_IGNORED)
    page_tables = product_parser.get_data_tables()
    for page in page_tables:
        for table in page:
            print(tabulate(table, headers='keys', tablefmt='psql', showindex=False))
