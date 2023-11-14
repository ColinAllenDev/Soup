from soup import Soup, Page
from tqdm import tqdm
from urllib.parse import urljoin
import requests
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
        assert image_url
        return image_url

def handle_links(page):
    # Create page progress bar
    page_bar = tqdm(total=len(page.tables), colour='blue', position=0, leave=False, dynamic_ncols=True, desc=page.title)
    for table in page.tables:
        # Create table progress bar
        table_bar = tqdm(total=len(table.links), colour='red', position=1, leave=False, dynamic_ncols=True, desc=table.title)
        for link in table.links:
            # Create link progress bar
            ProductPage(link)
            table_bar.update(1)
        table_bar.close()
        page_bar.update(1)
    page_bar.close()

# Main Loop
def ProductParser():
    # Environment Variables
    root_url = "https://www.diamondantenna.net/products.html"
    endpoints_ignored = ['techno.html', 'accessories.html', 'discontinued.html']
    pattern = r'Product_Catalog/.*\.html'

    # Welcome message
    Soup.log.info('Welcome to Soup!')

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

    # Track extracted endpoints to avoid repeats
    endpoints_tracked = set()

    # Loop through the endpoint links and fetch/parse each one
    category_pages = []
    for endpoint_link in endpoint_links:
        # Check if we've already processed this endpoint
        if endpoint_link in endpoints_tracked:
            continue
        # Add endpoint to tracked endpoints
        endpoints_tracked.add(endpoint_link)

        # Parse the current endpoint url
        current_page = CategoryPage(endpoint_link)
        current_page.print()
        category_pages.append(current_page)
    return category_pages
    # Loop through product pages on each table
    #product_pages = []
    #for page in category_pages:
    #    for table in page.tables:
    #        for link in table.links:
    #            product_page = ProductPage(link)
    #            product_pages.append(product_page)
