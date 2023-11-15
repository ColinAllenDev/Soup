import json
import pandas
from rich import print
from dataclasses import asdict
from DAParser import ProductParser

def main() -> None:
    ROOT_URL = "https://www.diamondantenna.net/products.html"
    IGNORED_ENDPOINTS = ['techno.html', 'accessories.html', 'discontinued.html']
    PATTERN = r'Product_Catalog/.*\.html'

    product_parser = ProductParser(ROOT_URL, IGNORED_ENDPOINTS, PATTERN)

    print(product_parser.categories)
    print(product_parser.products)

    product_dicts = [asdict(product) for product in product_parser.products]
    product_file = open('products.json', 'w')
    try:
        json.dump(product_dicts, product_file, indent=2)
    finally:
        product_file.close()

    category_dicts = [asdict(category) for category in product_parser.categories]
    category_file = open('categories.json', 'w')
    try:
        json.dump(category_dicts, category_file, indent=2)
    finally:
        category_file.close()

if __name__ == '__main__':
    main()