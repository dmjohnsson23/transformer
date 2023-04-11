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
from typing import Iterable, Any

def main(input_path, output_path, *, pdf2html, pdf2html_options=[], no_scripts=False, no_ui=False, do_form=False, zoom=1):
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
            _process_form(input_path, soup, zoom)
        
        file.seek(0)
        file.write(str(soup))
        file.truncate()

def _decode_pdf_value(value):
    if isinstance(value, (PSLiteral, PSKeyword)):
        value = value.name
    if isinstance(value, bytes):
        value = decode_text(value)
    return value


def process_form_to_trees(pdf_filename: str):
    from json import dumps
    with open(pdf_filename, 'rb') as pdf_file:
        parser = PDFParser(pdf_file)
        doc = PDFDocument(parser)
        res = resolve1(doc.catalog)
        if 'AcroForm' not in res:
            return # No form found, so nothing to do
        fields = resolve1(doc.catalog['AcroForm'])['Fields']  # may need further resolving
        return list(_iter_pdf_form_fields(fields))

# See https://pdfminersix.readthedocs.io/en/latest/howto/acro_forms.html
def _process_form(pdf_filename: str, soup: BeautifulSoup, zoom: int = 1):
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
    def name(self):
        return _decode_pdf_value(self.raw_data.get('T'))
    @property
    def alt_name(self):
        return _decode_pdf_value(self.raw_data.get('TU')) or self.name
    @property
    def map_name(self):
        return _decode_pdf_value(self.raw_data.get('TM')) or self.name

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
    @property
    def type(self):
        if 'FT' in self.raw_data:
            return FormFieldType(_decode_pdf_value(self.raw_data['FT']))
        # Type can be inherited from parent
        if self.parent is not None:
            return self.parent.type
        return None
    @property
    def values(self):
        if self._values is not None:
            return self._values
        if 'V' in self.raw_data:
            values = resolve1(self.raw_data.get('V'))
            if isinstance(values, list):
                values = [_decode_pdf_value(v) for v in values]
            else:
                values = _decode_pdf_value(values)
            self._values = values
            return self._values
        # Values can also be inherited from parent
        if self.parent is not None:
            return self.parent.values
        return None
    @property
    def default_values(self):
        if self._default_values is not None:
            return self._default_values
        if 'DV' in self.raw_data:
            values = resolve1(self.raw_data.get('DV'))
            if isinstance(values, list):
                values = [_decode_pdf_value(v) for v in values]
            else:
                values = _decode_pdf_value(values)
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
    def rect(self):
        if self._rect is not None:
            return self._rect
        if 'Rect' in self.raw_data:
            self._rect = Rect(*self.raw_data.get('Rect'))
            return self._rect
        return None
    @property
    def children(self):
        if self._children is not None:
            return self._children
        if 'Kids' in self.raw_data:
            self._children = tuple([FormField(resolve1(child), self) for child in self.raw_data['Kids']])
            return self._children
        return None

    #TODO MaxLen
    #TODO Mk (style dictionary)


Rect = namedtuple('Rect', 'x1,y1,x2,y2')

def _iter_pdf_form_fields(fields):
    for field in fields:
        if isinstance(field, FormField):
            field_obj = field
        else:
            field_obj = FormField(resolve1(field))
        if field_obj.children is not None:
            yield from _iter_pdf_form_fields(field_obj.children)
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
    parser.add_argument('--bg-format', type=lambda val: ('--bg-format', val), dest='options', action='append')

    # indirect passthrough
    zoom_group = parser.add_mutually_exclusive_group()
    zoom_group.add_argument('--zoom')
    zoom_group.add_argument('--fit-width')
    zoom_group.add_argument('--fit-height')

    args = parser.parse_args()
    indirect_options = []
    for key in ['zoom', 'fit-width', 'fit-height']:
        val = getattr(args, key.replace('-', '_'))
        if val is not None:
            indirect_options.append((f"--{key}", val))
    main(
        args.pdf, 
        args.output or f"{args.pdf}.html", 
        pdf2html=args.pdf2html, 
        pdf2html_options = list(chain(*(args.options or []), *indirect_options)),
        no_scripts=args.no_scripts,
        no_ui=args.no_ui,
        do_form=args.do_form,
        zoom=int(args.zoom) # todo calculate zoom from fit-width or fit-height too (fit_width / actual_width, fit_height / actual_height)
    )