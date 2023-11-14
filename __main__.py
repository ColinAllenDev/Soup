import asyncio
import re
from DAParser import PageParser, CategoryParser, TableParser
from prisma import Prisma

async def POST_PRODUCTS() -> None:
    prisma = Prisma()
    await prisma.connect()

    # Queries go here

def main():
    ROOT_URL = "https://www.diamondantenna.net/products.html"
    IGNORED_ENDPOINTS = ['techno.html', 'accessories.html', 'discontinued.html']
    PATTERN = r'Product_Catalog/.*\.html'

    CategoryParser('https://diamondantenna.net/Product_Catalog/base_station.html')
    #SiteParser(ROOT_URL, IGNORED_ENDPOINTS, PATTERN)

if __name__ == '__main__':
    main()