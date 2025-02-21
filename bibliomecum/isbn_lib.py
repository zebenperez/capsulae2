#from bs4 import BeautifulSoup as BS
#import requests

import urllib.request
import json


def datas_to_dict(isbn, title, author):
    return {"isbn": isbn, "author": author, "title": title}

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

        with urllib.request.urlopen(base_api_link.format(title.replace(" ", "+"), author.replace(" ", "+"))) as f:
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

#def isbn_search_old(isbn):
#    isbn = isbn.replace('-','')
#    url = 'http://www.mcu.es/webISBN/tituloSimpleDispatch.do'
#    url = 'http://www.cultura.gob.es/webISBN/tituloSimpleDispatch.do'
#    payload = {'params.forzaQuery':'N','cache':'init','prev_layout':'busquedaisbn', 'layout':'busquedaisbn', 'language':'es','action':'Buscar', 'params.cdispo':'A','params.cisbnExt':isbn,"params.liConceptosExt[0].texto":'','params.orderByFormId':'2'}
#    r=requests.post(url, data=payload, timeout=100)
#    print(r.text)
#    content = BS(r.text, "html.parser")
#    results = content.find_all('div', {'class':'isbnResultado'})
#    return results
