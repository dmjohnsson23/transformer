from __future__ import annotations
from collections import defaultdict
from bs4 import BeautifulSoup
from pypdf import PdfReader
from pypdf.constants import FieldDictionaryAttributes, AnnotationDictionaryAttributes
from pypdf.generic import RectangleObject, Field
from .field_renderer import FieldRenderer
from ..forms.utils import get_fields_annotations_by_page

# See https://pdfminersix.readthedocs.io/en/latest/howto/acro_forms.html
def process_form(pdf_filename: str, soup: BeautifulSoup, zoom: int = 1, rename_fields = {}, field_labels = {}):
    with open(pdf_filename, 'rb') as pdf_file:
        parser = PdfReader(pdf_file)
        fields = parser.get_fields()
        if not fields:
            return {} # No form found, so nothing to do
        html_form = soup.find(id='page-container').wrap(soup.new_tag('form'))
        html_pages = html_form.find_all(class_='pf')
        rendered_fields = {}
        i = 0
        for page_no, pdf_page in enumerate(parser.pages):
            if pdf_page.annotations is None: continue
            html_page = html_pages[page_no]
            fieldset = soup.new_tag('div', attrs={'class':'form-inputs'})
            for annot in pdf_page.annotations:
                annot = annot.get_object()
                # All field widgets are annotations with type "widget"
                # See 12.5.6.19 at https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf
                if annot[AnnotationDictionaryAttributes.Subtype] != "/Widget":
                    continue
                # Actual field data *may* use the same dictionary as the widget, but may not. 
                # E.g. for radio groups the parent is the field, and the children are the widgets
                # Docs seem to indicate that /Parent should be absent when the annotation is the field,
                # at least as I read it, but in practice this does not seem to actually be the case.
                # So instead, I'm guessing based on the FT (field type, see 12.7.3.1)
                if FieldDictionaryAttributes.FT in annot:
                    field = Field(annot)
                elif FieldDictionaryAttributes.Parent in annot and FieldDictionaryAttributes.FT in annot[FieldDictionaryAttributes.Parent].get_object():
                    field = Field(annot[FieldDictionaryAttributes.Parent].get_object())
                else:
                    # I don't think this should ever happen, but if so I guess skip this widget
                    continue
                i += 1
                if field.field_type == "/Btn":
                    if (field.flags or 0) & FieldDictionaryAttributes.FfBits.Radio:
                        input = FieldRenderer.make('radio')
                    elif (field.flags or 0) & FieldDictionaryAttributes.FfBits.Pushbutton:
                        input = FieldRenderer.make('button')
                    else: # field is checkbox
                        input = FieldRenderer.make('checkbox')
                elif field.field_type == "/Tx":
                    if (field.flags or 0) & FieldDictionaryAttributes.FfBits.Multiline:
                        input = FieldRenderer.make('textarea')
                    elif (field.flags or 0) & FieldDictionaryAttributes.FfBits.Password:
                        input = FieldRenderer.make('password')
                    elif (field.flags or 0) & FieldDictionaryAttributes.FfBits.FileSelect:
                        input = FieldRenderer.make('file')
                    else:
                        input = FieldRenderer.make('text')
                elif field.field_type ==  "/Ch":
                    input = FieldRenderer.make('select')
                elif field.field_type == "/Sig":
                    input = FieldRenderer.make('signature')
                else:
                    continue
                name = field.name
                if name in rename_fields:
                    input.name = rename_fields[name]
                else:
                    input.name = field.mapping_name or name
                if name in field_labels:
                    input.label = field_labels[name]
                else:
                    input.label = field.alternate_name
                rect = RectangleObject(annot[AnnotationDictionaryAttributes.Rect])
                rect = rect.scale(zoom, zoom)
                # The PDF format considers the bottom-left corner to be the origin, so we use that to place
                input.style = {
                    'position': 'absolute',
                    'left': f'{rect.left}px',
                    'bottom': f'{rect.bottom}px',
                    'width': f'{rect.width}px',
                    'height': f'{rect.height}px',
                }
                placeholder_name = f'field{i}'
                rendered_fields[placeholder_name] = input.render()
                fieldset.append(f'\n${{{placeholder_name}}}\n')
            html_page.append(fieldset)
    style = soup.new_tag('style')
    style.append("""
        .form-inputs{
            bottom: -3px;
            left: -4px;
            position: absolute;
        }
        .form-inputs input,
        .form-inputs textarea,
        .form-inputs select{
            border: none;
            background: rgba(0,0,0,.05);
            resize: none;
        }
    """)
    soup.find('head').append(style)
    return rendered_fields