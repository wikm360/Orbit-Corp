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

test('bulk confirm sends only selected rows that have a decision, mapping «سایر»/duplicate correctly (no «remove from report»)', () => {
  const a = group({ group_key: 'a'.repeat(64) });
  const b = group({ group_key: 'b'.repeat(64), disposition: 'excluded', item_key: null, exclude_reason: 'surcharge', role: 'na' });
  const c = group({ group_key: 'c'.repeat(64), disposition: 'needs_input', item_key: null, role: null, source: 'system' });
  const d = group({ group_key: 'd'.repeat(64) });
  const e = group({ group_key: 'e'.repeat(64) });
  const drafts = { [d.group_key]: { choice: 'unmatched', role: 'na', scope: 'global' }, [e.group_key]: { choice: 'duplicate', role: 'na', scope: 'line' } };
  const { items, skipped } = review.buildBulkPayload([a, b, c, d, e], drafts, new Set([a.group_key, b.group_key, c.group_key, d.group_key, e.group_key]));
  assert.equal(skipped, 1); // c has no decision yet
  assert.deepEqual(items[0], { group_key: a.group_key, role: 'execute', remember_scope: 'global', item_key: 'base' });
  // a legacy "excluded" group now reads as «سایر» and is confirmed as such
  assert.deepEqual(items[1], { group_key: b.group_key, role: 'na', remember_scope: 'global', disposition: 'unmatched' });
  // «سایر» follows the memory scope the user picked (it used to be forced to "line")
  assert.deepEqual(items[2], { group_key: d.group_key, role: 'na', remember_scope: 'global', disposition: 'unmatched' });
  assert.deepEqual(items[3], { group_key: e.group_key, role: 'na', remember_scope: 'line', exclude_reason: 'duplicate' });
  assert.equal(review.draftFromGroup(group({ disposition: 'excluded', item_key: null, exclude_reason: 'duplicate' })).choice, 'duplicate');
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

test('source location helpers merge duplicates, respect priority, and distinguish Excel sheets from PDF pages', () => {
  assert.equal(q.isPdfFilename('weekly-report.PDF'), true);
  assert.equal(q.isPdfFilename('sheet.xlsx'), false);
  assert.equal(q.formatRowNumbersLabel([5], 1), 'ردیف ۵');
  assert.equal(q.formatRowNumbersLabel([5, 8], 4), 'ردیف‌های ۵، ۸ و ۲ ردیف دیگر');
  assert.equal(q.formatRowNumbersLabel([], 3), '۳ ردیف');
  assert.equal(
    q.formatSourceLocationText({ filename: 'report.pdf', sheet: 'درآمد معدن (صفحه ۲)', section: 'خاک‌برداری', row_nos: [7], n_lines: 1 }),
    'فایل report.pdf · صفحه درآمد معدن (صفحه ۲) · بخش خاک‌برداری · ردیف ۷',
  );

  // question.locations wins and merges repeated rows sharing file/site/sheet/section
  const merged = q.locationsForQuestion(question({
    locations: [
      { filename: 'a.xlsx', company: 'گلومک', site: 'سیرجان', sheet: 'درآمد', section: 'عملیات آسفالت', row_nos: [15], n_lines: 1 },
      { filename: 'a.xlsx', company: 'گلومک', site: 'سیرجان', sheet: 'درآمد', section: 'عملیات آسفالت', row_nos: [12, 15], n_lines: 2 },
    ],
  }), [group({ locations: [{ filename: 'ignored.xlsx', sheet: 'سایر', row_nos: [1], n_lines: 1 }] })]);
  assert.equal(merged.length, 1);
  assert.deepEqual(merged[0].row_nos, [12, 15]);
  assert.equal(merged[0].n_lines, 3);

  // fallback to groups[].locations when question.locations is missing
  const fromGroups = q.locationsForQuestion(question(), [group({
    locations: [{ filename: 'b.xlsx', site: 'کرمان', sheet: 'جدول ۱', section: 'زیرسازی', row_nos: [4], n_lines: 1 }],
  })]);
  assert.equal(fromGroups[0].filename, 'b.xlsx');

  // layout fallback uses spec.sheet when no locations exist yet
  const layoutFallback = q.locationsForQuestion(
    question({ spec: { kind: 'confirm_group', prompt: 'تایید ساختار', group_ids: [], options: [], system: 'layout', file_id: 'f1', sheet: 'شیت ناشناس' } }),
    [],
  );
  assert.deepEqual(layoutFallback, [{ filename: '', sheet: 'شیت ناشناس' }]);
});

test('QuestionCard displays source file, sheet/page, section, site, and row numbers across question types', () => {
  const excelHtml = render(React.createElement(QuestionCard, {
    question: question(), busy: false, onAnswer: noop, onSkip: noop,
    groups: [group({
      description: 'قشر آسفالتی نامشخص', unit: 't', total_quantity: '693.0000', section_headings: ['عملیات آسفالت'],
      locations: [{ filename: 'faragir-week2.xlsx', site: 'بم', sheet: 'کارکرد هفتگی', section: 'عملیات آسفالت', row_nos: [12, 15], n_lines: 2 }],
    })],
  }));
  assert.match(excelHtml, /aria-label="منبع در فایل‌ها"/);
  assert.match(excelHtml, /محل در فایل‌های گزارش/);
  assert.match(excelHtml, /faragir-week2\.xlsx/);
  assert.match(excelHtml, /شیت:/);
  assert.match(excelHtml, /کارکرد هفتگی/);
  assert.match(excelHtml, /بخش:.*عملیات آسفالت/);
  assert.match(excelHtml, /کارگاه بم/);
  assert.match(excelHtml, /ردیف‌های ۱۲، ۱۵/);

  const convPdfQ = question({
    kind: 'number',
    locations: [{ filename: 'aban-pdf-report.pdf', site: 'سیرجان', sheet: 'درآمد معدن (صفحه ۲)', section: 'حمل مواد', row_nos: [7], n_lines: 1 }],
    spec: { kind: 'number', prompt: 'چگالی؟', group_ids: [], options: [], number: { param_key: 'density_t_per_m3', unit: 't/m3', min: 1, max: 3 }, system: 'no_conversion' },
  });
  const convHtml = render(React.createElement(QuestionCard, { question: convPdfQ, groups: [], onAnswer: noop, onSkip: noop }));
  assert.match(convHtml, /aban-pdf-report\.pdf/);
  assert.match(convHtml, /صفحه:/);
  assert.match(convHtml, /درآمد معدن \(صفحه ۲\)/);
  assert.match(convHtml, /حمل مواد/);
  assert.match(convHtml, /ردیف ۷/);

  const siteQ = question({
    locations: [{ filename: 'site-doc.xlsx', site: 'سیرجان', sheet: 'جدول کارکرد', row_nos: [3, 9], n_lines: 2 }],
    spec: { ...question().spec, group_ids: [], system: 'site_kind', options: [{ key: 'road', label: 'راهسازی' }, { key: 'mining', label: 'معدن' }] },
  });
  const siteHtml = render(React.createElement(QuestionCard, { question: siteQ, groups: [], onAnswer: noop, onSkip: noop }));
  assert.match(siteHtml, /site-doc\.xlsx/);
  assert.match(siteHtml, /جدول کارکرد/);

  const layoutQ = question({
    locations: [{ filename: 'raw-layout.xlsx', sheet: 'درآمد خام' }],
    spec: { kind: 'confirm_group', prompt: 'آیا ستون‌ها درست است؟', group_ids: [], options: [], system: 'layout', file_id: 'f1', sheet: 'درآمد خام' },
  });
  const layoutHtml = render(React.createElement(QuestionCard, { question: layoutQ, groups: [], onAnswer: noop, onSkip: noop }));
  assert.match(layoutHtml, /raw-layout\.xlsx/);
  assert.match(layoutHtml, /درآمد خام/);
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
      { sheet: 'برنامه های دست اجرا (صفحه 1)', visibility: 'visible', kind: 'evm', used: true, reason: null, basis: 'actual', evm_rows: 8 },
      { sheet: ' درآمد سیرجان', visibility: 'visible', kind: 'income', used: true, reason: null, site_name: 'سیرجان', rows_nonzero: 22 },
      { sheet: 'درآمد برنامه ای', visibility: 'visible', kind: 'planned', used: false, reason: 'planned_sheet' },
      { sheet: 'EVM Y', visibility: 'hidden', kind: 'hidden', used: false, reason: 'hidden' },
    ],
  }];
  const html = render(React.createElement(SourceDetails, { sources }));
  assert.match(html, /خلاصه مالی EVM/);
  assert.match(html, /۸ ردیف/);
  assert.doesNotMatch(html, /۰ ردیف دارای حجم/);
  assert.doesNotMatch(html, /undefined/);
  assert.match(html, /شیت برنامه‌ای/);
  assert.match(html, /شیت پنهان/);
  assert.match(html, /ماه عنوان شیت با دوره‌ی واردشده نمی‌خواند/);
  assert.match(html, /۲۲ ردیف دارای حجم/);
  assert.match(describeWarning({ code: 'unit_missing', row: 7 }), /ردیف ۷/);
});

