#from bs4 import BeautifulSoup as BS
#import requests
from books.models import Book
from books.books_update_lib import get_isbn_reg

import urllib.request
import json


def datas_to_dict(isbn, title, author):
    return {"isbn": isbn, "author": author, "title": title}

'''
    LOCAL API
'''
def isbn_search_cache(isbn):
    try:
        book_list = Book.objects.filter(isbn=isbn)
        result_list = []
        if len(book_list) == 0:
            print("- NOT FOUND -")
            book = get_isbn_reg(isbn)
            result_list.append(datas_to_dict(book.isbn, book.title, book.authors))
        else:
            for book in book_list:
                result_list.append(datas_to_dict(book.isbn, book.title, book.authors))
        return result_list 
    except:
        return []

def ta_search_cache(title, author):
    try:
        if title == "" and author == "":
            return []

        kwargs = {}
        if title != "":
            kwargs["title__icontains"] = title
        if author != "":
            kwargs["authors__icontains"] = author
        book_list = Book.objects.filter(**kwargs)
        result_list = []
        #if len(book_list) == 0:
        #    print("- NOT FOUND -")
            #res = get_isbns_openlibrary(title, author=author)
        #    print("--A--")
        #    print(res)
            
        for book in book_list:
            result_list.append(datas_to_dict(book.isbn, book.title, book.authors))
        return result_list 
    except:
        return []


'''
    OPEN LIBRARY
'''
def get_isbns_openlibrary(title, author=None, limit=50):
    params = {
        "title": title,
        "limit": limit
    }
    if author:
        params["author"] = author

    url = "https://openlibrary.org/search.json"
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    isbns = set()
    for doc in data.get("docs", []):
        print(doc)
        for isbn in doc.get("isbn", []) or []:
            clean = isbn.replace("-", "").strip()
            if clean:
                isbns.add(clean)

    return sorted(isbns)

'''
    GOOGLE API
'''
def get_google_isbn(dic):
    isbn = ""
    if "industryIdentifiers" in dic:
        for a in dic["industryIdentifiers"]:
            isbn = a["identifier"]
            break
    return isbn
 
def get_google_title(dic):
    return dic["title"]

def get_google_authors(dic):
    authors = ""
    if "authors" in dic:
        for a in dic["authors"]:
            authors += "{},".format(a)
    return authors[:-1]

def isbn_search(isbn):
    try:
        base_api_link = "https://www.googleapis.com/books/v1/volumes?q=isbn:"

        with urllib.request.urlopen(base_api_link + isbn) as f:
            text = f.read()

        decoded_text = text.decode("utf-8")
        obj = json.loads(decoded_text) # deserializes decoded_text to a Python object

        #volume_info = obj["items"][0]
        #print(obj["items"])
        result_list = []
        for dic in obj["items"]:
            title = get_google_title(dic["volumeInfo"])
            authors = get_google_authors(dic["volumeInfo"])
            result_list.append(datas_to_dict(isbn, title, authors[:-1]))
        return result_list 
        #return volume_info["volumeInfo"]["title"], authors[:-1]
    except:
        return {}

def title_author_search(title, author):
    try:
        base_api_link = "https://www.googleapis.com/books/v1/volumes?q=intitle:{}&inauthor:{}"

        with urllib.request.urlopen(base_api_link.format(title.replace(" ", "%20"), author.replace(" ", "%20"))) as f:
            text = f.read()

        decoded_text = text.decode("utf-8")
        obj = json.loads(decoded_text) # deserializes decoded_text to a Python object
        
        #volume_info = obj["items"][0]
        #print(obj["items"])
        result_list = []
        for dic in obj["items"]:
            isbn = get_google_isbn(dic["volumeInfo"])
            title = get_google_title(dic["volumeInfo"])
            authors = get_google_authors(dic["volumeInfo"])
            result_list.append(datas_to_dict(isbn, title, authors))
        return result_list 
    except Exception as e:
        print(e)
        return ""

import requests
def isbn_search_mcu(isbn):
    isbn = isbn.replace('-','')
    #url = 'http://www.mcu.es/webISBN/tituloSimpleDispatch.do'
    url = 'http://www.cultura.gob.es/webISBN/tituloSimpleDispatch.do'
    payload = {'params.forzaQuery':'N','cache':'init','prev_layout':'busquedaisbn', 'layout':'busquedaisbn', 'language':'es','action':'Buscar', 'params.cdispo':'A','params.cisbnExt':isbn,"params.liConceptosExt[0].texto":'','params.orderByFormId':'2'}
    payload = {
        'params.forzaQuery':'N',
        'params.cdispo':'A',
        'params.cisbnExt':isbn,
        "params.liConceptosExt[0].texto":'',
        'params.orderByFormId':'2',
        'language':'es',
        'prev_layout':'busquedaisbn', 
        'layout':'busquedaisbn'
    }
    print(payload)
    r=requests.post(url, data=payload)
    #r=requests.post(url, data=payload, timeout=100)
    print("----")
    print(r)
    print(r.text)
    content = BS(r.text, "html.parser")
    results = content.find_all('div', {'class':'isbnResultado'})
    return results
