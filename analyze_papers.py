
import argparse
import textwrap
import string
import json
import csv
import sys
import re
import os

from rapidfuzz import fuzz
from rapidfuzz import process

TXT_PATH = '.txt'
MATCH_THRESHOLD = 90.0


def sanitize(title):
    # to lowercase
    title = title.lower()
    # remove punctuation
    title = title.translate(str.maketrans('', '', string.punctuation))
    # remove linebreaks
    title = title.replace('\r', '').replace('\n', '')
    # remove numbers
    title = re.sub(r'\d+', '', title)
    # remove whitespace
    title = " ".join(re.findall(r'[a-z]+', title))
    return title


def read_titles(zotero_csv):
    titles = {}
    with open(zotero_csv, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for entry in reader:
            assert(entry['Publication Year'])
            assert(entry['Author'])

            first_author = entry['Author'].split(';')[0]
            first_author_lastname = first_author.split()[0]
            cite_id = sanitize(first_author_lastname) + entry['Publication Year']
            assert(cite_id not in titles)

            titles[cite_id] = entry
            titles[cite_id]['Sanitized Title'] = sanitize(entry['Title'])
            titles[cite_id]['CiteID'] = cite_id

    return titles


def match_citations(titles_dict):
    edges = []
    for cite_id in titles_dict:
        pdf_file = next(path for path in titles_dict[cite_id]['File Attachments'].split(';') if path.lower().endswith('.pdf'))
        txt_file = os.path.join(TXT_PATH, os.path.splitext(os.path.basename(pdf_file))[0] + '.txt')

        try:
            with open(txt_file, "r") as txt:
                lines = txt.readlines()
        except FileNotFoundError:
            from PyPDF2 import PdfReader

            reader = PdfReader(pdf_file)
            text = '\n'.join(page.extract_text() for page in reader.pages)

            os.makedirs(os.path.dirname(txt_file), exist_ok=True)
            with open(txt_file, "w") as txt:
                txt.write(text)
            lines = text.splitlines()

        try:
            pivot = next(n for (n, line) in reversed(list(enumerate(lines))) if 'references' in line.lower())
        except StopIteration:
            sys.stderr.write(cite_id + ': ' + pdf_file + ': ')
            raise
        references = ''.join(lines[pivot:])
        references = references.replace('\n', ' ')

        candidates = [c for c in titles_dict if c != cite_id and int(titles_dict[c]['Publication Year']) <= int(titles_dict[cite_id]['Publication Year'])]

        for cite_id2 in candidates:
            r = fuzz.partial_ratio(references.lower(), titles_dict[cite_id2]['Title'].lower())
            sys.stderr.write(f'+{cite_id} -> {cite_id2}: {r}\n')
            if r > MATCH_THRESHOLD:
                edges.append((cite_id, cite_id2, r))

    return edges


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=
                                     'Extract citations from zotero records')
    parser.add_argument('zotero_csv', type=str, help='the Zotero exported CSV file of papers')
    args = parser.parse_args()

    # First, just get the titles in the csv
    titles_dict = read_titles(args.zotero_csv)

    # Second, try to determine citations by matching text
    edges = match_citations(titles_dict)

    # sort articles by publication year
    years = {}
    for cite_id in titles_dict:
        if int(titles_dict[cite_id]['Publication Year']) not in years:
            years[int(titles_dict[cite_id]['Publication Year'])] = []
        years[int(titles_dict[cite_id]['Publication Year'])].append(cite_id)

    # Last, produce a graphviz formatted output
    print('digraph "Citations" {')

    #print('  splines = ortho')
    #print('  concentrate = true')
    #print('  margin = 1')

    print('  node [fontsize=24, shape = plaintext]')
    print('  edge [style=invis]')
    years_keys = sorted(years.keys(), reverse=True)
    for year1, year2 in zip(years_keys[:-1], years_keys[1:]):
        print(f'  {year1} -> {year2}')

    print('')

    print('  node [fontsize=20, shape = box]')
    print('  edge [style=""]')
    for cite_id in titles_dict:
        label = '\\n'.join(textwrap.wrap(titles_dict[cite_id]["Title"], width=28))
        pdf_file = next(path for path in titles_dict[cite_id]['File Attachments'].split(';') if path.lower().endswith('.pdf'))
        print(f'  "{cite_id}" [label="{label}", URL="{pdf_file}"]')

    print('')

    for year in years_keys:
        print(f'  {{ rank=same;  {year} {" ".join(years[year])} }}')

    print('')

    for (cite_id1, cite_id2, r) in edges:
        print(f'  "{cite_id2}" -> "{cite_id1}" /* r = {r} */')

    print('}')

