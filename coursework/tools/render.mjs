import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';

const cache = path.resolve(process.env.COURSE_TOOLS_CACHE || path.join(os.homedir(), '.cache/course-tools'));
const require = createRequire(path.join(cache, 'renderer/package.json'));
const { createSubprocessConverter } = require('@matbee/libreoffice-converter');
const fontDir = path.join(cache, 'fonts');
const fonts = fs.readdirSync(fontDir).filter(x => x.endsWith('.ttf')).map(filename => ({
  filename, data: fs.readFileSync(path.join(fontDir, filename))
}));
const input = path.resolve(process.argv[2]);
const output = path.resolve(process.argv[3]);
const refreshed = process.argv[4] ? path.resolve(process.argv[4]) : null;
if (!input || !output) throw new Error('Usage: render.mjs input.docx output.pdf [refreshed.docx]');
console.time('total');
const converter = await createSubprocessConverter({
  wasmPath: path.join(cache, 'renderer/node_modules/@matbee/libreoffice-converter/wasm'),
  fonts, includeSystemFonts: false, verbose: false
});
console.log('initialized');
let data = fs.readFileSync(input);
if (refreshed) {
  const session = await converter.openDocument(data, { inputFormat: 'docx' });
  console.log('opened', session.sessionId, session.pageCount);
  const result = await converter.editorOperation(session.sessionId, 'refreshDocumentFields', []);
  console.log('refresh', result);
  const structure = await converter.editorOperation(session.sessionId, 'getStructure', [{ maxResponseChars: 1000 }]);
  console.log('structure', structure);
  const saved = await converter.closeDocument(session.sessionId);
  if (!saved) throw new Error('Saving refreshed document failed');
  data = Buffer.from(saved);
  fs.writeFileSync(refreshed, data);
}
const result = await converter.convert(data, { outputFormat: 'pdf' });
fs.writeFileSync(output, result.data);
console.log('PDF', result.data.length, 'ms', result.duration);
console.timeEnd('total');
// Kill the specific forked worker before exiting; graceful WASM shutdown may otherwise hang.
converter.killWorker();
process.exit(0);
