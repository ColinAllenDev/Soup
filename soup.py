import re
from dataclasses import dataclass
from urllib.parse import urljoin
import logging
import coloredlogs
import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from tabulate import tabulate

@dataclass
class Product:
    model: str
    title: str
    tagline: str
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
            self.links = self._get_links()
            self.title = self._get_title()
            self.header = self._get_table_header()
            self.rows = self._get_table_rows()
            self.data = self._get_table_data()

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

    @staticmethod
    def to_sql(data_frame, db_url, table_name):
        # Create a database connection
        engine = create_engine(db_url)

        # Upload the data frame to the database
        data_frame.to_sql(table_name, con=engine, if_exists='replace', index=False)