// ---- presentation helpers ---------------------------------------------------------------------------------------

const pres = load('features/volume-reports/lib/presentation.ts');

test('presentation decimal addition and unit conversion preserve exact decimal precision', () => {
  assert.equal(pres.addDecimalStrings('0.1', '0.2'), '0.3');
  assert.equal(pres.addDecimalStrings('1234.5000', '67.8500'), '1302.3500');
  assert.equal(pres.addDecimalStrings('100', '25.5'), '125.5');
  assert.equal(pres.convertMassDecimal('2.5', 't', 'kg'), '2500');
  assert.equal(pres.convertMassDecimal('1500', 'kg', 't'), '1.500');
});

test('presentation merges prime_coat and tack_coat in catalog and across all result scopes', () => {
  const catalog = [
    { key: 'excavation', title_fa: 'خاکبرداری', description_fa: '', dimension: 'volume', output_unit: 'm3', decimals: 2, is_rollup: false, rollup_of: [], mining_only: false },
    { key: 'asphalt_binder', title_fa: 'آسفالت بیندر', description_fa: '', dimension: 'mass', output_unit: 't', decimals: 2, is_rollup: false, rollup_of: [], mining_only: false },
    { key: 'asphalt_topka', title_fa: 'آسفالت توپکا', description_fa: '', dimension: 'mass', output_unit: 't', decimals: 2, is_rollup: false, rollup_of: [], mining_only: false },
    { key: 'asphalt_total', title_fa: 'آسفالت (جمع)', description_fa: '', dimension: 'mass', output_unit: 't', decimals: 2, is_rollup: true, rollup_of: ['asphalt_binder', 'asphalt_topka'], mining_only: false },
    { key: 'prime_coat', title_fa: 'پریمکت', description_fa: '', dimension: 'mass', output_unit: 'kg', decimals: 1, is_rollup: false, rollup_of: [], mining_only: false },
    { key: 'tack_coat', title_fa: 'تک‌کت', description_fa: '', dimension: 'mass', output_unit: 'kg', decimals: 1, is_rollup: false, rollup_of: [], mining_only: false },
    { key: 'concrete', title_fa: 'بتن', description_fa: '', dimension: 'volume', output_unit: 'm3', decimals: 2, is_rollup: false, rollup_of: [], mining_only: false },
  ];
  const { items, coatUnit, coatDecimals } = pres.mergeCoatCatalog(catalog);
  assert.equal(coatUnit, 'kg');
  assert.equal(coatDecimals, 1);
  assert.deepEqual(items.map((i) => i.key), ['excavation', 'asphalt_total', 'prime_tack_total', 'concrete']);
  assert.equal(items[2].title_fa, 'پریمکت و تک‌کت');

  const mkRow = (over) => ({
    scope: 'holding', company_id: null, company: null, site_id: null, site: null,
    item_key: 'excavation', item: 'خاکبرداری', decimals: 2, sort: 1, qty: '10.0000', unit: 'm3', n_lines: 1, has_unconfirmed: false, ...over,
  });

  const holdingMerged = pres.mergeCoatResultRows([
    mkRow({ item_key: 'prime_coat', unit: 'kg', decimals: 1, sort: 11, qty: '1200.4000', n_lines: 2, has_unconfirmed: false }),
    mkRow({ item_key: 'tack_coat', unit: 'kg', decimals: 1, sort: 12, qty: '300.6000', n_lines: 3, has_unconfirmed: true }),
    mkRow({ item_key: 'concrete', unit: 'm3', qty: '55.0000' }),
  ], coatUnit, coatDecimals);
  assert.equal(holdingMerged.length, 2);
  const holdingCoat = holdingMerged.find((r) => r.item_key === 'prime_tack_total');
  assert.equal(holdingCoat.qty, '1501.0000');
  assert.equal(holdingCoat.n_lines, 5);
  assert.equal(holdingCoat.has_unconfirmed, true);

  const companyMerged = pres.mergeCoatResultRows([
    mkRow({ scope: 'company', company_id: 'c1', company: 'شرکت الف', item_key: 'prime_coat', unit: 'kg', qty: '400.5' }),
    mkRow({ scope: 'company', company_id: 'c1', company: 'شرکت الف', item_key: 'tack_coat', unit: 'kg', qty: '99.5' }),
    mkRow({ scope: 'company', company_id: 'c2', company: 'شرکت ب', item_key: 'tack_coat', unit: 'kg', qty: '250.0' }),
  ], coatUnit, coatDecimals);
  assert.equal(companyMerged.length, 2);
  assert.equal(companyMerged.find((r) => r.company_id === 'c1').qty, '500.0');
  assert.equal(companyMerged.find((r) => r.company_id === 'c2').qty, '250.0');

  const siteMerged = pres.mergeCoatResultRows([
    mkRow({ scope: 'site', company_id: 'c1', site_id: 's1', site: 'کارگاه ۱', item_key: 'prime_coat', unit: 't', qty: '1.2' }),
    mkRow({ scope: 'site', company_id: 'c1', site_id: 's1', site: 'کارگاه ۱', item_key: 'tack_coat', unit: 'kg', qty: '300' }),
  ], coatUnit, coatDecimals);
  assert.equal(siteMerged.length, 1);
  assert.equal(siteMerged[0].qty, '1500');
  assert.equal(siteMerged[0].unit, 'kg');
});

