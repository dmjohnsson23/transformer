from __future__ import annotations
from pypdf import PdfReader

def get_fields_annotations_by_page(reader:PdfReader, *, page_nos=None, fields=None):
    """
    Gets fields, along with the associated annotations, divided out by page number

    Output is a dictionary in the form {page_no: {field_name: (field, annotation)}}
    """
    if page_nos is None:
        page_nos = range(len(reader.pages))
    if fields is None:
        fields = reader.get_fields()
    out = {}
    for page_no, page in enumerate(reader.pages):
        if page_no not in page_nos: continue
        if page.annotations is None: continue
        out[page_no] = {}
        for name, field in fields.items():
            for annot in page.annotations:
                if annot.indirect_reference == field.indirect_reference:
                    out[page_no][name] = (field, annot)
    return out