#from bs4 import BeautifulSoup as BS
#import requests

import urllib.request
import json


def isbn_search(isbn):
    try:
        base_api_link = "https://www.googleapis.com/books/v1/volumes?q=isbn:"

        with urllib.request.urlopen(base_api_link + isbn) as f:
            text = f.read()

        decoded_text = text.decode("utf-8")
        obj = json.loads(decoded_text) # deserializes decoded_text to a Python object
        volume_info = obj["items"][0]
        #print(volume_info["volumeInfo"])
        return volume_info["volumeInfo"]["title"], volume_info["volumeInfo"]["authors"]
    except:
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