test('presentation summary groups catalog into 4 departments and scales typography relative to widest number', () => {
  const mkItem = (key, title_fa, output_unit = 'm3') => ({
    key, title_fa, description_fa: '', dimension: 'volume', output_unit, decimals: 2, is_rollup: false, rollup_of: [], mining_only: false,
  });
  const catalog13 = [
    mkItem('excavation', 'خاکبرداری'),
    mkItem('fill', 'خاکریزی'),
    mkItem('subbase', 'زیراساس'),
    mkItem('base', 'اساس'),
    mkItem('asphalt_total', 'آسفالت (جمع)', 't'),
    mkItem('concrete', 'بتن'),
    mkItem('rebar', 'آرماتور', 't'),
    mkItem('formwork', 'قالب', 'm2'),
    mkItem('prime_tack_total', 'پریمکت و تک‌کت', 'kg'),
    mkItem('precast', 'بتن پیش‌ساخته'),
    mkItem('pile_drilling', 'حفاری شمع', 'm'),
    mkItem('pipe_laying', 'لوله‌گذاری', 'm'),
    mkItem('mining_load', 'بارگیری ماده معدنی و باطله'),
    mkItem('custom_extra', 'عملیات ویژه', 'm3'),
  ];
  const groups = pres.groupSummaryDepartments(catalog13);
  assert.equal(groups.length, 4);
  assert.deepEqual(groups.map((g) => g.id), ['earthwork', 'asphalt', 'concrete', 'infrastructure']);
  assert.deepEqual(groups[0].items.map((i) => i.key), ['excavation', 'fill', 'subbase', 'base']);
  assert.deepEqual(groups[1].items.map((i) => i.key), ['asphalt_total', 'prime_tack_total']);
  assert.deepEqual(groups[2].items.map((i) => i.key), ['concrete', 'rebar', 'formwork', 'precast']);
  assert.deepEqual(groups[3].items.map((i) => i.key), ['mining_load', 'pipe_laying', 'pile_drilling', 'custom_extra']);

  const smallMap = new Map([['excavation', { scope: 'holding', company_id: null, company: null, site_id: null, site: null, item_key: 'excavation', item: '', decimals: 2, sort: 1, qty: '450.00', unit: 'm3', n_lines: 1, has_unconfirmed: false }]]);
  const hugeMap = new Map([['excavation', { scope: 'holding', company_id: null, company: null, site_id: null, site: null, item_key: 'excavation', item: '', decimals: 2, sort: 1, qty: '1234567890.12', unit: 'm3', n_lines: 1, has_unconfirmed: false }]]);

  const smallTypo = pres.estimateSummaryTypography(groups, smallMap);
  const hugeTypo = pres.estimateSummaryTypography(groups, hugeMap);
  assert.ok(smallTypo.numberFontPx > hugeTypo.numberFontPx, `expected small numbers (${smallTypo.numberFontPx}px) to render larger than huge numbers (${hugeTypo.numberFontPx}px)`);
  assert.ok(smallTypo.numberFontPx >= 50);
  assert.ok(hugeTypo.numberFontPx >= 26);
});

