from pharma.common_lib import get_config_value, get_or_create_config_value, set_config_value
from capsulae2.commons import get_or_none
from datetime import datetime
from .models import Book

import xml.etree.ElementTree as ET

import math
import requests
import time

#DILVE_URL = "https://www.dilve.es/dilve/dilve/getRecordListX.do?user=defundparainnoinve01&password=_Fund3c_&publisher=546"
#DILVE_URL_REG = "https://www.dilve.es/dilve/dilve/getRecordsX.do?user=defundparainnoinve01&password=_Fund3c_&identifier=9788416120611"
DILVE_URL = "https://www.dilve.es/dilve/dilve/getRecordListX.do?user=defundparainnoinve01&password=_Fund3c_"
DILVE_URL_REG = "https://www.dilve.es/dilve/dilve/getRecordsX.do?user=defundparainnoinve01&password=_Fund3c_"
DATE_FORMAT = "%d-%m-%Y %H:%M"

class BookUpdateParams:
    is_running = "BOOKS_IS_RUNNING"
    total_pages = "BOOKS_TOTAL_PAGES"
    current_page = "BOOKS_CURRENT_PAGE"
    last_update = "BOOKS_LAST_UPDATE"

    def start(self):
        set_config_value(self.is_running, 1)

    def stop(self):
        set_config_value(self.is_running, 0)
        self.set_last_update(datetime.now().strftime(DATE_FORMAT))
   
    def get_is_running(self):
        return get_or_create_config_value(self.is_running)

    def get_last_update(self):
        return get_or_create_config_value(self.last_update)

    def set_last_update(self, date):
        set_config_value(self.last_update, date)

    def get_total_pages(self):
        return get_or_create_config_value(self.total_pages)

    def set_total_pages(self, total):
        set_config_value(self.total_pages, total)

    def get_current_page(self):
        return get_or_create_config_value(self.current_page)

    def set_current_page(self, current):
        set_config_value(self.current_page, current)

def save_book(isbn, title, subtitle, authors, serie, pub_code, pub_name):
    book, created = Book.objects.get_or_create(isbn=isbn)
    book.title = title
    book.subtitle = subtitle
    book.authors = authors
    book.serie = serie
    book.publisher_code = pub_code
    book.publisher_name = pub_name
    book.save()

def get_isbn_reg(isbn):
    url = "{}&identifier={}".format(DILVE_URL_REG, isbn)
    response = requests.get(url, {})
    xml_content = response.text  # Obtiene el XML como string
    try:
        ns = {
            'onix': 'http://www.editeur.org/onix/2.1/reference',
            'dilve': 'http://www.dilve.es/dilve/api/xsd/getRecordsXResponse'
        }

        root = ET.fromstring(xml_content)

        # Extraer datos clave
        product = root.find('.//onix:Product', ns)

        # ISBN (ProductIDType="03" es ISBN-13)
        isbn = product.find('.//onix:ProductIdentifier[onix:ProductIDType="03"]/onix:IDValue', ns).text

        # Título principal y subtítulo
        title = product.find('.//onix:Title[onix:TitleType="01"]/onix:TitleText', ns).text
        try:
            subtitle = product.find('.//onix:Title[onix:TitleType="01"]/onix:Subtitle', ns).text
        except:
            subtitle = ""

        # Autor (ContributorRole="B01" es autor principal)
        #author = product.find('.//onix:Contributor[onix:ContributorRole="B01"]/onix:PersonNameInverted', ns).text
        authors = []

        # Iterar sobre todos los contribuyentes y filtrar por rol "B01" (autores)
        for contributor in root.findall('.//onix:Contributor', ns):
            role = contributor.find('onix:ContributorRole', ns).text
            if role == 'B01':  # Solo autores
                name = contributor.find('onix:PersonNameInverted', ns).text
                authors.append(name)

        # Serie y número en la serie
        try:
            series = product.find('.//onix:Series/onix:Title/onix:TitleText', ns).text
        except:
            series = ""
        try:
            series_number = product.find('.//onix:Series/onix:NumberWithinSeries', ns).text
        except:
            series_number = ""

        # Publisher code y publisher name
        pub_code = product.find('.//onix:Publisher/onix:NameCodeValue', ns).text
        pub_name = product.find('.//onix:Publisher/onix:PublisherName', ns).text

        # Imprimir resultados
        #print(f"ISBN: {isbn}")
        #print(f"Título: {title}")
        #print(f"Subtítulo: {subtitle}")
        #print(f"Autor: {authors}")
        #print(f"Serie: {series} (Número: {series_number})")
        save_book(isbn, title, subtitle, authors, f"Serie: {series} (Número: {series_number})", pub_code, pub_name)
    except Exception as e:
        print(xml_content)
        print (str(e))

def update_books_cache():
    aup = BookUpdateParams()
    aup.start()
    start_time = time.time()

    total = 0
    total_editorial = 10000
    aup.set_total_pages(str(total_editorial))
    #for i in range(903, 904):
    for i in range(total_editorial):
        aup.set_current_page(str(i))
        url = "{}&publisher={}".format(DILVE_URL, i)
        response = requests.get(url, {})
        xml_content = response.text  # Obtiene el XML como string

        namespace = { 'ns': 'http://www.dilve.es/dilve/api/xsd/getRecordListXResponse' }
        root = ET.fromstring(xml_content)
        isbn_list = root.findall('.//ns:record', namespace)
        print("Editorial: {} - Libros: {}".format(i, len(isbn_list)))
        #j = len(isbn_list)
        #j = 0
        for isbn_node in isbn_list:
            #j += 1
            isbn = isbn_node.find("ns:id", namespace).text
            get_isbn_reg(isbn)
        #total += j
        #print("Publisher {}: {} isbns".format(i, j))

    print("--- TOTAL: {} | {} seconds ---".format(total, time.time() - start_time))
    aup.stop()
    return 0

def update_tasks():
    update_books_cache()
    return 0

