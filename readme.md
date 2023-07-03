# PDF Transformer

**This is a prototype/proof-of-concept only. It's not *actually* usable right now.**

Convert a PDF into a usable HTML form.

The application uses [Pdf2HtmlEX](https://pdf2htmlex.github.io/pdf2htmlEX/) to build the basic HTML structure, then uses [pdfminer.six](https://github.com/pdfminer/pdfminer.six) to extract form fields.

Example usage:

```shell
pip3 install beautifulsoup4 lxml bitarray pypdf pillow
wget https://github.com/pdf2htmlEX/pdf2htmlEX/releases/download/v0.18.8.rc1/pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-bionic-x86_64.AppImage -O pdf2htmlex.appimage
python3 transformer.py make-html test/VBA-21-526EZ-ARE.pdf --first-page 9 --bg-format svg --do-form --zoom 2
```

Resource to use for cross-checking results: https://www.pdfescape.com/online-pdf-editor