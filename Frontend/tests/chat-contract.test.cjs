const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const { File } = require('node:buffer');

// Exercise the actual TypeScript modules, with only the HTTP boundary replaced.
function load(relativePath, mocks = {}) {
  const filename = path.resolve(__dirname, '../src/features/chat', relativePath);
  const code = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const compiledModule = { exports: {} };
  const requireModule = (id) => {
    if (id in mocks) return mocks[id];
    if (id.startsWith('@/')) return load(path.relative(path.resolve(__dirname, '../src/features/chat'), path.resolve(__dirname, '../src', `${id.slice(2)}.ts`)), mocks);
    if (id.startsWith('.')) return load(path.relative(path.resolve(__dirname, '../src/features/chat'), path.resolve(path.dirname(filename), `${id}.ts`)), mocks);
    return require(id);
  };
  vm.runInThisContext(`(function(require,module,exports){${code}\n})`, { filename })(requireModule, compiledModule, compiledModule.exports);
  return compiledModule.exports;
}

const { normalizeAgentStatus, agentStatusLabel } = load('lib/agentStatus.ts');
const { createEventStreamParser } = load('lib/eventStream.ts');

function apiHarness(response) {
  const calls = [];
  return { calls, ...load('api/chatApi.ts', {
    '@/shared/lib/apiClient': {
      API_BASE_URL: 'https://api.example.test/api/v1',
      ApiError: class extends Error {},
      authorizedFetch: async () => response,
      parseErrorMessage: async () => 'server error',
      apiRequest: async (url, options = {}) => { calls.push({ url, ...options }); return { ...options.body }; },
    },
    '@/shared/lib/errorMessages': { friendlyErrorMessage: (error) => error.message },
  }) };
}

function sseResponse(text, chunkSize = 1) {
  const bytes = new TextEncoder().encode(text);
  return new Response(new ReadableStream({ start(controller) {
    for (let offset = 0; offset < bytes.length; offset += chunkSize) controller.enqueue(bytes.slice(offset, offset + chunkSize));
    controller.close();
  }}));
}

test('all nine tools have human-readable Persian labels and raw args stay out of labels', () => {
  for (const tool of ['search_knowledge_base', 'list_user_projects', 'recall_project_insights', 'remember_project_insight', 'get_document_outline', 'read_document_pages', 'read_entire_document', 'get_current_chat_attachments', 'list_project_documents']) {
    const activity = normalizeAgentStatus({ status: 'searching', tool, args: { private: 'secret' } });
    assert.deepEqual(activity.args, { private: 'secret' });
    assert.match(agentStatusLabel(activity), /[\u0600-\u06ff]/);
    assert.doesNotMatch(agentStatusLabel(activity), /secret|searching/);
    assert.notEqual(agentStatusLabel(activity), 'جست‌وجو و بررسی اطلاعات');
  }
});

test('legacy statuses, direct generation, unknown tools and malformed payloads', () => {
  assert.equal(agentStatusLabel(normalizeAgentStatus({ status: 'در حال جستجو...' })), 'در حال جستجو...');
  assert.equal(agentStatusLabel({ status: 'generating' }), 'در حال نوشتن پاسخ');
  assert.equal(agentStatusLabel({ status: 'reading_documents', tool: 'future_tool' }), 'در حال خواندن اسناد');
  assert.equal(agentStatusLabel({ status: 'future_status' }), 'در حال بررسی درخواست شما');
  assert.equal(normalizeAgentStatus(null), null);
  assert.equal(normalizeAgentStatus({ status: 42 }), null);
});

test('SSE accepts network splits, CRLF, comments, multiline data and final unterminated event', () => {
  const events = [];
  const parser = createEventStreamParser((...event) => events.push(event));
  const wire = ':keepalive\r\n\r\nevent: status\r\ndata: {"status":\r\ndata: "searching"}\r\n\r\nevent: done\ndata: {"message_id":"m1"}';
  for (const character of wire) parser.push(character);
  parser.finish();
  assert.deepEqual(events, [['status', { status: 'searching' }], ['done', { message_id: 'm1' }]]);
});