test('presentation rounds quantities to whole integers with no decimal separator and sizes scorecard tables dynamically', () => {
  assert.equal(pres.formatPresentationQuantity('145230.50'), '۱۴۵٬۲۳۱');
  assert.equal(pres.formatPresentationQuantity('185.642'), '۱۸۶');
  assert.equal(pres.formatPresentationQuantity('22551.0'), '۲۲٬۵۵۱');
  assert.equal(pres.formatPresentationQuantity('0.4'), '۰');
  assert.equal(pres.formatPresentationQuantity(null), '—');
  assert.ok(!pres.formatPresentationQuantity('145230.50').includes('٫'));

  const metricTitles = ['خاکبرداری', 'خاکریزی', 'زیراساس', 'اساس', 'آسفالت', 'بتن', 'آرماتور', 'قالب', 'پریمکت و تک‌کت', 'بتن پیش‌ساخته', 'لوله‌گذاری', 'بارگیری ماده معدنی و باطله'];
  const metricUnits = ['مترمکعب', 'مترمکعب', 'مترمکعب', 'مترمکعب', 'تن', 'مترمکعب', 'تن', 'مترمربع', 'کیلوگرم', 'مترمکعب', 'متر', 'مترمکعب'];

  const compactCompanies = pres.estimateScorecardTypography({
    metricTitles,
    metricUnits,
    entityNames: ['آبادگران رفاه نصر', 'فراگیر عمران نصر', 'گلومک سازه نصر', 'محور گستر نصر'],
    entityType: 'company',
    rowCount: 4,
    showTotal: true,
    hasSubtitles: false,
    hasPlanned: false,
    maxFormattedValue: '۳۲۰٬۵۰۰',
  });
  assert.equal(compactCompanies.tableHeightPx, pres.SUMMARY_CANVAS_H);
  assert.ok(compactCompanies.rowHeightPx >= 110);
  assert.ok(compactCompanies.cellValuePx >= 20);
  assert.ok(compactCompanies.headerTitlePx >= 15);
  assert.ok(compactCompanies.logoSizePx >= 40);

  const densePlannedProjects = pres.estimateScorecardTypography({
    metricTitles,
    metricUnits,
    entityNames: Array.from({ length: 10 }, (_, i) => `پروژه شماره ${i + 1}`),
    entityType: 'project',
    rowCount: 10,
    showTotal: true,
    hasSubtitles: true,
    hasPlanned: true,
    maxFormattedValue: '۳۲۰٬۵۰۰',
  });
  assert.equal(densePlannedProjects.tableHeightPx, pres.SUMMARY_CANVAS_H);
  assert.ok(densePlannedProjects.rowHeightPx < compactCompanies.rowHeightPx);
  assert.ok(densePlannedProjects.cellValuePx >= 14);
  assert.ok(densePlannedProjects.entityNamePx >= 14);
});

