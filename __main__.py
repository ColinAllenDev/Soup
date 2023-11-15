import asyncio
import re
from DAParser import ProductParser
from prisma import Prisma

async def POST_PRODUCTS() -> None:
    prisma = Prisma()
    await prisma.connect()

    # Queries go here

def main():
    ROOT_URL = "https://www.diamondantenna.net/products.html"
    IGNORED_ENDPOINTS = ['techno.html', 'accessories.html', 'discontinued.html']
    PATTERN = r'Product_Catalog/.*\.html'

    ProductParser.Parse(ROOT_URL, IGNORED_ENDPOINTS, PATTERN)

if __name__ == '__main__':
    main()