test('real streamChat preserves structured stages, Persian text and final citations', async () => {
  const statuses = [], text = [], errors = [], completions = [];
  const source = { document_id: 'd1', document_filename: 'contract.pdf', chunk_index: 2, snippet: 'source', score: 0.9 };
  const wire = [
    ['start', { conversation_id: 'c1' }],
    ['status', { status: 'reading_documents', tool: 'read_document_pages', args: { page_start: 1 } }],
    ['status', { status: 'searching', tool: 'recall_project_insights', args: {} }],
    ['status', { status: 'generating' }],
    ['delta', { content: 'پاسخ مستند' }],
    ['done', { message_id: 'm1', sources: [source] }],
  ].map(([name, data]) => `event: ${name}\r\ndata: ${JSON.stringify(data)}\r\n\r\n`).join('');
  const { streamChat } = apiHarness(sseResponse(wire));
  await streamChat('question', null, { onStatus: (value) => statuses.push(value), onDelta: (value) => text.push(value), onDone: (...value) => completions.push(value), onError: (value) => errors.push(value) });
  assert.deepEqual(statuses.map((value) => value.status), ['reading_documents', 'searching', 'generating']);
  assert.deepEqual(statuses[0].args, { page_start: 1 });
  assert.equal(text.join(''), 'پاسخ مستند');
  assert.deepEqual(completions, [[[source], 'm1', []]]);  // third argument: artifacts (empty when the server sends none)
  assert.deepEqual(errors, []);
});

test('truncated streams and explicit server errors surface instead of silently completing', async () => {
  for (const wire of ['event: delta\ndata: {"content":"partial"}\n\n', 'event: error\ndata: {"message":"upstream failed"}\n\n']) {
    const errors = [], done = [];
    await apiHarness(sseResponse(wire)).streamChat('question', null, { onDelta() {}, onDone: () => done.push(true), onError: (value) => errors.push(value) });
    assert.equal(errors.length, 1);
    assert.equal(done.length, 0);
  }
});

test('aborting a stream does not emit a user-facing error or late callbacks', async () => {
  const controller = new AbortController();
  controller.abort();
  const calls = [];
  await apiHarness(sseResponse('event: delta\ndata: {"content":"late"}\n\n')).streamChat('question', null, { onDelta: () => calls.push('delta'), onError: () => calls.push('error') }, controller.signal);
  assert.deepEqual(calls, []);
});

test('rename retains the personal project, sends null for groups, and detects old servers', async () => {
  const { chatApi, calls } = apiHarness();
  await chatApi.renameConversation({ id: 'c1', type: 'personal', linked_project_id: 'project-1' }, ' عنوان جدید ');
  await chatApi.renameConversation({ id: 'c2', type: 'project_group', linked_project_id: 'should-not-send' }, 'گفتگوی تیم');
  assert.deepEqual(calls.map((value) => value.body), [{ title: 'عنوان جدید', linked_project_id: 'project-1' }, { title: 'گفتگوی تیم', linked_project_id: null }]);
  const legacy = load('api/chatApi.ts', { '@/shared/lib/apiClient': { apiRequest: async () => ({ title: 'old title' }) }, '@/shared/lib/errorMessages': {} });
  await assert.rejects(legacy.chatApi.renameConversation({ id: 'c1', type: 'personal', linked_project_id: null }, 'new title'), /سرور تغییر عنوان/);
});

test('group creation trims optional title and omits empty title; websocket URL remains unchanged', async () => {
  const { chatApi, calls } = apiHarness();
  await chatApi.createGroup('project-1', '  اسپرینت ۳  ');
  await chatApi.createGroup('project-1', '  ');
  assert.deepEqual(calls[0].body, { type: 'project_group', project_id: 'project-1', title: 'اسپرینت ۳' });
  assert.deepEqual(calls[1].body, { type: 'project_group', project_id: 'project-1' });
  assert.equal(chatApi.websocketUrl('c1', 'a+b'), 'wss://api.example.test/api/v1/chat/conversations/c1/ws?token=a%2Bb');
});

