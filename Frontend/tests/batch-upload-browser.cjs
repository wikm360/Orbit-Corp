// Exercise real file/folder selectors, multipart requests, polling and retries against mocked APIs.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const user = { id: 'u1', full_name: 'سارا احمدی', email: 'sara@example.test', role: 'user' };
const project = { id: 'p1', team_id: 't1', name: 'پروژهٔ آزمایشی' };
const projectDocuments = [], chatDocuments = new Map(), conversations = [], sockets = new Map(), requests = [], errors = [];
let membership = 'leader', counter = 0, concurrent = 0, peak = 0;
let retryRejectId = null;
const payload = (name) => ({ name, mimeType: 'text/plain', buffer: Buffer.from('Document text') });
function document(filename, scope, status = 'processing') {
  return { id: `d${++counter}`, filename, status, content_type: 'text/plain', error_message: null, uploaded_by: user.id, created_at: new Date().toISOString(), project_id: scope === 'p1' ? 'p1' : null, conversation_id: scope === 'p1' ? null : scope };
}
projectDocuments.push(document('old-ready.txt', 'p1', 'ready'));

(async () => {
  const fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'rag-batch-fixture-'));
  const folder = path.join(fixture, 'policies');
  fs.mkdirSync(path.join(folder, 'hr'), { recursive: true });
  fs.mkdirSync(path.join(folder, 'finance'), { recursive: true });
  fs.writeFileSync(path.join(folder, 'hr', 'leave.txt'), 'HR policy');
  fs.writeFileSync(path.join(folder, 'finance', 'leave.txt'), 'Finance policy');
  fs.writeFileSync(path.join(folder, 'logo.png'), 'image');
  fs.writeFileSync(path.join(folder, '~$draft.docx'), 'temporary');
  fs.writeFileSync(path.join(folder, 'empty.txt'), '');
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
      const req = route.request(), endpoint = new URL(req.url()).pathname.replace('/api/v1', ''), method = req.method();
      const json = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
      requests.push({ endpoint, method });
      if (endpoint === '/teams/mine') return json([{ id: 't1', name: 'تیم' }]);
      if (endpoint === '/projects/mine' || endpoint === '/teams/t1/projects') return json([project]);
      if (endpoint.endsWith('/members')) return json([{ user, role: membership }]);
      if (endpoint === '/documents/personal') return json([]);
      if (endpoint.endsWith('/documents/batch')) {
        const scope = endpoint.startsWith('/projects/') ? 'p1' : endpoint.split('/')[3];
        const filenames = [...req.postDataBuffer().toString('utf8').matchAll(/filename="([^"]+)"/g)].map((match) => match[1]);
        assert.ok(filenames.length > 0 && filenames.length <= 20);
        requests.at(-1).filenames = filenames;
        peak = Math.max(peak, ++concurrent);
        await new Promise((resolve) => setTimeout(resolve, 50));
        concurrent -= 1;
        const store = scope === 'p1' ? projectDocuments : chatDocuments.get(scope);
        const items = filenames.map((filename) => {
          if (filename === 'reject.txt') return { filename, status: 'rejected', document: null, error: 'File rejected by server' };
          const doc = document(filename, scope, filename.includes('cached') ? 'ready' : 'processing');
          store.push(doc);
          return { filename, status: 'accepted', document: doc, error: null };
        });
        return json({ items, accepted: items.filter((item) => item.status === 'accepted').length, rejected: items.filter((item) => item.status === 'rejected').length });
      }
      if (endpoint.endsWith('/retry')) {
        assert.equal(method, 'POST');
        const id = endpoint.split('/')[4], doc = projectDocuments.find((item) => item.id === id);
        assert.equal(doc.status, 'failed');
        if (id === retryRejectId) return json({ detail: 'Retry denied' }, 403);
        await new Promise((resolve) => setTimeout(resolve, 30));
        doc.status = 'processing'; doc.error_message = null;
        return json(doc);
      }
      if (endpoint === '/projects/p1/documents') return json(projectDocuments);
      if (endpoint === '/chat/conversations') {
        if (method === 'GET') return json(conversations);
        const body = req.postDataJSON();
        const conversation = { id: `c${conversations.length + 1}`, type: 'personal', title: body.title, project_id: null, linked_project_id: body.linked_project_id, created_by: user.id, created_at: new Date().toISOString(), messages: [] };
        conversations.push(conversation); chatDocuments.set(conversation.id, []);
        return json(conversation);
      }
      if (endpoint.startsWith('/chat/conversations/')) {
        const id = endpoint.split('/')[3];
        if (endpoint.endsWith('/documents')) return json(chatDocuments.get(id));
        if (endpoint.endsWith('/messages')) return json([]);
        return json(conversations.find((item) => item.id === id));
      }
      return json({ detail: `Unexpected ${endpoint}` }, 404);
    });
    await page.routeWebSocket(/\/chat\/conversations\/.*\/ws/, (socket) => sockets.set(new URL(socket.url()).pathname.split('/')[5], socket));
    const base = process.env.APP_URL || 'http://127.0.0.1:3000';
    await page.goto(`${base}/documents`);
    await page.getByLabel('فایل‌های اسناد پروژه').waitFor({ state: 'attached' });
    const files = Array.from({ length: 43 }, (_, index) => payload(`file-${index}.txt`));
    files.push(payload('cached.txt'), payload('reject.txt'), payload('logo.png'), payload('~$draft.docx'), { ...payload('empty.txt'), buffer: Buffer.alloc(0) });
    await page.getByLabel('فایل‌های اسناد پروژه').setInputFiles(files);
    await page.getByText('45 فایل آمادهٔ ارسال · 3 فایل فیلترشده', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'آپلود فایل‌ها', exact: true }).click();
    await page.getByText('پایان ارسال: 44 پذیرفته، 1 ردشده', { exact: true }).waitFor();
    assert.equal(peak, 2);
    assert.deepEqual(requests.filter((item) => item.endpoint === '/projects/p1/documents/batch').map((item) => item.filenames.length), [20, 20, 5]);
    const progress = page.getByRole('progressbar', { name: 'پیشرفت پردازش فایل‌ها' });
    assert.equal(await progress.getAttribute('max'), '44');
    assert.equal(await progress.getAttribute('value'), '1', 'old project documents must not count toward this upload');
    await page.getByText('جزئیات فایل‌های ارسال‌نشده', { exact: true }).click();
    await page.getByText('reject.txt: File rejected by server', { exact: true }).waitFor();
    const uploaded = projectDocuments.filter((doc) => doc.filename !== 'old-ready.txt');
    uploaded.forEach((doc, index) => { doc.status = index < 3 ? 'failed' : 'ready'; doc.error_message = index < 3 ? 'Embedding failed' : null; });
    await page.getByText('41 از 44 سند آماده · 0 در حال پردازش · 3 ناموفق', { exact: true }).waitFor();
    await page.getByRole('button', { name: `تلاش مجدد برای ${uploaded[0].filename}`, exact: true }).click();
    await page.getByText('41 از 44 سند آماده · 1 در حال پردازش · 2 ناموفق', { exact: true }).waitFor();
    uploaded[0].status = 'ready';
    await page.getByText('42 از 44 سند آماده · 0 در حال پردازش · 2 ناموفق', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'تلاش مجدد برای همه‌ی ناموفق‌ها', exact: true }).click();
    await page.getByText('42 از 44 سند آماده · 2 در حال پردازش · 0 ناموفق', { exact: true }).waitFor();
    uploaded.forEach((doc) => { doc.status = 'ready'; });
    await page.getByText('44 از 44 سند آماده · 0 در حال پردازش · 0 ناموفق', { exact: true }).waitFor();
    assert.equal(requests.filter((item) => item.endpoint.endsWith('/retry')).length, 3);
    console.log('PASS: project batching, per-file rejections, upload-specific progress, polling and individual/bulk retry');

    uploaded[0].status = 'failed'; uploaded[1].status = 'failed';
    uploaded[0].error_message = 'Embedding failed'; uploaded[1].error_message = 'Embedding failed';
    retryRejectId = uploaded[0].id;
    await page.getByRole('button', { name: 'به‌روزرسانی', exact: true }).click();
    await page.getByText('42 از 44 سند آماده · 0 در حال پردازش · 2 ناموفق', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'تلاش مجدد برای همه‌ی ناموفق‌ها', exact: true }).click();
    await page.getByText('42 از 44 سند آماده · 1 در حال پردازش · 1 ناموفق', { exact: true }).waitFor();
    await page.getByRole('alert').filter({ hasText: 'برای انجام این کار دسترسی کافی ندارید.' }).waitFor();
    console.log('PASS: a failed bulk retry remains visible when another retry succeeds');

    membership = 'member'; projectDocuments[1].status = 'failed'; projectDocuments[1].error_message = 'Embedding failed';
    await page.reload();
    await page.getByText('Embedding failed', { exact: true }).first().waitFor();
    assert.equal(await page.getByRole('button', { name: 'انتخاب پوشه', exact: true }).count(), 0);
    assert.equal(await page.getByRole('button', { name: /تلاش مجدد/ }).count(), 0);
    console.log('PASS: ordinary project members have no upload/retry controls');

    await page.goto(`${base}/chat`);
    // Wait for hydration and workspace loading before firing a native file-change event.
    await page.getByRole('combobox', { name: 'محدودهٔ دانش', exact: true }).click();
    await page.getByRole('option', { name: 'پروژهٔ آزمایشی', exact: true }).waitFor();
    await page.keyboard.press('Escape');
    const chatFiles = Array.from({ length: 25 }, (_, index) => payload(`chat-${index}.txt`));
    chatFiles.push(payload('ignored.png'));
    await page.getByLabel('فایل پیوست گفتگو').setInputFiles(chatFiles);
    try {
      await page.getByText('پایان ارسال: 25 پذیرفته، 0 ردشده', { exact: true }).waitFor();
    } catch (error) {
      console.error('Chat upload diagnostics:', { requests: requests.filter((item) => item.endpoint.startsWith('/chat')), errors, text: await page.locator('main').innerText() });
      throw error;
    }
    assert.equal(conversations.length, 1, 'all batches attach to one new conversation');
    const conversationId = conversations[0].id, docs = chatDocuments.get(conversationId);
    assert.equal(docs.length, 25);
    assert.equal(requests.filter((item) => item.endpoint === `/chat/conversations/${conversationId}/documents/batch`).length, 2);
    assert.ok(docs.every((doc) => doc.project_id === null && doc.conversation_id === conversationId));
    await page.getByRole('textbox', { name: 'پیام', exact: true }).fill('پرسش درباره فایل‌ها');
    assert.equal(await page.getByRole('button', { name: 'در حال پردازش فایل‌ها', exact: true }).isDisabled(), true);
    const socket = sockets.get(conversationId);
    for (const doc of docs.slice(0, -1)) {
      doc.status = 'ready';
      socket.send(JSON.stringify({ event: 'document_status', document_id: doc.id, status: 'ready', filename: doc.filename }));
    }
    await page.getByText('24 از 25 سند آماده · 1 در حال پردازش · 0 ناموفق', { exact: true }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'در حال پردازش فایل‌ها', exact: true }).isDisabled(), true);
    const last = docs.at(-1); last.status = 'failed'; last.error_message = 'خطای پردازش فایل';
    socket.send(JSON.stringify({ event: 'document_status', document_id: last.id, status: 'failed', filename: last.filename }));
    await page.getByRole('alert').filter({ hasText: 'خطای پردازش فایل' }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'ارسال پیام', exact: true }).isEnabled(), true);
    console.log('PASS: chat batches stay in one conversation, socket progress waits for every document and GET supplies failure details');

    await page.getByRole('button', { name: 'افزودن سند به این گفتگو', exact: true }).click();
    assert.equal(await page.getByRole('button', { name: 'انتخاب پوشه', exact: true }).isVisible(), true);
    await page.getByLabel('پوشهٔ پیوست گفتگو').setInputFiles(folder);
    await page.getByText('پایان ارسال: 2 پذیرفته، 0 ردشده', { exact: true }).waitFor();
    await page.getByText('3 فایل نامعتبر یا موقت پیش از ارسال فیلتر شد.', { exact: true }).waitFor();
    const folderRequest = requests.filter((item) => item.endpoint.endsWith('/documents/batch')).at(-1);
    assert.equal(folderRequest.filenames.length, 2);
    assert.ok(folderRequest.filenames.some((name) => name === 'policies/hr/leave.txt'));
    assert.ok(folderRequest.filenames.some((name) => name === 'policies/finance/leave.txt'));
    await page.getByText('policies/hr/leave.txt', { exact: true }).waitFor();
    await page.getByText('policies/finance/leave.txt', { exact: true }).waitFor();
    const artifactDir = process.env.ARTIFACT_DIR || path.join(os.tmpdir(), 'rag-batch-browser-qa');
    fs.mkdirSync(artifactDir, { recursive: true });
    await page.screenshot({ path: path.join(artifactDir, 'chat-folder-desktop.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    const closeSidebar = page.getByRole('button', { name: 'بستن نوار کناری', exact: true });
    const sidebarOpen = await page.getByRole('complementary', { name: 'نوار کناری اصلی' }).evaluate((element) => element.classList.contains('translate-x-0'));
    if (sidebarOpen) await closeSidebar.click();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    await page.screenshot({ path: path.join(artifactDir, 'chat-folder-mobile.png'), fullPage: true, animations: 'disabled' });
    assert.deepEqual(errors, []);
    console.log('PASS: real directory upload preserves subfolder paths, filters unrelated files and fits mobile');
  } finally {
    await browser.close();
    // Delete only the unique directory created by this test under the OS temp directory.
    assert.equal(path.dirname(path.resolve(fixture)), path.resolve(os.tmpdir()));
    assert.ok(path.basename(fixture).startsWith('rag-batch-fixture-'));
    fs.rmSync(fixture, { recursive: true, force: true });
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
