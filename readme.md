# PDF Transformer

**This is a prototype/proof-of-concept only. It's not *actually* usable right now.**

Convert a PDF into a usable HTML form.

The application uses [Pdf2HtmlEX](https://pdf2htmlex.github.io/pdf2htmlEX/) to build the basic HTML structure, then uses [pdfminer.six](https://github.com/pdfminer/pdfminer.six) to extract form fields.

