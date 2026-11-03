const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

// Runs the real TypeScript/TSX modules under src/, with only the HTTP boundary replaced.
function load(relativeToSrc, mocks = {}) {
  const filename = path.resolve(__dirname, '../src', relativeToSrc);
  const code = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    fileName: filename,
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const compiled = { exports: {} };
  const resolveLocal = (base, id) => {
    for (const ext of ['.ts', '.tsx', '/index.ts', '/index.tsx']) {
      const candidate = path.resolve(base, `${id}${ext}`);
      if (fs.existsSync(candidate)) return path.relative(path.resolve(__dirname, '../src'), candidate);
    }
    throw new Error(`cannot resolve ${id} from ${filename}`);
  };
  const requireModule = (id) => {
    if (id in mocks) return mocks[id];
    if (id.startsWith('@/')) return load(resolveLocal(path.resolve(__dirname, '../src'), id.slice(2)), mocks);
    if (id.startsWith('.')) return load(resolveLocal(path.dirname(filename), id), mocks);
    return require(id);
  };
  vm.runInThisContext(`(function(require,module,exports){${code}\n})`, { filename })(requireModule, compiled, compiled.exports);
  return compiled.exports;
}

const jalali = load('features/volume-reports/lib/jalali.ts');
const fmt = load('features/volume-reports/lib/format.ts');
const polling = load('features/volume-reports/lib/polling.ts');
const q = load('features/volume-reports/lib/questions.ts');
const status = load('features/volume-reports/lib/status.ts');

// ---- Jalali ----------------------------------------------------------------------------------------------------

