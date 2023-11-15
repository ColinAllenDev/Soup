import re
from urllib.parse import urljoin
import logging
import coloredlogs
import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from tabulate import tabulate

class Page:
    def __init__(self, url):
        self.url = url
        self.soup = Soup.parse_url(url)
        self.title = self._get_title()
        self.tables = self._parse_tables()
        self.data = self._get_data()

    def _parse_tables(self):
        assert self.soup
        tables = []
        for table in self.soup.find_all('table'):
            tables.append(self.Table(table))
        return tables

    def _get_title(self):
        assert self.soup
        return self.soup.find('h1').get_text(strip=True)

    def _get_data(self):
        assert self.tables
        data = []
        for table in self.tables:
            data.append(table.to_dataframe())
        return data

    def print(self):
        assert self.title
        Soup.log.info(f'Page: {self.title}')
        for table in self.tables:
            table.print()

    class Table:
        def __init__(self, soup):
            self.soup = soup
            self.title = self._get_title()
            self.header = self._get_table_header()
            self.rows = self._get_table_rows()
            self.data = self._get_table_data()
            self.links = self._get_links()

        def _get_links(self):
            assert self.soup
            endpoint_pattern = re.compile(r'\.\./([\w\d-]+\.html)')
            return [urljoin('https://diamondantenna.net/', a['href'])
                        for a in self.soup.find_all('a', href=endpoint_pattern)]

        def to_dataframe(self):
            data_frame = pd.DataFrame(columns=self.header)
            data_frame.style.set_caption(self.title)
            for data in self.data:
                data_frame = data_frame._append(pd.Series(data, index=self.header), ignore_index=True)
            return data_frame

        def _get_title(self):
            assert self.soup
            title = self.soup.find_previous(['h2', 'h3', 'h4', 'strong'])
            if title == None:
                return 'Not Found'
            return title.get_text(strip=True)

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

        def print(self):
            print(f'Table: {self.title}')
            print(tabulate(self.to_dataframe(), headers='keys', tablefmt='psql', showindex=False))

class Soup:
    log = logging.getLogger(__name__)
    coloredlogs.install(fmt="[SOUP] %(levelname)s %(message)s")

    # Parse an html page using BeautifulSoup
    @staticmethod
    def parse_url(url):
        response = requests.get(url)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        return None
    
    # Parse endpoints to match a pattern
    @staticmethod
    def EndpointParser(root_url, endpoints_ignored, pattern):
        # Welcome message
        Soup.log.info('Parsing Endpoints...')

        # Fetch and parse the main URL
        root_page = Soup.parse_url(root_url)
        assert root_page

        Soup.log.info(f'Using root url: {root_url}')

        # Define a regular expression pattern for endpoint links
        endpoint_pattern = re.compile(pattern)

        # Extract links to HTML endpoints matching the pattern above
        endpoint_links = [urljoin(root_url, a['href'])
                          for a in root_page.find_all('a', href=endpoint_pattern)
                          if not any(a['href'].endswith(ignr_endpoint)
                                     for ignr_endpoint in endpoints_ignored)]

        return endpoint_links

    @staticmethod
    def to_sql(data_frame, db_url, table_name):
        # Create a database connection
        engine = create_engine(db_url)

        # Upload the data frame to the database
        data_frame.to_sql(table_name, con=engine, if_exists='replace', index=False)

    @staticmethod
    def clean_whitespace(str):
        return re.sub(r'\s+', ' ', str).strip()
