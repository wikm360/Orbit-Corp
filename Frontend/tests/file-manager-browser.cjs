// Drives the project file manager in a real browser against an in-memory mock of the folder API.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const user = { id: 'u1', full_name: 'سارا احمدی', email: 'sara@example.test', role: 'user' };
const project = { id: 'p1', team_id: 't1', name: 'پروژهٔ آزمایشی' };
let membership = 'leader', counter = 0;
const folders = [], docs = [], archives = [], requests = [], errors = [];
const now = () => new Date().toISOString();
const addFolder = (name, parent_id = null) => { const f = { id: `f${++counter}`, parent_id, name, created_at: now() }; folders.push(f); return f; };
const addDoc = (filename, folder_id = null, status = 'processing') => { const d = { id: `d${++counter}`, filename, folder_id, status, content_type: 'text/plain', error_message: status === 'failed' ? 'Embedding failed' : null, uploaded_by: user.id, project_id: 'p1', conversation_id: null, created_at: now() }; docs.push(d); return d; };
const subtree = (id) => [id, ...folders.filter((f) => f.parent_id === id).flatMap((f) => subtree(f.id))];
const countsFor = (id) => { const ids = new Set(subtree(id)); const out = {}; docs.filter((d) => ids.has(d.folder_id)).forEach((d) => { out[d.status] = (out[d.status] ?? 0) + 1; }); return out; };
const crumbs = (id) => { const out = []; for (let f = folders.find((x) => x.id === id); f; f = folders.find((x) => x.id === f.parent_id)) out.unshift(f); return out; };

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  try {
    await context.addInitScript(({ user }) => {
      localStorage.setItem('auth_token', 'test-token');
      localStorage.setItem('auth-store', JSON.stringify({ state: { token: 'test-token', user }, version: 0 }));
    }, { user });
    const page = await context.newPage();
    page.on('pageerror', (error) => errors.push(error.message));
    await page.route('**/api/v1/**', async (route) => {
      const req = route.request(), url = new URL(req.url()), endpoint = url.pathname.replace('/api/v1', ''), method = req.method();
      const json = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
      const body = () => req.postDataJSON();
      requests.push({ endpoint, method, body: ['POST', 'PATCH'].includes(method) && !endpoint.endsWith('/batch') ? body() : undefined, raw: endpoint.endsWith('/batch') ? req.postDataBuffer().toString('utf8') : undefined });
      if (endpoint === '/teams/mine') return json([{ id: 't1', name: 'تیم' }]);
      if (endpoint === '/projects/mine' || endpoint === '/teams/t1/projects') return json([project]);
      if (endpoint.endsWith('/members')) return json([{ user, role: membership }]);
      if (endpoint === '/documents/personal') return json([]);
      if (endpoint === '/projects/p1/documents' && method === 'GET') return json(docs);
      if (endpoint === '/projects/p1/files' && method === 'GET') {
        const id = url.searchParams.get('folder_id');
        if (id && !folders.some((f) => f.id === id)) return json({ detail: 'Folder not found' }, 404);
        return json({
          folder_id: id, breadcrumb: crumbs(id),
          folders: folders.filter((f) => f.parent_id === id).map((folder) => ({ folder, status_counts: countsFor(folder.id) })),
          documents: docs.filter((d) => d.folder_id === id), archives: archives.filter((a) => a.folder_id === id),
        });
      }
      if (endpoint === '/projects/p1/files/search') {
        const q = url.searchParams.get('q').toLowerCase();
        return json(docs.filter((d) => d.filename.toLowerCase().includes(q)).map((document) => ({ document, path: crumbs(document.folder_id).map((f) => f.name) })));
      }
      if (endpoint === '/projects/p1/folders' && method === 'POST') {
        const { name, parent_id } = body();
        if (folders.some((f) => f.parent_id === parent_id && f.name.toLowerCase() === name.toLowerCase())) return json({ detail: 'A folder named already exists' }, 409);
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(addFolder(name, parent_id)) });
      }
      if (endpoint.startsWith('/projects/p1/documents/') && method === 'PATCH') { const d = docs.find((x) => x.id === endpoint.split('/')[4]); d.filename = body().filename; return json(d); }
      if (endpoint === '/projects/p1/files/move') {
        const { document_ids, folder_ids, target_folder_id, on_conflict } = body();
        const taken = docs.filter((d) => d.folder_id === target_folder_id).map((d) => d.filename);
        const clash = docs.filter((d) => document_ids.includes(d.id) && taken.includes(d.filename));
        if (clash.length && on_conflict === 'fail') return json({ detail: `Already exists in the destination: ${clash[0].filename}` }, 409);
        docs.filter((d) => document_ids.includes(d.id)).forEach((d) => { if (clash.includes(d)) d.filename = d.filename.replace('.txt', ' (1).txt'); d.folder_id = target_folder_id; });
        folders.filter((f) => folder_ids.includes(f.id)).forEach((f) => { f.parent_id = target_folder_id; });
        return json({ count: document_ids.length + folder_ids.length, skipped: 0 });
      }
      if (endpoint === '/projects/p1/files/delete') {
        const { document_ids, folder_ids } = body();
        const gone = new Set(folder_ids.flatMap(subtree));
        for (let i = docs.length - 1; i >= 0; i--) if (document_ids.includes(docs[i].id) || gone.has(docs[i].folder_id)) docs.splice(i, 1);
        for (let i = folders.length - 1; i >= 0; i--) if (gone.has(folders[i].id)) folders.splice(i, 1);
        return json({ count: 1, skipped: 0 });
      }
      if (endpoint === '/projects/p1/files/retry') { const t = docs.filter((d) => body().document_ids.includes(d.id) && ['failed', 'cancelled'].includes(d.status)); t.forEach((d) => { d.status = 'processing'; d.error_message = null; }); return json({ count: t.length, skipped: 0 }); }
      if (endpoint === '/projects/p1/files/cancel') { const t = docs.filter((d) => body().document_ids.includes(d.id) && d.status === 'processing'); t.forEach((d) => { d.status = 'cancelled'; }); return json({ count: t.length, skipped: 0 }); }
      if (endpoint.startsWith('/projects/p1/archives/') && method === 'DELETE') { archives.splice(archives.findIndex((a) => a.id === endpoint.split('/')[4]), 1); return route.fulfill({ status: 204 }); }
      if (endpoint === '/projects/p1/documents/batch') {
        await new Promise((resolve) => setTimeout(resolve, 600)); // keep the upload in flight long enough to observe progress
        const raw = requests.at(-1).raw;
        const folderId = /name="folder_id"\r\n\r\n([^\r]+)/.exec(raw)?.[1] ?? null;
        const names = [...raw.matchAll(/filename="([^"]+)"/g)].map((m) => m[1]);
        const items = names.map((filename) => {
          if (filename.endsWith('.zip')) { const archive = { id: `a${++counter}`, folder_id: folderId, filename, status: 'extracting', error_message: null, total_files: 0, imported_files: 0, skipped_files: 0, failed_files: [], created_at: now(), finished_at: null }; archives.push(archive); return { filename, status: 'accepted', document: null, archive, error: null }; }
          const document = addDoc(filename, folderId, filename.endsWith('.dwg') ? 'unsupported' : 'processing');
          return { filename, status: 'accepted', document, archive: null, error: null };
        });
        return json({ items, accepted: items.length, rejected: 0 });
      }
      return json({ detail: `Unexpected ${method} ${endpoint}` }, 404);
    });

    const reports = addFolder('گزارش‌ها');
    addDoc('ready.txt', null, 'ready'); addDoc('failed.txt', null, 'failed'); const slow = addDoc('slow.txt', null, 'processing');
    addDoc('report.txt', reports.id, 'ready');
    const base = process.env.APP_URL || 'http://127.0.0.1:3000';
    await page.goto(`${base}/documents`);
    await page.getByRole('button', { name: 'پوشهٔ جدید' }).waitFor();

    // 1. listing: folder summary + statuses
    await page.getByTestId('folder-row').filter({ hasText: 'گزارش‌ها' }).waitFor();
    assert.equal(await page.getByTestId('document-row').count(), 3);
    await page.getByTestId('document-row').filter({ hasText: 'failed.txt' }).getByText('Embedding failed').waitFor();
    console.log('PASS: root listing shows folders, documents and per-file status');

    // 2. create folder; duplicate name error stays in the dialog
    await page.getByRole('button', { name: 'پوشهٔ جدید' }).click();
    await page.getByRole('textbox', { name: 'نام' }).fill('قراردادها');
    await page.getByRole('button', { name: 'ساخت' }).click();
    await page.getByTestId('folder-row').filter({ hasText: 'قراردادها' }).waitFor();
    await page.getByRole('button', { name: 'پوشهٔ جدید' }).click();
    await page.getByRole('textbox', { name: 'نام' }).fill('قراردادها');
    await page.getByRole('button', { name: 'ساخت' }).click();
    await page.getByRole('alert').filter({ hasText: 'از قبل وجود دارد' }).waitFor();
    await page.getByRole('button', { name: 'انصراف' }).click();
    console.log('PASS: new folder, duplicate name rejected inside the dialog');

    // 3. open folder, upload into it: folder_id is sent, breadcrumb shows the path
    await page.getByRole('button', { name: 'قراردادها' }).click();
    await page.getByRole('navigation', { name: 'مسیر پوشه' }).getByText('قراردادها').waitFor();
    await page.getByLabel('فایل‌های اسناد پروژه').setInputFiles([
      { name: 'a.txt', mimeType: 'text/plain', buffer: Buffer.from('a') },
      { name: 'plan.dwg', mimeType: 'application/octet-stream', buffer: Buffer.from('AC') },
      { name: 'font.shx', mimeType: 'application/octet-stream', buffer: Buffer.from('junk') },
    ]);
    await page.getByRole('progressbar', { name: 'پیشرفت آپلود' }).waitFor();
    await page.getByText(/مگابایت \(.*٪\)/).waitFor();
    await page.getByTestId('document-row').filter({ hasText: 'a.txt' }).waitFor();
    await page.getByRole('progressbar', { name: 'پیشرفت آپلود' }).waitFor({ state: 'detached' });
    await page.getByTestId('document-row').filter({ hasText: 'plan.dwg' }).getByText('پشتیبانی‌نشده').waitFor();
    assert.equal(await page.getByText('font.shx').count(), 1, 'junk is only listed in the skipped details');
    const upload = requests.filter((r) => r.endpoint.endsWith('/batch')).at(-1);
    assert.ok(upload.raw.includes('name="folder_id"') && !upload.raw.includes('font.shx"\r\nContent'));
    console.log('PASS: upload goes into the open folder; unsupported kept, junk filtered');

    // 4. archive: card while extracting, then members appear with their own status and the folder summarises them
    await page.getByLabel('فایل‌های اسناد پروژه').setInputFiles({ name: 'bundle.zip', mimeType: 'application/zip', buffer: Buffer.from('PK') });
    await page.getByText('در حال باز کردن آرشیو…').waitFor();
    const archive = archives.at(-1), inner = addFolder('bundle', folders.find((f) => f.name === 'قراردادها').id);
    ['x1.txt', 'x2.txt', 'x3.txt'].forEach((n) => addDoc(n, inner.id));
    Object.assign(archive, { status: 'done', imported_files: 3, skipped_files: 2, failed_files: [{ path: 'huge.pdf', error: 'File exceeds the maximum allowed upload size' }], finished_at: now() });
    await page.getByText('آرشیو باز شد').waitFor();
    await page.getByTestId('folder-row').filter({ hasText: 'bundle' }).getByText('۳ در حال پردازش').waitFor();
    await page.getByText('فایل‌های واردنشده').click();
    await page.getByText('huge.pdf: File exceeds the maximum allowed upload size').waitFor();
    docs.filter((d) => d.folder_id === inner.id).forEach((d) => { d.status = 'ready'; });
    await page.getByTestId('folder-row').filter({ hasText: 'bundle' }).getByText('۳ آماده').waitFor({ timeout: 8000 });
    await page.getByRole('button', { name: /حذف اعلان bundle.zip/ }).click();
    await page.getByText('آرشیو باز شد').waitFor({ state: 'detached' });
    console.log('PASS: archive card, extracted members, live folder summary via polling, dismiss');

    // 5. cut + paste into another folder (breadcrumb back to root first)
    await page.getByRole('navigation', { name: 'مسیر پوشه' }).getByRole('button', { name: 'ریشهٔ پروژه' }).click();
    await page.getByLabel('انتخاب ready.txt').check();
    await page.getByRole('button', { name: 'برش', exact: true }).click();
    await page.getByRole('button', { name: 'گزارش‌ها' }).click();
    await page.getByRole('button', { name: /چسباندن/ }).click();
    await page.getByTestId('document-row').filter({ hasText: 'ready.txt' }).waitFor();
    assert.equal(requests.filter((r) => r.endpoint.endsWith('/files/move')).at(-1).body.on_conflict, 'fail');
    console.log('PASS: cut and paste moves the file into the open folder');

    // 6. name clash -> dialog -> keep both retries with rename
    await page.getByRole('navigation', { name: 'مسیر پوشه' }).getByRole('button', { name: 'ریشهٔ پروژه' }).click();
    addDoc('report.txt', null, 'ready');
    await page.getByRole('button', { name: 'به‌روزرسانی' }).click();
    await page.getByLabel('انتخاب report.txt').check();
    await page.getByRole('button', { name: 'برش', exact: true }).click();
    await page.getByRole('button', { name: 'گزارش‌ها' }).click();
    await page.getByRole('button', { name: /چسباندن/ }).click();
    await page.getByText('نام تکراری').waitFor();
    await page.getByRole('button', { name: 'نگه‌داشتن هر دو' }).click();
    await page.getByTestId('document-row').filter({ hasText: 'report (1).txt' }).waitFor();
    assert.equal(requests.filter((r) => r.endpoint.endsWith('/files/move')).at(-1).body.on_conflict, 'rename');
    console.log('PASS: name clash offers keep-both and retries with rename');

    // 7. drag a file onto a folder row
    await page.getByRole('navigation', { name: 'مسیر پوشه' }).getByRole('button', { name: 'ریشهٔ پروژه' }).click();
    await page.getByTestId('document-row').filter({ hasText: 'failed.txt' }).dragTo(page.getByTestId('folder-row').filter({ hasText: 'قراردادها' }));
    await page.getByTestId('document-row').filter({ hasText: 'failed.txt' }).waitFor({ state: 'detached' });
    assert.equal(docs.find((d) => d.filename === 'failed.txt').folder_id, folders.find((f) => f.name === 'قراردادها').id);
    console.log('PASS: drag and drop onto a folder moves the file');

    // 8. row actions: cancel then retry, bulk delete with confirmation
    await page.getByRole('button', { name: 'لغو پردازش slow.txt' }).click();
    await page.getByTestId('document-row').filter({ hasText: 'slow.txt' }).getByText('لغوشده').waitFor();
    await page.getByRole('button', { name: 'تلاش مجدد برای slow.txt' }).click();
    await page.getByTestId('document-row').filter({ hasText: 'slow.txt' }).getByText('در حال پردازش').waitFor();
    assert.equal(slow.status, 'processing');
    await page.getByLabel('انتخاب گزارش‌ها').check();
    await page.getByRole('button', { name: 'حذف', exact: true }).click();
    await page.getByText('(با همه‌ی محتوایش)').waitFor();
    await page.getByRole('dialog').getByRole('button', { name: 'حذف', exact: true }).click();
    await page.getByTestId('folder-row').filter({ hasText: 'گزارش‌ها' }).waitFor({ state: 'detached' });
    assert.equal(docs.some((d) => d.filename.startsWith('report')), false, 'folder contents are deleted with it');
    console.log('PASS: cancel, retry and recursive delete with confirmation');

    // 9. search with path, then jump to the folder
    await page.getByLabel('جست‌وجوی نام فایل').fill('x2');
    await page.getByRole('list', { name: 'نتایج جست‌وجو' }).getByText('ریشهٔ پروژه / قراردادها / bundle').waitFor();
    await page.getByRole('button', { name: 'نمایش در پوشه' }).click();
    await page.getByTestId('document-row').filter({ hasText: 'x2.txt' }).waitFor();
    console.log('PASS: search shows the folder path and opens the folder');

    // 10. members can browse but not change anything
    membership = 'member';
    await page.reload();
    await page.getByTestId('folder-row').first().waitFor();
    for (const name of ['پوشهٔ جدید', 'آپلود پوشه', 'برش', 'حذف']) assert.equal(await page.getByRole('button', { name, exact: true }).count(), 0, name);
    assert.equal(await page.getByRole('button', { name: /تلاش مجدد|لغو پردازش|تغییر نام/ }).count(), 0);
    assert.equal(await page.getByTestId('document-row').first().getAttribute('draggable'), null);
    console.log('PASS: project members have a read-only file manager');

    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), 'no horizontal page overflow on mobile');
    assert.deepEqual(errors, []);
    console.log('PASS: mobile layout and no page errors');
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