test('conversation documents have a dedicated status endpoint', async () => {
  const { chatApi, calls } = apiHarness();
  await chatApi.listDocuments('conversation-1');
  assert.equal(calls.at(-1).url, '/chat/conversations/conversation-1/documents');
  assert.equal(calls.at(-1).method, undefined);
});

const { ConversationDocumentTracker } = load('lib/conversationDocuments.ts');
const attachment = (id, status = 'processing', error_message = null) => ({
  id, status, error_message, filename: `${id}.txt`, conversation_id: 'c1', project_id: null,
});

test('document completion before upload response is retained and failed details arrive via GET', () => {
  for (const status of ['ready', 'failed']) {
    const tracker = new ConversationDocumentTracker();
    tracker.receive({ event: 'document_status', document_id: 'd1', status });
    tracker.merge([attachment('d1')]);
    assert.equal(tracker.snapshot[0].status, status);
    assert.equal(tracker.hasProcessing, false);
    tracker.merge([attachment('d1', status, status === 'failed' ? 'Invalid document' : null)]);
    assert.equal(tracker.snapshot[0].error_message, status === 'failed' ? 'Invalid document' : null);
  }
});

test('stale lists cannot remove a new upload or downgrade a terminal status', () => {
  const tracker = new ConversationDocumentTracker();
  tracker.merge([attachment('d1'), attachment('d2')]);
  tracker.merge([]);
  assert.equal(tracker.hasProcessing, true);
  tracker.receive({ event: 'document_status', document_id: 'd1', status: 'ready' });
  tracker.merge([attachment('d1')]);
  assert.deepEqual(tracker.snapshot.map((item) => item.status), ['ready', 'processing']);
  tracker.merge([attachment('d2', 'failed', 'Parse failed')]);
  tracker.merge([attachment('d2')]);
  assert.equal(tracker.hasProcessing, false);
  assert.equal(tracker.snapshot[1].error_message, 'Parse failed');
});

test('polling alone completes multiple uploads; immediate ready uploads never block sending', () => {
  const tracker = new ConversationDocumentTracker();
  tracker.merge([attachment('cached', 'ready')]);
  assert.equal(tracker.hasProcessing, false);
  tracker.merge([attachment('d1'), attachment('d2')]);
  tracker.merge([attachment('d1', 'ready')]);
  assert.equal(tracker.hasProcessing, true);
  tracker.merge([attachment('d2', 'ready')]);
  assert.equal(tracker.hasProcessing, false);
});

test('malformed events cannot release the processing guard and a new session has no old statuses', () => {
  const tracker = new ConversationDocumentTracker();
  tracker.merge([attachment('d1')]);
  for (const payload of [null, {}, { event: 'document_status', status: 'ready' }, { event: 'document_status', document_id: 'd1', status: 'unknown' }]) {
    assert.equal(tracker.receive(payload), false);
  }
  assert.equal(tracker.hasProcessing, true);
  tracker.receive({ event: 'document_status', document_id: 'd1', status: 'ready' });
  const next = new ConversationDocumentTracker();
  next.merge([attachment('d1')]);
  assert.equal(next.hasProcessing, true);
});

const { filterUploadFiles, batchFormData, uploadFileBatches, summarizeBatch } = load('../documents/lib/batchUpload.ts');

test('batch validation filters unsupported, temporary, empty, oversized and long-path files', () => {
  const file = (name, size = 1, webkitRelativePath = '') => ({ name, size, webkitRelativePath });
  const result = filterUploadFiles([
    file('leave.PDF', 1, 'policies/hr/leave.PDF'), file('logo.png'), file('.DS_Store'),
    file('~$draft.docx'), file('empty.txt', 0), file('large.xlsx', 50 * 1024 * 1024 + 1),
    file('note.txt', 1, `${'a'.repeat(501)}/note.txt`), file('limit.txt', 50 * 1024 * 1024),
  ]);
  assert.equal(result.eligible.length, 2);
  assert.equal(result.skipped.length, 6);
  assert.match(result.skipped[3].error, /خالی/);
  assert.equal(result.eligible[0].webkitRelativePath, 'policies/hr/leave.PDF');
});

