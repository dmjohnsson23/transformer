from __future__ import annotations
from pdfminer.pdftypes import resolve1
from pdfminer.psparser import PSLiteral, PSKeyword
from pdfminer.utils import decode_text


def decode_pdf_value(value):
    if isinstance(value, (PSLiteral, PSKeyword)):
        value = value.name
    if isinstance(value, bytes):
        value = decode_text(value)
    return value


def iter_pdf_form_fields(fields):
    from .types import FormField # Import here to avoid circular import
    for field in fields:
        if isinstance(field, FormField):
            field_obj = field
        else:
            field_obj = FormField(resolve1(field))
        if field_obj.children is not None:
            yield from iter_pdf_form_fields(field_obj.children)
        else:
            yield field_obj

