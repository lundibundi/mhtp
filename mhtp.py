__author__ = 'lundibundi'

from io import BytesIO
from urllib.request import urlsplit
from itertools import cycle
import logging
import os
import argparse

from weasyprint import HTML

from PyPDF2 import PdfFileMerger, PdfFileReader

from parsers import find_parser, supported_parsers
from propagate import propagate, supported_propagators


# define script options
class NameAndUrls(argparse.Action):
    def __init__(self, option_strings, dest, nargs='+', **kwargs):
        if nargs != '+':
            raise ValueError('must have at least 1 value in a list')
        super(NameAndUrls, self).__init__(option_strings, dest, nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        data = []
        # first name must exist or be empty
        name = ''
        if urlsplit(values[0]).scheme == '':
            name = values[0]
            values = values[1:]
        urls = []
        for val in values:
            if urlsplit(val).scheme == '':
                data.append((name, urls))
                urls = []
                name = val
            else:
                urls.append(val)
        data.append((name, urls))
        setattr(namespace, self.dest, data)


# automatically add defaults to help-text
argparser = argparse.ArgumentParser(
    description='Download html-pages from multiple sites and convert them to pdf.\n\n'
                'Supported for parsing: \n' + '\n'.join(supported_parsers()) +
                '\n\nSupported for propagation: \n' + '\n'.join(supported_propagators()),
    # workaround: -p in optional arg with nargs which leads to the possibility of it
    # consuming positional arguments, to prevent this add -- at the end of -p
    # see https://bugs.python.org/issue9338
    # but it's hard to insert -- in usage pattern of single option -> hardcoded
    usage='''usage: mhtp.py [-h] [-s] [-p deepness [deepness ...] --] [--no-css]
                            [-a] [-q] [-v]
                            name url [url ...] [name url [url ...] ...]''',
    formatter_class=argparse.RawDescriptionHelpFormatter)
# formatter_class=argparse.ArgumentDefaultsHelpFormatter)

# define arguments
argparser.add_argument('data', action=NameAndUrls, nargs='+',
                       metavar='name url [url ...]',
                       help='name - absolute or relative path (if relative current_dir/path used, '
                            'if only path title from html is used). url - urls to be downloaded, '
                            'converted to pdf and saved to name. Name may be omitted '
                            '(name from first url/html will be used) but be aware that in case of '
                            'multiple queries Names split queries')
argparser.add_argument('-s', '--separate-pdfs', action='store_true', default=False,
                       help='store each supplied url as a separate pdf. '
                            'Warning name-argument is used as directory(name/html_title)'
                            ' or current_dir/html_title is used instead for each url')
argparser.add_argument('-p', '--propagate', action='store', type=int, nargs='+', default=False,
                       metavar='deepness',
                       help='Will be applied to each url in order(1st deepness to 1st url ...) '
                            'or cycle over deepnesses if not enough. '
                            'deepness: >0 - propagate forth, <0 - backwards')
argparser.add_argument('--no-css', action='store_true', default=False,
                       help='Don\'t use css files and text, gathered from html while generating pdf')
argparser.add_argument('-a', '--append', action='store_true', default=False,
                       help='If pdf file already exists add new pages instead of rewriting pdf')
argparser.add_argument('-q', '--quiet', action='store_true', default=False,
                       help='Suppress all output(default is: progress and errors)')
argparser.add_argument('-v', '--verbose', action='store_true', default=False,
                       help='Verbose output(default is: progress and errors). '
                            'P.s. expect a lot of warnings because of css parsing, that is actually okay.')


def process_urls(name_urls):
    """
    Download html for each url, merge them if needed and save
    :param name_urls: tuple or list of (name, urls)
            name: string - filename(either absolute path or not)
            urls: string - urls to download
    :return: None
    """
    for name, urls in name_urls:
        logger.info('Processing: {0} - {1}'.format(name, urls))
        documents = []
        for url in urls:
            logger.info('{: <8}Finding parser for {} :'.format('', url))
            parser = find_parser(url)
            if not parser:
                logger.error('{: <16}There is no parser to process: {} . Skipping.'.format('', url))
            else:
                logger.info('{: <16}ok: {}'.format('', parser.__name__))
                logger.info('{: <8}Parsing: {} :'.format('', url))
                try:
                    parsed = parser(url, not OPTIONS['no_css'])
                    parsed.parse()
                except:
                    logger.error('{: <16}Error while parsing: {} - '.format('', url))
                    raise
                doc = HTML(string=parsed.data, base_url=parsed.base_url).render(stylesheets=parsed.css)
                doc.metadata.title = parsed.title
                documents.append(doc)
                logger.info('{: <16}ok: {}'.format('', parsed.title))

        if not os.path.isabs(name):
            name = os.path.join(os.getcwd(), name)

        if OPTIONS['separate_pdfs']:
            if os.path.basename(name):
                # add os.path.sep at the end to indicate directory
                name = os.path.join(name, '')
        # check if there are no documents
        elif documents:
            # all in one document
            all_pages = [p for doc in documents for p in doc.pages]
            documents = [documents[0].copy(all_pages)]
            if os.path.basename(name):
                documents[0].metadata.title = ''

        for doc in documents:
            path = name
            if doc.metadata.title:
                path = os.path.join(path, doc.metadata.title)
            if not path.endswith('.pdf'):
                path += '.pdf'
            os.path.normpath(path)
            if OPTIONS['append'] and os.path.isfile(path):
                logger.info('{: <8}Appending pdf: {}'.format('', path))
                merger = PdfFileMerger()
                merger.append(PdfFileReader(path))
                merger.append(BytesIO(doc.write_pdf()))
                merger.write(path)
                merger.close()
            else:
                logger.info('{: <8}Saving pdf: {}'.format('', path))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                doc.write_pdf(path)


# configure logging
logging.basicConfig(format='{name} {levelname:8s}: {message}', style='{')
logger = logging.getLogger()
# delete handler for weasyprint -> use root handler
logging.getLogger('weasyprint').removeHandler(logging.getLogger('weasyprint').handlers[0])

if __name__ == '__main__':
    # get options from command line
    OPTIONS = vars(argparser.parse_args())
    # configure logging level
    if OPTIONS['quiet']:
        logging.getLogger().disabled = True
        logging.getLogger('weasyprint').disabled = True
    elif OPTIONS['verbose']:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('weasyprint').setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
        logging.getLogger('weasyprint').setLevel(logging.ERROR)

    # check data
    data = OPTIONS['data']
    if not data:
        argparser.print_help()
    elif OPTIONS['propagate']:
        logger.info('Propagating urls:')
        deepnesses = cycle(OPTIONS['propagate'])
        # propagate each url by corresponding deepness or cycle form start
        data = [(name, propagate(urls, [d for _, d in zip(range(0, len(urls)), deepnesses)])) for name, urls in data]
        logger.info('Propagated data: {}'.format(data))
    process_urls(data)