test('multipart uses repeated files fields and preserves relative paths for same-named files', () => {
  const files = ['policies/hr/leave.txt', 'policies/finance/leave.txt'].map((relative) => {
    const file = new File(['text'], 'leave.txt');
    Object.defineProperty(file, 'webkitRelativePath', { value: relative });
    return file;
  });
  const form = batchFormData(files);
  assert.deepEqual([...form.keys()], ['files', 'files']);
  assert.deepEqual(form.getAll('files').map((file) => file.name), ['policies/hr/leave.txt', 'policies/finance/leave.txt']);
});

test('500 files are split into 25 batches with at most two in flight and all outcomes retained', async () => {
  const files = Array.from({ length: 500 }, (_, index) => new File(['x'], `${index}.txt`));
  const lengths = [], progress = [];
  let inFlight = 0, peak = 0;
  const result = await uploadFileBatches(files, async (batch) => {
    lengths.push(batch.length);
    peak = Math.max(peak, ++inFlight);
    await new Promise((resolve) => setImmediate(resolve));
    inFlight -= 1;
    return summarizeBatch(batch.map((file) => ({ filename: file.name, status: 'accepted', document: attachment(file.name), error: null })));
  }, (batch) => progress.push(batch.items.length));
  assert.equal(lengths.length, 25);
  assert.ok(lengths.every((length) => length === 20));
  assert.equal(peak, 2);
  assert.equal(progress.reduce((sum, count) => sum + count, 0), 500);
  assert.equal(result.accepted, 500);
  assert.deepEqual(result.items.map((item) => item.filename), files.map((file) => file.name));
});

test('partial rejections and a failed HTTP request do not discard successful batches', async () => {
  const files = Array.from({ length: 45 }, (_, index) => new File(['x'], `${index}.txt`));
  const result = await uploadFileBatches(files, async (batch) => {
    if (batch[0].name === '20.txt') throw new Error('request failed');
    return summarizeBatch(batch.map((file) => file.name === '0.txt'
      ? { filename: file.name, status: 'rejected', document: null, error: 'backend validation error' }
      : { filename: file.name, status: 'accepted', document: attachment(file.name, 'ready'), error: null }));
  });
  assert.equal(result.accepted, 24);
  assert.equal(result.rejected, 21);
  assert.equal(result.items[0].error, 'backend validation error');
  assert.match(result.items[20].error, /request failed/);
  assert.equal(result.items[44].status, 'accepted');
});

test('switching scope stops the scheduler from sending queued batches', async () => {
  let active = true, count = 0;
  await uploadFileBatches(Array.from({ length: 500 }, (_, index) => new File(['x'], `${index}.txt`)), async (batch) => {
    count += 1;
    active = false;
    return summarizeBatch(batch.map((file) => ({ filename: file.name, status: 'accepted', document: attachment(file.name), error: null })));
  }, undefined, () => active);
  assert.equal(count, 1);
});

test('project and chat batch APIs use their own scopes; retry uses the project endpoint', async () => {
  const { chatApi, calls } = apiHarness();
  const { documentsApi } = load('../documents/api/documentsApi.ts', {
    '@/shared/lib/apiClient': { apiRequest: async (url, options) => { calls.push({ url, ...options }); return {}; } },
  });
  const files = [new File(['x'], 'note.txt')];
  await chatApi.uploadBatch('c1', files);
  await documentsApi.uploadBatch('p1', files);
  await documentsApi.retry('p1', 'd1');
  assert.deepEqual(calls.map((call) => call.url), ['/chat/conversations/c1/documents/batch', '/projects/p1/documents/batch', '/projects/p1/documents/d1/retry']);
  assert.ok(calls.every((call) => call.method === 'POST'));
  assert.equal(calls[0].formData.getAll('files').length, 1);
  assert.equal(calls[2].formData, undefined);
});

