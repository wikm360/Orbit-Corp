const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const { File } = require('node:buffer');

// Runs the real TypeScript modules under src/, with only the HTTP boundary replaced.
function load(relativeToSrc, mocks = {}) {
  const filename = path.resolve(__dirname, '../src', relativeToSrc);
  const code = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const compiled = { exports: {} };
  const requireModule = (id) => {
    if (id in mocks) return mocks[id];
    if (id.startsWith('@/')) return load(`${id.slice(2)}.ts`, mocks);
    if (id.startsWith('.')) return load(path.relative(path.resolve(__dirname, '../src'), path.resolve(path.dirname(filename), `${id}.ts`)), mocks);
    return require(id);
  };
  vm.runInThisContext(`(function(require,module,exports){${code}\n})`, { filename })(requireModule, compiled, compiled.exports);
  return compiled.exports;
}

const fm = load('features/documents/lib/fileManager.ts');
const { filterUploadFiles, batchFormData, planBatches, uploadFileBatches, summarizeBatch } = load('features/documents/lib/batchUpload.ts');

test('selection keys round-trip into the API selection and keep documents and folders apart', () => {
  const keys = [fm.docKey('a'), fm.folderKey('f1'), fm.docKey('b')];
  assert.deepEqual(fm.selectionFromKeys(keys), { document_ids: ['a', 'b'], folder_ids: ['f1'] });
  assert.equal(fm.selectionSize(fm.selectionFromKeys(keys)), 3);
});

test('folder status summary lists only present statuses, in a fixed order, with Persian digits', () => {
  assert.equal(fm.summarizeCounts({ processing: 7, ready: 40, failed: 1 }), '۴۰ آماده · ۷ در حال پردازش · ۱ ناموفق');
  assert.equal(fm.summarizeCounts({}), '');
  assert.equal(fm.countTotal({ ready: 2, unsupported: 3, cancelled: 1 }), 6);
});

test('polling is only needed while something processes or an archive extracts', () => {
  const idle = { folders: [{ status_counts: { ready: 3 } }], documents: [{ status: 'ready' }, { status: 'failed' }], archives: [{ status: 'done' }] };
  assert.equal(fm.hasActiveWork(idle), false);
  assert.equal(fm.hasActiveWork(null), false);
  assert.equal(fm.hasActiveWork({ ...idle, documents: [{ status: 'processing' }] }), true);
  assert.equal(fm.hasActiveWork({ ...idle, folders: [{ status_counts: { processing: 1 } }] }), true);
  assert.equal(fm.hasActiveWork({ ...idle, archives: [{ status: 'extracting' }] }), true);
});

test('dragging a selected row carries the whole selection; an unselected row only itself', () => {
  const selected = new Set([fm.docKey('a'), fm.folderKey('f1')]);
  assert.deepEqual(fm.dragSelection(selected, fm.docKey('a')), { document_ids: ['a'], folder_ids: ['f1'] });
  assert.deepEqual(fm.dragSelection(selected, fm.docKey('z')), { document_ids: ['z'], folder_ids: [] });
});

test('a folder cannot be dropped on itself; the root and other folders are fine', () => {
  const dragged = { document_ids: [], folder_ids: ['f1'] };
  assert.equal(fm.canDropOn(dragged, 'f1'), false);
  assert.equal(fm.canDropOn(dragged, 'f2'), true);
  assert.equal(fm.canDropOn(dragged, null), true);
});

test('project uploads keep unsupported types and archives but skip junk, empty and oversized files', () => {
  const file = (name, size = 1, rel = '') => ({ name, size, webkitRelativePath: rel });
  const mb = 1024 * 1024;
  const result = filterUploadFiles([
    file('plan.dwg'), file('pack.zip', 400 * mb), file('big.pdf', 201 * mb), file('Thumbs.db'), file('font.shx'),
    file('~$draft.docx'), file('empty.txt', 0), file('ok.xls'), file('huge.zip', 501 * mb), file('._x.txt'),
  ], { projectFiles: true });
  assert.deepEqual(result.eligible.map((f) => f.name), ['plan.dwg', 'pack.zip', 'ok.xls']);
  assert.equal(result.skipped.length, 7);
  assert.match(result.skipped.find((s) => s.filename === 'big.pdf').error, /۲۰۰|200/);
  // chat/conversation uploads keep the strict allow-list
  assert.equal(filterUploadFiles([file('plan.dwg')]).eligible.length, 0);
});

test('folder_id is sent as a form field before the files, only when a folder is chosen', () => {
  const files = [new File(['x'], 'a.txt')];
  assert.deepEqual([...batchFormData(files, 'f1').keys()], ['folder_id', 'files']);
  assert.equal(batchFormData(files, 'f1').get('folder_id'), 'f1');
  assert.deepEqual([...batchFormData(files).keys()], ['files']);
  assert.deepEqual([...batchFormData(files, null).keys()], ['files']);
});

