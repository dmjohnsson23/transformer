from __future__ import annotations
import os, sys
from subprocess import run
from bs4 import BeautifulSoup
from io import IOBase, TextIOBase
import tempfile
from shutil import copyfileobj
from string import Template

def transform(input_path, output_path, *, pdf2html, pdf2html_options=[], no_scripts=False, no_ui=False, do_form=False, zoom=1):
    if not os.path.isfile(pdf2html):
        print("Cannot run pdf2html; path is not valid", file=sys.stderr)
        exit(1)
    try:
        temps = []
        if isinstance(input_path, TextIOBase):
            temp_in = tempfile.NamedTemporaryFile('w')
            copyfileobj(input_path, temp_in)
            input_path = temp_in.name
            temp_in.close()
            temps.append(input_path)
        elif isinstance(input_path, IOBase):
            temp_in = tempfile.NamedTemporaryFile('wb')
            copyfileobj(input_path, temp_in)
            input_path = temp_in.name
            temp_in.close()
            temps.append(input_path)
        output_file = None
        if isinstance(output_path, IOBase):
            output_file = output_path
            output_path = tempfile.mktemp()
            temps.append(output_path)
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
            placeholder_replacements = {}

            if no_scripts:
                for script in soup.find_all('script'):
                    script.decompose()

            if no_ui:
                soup.find(id='sidebar').decompose()
                for el in soup.find_all(class_='loading-indicator'):
                    el.decompose()
            
            if do_form:
                from .process_form import process_form
                placeholder_replacements.update(process_form(input_path, soup, zoom))
            
            file.seek(0)
            print(placeholder_replacements)
            file.write(Template(str(soup)).safe_substitute(placeholder_replacements))
            file.truncate()
            if output_file is not None:
                file.seek(0)
                copyfileobj(file, output_file)
    finally:
        for file in temps:
            os.remove(file)