test('presentation share pages balance cards evenly and compute large filled pie charts with inside percentages', () => {
  const twelve = Array.from({ length: 12 }, (_, i) => i);
  const pages12 = pres.splitSharePages(twelve, 8);
  assert.deepEqual(pages12.map((p) => p.length), [6, 6]);
  assert.deepEqual(pres.splitSharePages(twelve.slice(0, 8), 8).map((p) => p.length), [8]);
  assert.deepEqual(pres.splitSharePages([...twelve, 12], 8).map((p) => p.length), [7, 6]);

  const geo6 = pres.estimateShareCardGeometry(6);
  assert.equal(geo6.cols, 3);
  assert.equal(geo6.rows, 2);
  assert.ok(geo6.pieSizePx >= 250, `expected large pie (>=250px) in 3x2 grid, got ${geo6.pieSizePx}`);

  const geo4 = pres.estimateShareCardGeometry(4);
  assert.equal(geo4.cols, 2);
  assert.equal(geo4.rows, 2);
  assert.ok(geo4.pieSizePx >= 250);

  const single = pres.computePieSlices([{ companyId: 'c1', companyName: 'محور گستر نصر', pct: 100, color: '#252850' }], 260);
  assert.equal(single.length, 1);
  assert.equal(single[0].isFullCircle, true);
  assert.equal(single[0].labelText, '۱۰۰٪');
  assert.equal(single[0].labelX, 130);
  assert.equal(single[0].labelY, 130);
  assert.equal(single[0].isOutside, false);

  const multi = pres.computePieSlices([
    { companyId: 'c1', companyName: 'الف', pct: 55, color: '#d97706' },
    { companyId: 'c2', companyName: 'ب', pct: 45, color: '#252850' },
  ], 260);
  assert.equal(multi.length, 2);
  assert.equal(multi[0].isFullCircle, false);
  assert.match(multi[0].pathD, /^M /);
  assert.equal(multi[0].labelText, '۵۵٪');
  assert.equal(multi[1].labelText, '۴۵٪');
  assert.equal(multi[0].isOutside, false);

  const staggeredTiny = pres.computePieSlices([
    { companyId: 'c1', companyName: 'الف', pct: 88, color: '#252850' },
    { companyId: 'c2', companyName: 'ب', pct: 5, color: '#d97706' },
    { companyId: 'c3', companyName: 'ج', pct: 5, color: '#059669' },
    { companyId: 'c4', companyName: 'د', pct: 2, color: '#7c3aed' },
  ], 260);
  const dist23 = Math.hypot(staggeredTiny[1].labelX - staggeredTiny[2].labelX, staggeredTiny[1].labelY - staggeredTiny[2].labelY);
  assert.ok(dist23 >= 16, `adjacent narrow slices should stagger radially (dist=${dist23})`);
  assert.equal(staggeredTiny[3].isOutside, true);
  assert.ok(staggeredTiny[3].labelX >= 0 && staggeredTiny[3].labelX <= 260);
  assert.ok(staggeredTiny[3].labelY >= 0 && staggeredTiny[3].labelY <= 260);
});

