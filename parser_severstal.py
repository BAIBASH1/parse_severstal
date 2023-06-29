import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from urllib.parse import urljoin
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import csv


PARSING_STATE = {
    'product_url': ''
}
MAIN_URL = 'https://market.severstal.com/ru/ru'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}


def collect_product_urls():
    catalog_urls = get_catalog_urls()
    product_urls = get_product_urls(catalog_urls)
    with open('product_urls.txt', 'w', encoding='utf-8') as file:
        for product_url in product_urls:
            file.write(f'{product_url}\n')


def get_catalog_urls():
    headers = {
        'User-Agent': UserAgent().chrome
    }
    response = requests.get(MAIN_URL, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'lxml')
    catalog_bloks = soup.findAll('div', class_="catalog-card")
    catalog_urls = []
    for catalog_blok in catalog_bloks:
        catalog_urls += [urljoin('https://market.severstal.com/', calalog_url.get('href')) for calalog_url in
                         catalog_blok.findAll('a', class_="link color-primary catalog-card__link")]
    return catalog_urls


def get_product_urls(catalog_urls):

    product_urls = []
    for catalog_url in catalog_urls:
        n = 1
        while True:
            params = {
                'page': n
            }
            headers = {
                'User-Agent': UserAgent().chrome
            }
            response = requests.get(catalog_url, headers=headers, params=params)
            response.raise_for_status()
            time.sleep(5)
            soup = BeautifulSoup(response.text, 'lxml')
            if soup.find('a', class_='bold link'):
                product_urls += [urljoin('https://market.severstal.com/', product_url.get('href')) for product_url in
                                 soup.findAll('a', class_='bold link')]
                n += 1
            else:
                break
    return product_urls


def parse_product(product_url, dict_product_headings):
    dict_product_inform = dict_product_headings.copy()
    service = Service(executable_path='chromedriver.exe')
    driver = webdriver.Chrome(service=service)
    driver.get(url=product_url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    name = soup.find('h1', class_="bold").text.strip()
    dict_product_inform['Наименование'] = name
    dict_product_inform['Ссылка'] = product_url
    code = soup.find('div', class_="d-f ai-c jc-sb").find('span').text.strip()
    dict_product_inform['Код товара'] = code[12:]
    category = soup.findAll('div', class_="s-breadcrumbs__item")[2].find('span').text.strip()
    dict_product_inform['Категория'] = category
    subcategory = soup.findAll('div', class_="s-breadcrumbs__item")[3].find('span').text.strip()
    dict_product_inform['Подкатегория'] = subcategory
    characteristic_blocks = soup.findAll('div', class_="catalog-detail__item")[1].findAll('div', class_="s-col characteristics py-8 ai-c s-col-12 s-col--align-start")
    for characteristic_block in characteristic_blocks:
        characteristic_key = characteristic_block.find('span').text.strip()[:-1]
        characteristic_value = characteristic_block.find('span', class_='p-r').find('span').text.strip()
        dict_product_inform[characteristic_key] = characteristic_value
    try:
        storage_blocks = soup.find('div', class_="storage-listing__content").findAll('div', class_="storage-listing__row")
        for storage_block in storage_blocks:
            storage = storage_block.find('span', class_="bold").text.strip()
            dict_product_inform[storage] = storage
            tons = storage_block.find('span', class_="s-stock__content").text.strip()
            dict_product_inform[f'Наличие(тонн) в складе: {storage}'] = tons
            try:
                price = storage_block.find('div', class_="text-l bold").text.strip()
                num_price = ''
                for s in str.split(price):
                    if s.isdigit():
                        num_price += s
                price = num_price
            except AttributeError:
                price = 'Цена не указана'
            dict_product_inform[f'Цена в складе: {storage}'] = [int(s) for s in str.split(price) if s.isdigit()]

            if storage_block.findAll('use')[0].get('href') == "/_nuxt/sprite.svg#delivery":
                is_deliver = 'да'
            else:
                is_deliver = 'нет'
            dict_product_inform[f'Доставка(да/нет) из склада: {storage}'] = is_deliver

            if storage_block.findAll('use')[1].get('href') == "/_nuxt/sprite.svg#pickup":
                is_pickup = 'да'
            else:
                is_pickup = 'нет'
            dict_product_inform[f'Самовывоз(да/нет) из склада: {storage}'] = is_pickup
    except AttributeError:
        print(f'Товара: {product_url}, нет в наличии')
    return dict_product_inform


def write_to_csv(product_headings, dict_product_inf):
    with open('severstal_products.csv', 'a', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([dict_product_inf[product_heading] for product_heading in product_headings])


def main():
    # collect_product_urls()
    # print('Ссылки на всю продукцию записаны')
    with open('product_urls.txt', 'r') as file:
        product_urls = [product_url.strip() for product_url in file.readlines()]
    with open('product_headings.txt', 'r', encoding='utf-8') as file:
        product_headings = [product_heading.strip() for product_heading in file.readlines()]

    dict_product_headings = {}
    for product_heading in product_headings:
        dict_product_headings[product_heading] = ''

    for num, product_url in enumerate(product_urls):
        if num >= 0:
            dict_product_inf = parse_product(product_url, dict_product_headings)
            if num == 0:
                with open('severstal_products.csv', 'w', encoding='utf-8') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(product_headings)
            write_to_csv(product_headings, dict_product_inf)
            print(num, product_url)

if __name__ == '__main__':
    main()
