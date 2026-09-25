const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

// Exercise the actual TypeScript modules, with only the HTTP boundary replaced.
function load(relativePath, mocks = {}) {
  const filename = path.resolve(__dirname, '../src/features/chat', relativePath);
  const code = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const compiledModule = { exports: {} };
  const requireModule = (id) => {
    if (id in mocks) return mocks[id];
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
      apiRequest: async (url, options) => { calls.push({ url, ...options }); return { ...options.body }; },
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
  assert.deepEqual(completions, [[[source], 'm1']]);
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