test('presentation exposes all 6 summary layout variants and computes hole-free grids and infographic splits', () => {
  assert.equal(pres.SUMMARY_VARIANTS.length, 6);
  assert.deepEqual(
    pres.SUMMARY_VARIANTS.map((v) => v.id),
    ['departments', 'hero_bento', 'infographic', 'split_rows', 'aligned_split', 'classic'],
  );
  assert.equal(pres.DEFAULT_SUMMARY_VARIANT, 'departments');
  assert.equal(pres.isSummaryVariant('aligned_split'), true);
  assert.equal(pres.isSummaryVariant('unknown'), false);

  const mkItem = (key, title_fa, output_unit = 'm3') => ({
    key, title_fa, description_fa: '', dimension: 'volume', output_unit, decimals: 2, is_rollup: false, rollup_of: [], mining_only: false,
  });
  const mkRow = (item_key, qty, company_id = null, scope = 'holding') => ({
    scope, company_id, company: company_id ? `Company ${company_id}` : null, site_id: null, site: null,
    item_key, item: '', decimals: 2, sort: 1, qty, unit: 'm3', n_lines: 1, has_unconfirmed: false,
  });

  const items13 = [
    mkItem('excavation', 'خاکبرداری', 'm3'),
    mkItem('fill', 'خاکریزی', 'm3'),
    mkItem('subbase', 'زیراساس', 'm3'),
    mkItem('base', 'اساس', 'm3'),
    mkItem('asphalt_total', 'آسفالت (جمع)', 't'),
    mkItem('prime_tack_total', 'پریمکت و تک‌کت', 'kg'),
    mkItem('concrete', 'بتن', 'm3'),
    mkItem('rebar', 'آرماتور', 't'),
    mkItem('formwork', 'قالب', 'm2'),
    mkItem('precast', 'بتن پیش‌ساخته', 'm3'),
    mkItem('mining_load', 'بارگیری معدن', 'm3'),
    mkItem('pipe_laying', 'لوله‌گذاری', 'm'),
    mkItem('pile_drilling', 'حفاری شمع', 'm'),
  ];

  // Classic balanced rows: 13 -> [4, 3, 3, 3]
  const classicRows = pres.splitSummaryRows(items13, 4);
  assert.deepEqual(classicRows.map((r) => r.length), [4, 3, 3, 3]);

  // 11 active + 2 inactive -> 4x3 = 12 slots (1 colSpan=2 wide hero + 10 single = 12)
  const map11 = new Map([
    ['excavation', mkRow('excavation', '150000')],
    ['fill', mkRow('fill', '90000')],
    ['subbase', mkRow('subbase', '42000')],
    ['base', mkRow('base', '31000')],
    ['asphalt_total', mkRow('asphalt_total', '18500')],
    ['prime_tack_total', mkRow('prime_tack_total', '22500')],
    ['concrete', mkRow('concrete', '14200')],
    ['rebar', mkRow('rebar', '410')],
    ['formwork', mkRow('formwork', '9800')],
    ['mining_load', mkRow('mining_load', '84000')],
    ['pipe_laying', mkRow('pipe_laying', '186')],
  ]);

  const classicTypo = pres.estimateClassicSummaryTypography(classicRows, map11);
  assert.ok(classicTypo.numberFontPx >= 36 && classicTypo.numberFontPx <= 70);

  const bento11 = pres.planSymmetricBentoGrid(items13, map11);
  assert.equal(bento11.cols, 4);
  assert.equal(bento11.rows, 3);
  assert.equal(bento11.cells.reduce((acc, c) => acc + c.colSpan, 0), 12);
  assert.equal(bento11.inactiveItems.length, 2);
  assert.equal(bento11.cells.filter((c) => c.isHero).length, 3);

  // 12 active + 1 inactive -> 4x3 = 12 exact cells
  const map12 = new Map(map11);
  map12.set('precast', mkRow('precast', '320'));
  const bento12 = pres.planSymmetricBentoGrid(items13, map12);
  assert.equal(bento12.cols, 4);
  assert.equal(bento12.rows, 3);
  assert.equal(bento12.cells.reduce((acc, c) => acc + c.colSpan, 0), 12);
  assert.equal(bento12.cells.filter((c) => c.colSpan === 2).length, 0);

  // Infographic splits m3 sorted desc and non-m3 metrics with true share percentages
  const mapTiny = new Map(map11);
  mapTiny.set('precast', mkRow('precast', '400'));
  const info = pres.splitInfographicItems(items13, mapTiny);
  assert.equal(info.m3Items[0].item.key, 'excavation');
  assert.equal(info.m3Items[0].barPct, 100);
  const smallest = info.m3Items[info.m3Items.length - 1];
  assert.equal(smallest.barPct, 4);
  assert.equal(smallest.sharePctLabel, 'زیر ۱٪');
  assert.ok(info.m3Items.every((x) => x.item.output_unit === 'm3'));
  assert.ok(info.otherItems.every((x) => x.item.output_unit !== 'm3'));
  assert.equal(info.inactiveItems.length, 1);
  assert.equal(pres.getSummaryDepartmentTitle('asphalt_total'), 'آسفالت و قیرپاشی');

  // Executive 2-column split counts real participating companies & planned attainment
  const companyRows = [
    mkRow('excavation', '100000', 'c1', 'company'),
    mkRow('excavation', '50000', 'c2', 'company'),
    mkRow('excavation', '0', 'c3', 'company'),
    mkRow('asphalt_total', '18500', 'c1', 'company'),
  ];
  const plannedMap = new Map([['excavation', mkRow('excavation', '120000')]]);
  const splitPlan = pres.buildExecutiveSplitColumns(items13, map11, plannedMap, companyRows);
  assert.deepEqual(splitPlan.columns.map((c) => c.length), [6, 5]);
  assert.equal(splitPlan.inactiveItems.length, 2);
  const excRow = splitPlan.columns[0].find((r) => r.item.key === 'excavation');
  assert.equal(excRow.activeCompanyCount, 2);
  assert.equal(excRow.planPct, 125);
});

