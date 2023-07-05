from pypdf import PdfReader, PdfWriter, PageRange
from pypdf.generic import RectangleObject, Field
from pypdf.constants import AnnotationDictionaryAttributes, FieldDictionaryAttributes
import warnings
from .paste_img import paste_img
from io import IOBase, BytesIO

def fill(template_pdf, output_pdf, data, *, output_pages=None, rename_fields={}):
    real_names = {v:k for k,v in rename_fields.items()}
    with template_pdf if isinstance(template_pdf, IOBase) else open(template_pdf, 'rb') as pdf_file:
        reader = PdfReader(pdf_file)
        writer = PdfWriter()
        if output_pages is None:
            output_pages = PageRange(':')
        elif not isinstance(output_pages, PageRange):
            output_pages = PageRange(output_pages)
        writer.append(reader, pages=output_pages)
    # Split and interpret incoming data based on associated field type
    fields = reader.get_fields()
    print(list(fields.keys()))
    fillable = {}
    imgs_to_paste = {}
    for name, value in data.items():
        dealiased_name = real_names.get(name, name)
        field = fields.get(dealiased_name)
        if not field:
            warnings.warn(f"Data field '{name}' not found in template PDF or alias map, skipping")
            continue
        if field.field_type == "/Sig":
            imgs_to_paste[dealiased_name] = value
        else:
            fillable[dealiased_name] = value
    # Populate the data into the PDF
    for page in writer.pages:
        writer.update_page_form_field_values(page, fillable)
        if page.annotations is None: continue
        for annot in page.annotations:
            annot = annot.get_object()
            if annot[AnnotationDictionaryAttributes.Subtype] == "/Widget" and annot.get(FieldDictionaryAttributes.FT) == "/Sig":
                field = Field(annot)
                rect = RectangleObject(annot[AnnotationDictionaryAttributes.Rect])
                print(rect)
                path = imgs_to_paste.get(field.name)
                if not path: continue
                if path.startswith('data:'):
                    # embedded base64
                    from base64 import b64decode
                    _, path = path.split(',', 2)
                    path = BytesIO(b64decode(path))
                paste_img(path, page, rect.left, rect.bottom, rect.width, rect.height)
    # Save output PDF
    if isinstance(output_pdf, IOBase):
        writer.write(output_pdf)
    else:
        with open(output_pdf, "wb") as output:
            writer.write(output)
        
        
