from __future__ import annotations
from collections import namedtuple
from pdfminer.pdftypes import resolve1
from bitarray import bitarray
from enum import Enum
from typing import Iterable, Any
from .utils import decode_pdf_value


Rect = namedtuple('Rect', 'x1,y1,x2,y2')

class FormFieldType(Enum):
    button = 'Btn'
    text = 'Tx'
    choice = 'Ch'
    signature = 'Sig'

class FormField:
    # see https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf
    parent: FormField
    raw_data: dict

    def __init__(self, raw_data:dict, parent:FormField=None) -> None:
        self.raw_data = raw_data
        self.parent = parent
        self._values = self._default_values = self._field_flags = self._annotation_flags = self._rect = self._children = None
    
    @property
    def name(self) -> str|None:
        return decode_pdf_value(self.raw_data.get('T'))
    @property
    def alt_name(self) -> str|None:
        return decode_pdf_value(self.raw_data.get('TU')) or self.name
    @property
    def map_name(self) -> str|None:
        return decode_pdf_value(self.raw_data.get('TM')) or self.name

    # TODO not sure I have the flag index right here
    @property
    def flag_read_only(self) -> bool:
        return self.field_flags[0]
    @property
    def flag_required(self) -> bool:
        return self.field_flags[1]
    @property
    def flag_no_export(self) -> bool:
        return self.field_flags[2]
    @property
    def type(self) -> FormFieldType|None:
        if 'FT' in self.raw_data:
            return FormFieldType(decode_pdf_value(self.raw_data['FT']))
        # Type can be inherited from parent
        if self.parent is not None:
            return self.parent.type
        return None
    @property
    def values(self) -> Any:
        if self._values is not None:
            return self._values
        if 'V' in self.raw_data:
            values = resolve1(self.raw_data.get('V'))
            if isinstance(values, list):
                values = [decode_pdf_value(v) for v in values]
            else:
                values = decode_pdf_value(values)
            self._values = values
            return self._values
        # Values can also be inherited from parent
        if self.parent is not None:
            return self.parent.values
        return None
    @property
    def default_values(self) -> Any:
        if self._default_values is not None:
            return self._default_values
        if 'DV' in self.raw_data:
            values = resolve1(self.raw_data.get('DV'))
            if isinstance(values, list):
                values = [decode_pdf_value(v) for v in values]
            else:
                values = decode_pdf_value(values)
            self._default_values = values
            return self._default_values
        # Default values can also be inherited from parent
        if self.parent is not None:
            return self.parent.default_values
        return None
    @property
    def field_flags(self) -> bitarray|None:
        if self._field_flags is not None:
            return self._field_flags
        if 'Ff' in self.raw_data:
            field_flags = self.raw_data['Ff']
            self._field_flags = bitarray("{0:b}".format(field_flags)) if field_flags else bitarray(32)
            return self._field_flags
        # Field flags values can also be inherited from parent
        if self.parent is not None:
            return self.parent.field_flags
        return None
    @property
    def annotation_flags(self) -> bitarray|None:
        if self._annotation_flags is not None:
            return self._annotation_flags
        if 'Ff' in self.raw_data:
            annotation_flags = self.raw_data['F']
            self._annotation_flags = bitarray("{0:b}".format(annotation_flags)) if annotation_flags else bitarray(32)
            return self._annotation_flags
        return None
    @property
    def rect(self) -> Rect|None:
        if self._rect is not None:
            return self._rect
        if 'Rect' in self.raw_data:
            self._rect = Rect(*self.raw_data.get('Rect'))
            return self._rect
        return None
    @property
    def children(self) -> Iterable[FormField]|None:
        if self._children is not None:
            return self._children
        if 'Kids' in self.raw_data:
            self._children = tuple([FormField(resolve1(child), self) for child in self.raw_data['Kids']])
            return self._children
        return None

    #TODO MaxLen
    #TODO Mk (style dictionary)
    #TODO button type (checkbox, radio, etc...)