test('Jalali conversion agrees with Intl for every day over 12 years, and round-trips', () => {
  const intl = new Intl.DateTimeFormat('en-u-ca-persian-nu-latn', { year: 'numeric', month: 'numeric', day: 'numeric', timeZone: 'UTC' });
  for (let t = Date.UTC(2020, 0, 1); t < Date.UTC(2032, 0, 1); t += 86400000) {
    const d = new Date(t);
    const parts = Object.fromEntries(intl.formatToParts(d).map((p) => [p.type, p.value]));
    const got = jalali.gregorianToJalali(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
    assert.deepEqual([got.jy, got.jm, got.jd], [Number(parts.year), Number(parts.month), Number(parts.day)], d.toISOString());
    const back = jalali.jalaliToGregorian(got.jy, got.jm, got.jd);
    assert.deepEqual([back.gy, back.gm, back.gd], [d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate()]);
  }
});

test('Jalali display uses Persian digits and parsing accepts Persian/Latin digits and separators', () => {
  assert.equal(jalali.formatJalaliDate('2026-09-23'), '۱۴۰۵/۰۷/۰۱');
  assert.equal(jalali.formatJalaliDate(null), '—');
  assert.equal(jalali.parseJalaliInput('۱۴۰۵/۰۷/۰۱'), '2026-09-23');
  assert.equal(jalali.parseJalaliInput('1405-7-1'), '2026-09-23');
  assert.equal(jalali.parseJalaliInput('1405/13/01'), null);
  assert.equal(jalali.parseJalaliInput('1405/12/30'), null); // 1405 is not a leap year
  assert.equal(jalali.parseJalaliInput('1403/12/30'), '2025-03-20'); // 1403 is
  assert.equal(jalali.parseJalaliInput('abc'), null);
  assert.equal(jalali.jalaliInputFromIso('2026-09-23'), '1405/07/01');
});

test('period label suggestion', () => {
  assert.equal(jalali.suggestPeriodLabel('month', '2026-08-23', '2026-09-22'), 'شهریور ۱۴۰۵');
  assert.match(jalali.suggestPeriodLabel('week', '2026-09-19', '2026-09-25'), /^هفته‌ی ۱۴۰۵\/۰۶\/۲۸ تا ۱۴۰۵\/۰۷\/۰۳$/);
});

// ---- numbers ----------------------------------------------------------------------------------------------------

test('quantities are formatted from decimal strings with Persian digits, grouping and exact half-up rounding', () => {
  assert.equal(fmt.formatQuantity('1949.3600', 2), '۱٬۹۴۹٫۳۶');
  assert.equal(fmt.formatQuantity('2572.8717', 2), '۲٬۵۷۲٫۸۷');
  assert.equal(fmt.formatQuantity('0.005', 2), '۰٫۰۱');
  assert.equal(fmt.formatQuantity('999.995', 2), '۱٬۰۰۰٫۰۰');
  assert.equal(fmt.formatQuantity('9999999999999999.9995', 3), '۱۰٬۰۰۰٬۰۰۰٬۰۰۰٬۰۰۰٬۰۰۰٫۰۰۰'); // beyond float precision
  assert.equal(fmt.formatQuantity('43.1669', 3), '۴۳٫۱۶۷');
  assert.equal(fmt.formatQuantity('563', 0), '۵۶۳');
  assert.equal(fmt.formatQuantity('-72283.0000', 0), '-۷۲٬۲۸۳');
  assert.equal(fmt.formatQuantity('-0.0001', 2), '۰٫۰۰'); // never "-0"
  assert.equal(fmt.formatQuantity('abc'), '—');
  assert.equal(fmt.formatQuantity(null), '—');
  assert.equal(fmt.formatQuantityWithUnit('693.0000', 't', 2), '۶۹۳٫۰۰ تن');
  assert.equal(fmt.formatQuantityWithUnit('12', 'm3', 0), '۱۲ مترمکعب');
});

// ---- polling ----------------------------------------------------------------------------------------------------

test('polling policy: steady when visible, slow when hidden, stops outside processing', () => {
  assert.equal(polling.nextDelay('processing', true, 0), 2000);
  assert.equal(polling.nextDelay('processing', true, 25), 4000);
  assert.equal(polling.nextDelay('processing', true, 1000), 8000); // capped
  assert.equal(polling.nextDelay('processing', false, 0), 15000);
  for (const s of ['draft', 'awaiting_user', 'needs_review', 'ready', 'published', 'failed']) assert.equal(polling.nextDelay(s, true, 0), null);
});

test('pollProgress polls until the run finishes and passes every update through', async () => {
  const sequence = [{ status: 'processing', progress: { done: 1, total: 3 } }, { status: 'processing', progress: { done: 2, total: 3 } }, { status: 'awaiting_user', progress: {} }];
  const delays = [];
  const seen = [];
  let visible = true;
  const result = await polling.pollProgress({
    fetchProgress: async () => sequence.shift(),
    onUpdate: (p) => { seen.push(p.status); visible = false; },
    isVisible: () => visible,
    sleep: async (ms) => { delays.push(ms); },
    signal: new AbortController().signal,
  });
  assert.deepEqual(seen, ['processing', 'processing', 'awaiting_user']);
  assert.deepEqual(delays, [2000, 15000, 15000]); // tab hidden after the first update -> slow polling
  assert.equal(result.status, 'awaiting_user');
});

test('pollProgress stops on abort and gives up after repeated failures', async () => {
  const controller = new AbortController();
  let calls = 0;
  await polling.pollProgress({ fetchProgress: async () => ({ status: 'processing', progress: {} }), onUpdate: () => { calls += 1; if (calls === 2) controller.abort(); }, isVisible: () => true, sleep: async () => {}, signal: controller.signal });
  assert.equal(calls, 2);
  let failures = 0;
  await polling.pollProgress({ fetchProgress: async () => { failures += 1; throw new Error('x'); }, onUpdate: () => {}, onError: () => {}, isVisible: () => true, sleep: async () => {}, signal: new AbortController().signal });
  assert.equal(failures, 5);
  assert.equal(polling.progressPercent({ done: 1, total: 4 }), 25);
  assert.equal(polling.progressPercent({ done: 0, total: 0 }), null);
});

// ---- question logic ---------------------------------------------------------------------------------------------

const question = (over = {}) => ({
  id: 'q1', kind: 'choice', impact_score: 0.2, status: 'open', group_keys: ['g'], answer: null, answered_at: null, created_at: '2026-01-01T00:00:00Z',
  spec: { kind: 'choice', prompt: 'کدام؟', group_ids: ['abc'], options: [{ key: 'exclude', label: 'حذف' }, { key: 'base', label: 'اساس' }, { key: 'subbase', label: 'زیراساس' }, { key: 'unknown', label: 'نمی‌دانم' }], remember_scopes: ['global', 'line'], default_remember: 'global' },
  ...over,
});

test('questions are ordered by impact and fixed options come last', () => {
  const ordered = q.byImpact([question({ id: 'a', impact_score: 0.1 }), question({ id: 'b', impact_score: 0.9 }), question({ id: 'c', impact_score: 0.5 })]);
  assert.deepEqual(ordered.map((x) => x.id), ['b', 'c', 'a']);
  assert.deepEqual(q.orderedOptions(question().spec.options).map((o) => o.key), ['base', 'subbase', 'exclude', 'unknown']);
});

test('answers: choice needs exactly one option, number respects range and Persian digits, payload carries the scope', () => {
  const choice = question();
  assert.match(q.validateDraft(choice, q.emptyDraft(choice)), /یک گزینه/);
  const draft = { ...q.emptyDraft(choice), choice: ['base'], scope: 'line' };
  assert.equal(q.validateDraft(choice, draft), null);
  assert.deepEqual(q.buildAnswer(choice, draft), { choice_keys: ['base'], remember_scope: 'line' });

  const number = question({ kind: 'number', spec: { kind: 'number', prompt: 'p', group_ids: [], options: [], number: { param_key: 'cross_section_m2', unit: 'm2', min: 0, max: 10 } } });
  assert.match(q.validateDraft(number, q.emptyDraft(number)), /عدد/);
  assert.match(q.validateDraft(number, { ...q.emptyDraft(number), number: '11' }), /بین/);
  assert.match(q.validateDraft(number, { ...q.emptyDraft(number), number: '-1' }), /عدد/);
  const ok = { ...q.emptyDraft(number), number: '۰٫۵' };
  assert.equal(q.validateDraft(number, ok), null);
  assert.equal(q.buildAnswer(number, ok).number, 0.5);

  const text = question({ kind: 'text', spec: { kind: 'text', prompt: 'p', group_ids: [], options: [] } });
  assert.match(q.validateDraft(text, q.emptyDraft(text)), /یادداشت/);
  const multi = question({ kind: 'multi_choice' });
  assert.match(q.validateDraft(multi, { ...q.emptyDraft(multi), choice: ['base', 'subbase'] }), /فقط یک/);
  assert.equal(q.parseNumberInput('1,5'), 1.5);
  assert.equal(q.parseNumberInput('x'), null);
});

test('remember selector is hidden for notes and the site-kind/layout system cards', () => {
  assert.equal(q.showsRemember(question()), true);
  assert.equal(q.showsRemember(question({ kind: 'text' })), false);
  assert.equal(q.showsRemember(question({ spec: { ...question().spec, system: 'site_kind' } })), false);
  assert.equal(q.showsRemember(question({ spec: { ...question().spec, system: 'no_conversion' }, kind: 'number' })), true);
});

test('publish-gate errors are parsed from the backend message, other errors are not', () => {
  const causes = status.parseGateError('Publish blocked: [{"code": "open_questions", "count": 2}, {"code": "site_kind_unconfirmed", "count": 1}]');
  assert.deepEqual(causes, [{ code: 'open_questions', count: 2 }, { code: 'site_kind_unconfirmed', count: 1 }]);
  assert.equal(status.parseGateError('Report not found'), null);
  assert.equal(status.parseGateError('Publish blocked: nonsense'), null);
  assert.equal(status.gateLabel('unit_mismatch'), 'ناسازگاری واحد');
});

// ---- review / wizard / chart helpers ---------------------------------------------------------------------------

const review = load('features/volume-reports/lib/review.ts');
const wizard = load('features/volume-reports/lib/wizard.ts');
const chart = load('features/volume-reports/lib/chart.ts');

const group = (over = {}) => ({
  group_key: 'k'.repeat(64), description: 'اجرای اساس', unit: 'm3', site_kind: 'road', n_lines: 2, section_headings: [], tokens: [], total_quantity: '10.0000',
  disposition: 'counted', item_key: 'base', role: 'execute', exclude_reason: null, source: 'agent', confirmed: false, reason: null, confidence: 0.82, ...over,
});

test('bulk confirm sends only selected rows that have a decision, mapping exclude/unmatched correctly', () => {
  const a = group({ group_key: 'a'.repeat(64) });
  const b = group({ group_key: 'b'.repeat(64), disposition: 'excluded', item_key: null, exclude_reason: 'surcharge', role: 'na' });
  const c = group({ group_key: 'c'.repeat(64), disposition: 'needs_input', item_key: null, role: null, source: 'system' });
  const d = group({ group_key: 'd'.repeat(64) });
  const drafts = { [d.group_key]: { choice: 'unmatched', role: 'na', scope: 'global' } };
  const { items, skipped } = review.buildBulkPayload([a, b, c, d], drafts, new Set([a.group_key, b.group_key, c.group_key, d.group_key]));
  assert.equal(skipped, 1); // c has no decision yet
  assert.deepEqual(items[0], { group_key: a.group_key, role: 'execute', remember_scope: 'global', item_key: 'base' });
  assert.deepEqual(items[1], { group_key: b.group_key, role: 'na', remember_scope: 'global', exclude_reason: 'surcharge' });
  assert.deepEqual(items[2], { group_key: d.group_key, role: 'na', remember_scope: 'line', disposition: 'unmatched' }); // never remembered globally
  assert.deepEqual(review.pendingGroups([a, group({ confirmed: true })]).length, 1);
  assert.equal(review.confidenceLabel(0.824), '82');
  assert.equal(review.confidenceLabel(null), '—');
});

test('wizard validation: Jalali dates, order, required fields and company suggestion', () => {
  const ok = wizard.validateInfo({ title: 'گزارش', periodType: 'month', start: '۱۴۰۵/۰۶/۰۱', end: '1405/06/31', label: 'شهریور ۱۴۰۵' });
  assert.deepEqual(ok.errors, {});
  assert.equal(ok.startIso, '2026-08-23');
  assert.equal(ok.endIso, '2026-09-22');
  const bad = wizard.validateInfo({ title: ' ', periodType: 'week', start: '1405/13/01', end: '1405/06/01', label: '' });
  assert.deepEqual(Object.keys(bad.errors).sort(), ['label', 'start', 'title']);
  assert.match(wizard.validateInfo({ title: 'x', periodType: 'week', start: '1405/06/10', end: '1405/06/01', label: 'x' }).errors.end, /قبل از شروع/);
  assert.equal(wizard.isExcelName('A.XLSX'), true);
  assert.equal(wizard.isExcelName('a.pdf'), true);
  assert.equal(wizard.isExcelName('a.docx'), false);
  const companies = [{ id: '1', name: 'محورگستر نصر' }, { id: '2', name: 'فراگیر عمران' }];
  assert.equal(wizard.matchSuggestedCompany('شرکت محور گستر نصر', [{ id: '1', name: 'محور گستر نصر' }]), '1');
  assert.equal(wizard.matchSuggestedCompany('شرکت فراگیر عمران نصر', companies), '2');
  assert.equal(wizard.matchSuggestedCompany('شرکت ناشناس', companies), null);
  assert.equal(wizard.filesReady({ a: 'c1', b: '' }), false);
  assert.equal(wizard.filesReady({ a: 'c1' }), true);
  assert.equal(wizard.filesReady({}), false);
});

test('chart option: one series for the holding, one per entity otherwise, one unit at a time', () => {
  const catalog = [{ key: 'base', title_fa: 'اساس', decimals: 2, output_unit: 'm3' }, { key: 'rebar', title_fa: 'آرماتور', decimals: 3, output_unit: 't' }];
  const row = (over) => ({ scope: 'holding', company: null, site: null, item_key: 'base', unit: 'm3', qty: '563.0000', ...over });
  const holding = [row({}), row({ item_key: 'rebar', unit: 't', qty: '43.1669' })];
  assert.deepEqual(chart.unitsPresent(holding, catalog), ['m3', 't']);
  const option = chart.buildBarOption({ rows: holding, unit: 'm3', scope: 'holding', catalog });
  assert.equal(option.series.length, 1);
  assert.deepEqual(option.xAxis.data, ['اساس']);
  assert.deepEqual(option.series[0].data, [563]);
  const sites = [row({ scope: 'site', site: 'الف' }), row({ scope: 'site', site: 'ب', qty: '10' })];
  const per = chart.buildBarOption({ rows: sites, unit: 'm3', scope: 'site', catalog });
  assert.deepEqual(per.series.map((s) => s.name), ['الف', 'ب']);
  assert.ok(per.legend);
});

// ---- components (server-rendered markup) -----------------------------------------------------------------------

const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const componentMocks = {
  'next/link': { default: ({ href, children, ...rest }) => React.createElement('a', { href, ...rest }, children) },
};
const { QuestionCard } = load('features/volume-reports/components/QuestionCard.tsx', componentMocks);
const { VolumeTableCard } = load('features/volume-reports/components/VolumeTableCard.tsx', componentMocks);
const { SourceDetails, describeWarning } = load('features/volume-reports/components/SourcesPanel.tsx', componentMocks);

const render = (el) => renderToStaticMarkup(el);
const noop = () => {};

test('QuestionCard (choice): prompt, the rows it is about, ordered options with fixed ones last, remember selector, actions', () => {
  const html = render(React.createElement(QuestionCard, {
    question: question(), busy: false, onAnswer: noop, onSkip: noop,
    groups: [group({ description: 'قشر آسفالتی نامشخص', unit: 't', total_quantity: '693.0000', section_headings: ['عملیات آسفالت'] })],
  }));
  assert.match(html, /کدام؟/);
  assert.match(html, /قشر آسفالتی نامشخص/);
  assert.match(html, /۶۹۳٫۰۰ تن/); // exact decimal string -> Persian digits + unit
  assert.match(html, /عملیات آسفالت/);
  assert.ok(html.indexOf('اساس') < html.indexOf('حذف') && html.indexOf('زیراساس') < html.indexOf('نمی‌دانم'));
  assert.equal((html.match(/<input type="radio"[^>]*name="q-q1"/g) ?? []).length, 4);
  assert.match(html, /سراسری/);
  assert.match(html, /فقط همین ردیف/);
  assert.match(html, /ثبت پاسخ/);
  assert.match(html, /رد کردن/);
  assert.doesNotMatch(html, /role="alert"/); // no error before the first attempt
});

test('QuestionCard (number / text / multi-choice / site kind)', () => {
  const number = question({ kind: 'number', spec: { kind: 'number', prompt: 'مقطع؟', group_ids: [], options: [], number: { param_key: 'cross_section_m2', unit: 'm2', min: 0, max: 5 }, remember_scopes: ['global', 'line'], default_remember: 'global', system: 'no_conversion' } });
  const nHtml = render(React.createElement(QuestionCard, { question: number, groups: [], onAnswer: noop, onSkip: noop }));
  assert.match(nHtml, /مقدار \(m2\)/);
  assert.match(nHtml, /۰ تا ۵/);
  assert.match(nHtml, /inputMode="decimal"/);
  const text = question({ kind: 'text', spec: { kind: 'text', prompt: 'نظر؟', group_ids: [], options: [] } });
  const tHtml = render(React.createElement(QuestionCard, { question: text, groups: [], onAnswer: noop, onSkip: noop }));
  assert.match(tHtml, /<textarea/);
  assert.doesNotMatch(tHtml, /حافظه/); // a note never changes a decision, so no "remember" selector
  const multi = question({ kind: 'multi_choice' });
  const mHtml = render(React.createElement(QuestionCard, { question: multi, groups: [], onAnswer: noop, onSkip: noop }));
  assert.equal((mHtml.match(/type="checkbox"/g) ?? []).length, 4);
  assert.match(mHtml, /فقط یک گزینه/);
  const site = question({ spec: { ...question().spec, system: 'site_kind', options: [{ key: 'road', label: 'راهسازی' }, { key: 'mining', label: 'معدن' }] } });
  const sHtml = render(React.createElement(QuestionCard, { question: site, groups: [], onAnswer: noop, onSkip: noop }));
  assert.doesNotMatch(sHtml, /فقط همین ردیف/);
});

test('VolumeTableCard renders the chat artifact: title, period, per-row unit column, notes, link to the report', () => {
  const artifact = {
    type: 'volume_table', version: 1, report_id: 'rep-1', title: 'گزارش شهریور', period: 'شهریور 1405',
    columns: ['کارگاه', 'آیتم', 'مقدار'], rows: [['سیرجان', 'اساس', '1,563.50*'], ['سیرجان', 'آرماتور', '43.167']], unit_by_row: ['m3', 't'],
    notes: ['گزارش منتشرشده: گزارش شهریور', '* شامل ردیف‌های تأییدنشده'],
  };
  const html = render(React.createElement(VolumeTableCard, { artifact }));
  assert.match(html, /dir="rtl"/);
  assert.match(html, /گزارش شهریور/);
  assert.match(html, /href="\/volume-reports\/rep-1"/);
  assert.match(html, /۱٬۵۶۳٫۵۰\*/);
  assert.match(html, /۴۳٫۱۶۷/);
  assert.match(html, /مترمکعب/);
  assert.match(html, />تن</);
  assert.match(html, /شامل ردیف‌های تأییدنشده/);
  assert.equal((html.match(/<th /g) ?? []).length, 4); // 3 columns + the unit column
});

test('Source details list used sheets, skipped sheets with the reason, and warnings in Persian', () => {
  const sources = [{
    id: 's1', filename: 'a.xls', status: 'parsed', error_message: null, suggested_company: null,
    warnings: [{ code: 'period_label_mismatch', sheet: 'درآمد کازرون', found: ['خرداد'], expected: ['شهریور'] }],
    sheet_log: [
      { sheet: ' درآمد سیرجان', visibility: 'visible', kind: 'income', used: true, reason: null, site_name: 'سیرجان', rows_nonzero: 22 },
      { sheet: 'درآمد برنامه ای', visibility: 'visible', kind: 'planned', used: false, reason: 'planned_sheet' },
      { sheet: 'EVM Y', visibility: 'hidden', kind: 'hidden', used: false, reason: 'hidden' },
    ],
  }];
  const html = render(React.createElement(SourceDetails, { sources }));
  assert.match(html, /شیت برنامه‌ای/);
  assert.match(html, /شیت پنهان/);
  assert.match(html, /ماه عنوان شیت با دوره‌ی واردشده نمی‌خواند/);
  assert.match(html, /۲۲ ردیف دارای حجم/);
  assert.match(describeWarning({ code: 'unit_missing', row: 7 }), /ردیف ۷/);
});
