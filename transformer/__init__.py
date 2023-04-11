from __future__ import annotations
import os, sys
from subprocess import run
from bs4 import BeautifulSoup

def transform(input_path, output_path, *, pdf2html, pdf2html_options=[], no_scripts=False, no_ui=False, do_form=False, zoom=1):
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
            from .forms import process_form
            process_form(input_path, soup, zoom)
        
        file.seek(0)
        file.write(str(soup))
        file.truncate()


def main():
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
    transform(
        args.pdf, 
        args.output or f"{args.pdf}.html", 
        pdf2html=args.pdf2html, 
        pdf2html_options = list(chain(*(args.options or []), *indirect_options)),
        no_scripts=args.no_scripts,
        no_ui=args.no_ui,
        do_form=args.do_form,
        zoom=int(args.zoom) # todo calculate zoom from fit-width or fit-height too (fit_width / actual_width, fit_height / actual_height)
    )