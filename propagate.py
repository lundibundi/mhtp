__author__ = 'lundibundi'
from urllib.request import urlopen, Request, urlsplit

from lxml import html

from utils import *


def down_parse_html(url):
    """
    download html and parse it with lxml.html
    :param url: string
    :return: lxml html parsed document
    """
    request = urlopen(Request(url, headers={'User-Agent':
                                                'Mozilla/5.0 (Windows NT 5.1; rv:10.0.1) '
                                                'Gecko/20100101 Firefox/10.0.1'}))
    encoding = request.headers.get_content_charset()
    data = request.read().decode(encoding if encoding else 'utf-8')
    doc = html.fromstring(data)
    doc.make_links_absolute('{0.scheme}://{0.netloc}'.format(urlsplit(url)))
    return doc


def propagate_generic(url, deepness, xpath, prev_pattern='Prev', next_pattern='Next'):
    """
    propagates url deepness times or while possible
    :param url: string
    :param deepness: int (>0 if forth, <0 if backwards)
    :param xpath: xpath to search in page (place where to insert 'Next' 'Prev' is {})
    :param prev_pattern: string to recognize as previous chapter link description
    :param next_pattern: string to recognize as next chapter link description
    :return: list of urls in order
    """

    xpath = xpath.format(prev_pattern if deepness < 0 else next_pattern)
    deepness = abs(deepness)
    links = []
    next_url = [url]
    while next_url and deepness > 0:
        links.append(next_url[0])
        next_url = down_parse_html(links[-1]).xpath(xpath)
        # maybe add check for same urls (pretty common error with broken/recursive links)
        deepness -= 1
    return links


def propagate_nanodesu(url, deepness):
    xpath = '//a[contains(text(), \'{0}\') or contains(following-sibling::text(), \'{0}\')]/@href'
    return propagate_generic(url, deepness, xpath)


def propagate_clickclick(url, deepness):
    xpath = '//div[@class=\'post-body entry-content\']' \
            '//a[contains(text(), \'{}\')]/@href'
    return propagate_generic(url, deepness, xpath)


def propagate_totobro(url, deepness):
    xpath = '//div[@class=\'entry-content\']//a[contains(text(), \'{}\')]/@href'
    return propagate_generic(url, deepness, xpath)


PROPAGATORS = {r'http(s)?://totobro.com/': propagate_totobro,
               r'http(s)?://.*thetranslation.wordpress.com/': propagate_nanodesu,
               r'http(s)?://clickyclicktranslation.blogspot.(com|co.za)/': propagate_clickclick}


def propagate(urls, deepnesses):
    """
    apply appropriate propagation function to each url with
    corresponding deepness
    :param urls: list/tuple
    :param deepnesses: list/tuple
    :return:
    """
    all_urls = []
    for url, deepness in zip(urls, deepnesses):
        if deepness == 0:
            all_urls.append(url)
        else:
            propagator = find_best_match(url, PROPAGATORS)
            try:
                all_urls.extend(propagator(url, deepness))
            except TypeError:
                raise RuntimeError('Unable to propagate {} . Absence of appropriate propagator'.format(url))
    if len(urls) > len(deepnesses):
        all_urls.extend(urls[len(deepnesses):])
    return all_urls


def supported_propagators():
    return PROPAGATORS.keys()
