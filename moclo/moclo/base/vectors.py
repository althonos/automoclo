# coding: utf-8

import abc

import cached_property
import six
import typing
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from ..record import CircularRecord
from ._structured import StructuredRecord

if typing.TYPE_CHECKING:
    from .modules import AbstractModule


class AbstractVector(StructuredRecord):
    """An abstract modular cloning vector.
    """
    _level = None

    def overhang_start(self):
        return Seq(self._match.group(3))

    def overhang_end(self):
        return Seq(self._match.group(1))

    def placeholder_sequence(self):
        start, end = self._match.span(2)
        if isinstance(self.record, CircularRecord):
            return (self.record << start)[:end-start]
        else:
            return self.record[start:end]

    def insert(self, module, *modules):
        # type: (AbstractModule, *AbstractModule) -> SeqRecord

        # FIXME

        # Identify all modules by their respective overhangs, checking
        # for possible duplicates.
        modmap = {module.overhang_start(): module}
        for mod in modules:
            mod2 = modmap.setdefault(mod.overhang_start(), mod)
            if mod2 is not mod:
                msg = "'{}' and '{}' share the same start overhang: '{}'".format(
                    mod2.record.name or mod2.record.id,
                    mod.record.name or mod.record.id,
                    mod.overhang_start())
                raise RuntimeError(msg)

        assert self.overhang_end() != self.overhang_start()
        assert self.overhang_end() in modmap

        # Generate the complete inserted sequence
        overhang_next = self.overhang_end()
        assembly = SeqRecord(overhang_next, id='assembly')
        while overhang_next != self.overhang_start():
            module = modmap.pop(overhang_next)
            assembly += module.target_sequence()
            overhang_next = module.overhang_end()
            if overhang_next != self.overhang_end():
                assembly += overhang_next

        if modmap:
            raise RuntimeError('not all parts were used!')

        # Replace placeholder in the vector while keeping annotations
        ph_start, ph_end = self._match.span(0)
        rec = (self.record << ph_start)
        return CircularRecord(assembly + rec[ph_end - ph_start:])


class EntryVector(AbstractVector):
    """Level 0 vector.
    """

    _level = 0


class CassetteVector(AbstractVector):
    """Level 1 vector.
    """

    _level = 1


class MultigeneVector(AbstractVector):
    """Level 2 vector.
    """

    _level = 2
