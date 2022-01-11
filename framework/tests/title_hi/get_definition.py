import requests
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup


def byte_to_xml(response):
    content = json.loads(response.content.decode().replace('/**/(', '').rstrip(')'))
    return ET.fromstring(content["parse"]["text"]["*"]) if "parse" in content else None


def get_synonyms(word):
    """Get a list of reference words(related words)"""
    
    lst = list()
    response = requests.get(
        'http://en.wiktionary.org/w/api.php?action=parse&format=json&prop=text|revid|displaytitle&callback=?&page=' +
        word)
    if response.status_code != 200:
        return []
    xml = byte_to_xml(response)
    if xml is None:
        return []
    for child in xml.iter():
        if child.tag == 'ol':
            for item in child.iter():
                if item.tag == 'li':
                    for ch in item.iter():
                        if ch.tag == 'a' and ch.text is not None and ch.text.islower() and ch.text.find(' ') == -1:
                            lst.append(ch.text)
    return lst


def get_definition(word):
    """Get definition in wikipedia"""
    stop_string = 'Wikipedia does not currently have an article on'
    response = requests.get(
        'http://en.wikipedia.org/w/api.php?action=parse&format=json&prop=text|revid|displaytitle&callback=?&page=' +
        word)
    if response.status_code != 200:
        return ""
    definition = ' '.join([p.get_text() for p in BeautifulSoup(response.text, 'html.parser').find_all('p')])
    return "" if stop_string in definition else definition