test('presentation overview semi-circular radar distributes companies symmetrically below center mother card', () => {
  assert.equal(pres.getCompanyColor('محور گستر نصر'), '#252850');
  assert.equal(pres.matchCompanyLogo('آبادگران رفاه نصر')?.src, '/volume-reports/logo_abadgaran.png');

  assert.equal(pres.isExcludedFromOverviewRing('شرکت محور گستر نصر'), true);
  assert.equal(pres.isExcludedFromOverviewRing('محور\u200cگستر نصر'), true);
  assert.equal(pres.isExcludedFromOverviewRing('شرکت جهاد نصر کرمان'), true);
  assert.equal(pres.isExcludedFromOverviewRing('جهاد نصر کرمان'), true);
  assert.equal(pres.isExcludedFromOverviewRing('jihad_nasr_kerman'), true);
  assert.equal(pres.isExcludedFromOverviewRing('جهاد نصر سیستان'), false);
  assert.equal(pres.isExcludedFromOverviewRing('آبادگران رفاه نصر'), false);

  const builtOverview = pres.buildOverviewWheelCompanies(
    [
      { id: 'm', name: 'محور گستر نصر', projectCount: 2 },
      { id: 'a', name: 'آبادگران', projectCount: 6 },
      { id: 'f', name: 'فراگیر', projectCount: 2 },
      { id: 'g', name: 'گلومک سازه', projectCount: 6 },
      { id: 's', name: 'جهاد نصر سیستان و بلوچستان', projectCount: 2 },
    ],
    [{ id: 't-db', name: 'تژه', is_active: true }],
  );
  assert.equal(builtOverview.length, 5);
  assert.equal(builtOverview.some((c) => c.name === 'تژه' && c.projectCount === 0 && c.id === 't-db'), true);
  assert.equal(builtOverview.some((c) => c.name.includes('محور')), false);

  const builtFallbackTezhe = pres.buildOverviewWheelCompanies([
    { id: 'a', name: 'آبادگران', projectCount: 1 },
  ]);
  assert.equal(builtFallbackTezhe.length, 2);
  assert.equal(builtFallbackTezhe.some((c) => c.name === 'تژه نصر' && c.projectCount === 0), true);

  const emptyRadar = pres.computeOverviewRadarLayout([]);
  assert.equal(emptyRadar.nodes.length, 0);
  assert.ok(emptyRadar.primaryArcPath.startsWith('M '));

  const singleRadar = pres.computeOverviewRadarLayout([
    { id: 'c1', name: 'آبادگران رفاه نصر', color: '#d97706', projectCount: 2, sublabel: '۲ پروژه' },
  ]);
  assert.equal(singleRadar.nodes.length, 1);
  assert.equal(singleRadar.nodes[0].angleDeg, 90);
  assert.ok(Math.abs(singleRadar.nodes[0].x - singleRadar.cx) < 0.01);

  const radar5 = pres.computeOverviewRadarLayout([
    { id: '1', name: 'آبادگران رفاه نصر', color: '#d97706', projectCount: 6, sublabel: '۶ پروژه' },
    { id: '2', name: 'تژه نصر', color: '#e11d48', projectCount: 0, sublabel: 'عضو هلدینگ' },
    { id: '3', name: 'جهاد نصر سیستان و بلوچستان', color: '#0284c7', projectCount: 2, sublabel: '۲ پروژه' },
    { id: '4', name: 'فراگیر عمران نصر', color: '#059669', projectCount: 2, sublabel: '۲ پروژه' },
    { id: '5', name: 'گلومک سازه', color: '#7c3aed', projectCount: 6, sublabel: '۶ پروژه' },
  ]);
  assert.equal(radar5.nodes.length, 5);
  assert.deepEqual(radar5.nodes.map((n) => n.angleDeg), [160, 125, 90, 55, 20]);
  assert.ok(Math.abs(radar5.nodes[2].x - radar5.cx) < 0.01);
  assert.ok(Math.abs((radar5.nodes[0].x - radar5.cx) + (radar5.nodes[4].x - radar5.cx)) < 0.05);
  assert.ok(Math.abs(radar5.nodes[0].y - radar5.nodes[4].y) < 0.05);
  assert.ok(radar5.nodes.every((n) => n.spokeX1 === radar5.cx && n.spokeY1 < n.y));
  assert.ok(radar5.nodes.every((n) => n.y > radar5.originY));
  assert.ok(radar5.nodes[2].y > radar5.nodes[0].y);

  const radar6 = pres.computeOverviewRadarLayout([
    { id: '1', name: 'ش۱', color: '#d97706', projectCount: 1, sublabel: '۱ پروژه' },
    { id: '2', name: 'ش۲', color: '#e11d48', projectCount: 0, sublabel: 'عضو هلدینگ' },
    { id: '3', name: 'ش۳', color: '#0284c7', projectCount: 2, sublabel: '۲ پروژه' },
    { id: '4', name: 'ش۴', color: '#059669', projectCount: 2, sublabel: '۲ پروژه' },
    { id: '5', name: 'ش۵', color: '#7c3aed', projectCount: 1, sublabel: '۱ پروژه' },
    { id: '6', name: 'ش۶', color: '#252850', projectCount: 3, sublabel: '۳ پروژه' },
  ]);
  assert.equal(radar6.nodes.length, 6);
  assert.ok(radar6.nodes[0].cardW < radar5.nodes[0].cardW);

  const radar10 = pres.computeOverviewRadarLayout(
    Array.from({ length: 10 }, (_, idx) => ({ id: String(idx), name: `شرکت ${idx + 1}`, color: '#252850', projectCount: 1, sublabel: '۱ پروژه' })),
  );
  assert.equal(radar10.nodes.length, 10);
  assert.ok(radar10.nodes[0].logoSizePx < radar6.nodes[0].logoSizePx);
});

