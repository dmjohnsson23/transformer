from __future__ import annotations
from collections import defaultdict
from bs4 import BeautifulSoup
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdftypes import resolve1
from .utils import *
from .types import *




def process_form_to_trees(pdf_filename: str):
    from json import dumps
    with open(pdf_filename, 'rb') as pdf_file:
        parser = PDFParser(pdf_file)
        doc = PDFDocument(parser)
        res = resolve1(doc.catalog)
        if 'AcroForm' not in res:
            return # No form found, so nothing to do
        fields = resolve1(doc.catalog['AcroForm'])['Fields']  # may need further resolving
        return list(iter_pdf_form_fields(fields))

# See https://pdfminersix.readthedocs.io/en/latest/howto/acro_forms.html
def process_form(pdf_filename: str, soup: BeautifulSoup, zoom: int = 1):
    from json import dumps
    with open(pdf_filename, 'rb') as pdf_file:
        parser = PDFParser(pdf_file)
        doc = PDFDocument(parser)
        res = resolve1(doc.catalog)
        if 'AcroForm' not in res:
            return # No form found, so nothing to do
        html_form = soup.find(id='page-container').wrap(soup.new_tag('form'))
        html_pages = html_form.find_all(class_='pf')
        inputs_by_parent = defaultdict(lambda: soup.new_tag('div', attrs={'class':'form-inputs'}))
        fields = resolve1(doc.catalog['AcroForm'])['Fields']  # may need further resolving
        for field in iter_pdf_form_fields(fields):
            if field.type == FormFieldType.button:
                input = soup.new_tag('input', type='checkbox')
            elif field.type == FormFieldType.text:
                input = soup.new_tag('input', type='text')
            elif field.type == FormFieldType.choice:
                input = soup.new_tag('select')
            elif field.type == FormFieldType.signature:
                input = soup.new_tag('input', type='file')
            else:
                continue
            input.attrs['name'] = field.map_name
            input.attrs['aria-label'] = field.alt_name
            # The PDF format considers the bottom-left corner to be the origin
            input.attrs['style'] = f"""
                position: absolute;
                left: {field.rect.x1 * zoom}px;
                bottom: {field.rect.y1 * zoom}px;
                width: {(field.rect.x2 - field.rect.x1) * zoom}px;
                height: {(field.rect.y2 - field.rect.y1) * zoom}px;
            """.replace('                ', ' ').replace('\n', '')
            inputs_by_parent[field.raw_data['P'].objid].append('\n')
            inputs_by_parent[field.raw_data['P'].objid].append(input)
            inputs_by_parent[field.raw_data['P'].objid].append('\n')
        for fieldset, page in zip(inputs_by_parent.values(), html_pages):
            page.append(fieldset)
    style = soup.new_tag('style')
    style.append("""
        .form-inputs{
            bottom: -3px;
            left: -4px;
            position: absolute;
        }
        .form-inputs input,
        .form-inputs select{
            border: none;
            background: rgba(0,0,0,.05);
        }
    """)
    soup.find('head').append(style)