# -*- coding: utf-8 -*-
"""
Render digest_print.html to PDF in the cloud sandbox (no Windows/Edge available).

Cloud replacement for the old local step:
  & msedge.exe --headless=new --print-to-pdf=...

Uses WeasyPrint (pure Python, no browser binary needed) instead. Installs
itself on first run if missing. Hebrew/RTL fidelity is generally good but has
not been verified against a real routine run yet - if pagination or RTL
rendering looks wrong on the first cloud run, that is the first thing to
revisit (see README.md "Known gaps").
"""
import argparse, subprocess, sys


def ensure_weasyprint():
    try:
        import weasyprint  # noqa
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "weasyprint"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    args = ap.parse_args()

    ensure_weasyprint()
    from weasyprint import HTML

    HTML(filename=args.src).write_pdf(args.dst)
    print("wrote %s" % args.dst)


if __name__ == "__main__":
    main()