test('Jalali weekday and company scorecard period note format Wed-Tue and arbitrary ranges without timezone shift', () => {
  // Wed 2026-11-04 (1405/08/13) .. Tue 2026-11-10 (1405/08/19)
  assert.equal(jalali.formatJalaliWeekday('2026-11-01'), 'یکشنبه');
  assert.equal(jalali.formatJalaliWeekday('2026-11-02'), 'دوشنبه');
  assert.equal(jalali.formatJalaliWeekday('2026-11-03'), 'سه‌شنبه');
  assert.equal(jalali.formatJalaliWeekday('2026-11-04'), 'چهارشنبه');
  assert.equal(jalali.formatJalaliWeekday('2026-11-05'), 'پنج‌شنبه');
  assert.equal(jalali.formatJalaliWeekday('2026-11-06'), 'جمعه');
  assert.equal(jalali.formatJalaliWeekday('2026-11-07'), 'شنبه');
  assert.equal(jalali.formatJalaliWeekday('2026-02-31'), '');
  assert.equal(jalali.formatJalaliWeekday(null), '');
  assert.equal(jalali.formatJalaliDateWithWeekday('2026-11-04'), 'چهارشنبه ۱۴۰۵/۰۸/۱۳');
  assert.equal(jalali.formatJalaliDateWithWeekday('2026-11-10'), 'سه‌شنبه ۱۴۰۵/۰۸/۱۹');
  assert.equal(
    pres.formatCompanyScorecardPeriodNote('2026-11-04', '2026-11-10'),
    'گزارش هفتگی هلدینگ عمرانی از تاریخ چهارشنبه ۱۴۰۵/۰۸/۱۳ تا تاریخ سه‌شنبه ۱۴۰۵/۰۸/۱۹',
  );
  assert.equal(
    pres.formatCompanyScorecardPeriodNote('2026-10-24', '2026-10-30'),
    'گزارش هفتگی هلدینگ عمرانی از تاریخ شنبه ۱۴۰۵/۰۸/۰۲ تا تاریخ جمعه ۱۴۰۵/۰۸/۰۸',
  );
  assert.equal(pres.formatCompanyScorecardPeriodNote(null, null), null);
});

test('wizard helpers group folders, build file payloads, and seed resumed/appended report files', () => {
  const wizard = load('features/volume-reports/lib/wizard.ts', {
    '@/features/volume-reports/lib/jalali': jalali,
  });
  const companies = [
    { id: 'c1', name: 'شرکت گلومک سازه' },
    { id: 'c2', name: 'آبادگران رفاه' },
  ];
  const folders = [
    { id: 'f1', parent_id: null, name: 'گلومک سازه', created_at: '2026-01-01' },
    { id: 'f2', parent_id: 'f1', name: 'هفتگی', created_at: '2026-01-01' },
  ];
  const docs = [
    { id: 'd1', filename: 'root.xlsx', content_type: 'x', status: 'ready', error_message: null, project_id: 'p1', conversation_id: null, folder_id: null, uploaded_by: null, created_at: '' },
    { id: 'd2', filename: 'late.pdf', content_type: 'x', status: 'ready', error_message: null, project_id: 'p1', conversation_id: null, folder_id: 'f2', uploaded_by: null, created_at: '' },
  ];
  const groups = wizard.buildFolderGroups(docs, folders, companies);
  assert.equal(groups.length, 2);
  assert.equal(groups[0].id, '__root__');
  assert.equal(groups[1].path, 'گلومک سازه / هفتگی');
  assert.equal(groups[1].suggestedCompanyId, 'c1');

  const filtered = wizard.filterFolderGroups(groups, 'late', true, { d2: 'c1' });
  assert.equal(filtered.length, 1);
  assert.deepEqual(filtered[0].docs.map((d) => d.id), ['d2']);

  const seeded = wizard.seedSelectionFromReportFiles([
    { id: 'rf1', document_id: 'd1', filename: 'root.xlsx', company_id: 'c2', status: 'parsed', error_message: null, kind: 'period' },
    { id: 'rf2', document_id: 'd2', filename: 'late.pdf', company_id: 'c1', status: 'pending', error_message: null, kind: 'monthly_plan', plan_month: 8 },
    { id: 'rf3', document_id: 'd3', filename: 'pv.xlsx', company_id: 'c1', status: 'pending', error_message: null, kind: 'monthly_pv', plan_month: 0 },
  ]);
  assert.deepEqual(seeded.selection, { d1: 'c2', d2: 'c1', d3: 'c1' });
  assert.deepEqual(seeded.monthly, { d2: { kind: 'monthly_plan', month: 8 }, d3: { kind: 'monthly_pv', month: 0 } });

  const payload = wizard.selectionToPayload(seeded.selection, seeded.monthly);
  assert.deepEqual(payload, [
    { document_id: 'd1', company_id: 'c2' },
    { document_id: 'd2', company_id: 'c1', kind: 'monthly_plan', plan_month: 8 },
    { document_id: 'd3', company_id: 'c1', kind: 'monthly_pv' },
  ]);

  assert.equal(status.GATE_LABELS.pending_files, 'فایل در انتظار پردازش');
  assert.ok(status.GATE_HINTS.pending_files.includes('اجرای دور جدید'));
});

test('manual PV input: billions typed in Persian or Latin digits become exact rial strings, blank means no value', () => {
  assert.equal(fmt.billionInputToRial('257.7'), '257700000000');
  assert.equal(fmt.billionInputToRial('۲۵۷٫۷۳'), '257730000000');
  assert.equal(fmt.billionInputToRial('1,104.392021869'), '1104392021869');
  assert.equal(fmt.billionInputToRial('  '), null);
  assert.equal(fmt.billionInputToRial('abc'), undefined);
  assert.equal(fmt.billionInputToRial('-5'), undefined);
  assert.equal(fmt.billionInputToRial('1.2345678901'), undefined); // more than 9 decimals = sub-rial precision
  assert.equal(fmt.rialToBillionInput('257730000000'), '257.73');
  assert.equal(fmt.rialToBillionInput('1104392021869.88'), '1104.39');
  assert.equal(fmt.rialToBillionInput(null), '');
});
