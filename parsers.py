__author__ = 'lundibundi'

from urllib.parse import urlsplit
from urllib.request import urlopen, Request

from lxml import html
from weasyprint import unicode, CSS

from utils import *


def flatten(seq):
    flat = []
    for el in seq:
        if isinstance(el, (str, unicode)):
            flat.append(unicode(el))
        elif isinstance(el, html.etree._Element):
            flat.append(html.tostring(el, with_tail=False))
    return u''.join(flat)


class Parser(object):
    """
    base parser class
    """

    def __init__(self, url, process_css=True):
        super().__init__()
        self.url = url
        self.base_url = '{0.scheme}://{0.netloc}'.format(urlsplit(url))
        request = urlopen(Request(url, headers={'User-Agent':
                                                    'Mozilla/5.0 (Windows NT 5.1; rv:10.0.1) '
                                                    'Gecko/20100101 Firefox/10.0.1'}))
        self.data = request.read()
        encoding = request.headers.get_content_charset()
        self.data = self.data.decode(encoding if encoding else 'utf-8')
        self.doc = html.fromstring(self.data)
        self.doc.make_links_absolute(self.base_url)
        self.title = self.doc.xpath('//title')[0].text_content()
        self.css = []
        if process_css:
            # find all css-text
            for css in self.doc.xpath("//style[@type=\'text/css\']"):
                self.css.append(CSS(string=css.text_content()))
            # find css-links
            for css in self.doc.xpath("//link[@rel=\'stylesheet\']/@href"):
                self.css.append(css)

    def parse(self):
        raise NotImplementedError


class TotobroParser(Parser):
    def parse(self):
        self.data = html.tostring(self.doc.find_class('entry-header')[0])
        self.title = self.doc.xpath('//h1[@class=\'entry-title\']//text()')[0]
        # delete links to other chapters
        text = self.doc.find_class('entry-content')[0]
        for junk in text.xpath('.//*[@style]'):
            junk.getparent().remove(junk)

        self.data += html.tostring(text)
        return self.data


class SamlibParser(Parser):
    def parse(self):
        # self.data = self.doc.xpath('//*[preceding-sibling::comment()[. = '
        #                       '\'--------- Собственно произведение -------------\'] '
        #                       'and following-sibling::comment()[. = '
        #                       '\'-----------------------------------------------\']]')
        start_comm = '<!----------- Собственно произведение --------------->'
        end_comm = '<!--------------------------------------------------->'
        start_data = self.data.index(start_comm) + len(start_comm)
        end_data = self.data.index(end_comm, start_data)
        self.data = self.data[start_data:end_data].lstrip('\r\n')
        return self.data


class NanodesuParser(Parser):
    def parse(self):
        # add title
        self.data = html.tostring(self.doc.find_class('page-title')[0])
        text = self.doc.xpath('//div[@class=\'page-body\']')[0]

        # delete links to other chapters
        for junk in text.xpath('(//div[@id=\'jp-post-flair\'] | //a[. = \'Next Page\' or . = \'Previous Page\' '
                               'or contains(following-sibling::text(), \'Next Page\') '
                               'or contains(following-sibling::text(), \'Previous Page\')])'):
            junk.getparent().remove(junk)

        self.data += html.tostring(text)
        return self.data


class ClickClickParser(Parser):
    def parse(self):
        # add title
        self.data = html.tostring(self.doc.find_class('post-title entry-title')[0])
        text = self.doc.xpath('//div[@class=\'post-body entry-content\']')[0]

        # delete links to other chapters
        for junk in text.xpath('(//div[@style=\'text-align: center;\'] | '
                               '//a[contains(text(), \'Prev\') or contains(text(), \'Next\')])'):
            junk.getparent().remove(junk)

        self.data += html.tostring(text)
        return self.data


PARSERS = {r'http(s)?://totobro.com/': TotobroParser, r'http(s)?://samlib.ru/': SamlibParser,
           r'http(s)?://.*thetranslation.wordpress.com/': NanodesuParser,
           r'http(s)?://clickyclicktranslation.blogspot.(com|co.za)/': ClickClickParser}


def find_parser(url):
    return find_best_match(url, PARSERS)


def supported_parsers():
    return PARSERS.keys()
