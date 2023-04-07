from __future__ import annotations
from collections import defaultdict, namedtuple
import os, sys, shutil
from subprocess import run
from bs4 import BeautifulSoup
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdftypes import resolve1
from pdfminer.psparser import PSLiteral, PSKeyword
from pdfminer.utils import decode_text
from bitarray import bitarray
from dataclasses import dataclass, field as datafield
from enum import Enum
from typing import List, Any

def main(input_path, output_path, *, pdf2html, pdf2html_options=[], no_scripts=False, no_ui=False, do_form=False):
    if not os.path.isfile(pdf2html):
        print("Cannot run pdf2html; path is not valid", file=sys.stderr)
        exit(1)
    result = run([
        pdf2html,
        *pdf2html_options,
        input_path,
        output_path
    ])
    if result.returncode != 0:
        exit(result.returncode)
    with open(output_path, 'r+') as file:
        soup = BeautifulSoup(file.read(), 'lxml')

        if no_scripts:
            for script in soup.find_all('script'):
                script.decompose()

        if no_ui:
            soup.find(id='sidebar').decompose()
            for el in soup.find_all(class_='loading-indicator'):
                el.decompose()
        
        if do_form:
            _process_form(input_path, soup)
        
        file.seek(0)
        file.write(str(soup))
        file.truncate()

def _decode_pdf_value(value):
    if isinstance(value, (PSLiteral, PSKeyword)):
        value = value.name
    if isinstance(value, bytes):
        value = decode_text(value)
    return value

# See https://pdfminersix.readthedocs.io/en/latest/howto/acro_forms.html
def _process_form(pdf_filename: str, soup: BeautifulSoup):
    from json import dumps
    with open(pdf_filename, 'rb') as pdf_file:
        parser = PDFParser(pdf_file)
        doc = PDFDocument(parser)
        res = resolve1(doc.catalog)
        if 'AcroForm' not in res:
            return # No form found, so nothing to do
        html_form = soup.find(id='page-container').wrap(soup.new_tag('form'))
        html_pages = html_form.find_all(class_='pf')
        inputs_by_parent = defaultdict(lambda: soup.new_tag('div', class_='form-inputs'))
        fields = resolve1(doc.catalog['AcroForm'])['Fields']  # may need further resolving
        for field in _iter_pdf_form_fields(fields):
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
            input.attrs['style'] = f"""
                position: absolute;
                left: {field.rect.left}px;
                right: {field.rect.right}px;
                top: {field.rect.top}px;
                bottom: {field.rect.bottom}px;
            """.replace('\n', '').replace(' ', '')
            input.attrs['data-details'] = repr(field)
            inputs_by_parent[field.raw_data['P'].objid].append(input)
        for fieldset, page in zip(inputs_by_parent.values(), html_pages):
            page.append(fieldset)


class FormFieldType(Enum):
    none = None
    button = 'Btn'
    text = 'Tx'
    choice = 'Ch'
    signature = 'Sig'

@dataclass
class FormField:
    parent: FormField
    children: List[FormField] = datafield(init=False, repr=False)
    name: str
    values: Any
    default: Any
    type: str = datafield(repr=False)
    alt_name: str = datafield(repr=False)
    map_name: str = datafield(repr=False)
    annotation_flags: bitarray = datafield(repr=False)
    field_flags: bitarray = datafield(repr=False)
    rect: Rect = datafield(repr=False)
    raw_data: dict  = datafield(repr=False)

    # TODO not sure I have the flag index right here
    @property
    def flag_read_only(self):
        return self.field_flags[0]
    @property
    def flag_required(self):
        return self.field_flags[1]
    @property
    def flag_no_export(self):
        return self.field_flags[2]

Rect = namedtuple('Rect', 'left,top,right,bottom')

def _iter_pdf_form_fields(fields, parent=None):
    for f in fields:
        field = resolve1(f)
        print(field)
        # see https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf
        name = _decode_pdf_value(field.get('T'))
        alt_name = _decode_pdf_value(field.get('TU')) or name
        map_name = _decode_pdf_value(field.get('TM')) or name
        values = resolve1(field.get('V'))
        default = resolve1(field.get('DV'))
        type = FormFieldType(_decode_pdf_value(field.get('FT')))
        annotation_flags = field.get('F')
        field_flags = field.get('Ff')
        style_dict = field.get('Mk') # TODO parse this
        rect = Rect(*field.get('Rect')) if 'Rect' in field else None
        # TODO: MaxLen


        # decode value(s)
        if isinstance(values, list):
            values = [_decode_pdf_value(v) for v in values]
        else:
            values = _decode_pdf_value(values)

        field_obj = FormField(
            parent,
            name,
            values,
            default,
            type,
            alt_name,
            map_name,
            bitarray("{0:b}".format(annotation_flags)) if annotation_flags else bitarray(32),
            bitarray("{0:b}".format(field_flags)) if field_flags else bitarray(32),
            rect,
            field
        )
        children = field.get('Kids')
        # Yield only the terminal fields; the rest we can get though the parent attribute
        if children:
            field_obj.children = tuple(_iter_pdf_form_fields(children, field_obj))
            yield from field_obj.children
        else:
            yield field_obj

if __name__ == '__main__':
    import argparse
    from itertools import chain
    parser = argparse.ArgumentParser('python transformer.py', description='Wrapper over Pdf2HtmlEX to better handle forms')

    parser.add_argument('pdf', help="The PDF file to transform")
    parser.add_argument('output', help="The HTML file to output to. If not provided, will default to the same name and location as the source PDF.", nargs='?')
    parser.add_argument('--pdf2html', help='Override the path used to call Pdf2HmlEX', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pdf2htmlex.appimage'))
    parser.add_argument('--no-scripts', help='Disable javascript in the output file', action='store_true')
    parser.add_argument('--no-ui', help='Disable UI elements like the sidebar and loading indicator', action='store_true')
    parser.add_argument('--do-form', help='Turn form fields into an actual HTML form', action='store_true')

    # passthrough args
    parser.add_argument('--first-page', '-f', type=lambda val: ('-f', val), dest='options', action='append')
    parser.add_argument('--last-page', '-l', type=lambda val: ('-l', val), dest='options', action='append')
    parser.add_argument('--zoom', type=lambda val: ('--zoom', val), dest='options', action='append')
    parser.add_argument('--fit-width', type=lambda val: ('--fit-width', val), dest='options', action='append')
    parser.add_argument('--fit-height', type=lambda val: ('--fit-height', val), dest='options', action='append')
    parser.add_argument('--bg-format', type=lambda val: ('--bg-format', val), dest='options', action='append')

    args = parser.parse_args()
    main(
        args.pdf, 
        args.output or f"{args.pdf}.html", 
        pdf2html=args.pdf2html, 
        pdf2html_options = list(chain(*(args.options or []))),
        no_scripts=args.no_scripts,
        no_ui=args.no_ui,
        do_form=args.do_form,
    )