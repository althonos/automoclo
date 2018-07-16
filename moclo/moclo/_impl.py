# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import importlib


def _import_from(*names):
    for name in names:
        try:
            return importlib.import_module(name)
        except ImportError:
            pass
    raise ImportError('no module found among: {}'.format(', '.join(names)))


json = _import_from('ujson', 'yajl', 'simplejson', 'json')
lzma = _import_from('lzma', 'backports.lzma')
