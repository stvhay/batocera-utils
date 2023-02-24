#!/usr/bin/env python3

# Indexer v.2
# Author: Josh Brunty (josh dot brunty at marshall dot edu)
# DESCRIPTION: This script generates an .html index of files within a directory (recursive is OFF by default). Start from current dir or from folder passed as first positional argument. Optionally filter by file types with --filter "*.py". 
# Modified by Steve Hay to use Jinja templates

# -handle symlinked files and folders: displayed with custom icons
# By default only the current folder is processed.
# Use -r or --recursive to process nested folders.

from __future__ import annotations
from typing import Sequence

import argparse
import dataclasses
import datetime
import io
import jinja2
import os
import sys
import pathlib
import re
import urllib.parse



class JinjaEnv:
    templateLoader = jinja2.FileSystemLoader(searchpath=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates'))
    templateEnv = jinja2.Environment(loader=templateLoader, autoescape=jinja2.select_autoescape())

    @classmethod
    def get_template(cls, filename='index.html.jinja2'):
        return JinjaEnv.templateEnv.get_template(filename)


@dataclasses.dataclass
class JinjaEntry:
    path: str
    entrytype: str
    name: str
    size_bytes: int
    size_pretty: str
    last_modified_iso: str
    last_modified_human_readable: str


def pretty_size(bytes: int) -> str:
    """Human-readable file sizes.
    modified from https://pypi.python.org/pypi/hurry.filesize/
    """
    for factor, suffix in pretty_size.UNITS_MAPPING:
        if bytes >= factor:
            break
    raw_amount = bytes / factor
    if factor == 1:
        amount = f'{int(raw_amount):d}'
    elif raw_amount < 10:
        amount = f'{raw_amount:.2f}'
    elif raw_amount < 100:
        amount = f'{raw_amount:.1f}'
    else:
        amount = f'{int(raw_amount):d}'
    return f'{amount} {suffix}'

pretty_size.UNITS_MAPPING = [
    (1024 ** 5, 'P'),
    (1024 ** 4, 'T'),
    (1024 ** 3, 'G'),
    (1024 ** 2, 'M'),
    (1024 ** 1, 'K'),
    (1024 ** 0, 'B'),
]


def entries2jinja(opts, entries: Sequence[pathlib.PurePath]) -> Iterable[JinjaEntry]:
    for entry in entries:
        # don't include index.html in the file listing
        if entry.name.lower() == opts.output_file.lower():
            continue

        # From Python 3.6, os.access() accepts path-like objects
        if (not entry.is_symlink()) and not os.access(str(entry), os.W_OK):
            print(f"*** WARNING *** entry {entry.absolute()} is not writable! SKIPPING!")
            continue

        if opts.verbose:
            print(f'{entry.absolute()}')

        size_bytes = -1  ## is a folder
        size_pretty = '&mdash;'
        last_modified = '-'
        last_modified_human_readable = '-'
        last_modified_iso = ''
        try:
            if entry.is_file():
                entry_path = str(entry.name)
                size_bytes = entry.stat().st_size
                size_pretty = pretty_size(size_bytes)
            if entry.is_dir():
                entry_path = os.path.join(str(entry.name), opts.output_file.lower())

            if entry.is_dir() or entry.is_file():
                last_modified = datetime.datetime.fromtimestamp(entry.stat().st_mtime).replace(microsecond=0)
                last_modified_iso = last_modified.isoformat()
                last_modified_human_readable = last_modified.strftime("%c")

        except Exception as e:
            print('ERROR accessing file name:', e, entry)
            continue


        if entry.is_dir() and not entry.is_symlink():
            entry_type = 'folder'
            # if os.name not in ('nt',):
            #     # append trailing slash to dirs, unless it's windows
            #     entry_path = os.path.join(entry.name, '')

        elif entry.is_dir() and entry.is_symlink():
            entry_type = 'folder-shortcut'
            print('dir-symlink', entry.absolute())

        elif entry.is_file() and entry.is_symlink():
            entry_type = 'file-shortcut'
            print('file-symlink', entry.absolute())

        else:
            entry_type = 'file'

        yield(JinjaEntry(
            path=entry_path,
            entrytype=entry_type,
            name=entry.name,
            size_bytes=size_bytes,
            size_pretty=size_pretty,
            last_modified_iso=last_modified_iso,
            last_modified_human_readable=last_modified_human_readable))


def render(opts, sorted_entries: Sequence[pathlib.PurePath], top_dir: pathlib.PurePath) -> str:
    return JinjaEnv.get_template().render(
        entries=entries2jinja(opts, sorted_entries),
        path_top_dir=top_dir,
        index_name=opts.output_file.lower())


# def process_dir(opts, top_dir: Union[pathlib.PurePath, None]=None, level: int=0):
def process_dir(opts, top_dir: pathlib.PurePath|None=None, level=0) -> None:
    def hidden(x):
        return not opts.all and re.match(r'^\.', str(x))

    if not top_dir: 
        top_dir = pathlib.Path(opts.top_dir)
    
    if hidden(top_dir):
        return

    glob_patt = opts.filter or '[!.]*'
    index_file = None
    index_path = pathlib.Path(top_dir, opts.output_file)
    if level==0: 
        print('Traversing directories:')
        print(f'{top_dir.absolute()}')
    else:
        print(f'{level*"  "}∟ {top_dir.stem}')

    # sort dirs first
    unsorted_entries = filter(lambda x: not hidden(x), top_dir.glob(glob_patt))
    sorted_entries = sorted(unsorted_entries, key=lambda p: (p.is_file(), p.name))

    # render
    html = render(opts, sorted_entries, top_dir)
    
    # write to file
    try:
        num_bytes = -1
        with open(index_path, 'w', encoding='utf-8') as index_file:
            num_bytes = index_file.write(html) # atomic
            if num_bytes != len(html):
                raise Exception('Incomplete Write')
    except Exception as e:
        if num_bytes != -1 and num_bytes != len(html):
            e.add_note(f'Only {num_bytes} of {len(data)} was written to {index_file}.')
        raise e

    # Depth first search if recursive
    if opts.recursive:
        entry: pathlib.Path
        for entry in sorted_entries:
            if entry.is_dir():
                process_dir(opts, entry, level+1)


def main(argv) -> None:
    parser = argparse.ArgumentParser(description='This script generates an .html index of files within a directory (recursive is OFF by default). Start from current dir or from folder passed as first positional argument. Optionally filter by file types with --filter "*.py"')

    parser.add_argument('top_dir',
                        nargs='?',
                        action='store',
                        help='top folder from which to start generating indexes, '
                             'use current folder if not specified',
                        default=os.getcwd())
    parser.add_argument('--all', '-a',
                        action='store_true',
                        help="do not ignore entries starting with .",
                        required=False)

    parser.add_argument('--filter', '-f',
                        help='only include files matching glob',
                        required=False)

    parser.add_argument('--output-file', '-o',
                        metavar='filename',
                        default='index.html',
                        help='Custom output file, by default index.html')

    parser.add_argument('--recursive', '-r',
                        action='store_true',
                        help="recursively process nested dirs (FALSE by default)",
                        required=False)

    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='***WARNING: can take longer time with complex file tree structures on slow terminals***'
                             ' verbosely list every processed file',
                        required=False)

    config = parser.parse_args(argv[1:])
    process_dir(config)


if __name__ == "__main__":
    main(sys.argv)
