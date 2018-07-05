# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import gzip
import io
import itertools
import os
import textwrap
import unittest

import six
from Bio.Seq import Seq

from moclo.record import CircularRecord
from moclo.kits import cidar

from .utils import plasmids


### Test CIDAR plasmids

# Metaclass for test suites: create a test suite per type with a method per
# plasmid that will check if that plasmid is recognized as the test suite
# part or not rightfully. The `_TestCIDAR` instance acts as a single test case.
class _TestCIDAR(unittest.TestCase):

    _plasmids = None

    @classmethod
    def make_suite(cls, part_cls, part_name, exclude=frozenset()):
        if cls._plasmids is None:
            cls._plasmids = list(plasmids('cidar.tsv.xz'))
        case_name = str('Test{}'.format(part_cls.__name__))
        tests = {
            test.__name__: test
            for plasmid in cls._plasmids
            if plasmid[0] not in exclude
            for test in (cls(*plasmid, part_cls=part_cls, part_name=part_name),)
        }
        return type(case_name, (unittest.TestCase,), tests)

    def __init__(self, id_, type_, name, desc, seq, part_cls, part_name):
        self.id = id_
        self.type = type_
        self.name = name
        self.desc = desc
        self.seq = seq
        self.rec = CircularRecord(Seq(seq), name=name, id=id_)
        self._part_cls = part_cls
        self._part_type = part_name

    def _assert_valid(self):
        err = '{} is not a valid Type {} but should be!'
        self.assertTrue(
            self._part_cls(self.rec).is_valid(),
            err.format(self.id, self._part_type)
        )

    def _assert_invalid(self):
        err = '{} is a valid Type {} but should not be!'
        self.assertFalse(
            self._part_cls(self.rec).is_valid(),
            err.format(self.id, self._part_type)
        )

    def __call__(self):
        if self.type == self._part_type:
            self._assert_valid()
        else:
            self._assert_invalid()

    @property
    def __name__(self):
        if self.type == self._part_type:
            msg = "test_{}_is_{}"
        else:
            msg = "test_{}_is_not_{}"
        return str(msg.format(self.id, self._part_type))

    @property
    def __doc__(self):
        if self.name == self._part_type:
            doc = 'Check that {} ({}) is a CIDAR {}.\n'
        else:
            doc = 'Check that {} ({} - {}) is not a CIDAR {}.\n'
        return doc.format(self.id, self.type, self.name, self._part_type)


# Generate test cases
TestCIDARPromoter = _TestCIDAR.make_suite(cidar.CIDARPromoter, 'Promoter')
TestCIDARibosomeBindingSite = _TestCIDAR.make_suite(cidar.CIDARibosomeBindingSite, 'RBS')
TestCIDARCodingSequence = _TestCIDAR.make_suite(cidar.CIDARCodingSequence, 'CDS')
TestCIDARTerminator = _TestCIDAR.make_suite(cidar.CIDARTerminator, 'Terminator')