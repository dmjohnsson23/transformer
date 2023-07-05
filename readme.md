# PDF Transformer

**This is a prototype/proof-of-concept only. It sort of works, but contains approximately 509 bugs. Use at your own risk.**

Tool used to 1: Convert a PDF into an HTML form, and 2: Fill that PDF with captured data. Works with signatures (pasted images only, not cryptographic signatures).

## Installation

```shell
pip3 install beautifulsoup4 lxml pypdf pillow
git clone https://github.com/dmjohnsson23/transformer.git
cd transformer
wget https://github.com/pdf2htmlEX/pdf2htmlEX/releases/download/v0.18.8.rc1/pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-bionic-x86_64.AppImage -O pdf2htmlex.appimage
```

## Make HTML

Convert a PDF into a usable HTML form.

Uses [Pdf2HtmlEX](https://pdf2htmlex.github.io/pdf2htmlEX/) to build the basic HTML structure, then uses [pypdf](https://github.com/py-pdf/pypdf/) to extract form fields.


Resource to use for cross-checking results: https://www.pdfescape.com/online-pdf-editor

### Command-Line Usage

```shell
python -m transformer make-html test/VBA-21-526EZ-ARE.pdf test/VBA-21-526EZ-ARE.pdf.html --first-page 9 --bg-format svg --do-form --zoom 2
```

### Python Usage

```python
from transformer.make_html import transform
transform(input_path, output_path)
```

## Fill PDF

Populate a PDF with data

### Command-Line Usage

```shell
python3 -m transformer fill-pdf 'test/sample.pdf' 'test/sample-filled.pdf' --data-json '{"Given Name Text Box": "John J.", "Family Name Text Box":"Johnson", "signature_1":"sized_sig.png"}'
```

### Python Usage

```python
from transformer.fill_pdf import fill
fill(template_pdf_path, output_pdf_path, data)