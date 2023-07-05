from __future__ import annotations


def main():
    import os, sys
    import argparse
    from itertools import chain
    parser = argparse.ArgumentParser('python transformer.py', description='Tool for converting between PDF and HTML forms.')
    subparser = parser.add_subparsers()

    ###### make-html ######
    make_html_parser = subparser.add_parser('make-html', description='Wrapper around Pdf2HtmlEX to better handle forms')

    make_html_parser.add_argument('pdf', help="The PDF file to transform, otherwise use stdin.", nargs='?')
    make_html_parser.add_argument('output', help="The HTML file to output to. If not provided, will default to the same name and location as the source PDF, or to stdout if that is also not provided.", nargs='?')
    make_html_parser.add_argument('--pdf2html', help='Override the path used to call Pdf2HmlEX', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pdf2htmlex.appimage'))
    make_html_parser.add_argument('--no-scripts', help='Disable javascript in the output file', action='store_true')
    make_html_parser.add_argument('--no-ui', help='Disable UI elements like the sidebar and loading indicator', action='store_true')
    make_html_parser.add_argument('--do-form', help='Turn form fields into an actual HTML form', action='store_true')

    # passthrough args
    make_html_parser.add_argument('--first-page', '-f', type=lambda val: ('-f', val), dest='options', action='append')
    make_html_parser.add_argument('--last-page', '-l', type=lambda val: ('-l', val), dest='options', action='append')
    make_html_parser.add_argument('--bg-format', type=lambda val: ('--bg-format', val), dest='options', action='append')

    # indirect passthrough
    zoom_group = make_html_parser.add_mutually_exclusive_group()
    zoom_group.add_argument('--zoom')
    zoom_group.add_argument('--fit-width')
    zoom_group.add_argument('--fit-height')

    def do_make_html(args):
        from .make_html import transform
        indirect_options = []
        for key in ['zoom', 'fit-width', 'fit-height']:
            val = getattr(args, key.replace('-', '_'))
            if val is not None:
                indirect_options.append((f"--{key}", val))
        pdf = sys.stdin.buffer if args.pdf is None else args.pdf
        output = sys.stdout if args.output is None and args.pdf is None else f"{args.pdf}.html" if args.output is None else args.output
        transform(
            pdf, 
            output, 
            pdf2html=args.pdf2html, 
            pdf2html_options = list(chain(*(args.options or []), *indirect_options)),
            no_scripts=args.no_scripts,
            no_ui=args.no_ui,
            do_form=args.do_form,
            zoom=int(args.zoom) # todo calculate zoom from fit-width or fit-height too (fit_width / actual_width, fit_height / actual_height)
        )
    make_html_parser.set_defaults(func=do_make_html)

    ###### fill=pdf ######
    fill_pdf_parser = subparser.add_parser('fill-pdf', description='Fill form data into the PDF, including pasting images for signature fields.')
    fill_pdf_parser.add_argument('pdf', help="The template PDF file to fill, or stdin if not provided.", nargs='?')
    fill_pdf_parser.add_argument('output', help="The PDF file to output to. If not provided, will output to stdout.", nargs='?')

    data_group = fill_pdf_parser.add_mutually_exclusive_group(required=True)
    data_group.add_argument('--data-json-file', help="The data file to fill into the PDF, in JSON format.")
    data_group.add_argument('--data-json-stdin', help="Pull data in JSON format from stdin. (Obviously, the pdf cannot be coming from stdin in this case)", action='store_true')
    data_group.add_argument('--data-json', help="The data to fill, as a JSON string")
    data_group.add_argument('--data', help="The data to fill, as key-value pairs", nargs=2, metavar=('key', 'value'), action='append')
    
    def do_fill_form(args):
        from .fill_pdf import fill
        in_file = sys.stdin.buffer if args.pdf is None else args.pdf
        out_file = sys.stdout.buffer if args.output is None else args.output
        if (args.data):
            data = dict(args.data)
        elif args.data_json:
            from json import loads
            data = loads(args.data_json)
        elif args.data_json_stdin:
            if args.pdf is None:
                raise RuntimeError('PDF and Data cannot both come from stdin')
            from json import load
            data = load(sys.stdin)
        elif args.data_json_file:
            from json import load
            with open(args.data_json_file, 'r') as file:
                data = load(file)
        else:
            raise RuntimeError('No data source supplied')
        fill(in_file, out_file, data)
    fill_pdf_parser.set_defaults(func=do_fill_form)

    ###### end ######

    args = parser.parse_args()
    args.func(args)