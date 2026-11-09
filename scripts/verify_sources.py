#!/usr/bin/env python3
"""Проверка DOI через Crossref."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from diploma_builder.search import verify_doi
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("doi", nargs="+", help="DOI для проверки")
args = parser.parse_args()
for doi in args.doi:
    ok = verify_doi(doi)
    print(f"{doi}: {'✓ VALID' if ok else '✗ INVALID'}")

