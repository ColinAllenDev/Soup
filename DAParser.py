from soup import Soup, Page
from urllib.parse import urljoin
from dataclasses import dataclass
import re

class CategoryPage(Page):
    def __init__(self, url):
        super().__init__(url)

    def _parse_tables(self):
        parsed_tables = []
        for table in self.soup.find_all('table'):
            if len(table.find_all('table')) == 0:
                parsed_tables.append(self.Table(table))
        return parsed_tables

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

class ProductPage(Page):
    def __init__(self, url):
        self.specifications = []
        self.special_features = []
        super().__init__(url)
        self.image = self._get_image()
        self.model = self._get_model()

    def _parse_tables(self):
        pass

    def _get_data(self):
        assert self.soup
        data_ref = []
        description_table = self.soup.find('td', class_='tabsleft')
        for row in description_table.find_all('tr'):
            for cell in row.find_all('td'):
                if cell.get_text(strip=True) == 'Specifications:':
                    data_ref = self.specifications
                elif cell.get_text(strip=True) == 'Special Features':
                    data_ref = self.special_features
                data_ref.append(cell.get_text(strip=True))
        return []

    def _get_image(self):
        assert self.soup
        endpoint_pattern = re.compile(r'picts/.*\.jpg')
        image_url = self.soup.find('img', src=endpoint_pattern)
        
        # Handle missing images
        if image_url == None:
            image_url = ''
        
        return image_url

    def _get_model(self):
        assert self.tables
        for table in self.tables:
            

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

class ProductParser():
    @dataclass
    class Category:
        name: str
        children: []

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

    def __init__(self):
        self.products = []
        self.categories = []
    
    # Get all products
    def Parser(self, root_url, endpoints_ignored, pattern):
        # Get endpoints
        endpoint_links = EndpointParser(root_url, endpoints_ignored, pattern)
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
            category_page = CategoryPage(endpoint_link)
            category_title = re.sub(r'\s+', ' ', category_page.title).strip()
            Soup.log.info("[Category]: %s", category_title)

            # Parse each table for products
            tables = []
            for table in category_page.tables:
                Soup.log.info("\t[Table]: %s", table.title)
                tables.append(table.title)
                for link in table.links:
                    Soup.log.info("\t\t[Link]: %s", link)
                    page = self.PageParser(link)
                    
                    

                    product = self.Product(page.title, )

            self.products.append(self.CategoryParser(endpoint_link))
        

    