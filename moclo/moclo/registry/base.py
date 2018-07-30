# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import abc
import io
import itertools
import typing

import Bio.SeqIO
import cached_property
import fs
import pkg_resources
import six
from fs.wrap import read_only
from fs.path import splitext

from .._impl import bz2, json
from ..record import CircularRecord
from ..core import AbstractModule, AbstractVector, AbstractPart
from .utils import find_resistance, find_type


class Item(typing.NamedTuple('Item', [
            ('id', typing.Text),
            ('name', typing.Text),
            ('entity', typing.Union[AbstractModule, AbstractVector]),
            ('resistance', typing.Text),
        ])):
    """A uniquely identified record in a registry.
    """


class AbstractRegistry(typing.Mapping[typing.Text, Item]):
    """An abstract registry holding MoClo plasmids.
    """

class CombinedRegistry(AbstractRegistry):
    """A registry combining several registries into a single collection.
    """

    def __init__(self):
        self._data = {}

    def __lshift__(self, registry):
        self.add_registry(registry)
        return self

    def add_registry(self, registry):
        for item in six.itervalues(registry):
            self._data.setdefault(item.id, item)

    def __getitem__(self, item):
        return self._data[item]

    def __contains__(self, item):
        return item in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)


class EmbeddedRegistry(AbstractRegistry):
    """An embedded registry, distributed with the library source code.

    Records are stored within a BZ2 compressed JSON file, using standard
    annotations to allow retrieving features easily.
    """

    _module = NotImplemented
    _file = NotImplemented
    _types = NotImplemented

    def _load_id(self, raw, index):
        return raw['id']

    def _load_name(self, raw, index):
        return raw['name']

    def _load_location(self, raw, index):
        return raw['location']

    def _load_resistance(self, raw, index):
        return raw['resistance']

    def _load_entity(self, raw, index):
        return self._types[raw['type']](raw['record'])

    @cached_property.cached_property
    def _data(self):
        with pkg_resources.resource_stream(self._module, self._file) as rs:
            with io.TextIOWrapper(bz2.BZ2File(rs)) as decomp:
                raw_data = json.load(decomp)
        for raw in raw_data:
            record = Bio.SeqIO.read(six.StringIO(raw['gb']), 'gb')
            raw['record'] = CircularRecord(record)
        return {
            item.id: item
            for item in (
                Item(
                    id=self._load_id(raw, index),
                    name=self._load_name(raw, index),
                    # location=self._load_location(raw, index),
                    resistance=self._load_resistance(raw, index),
                    entity=self._load_entity(raw, index),
                )
                for index, raw in enumerate(raw_data)
            )
        }

    def __len__(self):
        return len(self._data)

    def __getitem__(self, item):
        return self._data[item]

    def __iter__(self):
        return iter(self._data)


class FilesystemRegistry(AbstractRegistry):
    """A registry located on a filesystem.
    """

    def __init__(self, fs_url, base, extensions=('gb', 'gbk')):

        bases = (AbstractPart, AbstractModule, AbstractVector)
        if not isinstance(base, type) or not issubclass(base, (bases)):
            raise TypeError("base cannot be '{}'".format(base))

        self.fs = read_only(fs.open_fs(fs_url))
        self.base = base
        self._recurse = False
        self._extensions = extensions
        self._cache = {}

    @cached_property.cached_property
    def _files(self):
        return ['*.{}'.format(extension) for extension in self._extensions]

    def __iter__(self):
        for f in self.fs.filterdir('/', files=self._files, exclude_dirs=['*']):
            name, _ = splitext(f.name)
            yield name

    def __len__(self):
        return sum(1 for _ in self.fs.filterdir('/', files=self._files, exclude_dirs=['*']))

    def __getitem__(self, item):
        files = ('{}.{}'.format(item, extension) for extension in self._extensions)
        for name in files:
            if self.fs.isfile(name):
                with self.fs.open(name) as handle:
                    record = Bio.SeqIO.read(handle, 'genbank')
                    record.id, _ = splitext(name)
                return Item(
                    id=record.id,
                    name=record.description,
                    entity=find_type(record, self.base),
                    resistance=find_resistance(record),
                )
        raise KeyError(item)
