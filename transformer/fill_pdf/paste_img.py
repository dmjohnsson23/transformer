from PIL import Image
from io import BytesIO
from pypdf import PageObject, PdfReader, Transformation

def paste_img(img, pdf_page:PageObject, x:int, y:int, width:int, height:int):
    img = Image.open(img)
    # Scale the image and add margins to perfectly match the destination
    img_width, img_height = img.size
    image_ratio = img_height / img_width
    target_ratio = height / width
    scale_factor = 1
    margin_x = 0
    margin_y = 0
    if image_ratio > target_ratio: 
        # Taller ratio than target
        if img_height > height:
            # Scale down, and center horizontally
            scale_factor = height / img_height
            margin_x = int((width - (img_width * scale_factor)) / 2)
        else:
            # Center without scaling
            margin_x = int((width - img_width) / 2)
            margin_y = int((height - img_height) / 2)
    elif image_ratio < target_ratio:
        # Wider ratio than target
        if img_width > width:
            # Scale down, and center vertically 
            scale_factor = width / img_width
            margin_y = int((height - (img_height * scale_factor)) / 2)
        else:
            # Center without scaling
            margin_x = int((width - img_width) / 2)
            margin_y = int((height - img_height) / 2)
    else:
        # Same ratio as target
        if img_height > height:
            # Scale down
            scale_factor = height / img_height
        else:
            # Center without scaling
            margin_x = int((width - img_width) / 2)
            margin_y = int((height - img_height) / 2)
    # Convert the image to a PDF
    img_as_pdf = BytesIO()
    img.save(img_as_pdf, 'pdf')
    del img
    stamp_pdf = PdfReader(img_as_pdf)
    # Overlay the PDF version of the image over the page
    pdf_page.merge_transformed_page(
        stamp_pdf.pages[0],
        Transformation().scale(scale_factor, scale_factor).translate(x+margin_x, y+margin_y)
    )