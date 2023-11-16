from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from soup import Soup, Page
from urllib.parse import urljoin
from dataclasses import dataclass
import pandas as pd
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
        
        def _get_links(self):
            endpoint_pattern = re.compile(r'\.\./([\w\d-]+\.html)')
            links = []
            if self.rows:
                for row in self.rows:
                    td = row.find('td')
                    if td:
                        a = td.find('a')
                        if a:
                            links.append(urljoin('https://diamondantenna.net/', a['href']))
            return links


class ProductPage(Page):
    def __init__(self, url, index, df):
        self.index = index
        self.df = df
        self.specifications = []
        self.special_features = []
        Page.__init__(self, url)
        self.image = self._get_image()
        self.model = self._get_model()
        self.tagline = self._get_tagline()
        self.metadata = self._get_metadata()

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
        image = self.soup.find('img', src=endpoint_pattern)
        
        # Handle missing images
        if image == None:
            image_url = ''
            return image_url
        
        image_alt = ''
        image_url = ''
        if 'alt' in image.attrs:
            image_alt = image['alt']
        if 'src' in image.attrs:
            image_url = urljoin('https://diamondantenna.net/', image['src'])

        return [image_alt, image_url]
    
    def _get_model(self):
        assert self.title
        return re.findall(r'[^\s]+', self.title)[0]
    
    def _get_tagline(self):
        if not self.df.empty:
            if 'Description' in self.df:
                return self.df.loc[self.index, 'Description']
            elif "Stacked ElementPhasing/Wavelength":
                re.sub('\\r\\n(.)', ' ', self.df.loc[self.index, "Stacked ElementPhasing/Wavelength"]).strip()
            elif "ElementPhasing/Wavelength":
                re.sub('\\r\\n(.)', ' ', self.df.loc[self.index, "ElementPhasing/Wavelength"]).strip()
            else:
                return ''
            
    def _get_metadata(self):
        if not self.df.empty:
            if 'Description' not in self.df:
                df_trimmed = self.df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
                return df_trimmed.loc[self.index][1:]
            else:
                return []

        
@dataclass
class Category:
    name: str
    children: []

@dataclass
class Product:
    model: str
    title: str
    tagline: str
    category: str
    metadata: []
    thumbnail: []

class ProductParser():
    def __init__(self, root_url, endpoints_ignored, pattern):
        self.products = []
        self.categories = []
        self.parse = self.Parse(root_url, endpoints_ignored, pattern)

    # Get all products
    def Parse(self, root_url, endpoints_ignored, pattern):
        # Create progress bar
        with Progress(SpinnerColumn(), *Progress.get_default_columns(), TimeElapsedColumn(), transient=False) as progress:
            # Get endpoints
            endpoint_links = Soup.EndpointParser(root_url, endpoints_ignored, pattern)
            # Track extracted endpoints to avoid repeats
            endpoints_tracked = set()
            # Loop through the endpoint links and fetch/parse each one
            categories = []
            products = []
            for endpoint_link in endpoint_links:
                # Check if we've already processed this endpoint
                if endpoint_link in endpoints_tracked:
                    continue
                # Add endpoint to tracked endpoints
                endpoints_tracked.add(endpoint_link)

                # Parse the current endpoint url
                category_page = CategoryPage(endpoint_link)
                category_title = Soup.clean_whitespace(category_page.title)
                category_task = progress.add_task(f"[cyan] Category: {category_title}", total=len(category_page.tables))
    
                # Parse each table for products
                category_children = []
                for table in category_page.tables:
                    table_title = Soup.clean_whitespace(table.title)
                    table_task = progress.add_task(f"[red] Table: {table_title}", total=len(table.links))

                    category_children.append(table_title)
                    for index, link in enumerate(table.links):
                        product_page = ProductPage(link, index, table.to_dataframe())
                        product_title = Soup.clean_whitespace(product_page.title)
                        if isinstance(product_page.metadata, pd.Series):
                            product_metadata = product_page.metadata.to_dict()
                        else:
                            product_metadata = product_page.metadata
                        products.append(Product(product_page.model, product_title, product_page.tagline, table_title, product_metadata, product_page.image))

                        progress.update(table_task, advance=1)
                    progress.update(category_task, advance=1)
                categories.append(Category(category_title, category_children))
            self.categories = categories
            self.products = products


        

    