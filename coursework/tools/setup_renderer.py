"""Restore local QA dependencies (not needed to open the delivered DOCX).
Run: python coursework/tools/setup_renderer.py
Downloads only from registry.npmjs.org via npm; does not alter the thesis template.
"""
from pathlib import Path
import os
import shutil
import subprocess

ROOT = Path(os.environ.get('COURSE_TOOLS_CACHE', str(Path.home() / '.cache/course-tools')))
RENDERER = ROOT / 'renderer'
PACKAGE = RENDERER / 'node_modules/@matbee/libreoffice-converter'
FONTS = ROOT / 'fonts'


def install():
    RENDERER.mkdir(parents=True, exist_ok=True)
    subprocess.run(['npm', 'install', '--prefix', str(RENDERER), '--ignore-scripts',
                    '--no-audit', '--no-fund', '@matbee/libreoffice-converter@2.7.2',
                    '@expo-google-fonts/tinos'], check=True, timeout=600)
    from fontTools.ttLib import TTFont
    FONTS.mkdir(parents=True, exist_ok=True)
    source = RENDERER / 'node_modules/@expo-google-fonts/tinos'
    for name in ('400Regular', '400Regular_Italic', '700Bold', '700Bold_Italic'):
        font = TTFont(source / f'Tinos_{name}.ttf')
        bold = '700' in name
        italic = 'Italic' in name
        style = ('Bold ' if bold else '') + ('Italic' if italic else 'Regular')
        names = {1: 'Times New Roman', 2: style, 4: 'Times New Roman ' + style,
                 6: 'TimesNewRoman-' + style.replace(' ', ''), 16: 'Times New Roman', 17: style}
        for record in font['name'].names:
            if record.nameID in names:
                record.string = names[record.nameID]
        font.save(FONTS / f'Tinos_{name}.ttf')
    # Retain the upstream font licence next to the derived, metrically compatible fonts.
    shutil.copyfile(source / 'LICENSE_FONT', FONTS / 'LICENSE_FONT.txt')
    patch_worker()


def patch_worker():
    path = PACKAGE / 'dist/subprocess.worker.cjs'
    text = path.read_text()
    if 'refreshDocumentFields()' in text:
        print('Field-refresh hook already installed.')
        return
    anchor = '      getDocPtr() {\n        return this.docPtr;\n      }'
    if text.count(anchor) != 1:
        raise RuntimeError('Unexpected worker source; refusing a speculative patch.')
    hook = '''
      refreshDocumentFields() {
        this.lok.postUnoCommand(this.docPtr, ".uno:UpdateAllIndexes", "{}", true);
        this.lok.flushCallbacks(this.docPtr);
        this.lok.postUnoCommand(this.docPtr, ".uno:UpdateFields", "{}", true);
        this.lok.flushCallbacks(this.docPtr);
        this.lok.postUnoCommand(this.docPtr, ".uno:UpdateAllIndexes", "{}", true);
        this.lok.flushCallbacks(this.docPtr);
        return this.createResult({ updated: true });
      }
'''
    path.write_text(text.replace(anchor, anchor + hook))
    print('Installed deterministic TOC/page-field refresh hook.')


if __name__ == '__main__':
    install()
