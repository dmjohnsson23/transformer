from __future__ import annotations
from collections import namedtuple
from pdfminer.pdftypes import resolve1
from bitarray import bitarray
from enum import Enum
from typing import Iterable, Any, List, Tuple
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

    # Note: all flag indexes should be the inverse of the value in the PDF documentation
    @property
    def is_read_only(self) -> bool:
        return self.field_flags[-1]
    @property
    def is_required(self) -> bool:
        return self.field_flags[-2]
    @property
    def is_no_export(self) -> bool:
        return self.field_flags[-3]
    @property
    def is_radio_button_no_toggle_off(self) -> bool:
        """For radio buttons, indicates that once set, the value cannot be unselected. (This behavior is the only supported behavior in HTML)"""
        return self.type == FormFieldType.button and self.field_flags[-15]
    @property
    def is_radio_button_in_unison(self) -> bool:
        """For radio buttons, indicates that buttons with the same value are selected "as one". (This behavior is not supported in HTML)"""
        return self.type == FormFieldType.button and self.field_flags[-26]
    @property
    def is_radio_button(self) -> bool:
        """For buttons, indicates if this is a radio button"""
        return self.type == FormFieldType.button and self.field_flags[-16]
    @property
    def is_push_button(self) -> bool:
        """For buttons, indicates if this is a regular button (push button)"""
        return self.type == FormFieldType.button and self.field_flags[-17]
    @property
    def is_checkbox(self) -> bool:
        """For buttons, indicates if this is a checkbox"""
        return self.type == FormFieldType.button and not (self.field_flags[-16] or self.field_flags[-17])
    @property
    def is_multiline_text(self) -> bool:
        """For text fields, indicates that this is a multiline field"""
        return self.type == FormFieldType.text and self.field_flags[-13]
    @property
    def is_password(self) -> bool:
        """For text fields, indicates that this is a password field"""
        return self.type == FormFieldType.text and self.field_flags[-14]
    @property
    def is_file(self) -> bool:
        """For text fields, indicates that this is a file upload field"""
        return self.type == FormFieldType.text and self.field_flags[-21]
    @property
    def spellcheck_allowed(self) -> bool:
        """For text or choice fields, indicates that this is a field allows spellchecking"""
        return self.type in (FormFieldType.text, FormFieldType.choice) and not self.field_flags[-23]
    @property
    def scroll_allowed(self) -> bool:
        """For text fields, indicates that this field allows more text than fits in it's defined area (This is the default behavior in HTML, so this flag is meaningless)"""
        return self.type == FormFieldType.text and not self.field_flags[-24]
    @property
    def is_text_comb(self) -> bool:
        """For text fields, indicates that this field is a comb field (Meaning somewhat unclear from docs?)"""
        return self.type == FormFieldType.text and self.field_flags[-25]
    @property
    def is_rich_text(self) -> bool:
        """For text fields, indicates that this field allows rich text"""
        return self.type == FormFieldType.text and self.field_flags[-26]
    @property
    def is_plain_text(self) -> bool:
        """For text fields, indicates that this field does not allow rich text"""
        return self.type == FormFieldType.text and not self.field_flags[-26]
    @property
    def max_length(self) -> int|None:
        """For text fields, indicates the max length of the input"""
        return self.raw_data.get('MaxLen')
    @property
    def is_combo_box(self) -> bool:
        """For choice fields, indicates that this field is a combobox"""
        return self.type == FormFieldType.choice and self.field_flags[-18]
    @property
    def is_list_box(self) -> bool:
        """For choice fields, indicates that this field is a list box"""
        return self.type == FormFieldType.choice and not self.field_flags[-18]
    @property
    def is_editable_combo_box(self) -> bool:
        """For choice fields, indicates that this field is a combobox and includes and editable text field"""
        return self.type == FormFieldType.choice and self.field_flags[-19]
    @property
    def is_multi_select(self) -> bool:
        """For choice fields, indicates that this field is a multiselect"""
        return self.type == FormFieldType.choice and self.field_flags[-22]
    @property
    def select_options(self) -> List[Tuple[str,str]]:
        """Options for select fields"""
        values = self.raw_data.get('Opt')
        if not values:
            return values
        options = []
        for val in values:
            if isinstance(val, list):
                options.append(tuple(val))
            else:
                options.append((val, val))
        return options
    # TODO TI and I values for choice fields
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
            self._field_flags = bitarray("{0:0>32b}".format(field_flags))
            return self._field_flags
        # Field flags values can also be inherited from parent
        if self.parent is not None:
            return self.parent.field_flags
        return bitarray(32)
    @property
    def annotation_flags(self) -> bitarray|None:
        if self._annotation_flags is not None:
            return self._annotation_flags
        if 'Ff' in self.raw_data:
            annotation_flags = self.raw_data['F']
            self._annotation_flags = bitarray("{0:0>32b}".format(annotation_flags))
            return self._annotation_flags
        return bitarray(32)
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

    #TODO Mk (style dictionary)