test('file manager API calls hit the project endpoints with the documented bodies', async () => {
  const calls = [];
  const { documentsApi } = load('features/documents/api/documentsApi.ts', {
    '@/shared/lib/apiClient': { apiRequest: async (url, options = {}) => { calls.push({ url, ...options }); return {}; } },
  });
  const selection = { document_ids: ['d1'], folder_ids: ['f1'] };
  await documentsApi.listFiles('p1', null);
  await documentsApi.listFiles('p1', 'f 1');
  await documentsApi.searchFiles('p1', 'گزارش ۱');
  await documentsApi.createFolder('p1', 'New', null);
  await documentsApi.renameFolder('p1', 'f1', 'B');
  await documentsApi.renameDocument('p1', 'd1', 'x.pdf');
  await documentsApi.move('p1', selection, 'f2', 'fail');
  await documentsApi.copy('p1', selection, null, 'rename');
  await documentsApi.deleteItems('p1', selection);
  await documentsApi.retryItems('p1', selection);
  await documentsApi.cancelItems('p1', selection);
  await documentsApi.dismissArchive('p1', 'a1');
  await documentsApi.uploadBatch('p1', [new File(['x'], 'a.txt')], 'f9');
  assert.deepEqual(calls.map((c) => `${c.method ?? 'GET'} ${c.url}`), [
    'GET /projects/p1/files',
    'GET /projects/p1/files?folder_id=f%201',
    `GET /projects/p1/files/search?q=${encodeURIComponent('گزارش ۱')}`,
    'POST /projects/p1/folders',
    'PATCH /projects/p1/folders/f1',
    'PATCH /projects/p1/documents/d1',
    'POST /projects/p1/files/move',
    'POST /projects/p1/files/copy',
    'POST /projects/p1/files/delete',
    'POST /projects/p1/files/retry',
    'POST /projects/p1/files/cancel',
    'DELETE /projects/p1/archives/a1',
    'POST /projects/p1/documents/batch',
  ]);
  assert.deepEqual(calls[3].body, { name: 'New', parent_id: null });
  assert.deepEqual(calls[6].body, { ...selection, target_folder_id: 'f2', on_conflict: 'fail' });
  assert.deepEqual(calls[7].body, { ...selection, target_folder_id: null, on_conflict: 'rename' });
  assert.equal(calls[12].formData.get('folder_id'), 'f9');
});

test('requests are planned by file count and by bytes; a file bigger than the byte budget travels alone', () => {
  const mb = 1024 * 1024;
  const sized = (name, size) => { const f = new File(['x'], name); Object.defineProperty(f, 'size', { value: size }); return f; };
  const plan = planBatches([sized('a', 30 * mb), sized('b', 30 * mb), sized('c', 30 * mb), sized('huge', 150 * mb), sized('d', 1 * mb)]);
  assert.deepEqual(plan.map((batch) => batch.map((f) => f.name)), [['a', 'b'], ['c'], ['huge'], ['d']]);
  const many = planBatches(Array.from({ length: 45 }, (_, i) => sized(`${i}`, 1)));
  assert.deepEqual(many.map((batch) => batch.length), [20, 20, 5]);
  assert.deepEqual(planBatches([]), []);
});

test('overall upload progress counts finished requests fully and in-flight ones by their fraction, never reaching 100% early', async () => {
  const mb = 1024 * 1024;
  const sized = (name, size) => { const f = new File(['x'], name); Object.defineProperty(f, 'size', { value: size }); return f; };
  const files = [sized('a', 60 * mb), sized('b', 60 * mb)]; // two requests of 60MB (80MB budget)
  const seen = [];
  await uploadFileBatches(files, async (batch, onFraction) => {
    onFraction(0.5);
    onFraction(1);
    return summarizeBatch(batch.map((f) => ({ filename: f.name, status: 'accepted', document: null, error: null })));
  }, undefined, () => true, (progress) => seen.push(progress));
  assert.equal(seen[0].totalBytes, 120 * mb);
  assert.ok(seen.every((p) => p.loadedBytes <= p.totalBytes));
  assert.ok(seen.some((p) => p.loadedBytes > 0 && p.loadedBytes < p.totalBytes), 'partial progress is reported');
  assert.equal(seen.at(-1).loadedBytes, 120 * mb, 'complete once every request was answered');
  // a request that mid-way reports 100% is still capped below its size until the server answered
  let capped = true;
  await uploadFileBatches([sized('c', 10 * mb)], async (batch, onFraction) => {
    const before = seen.length;
    onFraction(1);
    capped = seen.slice(before).every((p) => p.loadedBytes < p.totalBytes);
    return summarizeBatch(batch.map((f) => ({ filename: f.name, status: 'accepted', document: null, error: null })));
  }, undefined, () => true, (progress) => seen.push(progress));
  assert.ok(capped);
});

test('a failed request is reported per file and still counts as sent so progress finishes', async () => {
  const mb = 1024 * 1024;
  const f = new File(['x'], 'a.txt'); Object.defineProperty(f, 'size', { value: 5 * mb });
  let last;
  const result = await uploadFileBatches([f], async () => { throw new TypeError('offline'); }, undefined, () => true, (p) => { last = p; });
  assert.equal(result.rejected, 1);
  assert.equal(last.loadedBytes, last.totalBytes);
});
