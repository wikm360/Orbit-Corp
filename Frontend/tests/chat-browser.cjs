// Run against the local frontend. All API and WebSocket traffic is mocked in an isolated browser context.
// PLAYWRIGHT_MODULE can point to an existing Playwright installation.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const artifactDir = process.env.ARTIFACT_DIR || '/tmp/orbit-frontend-qa';
fs.mkdirSync(artifactDir, { recursive: true });
const user = { id: 'u1', full_name: 'سارا احمدی', email: 'sara@example.test', role: 'user', created_at: '2026-09-25T08:00:00Z' };
const project = { id: 'p1', team_id: 't1', name: 'توسعهٔ زیرساخت', description: 'برنامه‌ریزی و اجرای پروژه' };
const conversations = [
  { id: 'c1', type: 'personal', title: 'بررسی قرارداد پیمانکار', linked_project_id: 'p1', project_id: null },
  { id: 'g1', type: 'project_group', title: 'هماهنگی تیم پروژه', project_id: 'p1', linked_project_id: null },
];
conversations.forEach((item) => Object.assign(item, { created_by: 'u1', created_at: '2026-09-25T08:00:00Z', messages: [] }));
const requests = [], sockets = new Map(), errors = [], conversationDocuments = new Map();
let lateChatRoute;
function message(id, content, replyId = null, sender = 'assistant') {
  return { id, sender_type: sender, sender_id: sender === 'user' ? 'u1' : null, content, sources: [], reply_to_message_id: replyId, created_at: new Date().toISOString() };
}
function frame(name, data) { return `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`; }

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  try {
    await context.addInitScript(({ user }) => {
      localStorage.setItem('auth_token', 'local-test-token');
      localStorage.setItem('auth-store', JSON.stringify({ state: { token: 'local-test-token', user }, version: 0 }));
    }, { user });
    const page = await context.newPage();
    page.on('pageerror', (error) => errors.push(error.message));
    await page.route('**/api/v1/**', async (route) => {
      const req = route.request(), url = new URL(req.url()), endpoint = url.pathname.replace('/api/v1', ''), method = req.method();
      const json = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
      if (method === 'OPTIONS') return route.fulfill({ status: 204, headers: { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*' } });
      const body = method === 'GET' ? null : req.headers()['content-type']?.includes('application/json') ? req.postDataJSON() : null;
      requests.push({ endpoint, method, body });
      if (endpoint === '/teams/mine') return json([{ id: 't1', name: 'تیم مهندسی', description: '' }]);
      if (endpoint === '/projects/mine' || endpoint === '/teams/t1/projects') return json([project]);
      if (endpoint.endsWith('/members')) return json([{ user, role: 'leader' }]);
      if (endpoint.startsWith('/chat/conversations/') && endpoint.endsWith('/documents')) {
        const conversationId = endpoint.split('/')[3];
        if (method === 'POST') {
          const document = { id: `d-${conversationId}`, filename: 'sample.txt', content_type: 'text/plain', status: 'processing', error_message: null, project_id: null, conversation_id: conversationId, uploaded_by: 'u1', created_at: new Date().toISOString() };
          conversationDocuments.set(conversationId, [document]);
          return json({ document, message: 'Document accepted for processing' });
        }
        return json(conversationDocuments.get(conversationId) || []);
      }
      if (endpoint.includes('documents')) return json([]);
      if (endpoint === '/chat/conversations' && method === 'GET') return json(conversations);
      if (endpoint === '/chat/conversations' && method === 'POST') {
        const item = { id: `new-${conversations.length}`, ...body, title: body.title || 'New group conversation', linked_project_id: body.linked_project_id ?? null, project_id: body.project_id ?? null, messages: [], created_by: 'u1', created_at: new Date().toISOString() };
        conversations.push(item);
        return json(item);
      }
      const id = endpoint.split('/')[3], conversation = conversations.find((item) => item.id === id);
      if (endpoint.endsWith('/messages')) {
        if (method === 'POST') return json(message(`user-${Date.now()}`, body.content, null, 'user'));
        return json([]);
      }
      if (conversation && method === 'PATCH') { Object.assign(conversation, body); return json(conversation); }
      if (conversation && method === 'GET') return json(conversation);
      if (endpoint === '/chat') {
        if (body.message === 'پاسخ دیررس') { lateChatRoute = route; return; }
        const item = body.conversation_id ? conversations.find((item) => item.id === body.conversation_id) : { ...conversations[0], id: 'sse-new', title: 'گفتگوی تازه', messages: [] };
        if (!conversations.some((entry) => entry.id === item.id)) conversations.push(item);
        const finalMessage = message('answer-1', 'پاسخ مستند بر اساس اسناد پروژه.');
        finalMessage.sources = [{ document_id: 'd1', document_filename: 'قرارداد.pdf', chunk_index: 0, snippet: 'تحویل پروژه در پایان مهر', score: 0.9 }];
        item.messages = [message('question-1', body.message, null, 'user'), finalMessage];
        return route.fulfill({ contentType: 'text/event-stream', body: frame('start', { conversation_id: item.id }) + frame('status', { status: 'searching', tool: 'search_knowledge_base', args: { query: 'test' } }) + frame('status', { status: 'generating' }) + frame('delta', { content: finalMessage.content }) + frame('done', { message_id: finalMessage.id, sources: finalMessage.sources }) });
      }
      return json({ detail: `Unmocked: ${endpoint}` }, 404);
    });
    await page.routeWebSocket(/\/chat\/conversations\/.*\/ws/, (socket) => {
      const id = new URL(socket.url()).pathname.split('/')[5];
      sockets.set(id, socket);
    });
    await page.goto(process.env.APP_URL || 'http://127.0.0.1:3000/chat');
    await page.getByRole('heading', { name: /دانش سازمان/ }).waitFor();
    await page.getByRole('button', { name: /خلاصهٔ یک سند/ }).click();
    assert.match(await page.getByRole('textbox', { name: 'پیام', exact: true }).inputValue(), /خلاصه/);
    assert.equal(requests.filter((item) => item.endpoint === '/chat').length, 0, 'suggestions must not send immediately');
    await page.getByRole('textbox', { name: 'پیام', exact: true }).fill('');
    await page.screenshot({ path: path.join(artifactDir, 'desktop.png'), fullPage: true });
    console.log('PASS: desktop, editable suggestions');

    const projectToggle = page.getByRole('button', { name: /توسعهٔ زیرساخت/ }).first();
    assert.equal(await page.getByRole('button', { name: 'هماهنگی تیم پروژه', exact: true }).count(), 0, 'project chats start collapsed');
    await projectToggle.click();
    await page.getByRole('button', { name: 'هماهنگی تیم پروژه', exact: true }).waitFor();
    await page.getByRole('button', { name: 'بررسی قرارداد پیمانکار', exact: true }).waitFor();
    console.log('PASS: project conversations are nested under their project');

    await page.getByRole('textbox', { name: 'جست‌وجوی گفتگوها' }).fill('قرارداد');
    assert.equal(await page.getByRole('button', { name: 'هماهنگی تیم پروژه', exact: true }).count(), 0);
    await page.getByRole('button', { name: 'بررسی قرارداد پیمانکار', exact: true }).click();
    await page.getByRole('heading', { name: 'بررسی قرارداد پیمانکار', exact: true }).waitFor();
    await page.reload();
    await page.getByRole('heading', { name: 'بررسی قرارداد پیمانکار', exact: true }).waitFor();
    await page.getByRole('textbox', { name: 'پیام', exact: true }).waitFor();
    assert.equal(await page.getByRole('textbox', { name: 'پیام', exact: true }).isEnabled(), true);
    await page.getByRole('button', { name: 'ویرایش عنوان گفتگو' }).click();
    await page.getByRole('textbox', { name: 'عنوان گفتگو', exact: true }).fill('   ');
    assert.equal(await page.getByRole('button', { name: 'ذخیرهٔ عنوان' }).isDisabled(), true);
    await page.getByRole('textbox', { name: 'عنوان گفتگو', exact: true }).fill('مرور قرارداد جدید');
    await page.getByRole('button', { name: 'ذخیرهٔ عنوان' }).click();
    await page.getByRole('heading', { name: 'مرور قرارداد جدید', exact: true }).waitFor();
    assert.deepEqual(requests.find((item) => item.method === 'PATCH').body, { title: 'مرور قرارداد جدید', linked_project_id: 'p1' });
    console.log('PASS: search, personal rename preserves linked project');

    await page.getByRole('textbox', { name: 'پیام', exact: true }).fill('خلاصه قرارداد');
    await page.getByRole('button', { name: 'ارسال پیام', exact: true }).click();
    await page.getByText('پاسخ مستند بر اساس اسناد پروژه.', { exact: true }).waitFor();
    await page.getByText('[1] قرارداد.pdf', { exact: true }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'توقف دریافت پاسخ' }).count(), 0);
    console.log('PASS: SSE completion and citations');

    await page.getByRole('button', { name: 'گفتگوی گروهی جدید', exact: true }).click();
    await page.getByRole('textbox', { name: 'عنوان گفتگو (اختیاری)' }).fill('جلسهٔ طراحی');
    await page.getByRole('button', { name: 'ساخت گفتگو', exact: true }).click();
    await page.getByRole('heading', { name: 'جلسهٔ طراحی', exact: true }).waitFor();
    assert.equal(requests.find((item) => item.method === 'POST' && item.body?.title === 'جلسهٔ طراحی').body.project_id, 'p1');
    await page.getByText(/توسعهٔ زیرساخت · متصل/).waitFor();
    const groupId = new URL(page.url()).searchParams.get('conversation'), socket = sockets.get(groupId);
    assert.ok(socket, 'group websocket is available');
    const send = (data) => socket.send(JSON.stringify(data));
    send({ event: 'assistant_start', reply_to_message_id: 'reply-1' });
    send({ event: 'assistant_status', reply_to_message_id: 'reply-1', status: 'reading_documents', tool: 'read_document_pages', args: { secret: 'NEVER-RENDER' } });
    await page.getByRole('status').filter({ hasText: 'خواندن صفحه‌های سند' }).waitFor();
    send({ event: 'assistant_status', reply_to_message_id: 'reply-1', status: 'searching', tool: 'recall_project_insights', args: {} });
    await page.getByRole('status').filter({ hasText: 'مرور حافظهٔ پروژه' }).waitFor();
    assert.equal(await page.getByText('خواندن صفحه‌های سند', { exact: true }).count(), 0);
    assert.equal(await page.getByText('NEVER-RENDER').count(), 0);
    send({ event: 'assistant_start', reply_to_message_id: 'reply-2' });
    send({ event: 'assistant_status', reply_to_message_id: 'reply-2', status: 'searching', tool: 'remember_project_insight', args: {} });
    send({ event: 'message', message: message('group-answer-1', 'تصمیم‌های پروژه مرور شد.', 'reply-1') });
    await page.getByRole('status').filter({ hasText: 'ذخیرهٔ نکته در حافظهٔ پروژه' }).waitFor();
    assert.equal(await page.getByRole('textbox', { name: 'پیام', exact: true }).isEnabled(), true);
    await page.screenshot({ path: path.join(artifactDir, 'group-activity.png'), fullPage: true });
    send({ event: 'assistant_status', reply_to_message_id: 'reply-2', status: 'generating' });
    send({ event: 'assistant_delta', reply_to_message_id: 'reply-2', delta: 'تصمیم ثبت شد.' });
    await page.getByText('تصمیم ثبت شد.', { exact: true }).waitFor();
    assert.equal(await page.getByText('در حال نوشتن پاسخ', { exact: true }).count(), 0);
    send({ event: 'message', message: message('group-answer-2', 'تصمیم ثبت شد.', 'reply-2') });
    await page.getByRole('button', { name: 'ویرایش عنوان گفتگو' }).click();
    await page.getByRole('textbox', { name: 'عنوان گفتگو', exact: true }).fill('تصمیم‌های طراحی');
    await page.getByRole('button', { name: 'ذخیرهٔ عنوان' }).click();
    await page.getByRole('heading', { name: 'تصمیم‌های طراحی', exact: true }).waitFor();
    assert.equal(requests.filter((item) => item.method === 'PATCH').at(-1).body.linked_project_id, null);
    console.log('PASS: group creation, structured stages, concurrent replies, group rename');

    await page.getByRole('button', { name: 'گفتگوی گروهی جدید', exact: true }).click();
    await page.getByRole('button', { name: 'ساخت گفتگو', exact: true }).click();
    await page.getByRole('heading', { name: 'New group conversation', exact: true }).waitFor();
    assert.equal('title' in requests.filter((item) => item.method === 'POST' && item.endpoint === '/chat/conversations').at(-1).body, false);
    console.log('PASS: server default group title');

    await page.getByRole('button', { name: 'گفتگوی جدید', exact: true }).first().click();
    await page.getByRole('heading', { name: /دانش سازمان/ }).waitFor();
    await page.getByRole('textbox', { name: 'پیام', exact: true }).fill('پاسخ دیررس');
    await page.getByRole('button', { name: 'ارسال پیام', exact: true }).click();
    await page.getByRole('button', { name: 'توقف دریافت پاسخ' }).waitFor();
    await page.getByRole('button', { name: 'گفتگوی جدید', exact: true }).first().click();
    await page.getByRole('heading', { name: /دانش سازمان/ }).waitFor();
    if (lateChatRoute) await lateChatRoute.fulfill({ contentType: 'text/event-stream', body: frame('start', { conversation_id: 'old-id' }) + frame('delta', { content: 'نباید نمایش داده شود' }) + frame('done', { message_id: 'late', sources: [] }) }).catch(() => {});
    assert.equal(await page.getByText('نباید نمایش داده شود', { exact: true }).count(), 0);
    console.log('PASS: navigating away cancels pending personal response');

    await page.getByRole('textbox', { name: 'پیام', exact: true }).fill('پاسخ دیررس');
    await page.getByRole('button', { name: 'ارسال پیام', exact: true }).click();
    await page.getByRole('button', { name: 'توقف دریافت پاسخ' }).click();
    await page.getByRole('button', { name: 'توقف دریافت پاسخ' }).waitFor({ state: 'hidden' });
    assert.equal(await page.getByRole('textbox', { name: 'پیام', exact: true }).isEnabled(), true);
    if (lateChatRoute) await lateChatRoute.abort().catch(() => {});
    await page.getByRole('button', { name: 'گفتگوی جدید', exact: true }).first().click();
    await page.getByRole('heading', { name: /دانش سازمان/ }).waitFor();
    console.log('PASS: explicit stop releases composer');

    await page.getByLabel('فایل پیوست گفتگو').setInputFiles({ name: 'sample.txt', mimeType: 'text/plain', buffer: Buffer.from('Example document') });
    await page.getByText('سند «sample.txt» بارگذاری شد؛ تا پایان پردازش، ارسال پیام غیرفعال است.', { exact: true }).waitFor();
    await page.getByRole('heading', { name: 'sample.txt', exact: true }).waitFor();
    assert.equal(await page.getByRole('textbox', { name: 'پیام', exact: true }).isEnabled(), true);
    await page.getByRole('textbox', { name: 'پیام', exact: true }).fill('پرسش درباره سند');
    assert.equal(await page.getByRole('button', { name: 'در حال پردازش فایل‌ها', exact: true }).isDisabled(), true);
    assert.ok(requests.some((request) => request.endpoint.includes('/chat/conversations/') && request.endpoint.endsWith('/documents') && request.method === 'POST'));
    const uploadedConversationId = new URL(page.url()).searchParams.get('conversation');
    const uploadedSocket = sockets.get(uploadedConversationId);
    assert.ok(uploadedSocket, 'personal chat websocket is available for document status');
    const uploadedDocuments = conversationDocuments.get(uploadedConversationId);
    uploadedDocuments[0].status = 'ready';
    uploadedSocket.send(JSON.stringify({ event: 'document_status', document_id: uploadedDocuments[0].id, status: 'ready', filename: 'sample.txt' }));
    await page.getByRole('button', { name: 'ارسال پیام', exact: true }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'ارسال پیام', exact: true }).isEnabled(), true);
    await page.getByRole('button', { name: 'گفتگوی جدید', exact: true }).first().click();
    await page.getByRole('heading', { name: /دانش سازمان/ }).waitFor();
    console.log('PASS: uploading into a new conversation retains the attachment state');

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(artifactDir, 'mobile.png'), fullPage: true });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'mobile must not horizontally overflow');
    await page.getByRole('button', { name: 'باز کردن نوار کناری', exact: true }).click();
    await page.getByRole('textbox', { name: 'جست‌وجوی گفتگوها' }).fill('');
    await page.getByRole('link', { name: 'اسناد', exact: true }).click();
    await page.getByRole('heading', { name: 'پایگاه اسناد و دانش' }).waitFor();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    await page.screenshot({ path: path.join(artifactDir, 'mobile-documents.png'), fullPage: true });
    assert.deepEqual(errors, []);
    console.log('PASS: mobile navigation, documents, no horizontal overflow, no browser runtime errors');
    console.log(`Screenshots: ${artifactDir}`);
  } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exitCode = 1; });
