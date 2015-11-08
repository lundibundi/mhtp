__author__ = 'lundibundi'

import re


def find_best_match(item, container):
    """
    finds longest match of item in container's keys
    :param item: string
    :param container: dictionary of format value_to_compare: output
    :return: container value
    """
    match = None
    length = None
    for elem, t_match in container.items():
        t_length = len(elem)
        if (length is None or length < t_length) and re.search(elem, item):
            match = t_match
            length = t_length
    return match