// ---- accounting-database reference (SQL result artifact) ----
const { formatCell, tomanHint, formatDateValue, freshnessNotes } = load('lib/sqlResultFormat.ts');

test('database tool has a Persian activity label and the querying_database status is understood', () => {
  assert.match(agentStatusLabel(normalizeAgentStatus({ status: 'querying_database', tool: 'ask_accounting_db' })), /پایگاه داده/);
  assert.match(agentStatusLabel(normalizeAgentStatus({ status: 'querying_database' })), /پایگاه داده/);
});

test('Rial amounts keep every digit and add a Toman summary; ids/years are not grouped', () => {
  const money = formatCell('money', 2048558901);
  assert.equal(money.text.replace(/[\s٬,]/g, ''), '۲۰۴۸۵۵۸۹۰۱');
  assert.equal(money.hint, '≈ ۲۰۴٫۸۶ میلیون تومان');
  assert.equal(tomanHint(5e9), '≈ ۵۰۰ میلیون تومان');
  assert.equal(tomanHint(2e11), '≈ ۲۰ میلیارد تومان');
  assert.equal(tomanHint(5000), undefined);
  assert.equal(formatCell('text', 140505).text, '140505');
  assert.equal(formatCell('ratio', 0.3).text, '۳۰٪');
  assert.equal(formatCell('number', 517).text, '۵۱۷');
  assert.equal(formatCell('money', null).text, '—');
  assert.equal(formatCell('text', 'محمود').text, 'محمود');
});

test('ISO dates become Jalali, Jalali text is left alone, freshness notes mention provisional documents', () => {
  assert.equal(formatDateValue('2026-07-22'), '۱۴۰۵/۰۴/۳۱');
  assert.equal(formatDateValue('1405/04/31'), '1405/04/31');
  const notes = freshnessNotes({
    'آخرین تاریخ سند حسابداری معتبر (شامل موقت)': '2026-09-22',
    'آخرین تاریخ سند بررسی‌شده/قطعی (بعد از آن اسناد موقت‌اند)': '2026-07-22',
  });
  assert.deepEqual(notes, ['داده تا ۱۴۰۵/۰۶/۳۱', 'اسناد بعد از ۱۴۰۵/۰۴/۳۱ هنوز موقت‌اند']);
});

test('the done event delivers artifacts and tolerates servers that do not send them', async () => {
  const artifact = { type: 'sql_result', query_id: 'q1', sql: 'SELECT 1', columns: [], rows: [] };
  for (const [payload, expected] of [[{ sources: [], artifacts: [artifact], message_id: 'm1' }, [artifact]], [{ sources: [], message_id: 'm2' }, []]]) {
    const { streamChat } = apiHarness(sseResponse(`event: delta\ndata: {"content":"x"}\n\nevent: done\ndata: ${JSON.stringify(payload)}\n\n`, 7));
    let received;
    await streamChat('q', null, { onDelta() {}, onDone: (_sources, _id, artifacts) => { received = artifacts; } });
    assert.deepEqual(received, expected);
  }
});

test('artifact events are delivered immediately and malformed ones are ignored', async () => {
  const artifact = { type: 'sql_result', query_id: 'q9', sql: 'SELECT 1' };
  const wire = `event: artifact\ndata: ${JSON.stringify({ artifact })}\n\nevent: artifact\ndata: {"artifact":null}\n\nevent: delta\ndata: {"content":"x"}\n\nevent: done\ndata: {"sources":[],"message_id":"m"}\n\n`;
  const { streamChat } = apiHarness(sseResponse(wire, 5));
  const seen = [];
  await streamChat('q', null, { onDelta() {}, onArtifact: (a) => seen.push(a) });
  assert.deepEqual(seen, [artifact]);
});
