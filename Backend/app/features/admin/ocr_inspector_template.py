"""Interactive Visual OCR Inspector Dashboard Template."""

OCR_INSPECTOR_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>سامانه بازرسی و تحلیل دیداری OCR و RAG | Orbit Corp</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --table-color: #ef4444;
      --header-color: #3b82f6;
      --text-color: #22c55e;
      --footer-color: #f97316;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, "Segoe UI", Roboto, Tahoma, sans-serif; }
    body { background-color: var(--bg); color: var(--text); padding: 1.5rem; line-height: 1.5; }
    .container { max-width: 1600px; margin: 0 auto; }
    header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 1.5rem; }
    h1 { font-size: 1.5rem; display: flex; align-items: center; gap: 0.5rem; }
    .badge { font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 9999px; background: rgba(59, 130, 246, 0.2); color: var(--primary); font-weight: bold; }
    
    .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border); }
    .tab-btn { background: none; border: none; padding: 0.6rem 1.2rem; color: var(--text-muted); cursor: pointer; font-size: 0.95rem; border-bottom: 2px solid transparent; }
    .tab-btn.active { color: var(--primary); border-bottom-color: var(--primary); font-weight: bold; }

    .controls-bar { background: var(--card-bg); border: 1px solid var(--border); padding: 1rem; border-radius: 0.5rem; display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; margin-bottom: 1.5rem; }
    select, button { background: #0f172a; color: var(--text); border: 1px solid var(--border); padding: 0.5rem 1rem; border-radius: 0.375rem; font-size: 0.9rem; }
    button.refresh-btn { background: var(--primary); border-color: var(--primary); cursor: pointer; color: #fff; font-weight: bold; }
    button.refresh-btn:hover { background: var(--primary-hover); }

    .kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
    .kpi-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 0.5rem; padding: 1rem; }
    .kpi-title { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.25rem; }
    .kpi-val { font-size: 1.3rem; font-weight: bold; color: #fff; }

    .main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
    @media (max-width: 1024px) { .main-grid { grid-template-columns: 1fr; } }

    .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 0.5rem; padding: 1rem; }
    .card-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; }

    .image-viewer { text-align: center; background: #090d16; border-radius: 0.375rem; padding: 0.5rem; overflow: auto; max-height: 800px; border: 1px solid var(--border); }
    .image-viewer img { max-width: 100%; height: auto; border-radius: 0.25rem; }

    .legend { display: flex; gap: 1rem; margin-top: 0.75rem; font-size: 0.85rem; flex-wrap: wrap; }
    .legend-item { display: flex; align-items: center; gap: 0.35rem; }
    .dot { width: 12px; height: 12px; border-radius: 3px; }

    .blocks-list { display: flex; flex-direction: column; gap: 1rem; max-height: 800px; overflow-y: auto; padding-right: 0.25rem; }
    .block-card { background: #0f172a; border: 1px solid var(--border); border-radius: 0.375rem; padding: 0.75rem; border-right: 4px solid var(--border); }
    .block-card.table { border-right-color: var(--table-color); }
    .block-card.header { border-right-color: var(--header-color); }
    .block-card.text, .block-card.paragraph { border-right-color: var(--text-color); }
    .block-card.footer { border-right-color: var(--footer-color); }

    .block-header { display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; margin-bottom: 0.5rem; }
    .block-badge { padding: 0.15rem 0.5rem; border-radius: 4px; font-weight: bold; font-size: 0.75rem; color: #fff; }
    .block-badge.table { background: var(--table-color); }
    .block-badge.header { background: var(--header-color); }
    .block-badge.text, .block-badge.paragraph { background: var(--text-color); }
    .block-badge.footer { background: var(--footer-color); }

    .block-body { display: grid; grid-template-columns: 140px 1fr; gap: 0.75rem; align-items: start; }
    @media (max-width: 600px) { .block-body { grid-template-columns: 1fr; } }
    .crop-thumb { border: 1px solid var(--border); border-radius: 4px; overflow: hidden; background: #000; cursor: pointer; }
    .crop-thumb img { width: 100%; display: block; object-fit: contain; }

    .block-text { background: #131d2e; border: 1px solid #1e293b; border-radius: 4px; padding: 0.5rem; font-family: monospace; font-size: 0.8rem; white-space: pre-wrap; word-break: break-word; color: #e2e8f0; max-height: 180px; overflow-y: auto; }

    .final-text-card { margin-top: 1.5rem; }
    .code-box { background: #090d16; border: 1px solid var(--border); border-radius: 0.375rem; padding: 1rem; font-family: monospace; font-size: 0.85rem; white-space: pre-wrap; max-height: 400px; overflow-y: auto; }

    .log-snippet { background: #090d16; border: 1px solid var(--border); border-radius: 0.375rem; padding: 1rem; font-family: monospace; font-size: 0.85rem; color: #38bdf8; margin-top: 1rem; line-height: 1.6; }
    .help-section { line-height: 1.8; color: #cbd5e1; font-size: 0.95rem; }
    .help-section h3 { color: #fff; margin: 1rem 0 0.5rem 0; }
    .help-section code { background: #1e293b; color: #38bdf8; padding: 0.15rem 0.4rem; border-radius: 4px; font-family: monospace; }
  </style>
</head>
<body>

<div class="container">
  <header>
    <div>
      <h1>🔍 سامانه بازرسی دیداری OCR و RAG <span class="badge">Orbit Inspector</span></h1>
      <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.2rem;">بررسی خط‌به‌خط کادربندی Bounding Boxها، تصاویر کراپ‌شده و ردیابی تصمیمات هوش مصنوعی</p>
    </div>
    <div>
      <a href="/db-admin" style="color: var(--primary); text-decoration: none; font-size: 0.9rem;">بازگشت به پنل اصلی دیتابیس ↗</a>
    </div>
  </header>

  <div class="tabs">
    <button class="tab-btn active" onclick="switchTab('docs-tab')">📄 بازرسی متنی اسناد و صفحات</button>
    <button class="tab-btn" onclick="switchTab('ocr-tab')">🖼️ بازرسی دیداری OCR و برش‌ها</button>
    <button class="tab-btn" onclick="switchTab('agent-tab')">🤖 راهنمای لاگ‌های زنده Agent و RAG</button>
  </div>

  <!-- TAB 0: DOCUMENTS & PAGES INSPECTOR -->
  <div id="docs-tab">
    <div class="controls-bar">
      <div style="flex: 1; min-width: 250px;">
        <label style="font-size: 0.85rem; color: var(--text-muted); margin-left: 0.5rem;">انتخاب سند:</label>
        <select id="doc-inspect-select" onchange="onInspectDocSelected()" style="width: 100%;">
          <option value="">در حال دریافت لیست اسناد پایگاه دانش...</option>
        </select>
      </div>

      <div>
        <label style="font-size: 0.85rem; color: var(--text-muted); margin-left: 0.5rem;">صفحه:</label>
        <div style="display: inline-flex; align-items: center; gap: 0.25rem;">
          <button onclick="prevInspectPage()" style="padding: 0.4rem 0.7rem; cursor: pointer;">◀ قبلی</button>
          <select id="doc-inspect-page-select" onchange="onInspectPageSelected()" disabled style="min-width: 90px;">
            <option value="1">صفحه ۱</option>
          </select>
          <button onclick="nextInspectPage()" style="padding: 0.4rem 0.7rem; cursor: pointer;">بعدی ▶</button>
        </div>
      </div>

      <button class="refresh-btn" onclick="loadInspectDocsList()">بروزرسانی اسناد 🔄</button>
      <button onclick="purgeDocOcrCache()" style="background: #475569; border-color: #334155; color: #fff; cursor: pointer; font-weight: bold;" title="حذف تمام کش‌های OCR ثبت‌شده برای این سند">🗑️ حذف کش OCR این سند</button>
      <button onclick="reprocessCurrentDoc()" style="background: #e11d48; border-color: #be123c; color: #fff; cursor: pointer; font-weight: bold;">پردازش مجدد با OCR اجباری ⚡</button>
      <button onclick="reprocessFreshDoc()" style="background: #7c3aed; border-color: #6d28d9; color: #fff; cursor: pointer; font-weight: bold;" title="ابتدا کش OCR این سند را پاک کرده و سپس پردازش تازه انجام می‌دهد">⚡ پردازش مجدد بدون کش (Fresh OCR)</button>
    </div>

    <div id="docs-loading-state" style="display: none; padding: 2rem; text-align: center; color: var(--text-muted);">
      در حال فراخوانی محتوای صفحات سند...
    </div>

    <div id="docs-empty-state" style="display: none; padding: 3rem; text-align: center; background: var(--card-bg); border-radius: 0.5rem; border: 1px solid var(--border);">
      <h3 style="color: #fff; margin-bottom: 0.5rem;">هیچ سندی در سیستم یافت نشد</h3>
      <p style="color: var(--text-muted); font-size: 0.9rem;">
        برای بررسی، ابتدا از طریق محیط چت یا مدیریت فایل‌ها سندی را آپلود کنید.
      </p>
    </div>

    <div id="docs-content-view" style="display: none;">
      <!-- KPIs -->
      <div class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-title">پروژه / حوزه سند</div>
          <div class="kpi-val" id="docs-kpi-project" style="font-size: 1.05rem;">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">وضعیت سند و چانک‌ها</div>
          <div class="kpi-val" id="docs-kpi-status">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">تعداد کل صفحات</div>
          <div class="kpi-val" id="docs-kpi-pages">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">تعداد کش OCR این سند</div>
          <div class="kpi-val" id="docs-kpi-cache" style="color: #a855f7;">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">وضعیت لایه متنی این صفحه</div>
          <div class="kpi-val" id="docs-kpi-layer" style="font-size: 1.05rem; color: #22c55e;">-</div>
        </div>
      </div>

      <!-- MAIN SPLIT: Image Left, Extracted Text Right -->
      <div class="main-grid">
        <!-- LEFT: Rendered Page Image -->
        <div class="card">
          <div class="card-title">
            <span>تصویر رندرشده صفحه <span id="doc-img-page-num" class="badge">صفحه ۱</span></span>
            <span style="font-size: 0.8rem; color: var(--text-muted);">رندر مستقیم از فایل</span>
          </div>

          <div class="image-viewer" style="min-height: 450px; display: flex; align-items: center; justify-content: center;">
            <img id="docs-page-img" src="" alt="تصویر صفحه" style="max-height: 750px; display: none;" onload="this.style.display='block'; document.getElementById('docs-img-placeholder').style.display='none';" onerror="this.style.display='none'; document.getElementById('docs-img-placeholder').style.display='block';">
            <div id="docs-img-placeholder" style="color: var(--text-muted); font-size: 0.9rem;">در حال بارگذاری یا عدم وجود تصویر برای این صفحه...</div>
          </div>
        </div>

        <!-- RIGHT: Extracted Text for this page -->
        <div class="card">
          <div class="card-title">
            <span>متن استخراج‌شده صفحه (ذخیره‌شده در RAG)</span>
            <div style="display: flex; gap: 0.5rem; align-items: center;">
              <span id="doc-text-length" class="badge" style="background: rgba(34, 197, 94, 0.2); color: #22c55e;">۰ کاراکتر</span>
              <button onclick="copyCurrentPageText()" style="font-size: 0.8rem; cursor: pointer;">کپی متن 📋</button>
            </div>
          </div>

          <div class="code-box" id="docs-page-text" style="height: 750px; max-height: 750px; line-height: 1.8; font-size: 0.9rem; direction: rtl; text-align: right;">
            در حال بارگذاری...
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- TAB 1: OCR INSPECTOR -->
  <div id="ocr-tab" style="display: none;">
    <div class="controls-bar">
      <div>
        <label style="font-size: 0.85rem; color: var(--text-muted); margin-left: 0.5rem;">انتخاب سند:</label>
        <select id="doc-select" onchange="onDocumentSelected()">
          <option value="">در حال دریافت لیست اسناد...</option>
        </select>
      </div>

      <div>
        <label style="font-size: 0.85rem; color: var(--text-muted); margin-left: 0.5rem;">صفحه:</label>
        <select id="page-select" onchange="onPageSelected()" disabled>
          <option value="1">صفحه ۱</option>
        </select>
      </div>

      <button class="refresh-btn" onclick="loadDocumentsList()">بروزرسانی داده‌ها 🔄</button>
    </div>

    <div id="loading-state" style="display: none; padding: 2rem; text-align: center; color: var(--text-muted);">
      در حال فراخوانی جزئیات سند و تصاویر...
    </div>

    <div id="empty-state" style="display: none; padding: 3rem; text-align: center; background: var(--card-bg); border-radius: 0.5rem; border: 1px solid var(--border);">
      <h3 style="color: #fff; margin-bottom: 0.5rem;">هیچ سندی با لاگ دیباگ یافت نشد</h3>
      <p style="color: var(--text-muted); font-size: 0.9rem;">
        برای فعال شدن بازرسی، یک فایل اسکن یا PDF را آپلود کنید تا مراحل کادربندی میسترال و برش‌های جمنای ذخیره شوند.
      </p>
    </div>

    <div id="content-view" style="display: none;">
      <!-- KPIs -->
      <div class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-title">ابعاد تصویر اصلی</div>
          <div class="kpi-val" id="kpi-dims">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">زمان تحلیل میسترال</div>
          <div class="kpi-val" id="kpi-mistral-time">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">تعداد بلوک‌های برش‌خورده</div>
          <div class="kpi-val" id="kpi-blocks-count">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">زمان کل استخراج جمنای</div>
          <div class="kpi-val" id="kpi-total-time">-</div>
        </div>
      </div>

      <!-- MAIN SPLIT -->
      <div class="main-grid">
        <!-- LEFT: Annotated Image with Bounding Boxes -->
        <div class="card">
          <div class="card-title">
            <span>کادربندی صفحه با Bounding Box</span>
            <span style="font-size: 0.8rem; color: var(--text-muted);" id="annotated-status">وضوح ۳۰۰ DPI</span>
          </div>

          <div class="image-viewer">
            <img id="annotated-img" src="" alt="صفحه کادربندی‌شده">
          </div>

          <div class="legend">
            <div class="legend-item"><div class="dot" style="background: var(--table-color);"></div> <span>جدول داده‌ها (Table)</span></div>
            <div class="legend-item"><div class="dot" style="background: var(--header-color);"></div> <span>سربرگ سند (Header)</span></div>
            <div class="legend-item"><div class="dot" style="background: var(--text-color);"></div> <span>پاراگراف و متن (Text)</span></div>
            <div class="legend-item"><div class="dot" style="background: var(--footer-color);"></div> <span>پاورقی و امضا (Footer)</span></div>
          </div>
        </div>

        <!-- RIGHT: Individual Crops & Gemini Output -->
        <div class="card">
          <div class="card-title">
            <span>برش‌های ارسال‌شده به جمنای و خروجی هر بخش</span>
            <span class="badge" id="blocks-badge">۰ بلوک</span>
          </div>

          <div class="blocks-list" id="blocks-container">
            <!-- Dynamic block cards -->
          </div>
        </div>
      </div>

      <!-- FINAL ASSEMBLED TEXT -->
      <div class="card final-text-card">
        <div class="card-title">
          <span>متن نهایی ادغام‌شده صفحه (ذخیره‌شده در پایگاه دانش RAG)</span>
          <button onclick="copyFinalText()" style="font-size: 0.8rem; cursor: pointer;">کپی متن 📋</button>
        </div>
        <div class="code-box" id="final-text-box">در حال بارگذاری...</div>
      </div>

      <!-- JSON TRACE VIEW -->
      <div class="card final-text-card" style="margin-top: 1.5rem;">
        <div class="card-title">
          <span>📜 لاگ ساخت‌یافته و متادیتای فنی استخراج (JSON Trace)</span>
          <button onclick="copyJsonTrace()" style="font-size: 0.8rem; cursor: pointer;">کپی لاگ JSON 📋</button>
        </div>
        <div class="code-box" id="json-trace-box" style="max-height: 250px; color: #38bdf8;">در حال بارگذاری...</div>
      </div>
    </div>
  </div>

  <!-- TAB 2: AGENT & RAG TRACE GUIDE -->
  <div id="agent-tab" style="display: none;">
    <div class="card help-section">
      <h2 style="color: #fff; margin-bottom: 0.5rem;">راهنمای ردیابی زنده لاگ‌های Agent و RAG</h2>
      <p>
        وقتی کاربری در چت پیامی ارسال می‌کند، برای اینکه ببینید سیستم دقیقاً چه کاری انجام می‌دهد و چه تصمیماتی می‌گیرد، نیازی به حدس زدن نیست. از دستورات زیر روی سرور استفاده کنید:
      </p>

      <h3>۱. مشاهده زنده پردازش اسناد و کادربندی OCR (کانتینر Worker):</h3>
      <div class="log-snippet">
        docker compose logs -f worker
      </div>
      <p style="margin-top: 0.5rem;">
        در این لاگ، مراحل <code>[OCR:START]</code>، تشخیص میسترال <code>[OCR:LAYOUT]</code>، ذخیره کراپ‌ها <code>[OCR:CROP]</code> و خروجی رقم‌به‌رقم جمنای <code>[OCR:VISION]</code> به صورت رنگی و مرتب چاپ می‌شود.
      </p>

      <h3>۲. مشاهده زنده ردیابی پاسخ چت هوش مصنوعی (کانتینر Backend):</h3>
      <div class="log-snippet">
        docker compose logs -f backend
      </div>
      <p style="margin-top: 0.5rem;">
        هنگام ارسال پیام کاربر، مراحل زیر را بلافاصله خواهید دید:
      </p>
      <ul style="padding-right: 1.5rem; margin-top: 0.5rem;">
        <li><code>[AGENT:USER_QUERY]</code>: سوال دقیق کاربر و شناسه گفتگو.</li>
        <li><code>[RAG:SEARCH]</code>: متن جستجو و دامنه‌ی پروژه.</li>
        <li><code>[RAG:RESULTS]</code>: چانک‌های بازیابی‌شده به همراه <b>درصد تشابه (Score)</b> و نام سند و شماره صفحه.</li>
        <li><code>[AGENT:TOOL_CALL]</code>: آیا مدل ابزار <code>read_document_pages</code> را صدا زد؟ یا ابزار <code>view_document_page</code> (دیدن مستقیم عکس با جمنای)؟</li>
        <li><code>[AGENT:TURN_COMPLETE]</code>: مدت زمان کل، تعداد رفرنس‌ها و پاسخ آماده‌شده.</li>
      </ul>
    </div>
  </div>
</div>

<script>
  let currentDocTrace = null;
  const API_BASE = '/api/v1/admin/ocr-debug';
  const DOCS_API_BASE = '/api/v1/admin/documents-inspect';

  let currentInspectDoc = null;
  let currentInspectPageIndex = 0;
  let inspectDocsLoaded = false;

  function switchTab(tabId) {
    document.getElementById('docs-tab').style.display = tabId === 'docs-tab' ? 'block' : 'none';
    document.getElementById('ocr-tab').style.display = tabId === 'ocr-tab' ? 'block' : 'none';
    document.getElementById('agent-tab').style.display = tabId === 'agent-tab' ? 'block' : 'none';
    const btns = document.querySelectorAll('.tab-btn');
    btns[0].classList.toggle('active', tabId === 'docs-tab');
    btns[1].classList.toggle('active', tabId === 'ocr-tab');
    btns[2].classList.toggle('active', tabId === 'agent-tab');

    if (tabId === 'ocr-tab' && !currentDocTrace) {
      loadDocumentsList();
    }
  }

  // --- Document Inspector Methods ---
  async function loadInspectDocsList() {
    const loading = document.getElementById('docs-loading-state');
    loading.style.display = 'block';
    try {
      const resp = await fetch(`${DOCS_API_BASE}/list`);
      if (!resp.ok) throw new Error('خطا در فراخوانی لیست اسناد پایگاه دانش');
      const docs = await resp.json();
      const select = document.getElementById('doc-inspect-select');
      select.innerHTML = '';

      if (!docs || docs.length === 0) {
        document.getElementById('docs-empty-state').style.display = 'block';
        document.getElementById('docs-content-view').style.display = 'none';
        select.innerHTML = '<option value="">هیچ سندی در پایگاه دانش نیست</option>';
        return;
      }

      document.getElementById('docs-empty-state').style.display = 'none';
      docs.forEach((doc) => {
        const opt = document.createElement('option');
        opt.value = doc.id;
        opt.textContent = `${doc.filename} (${doc.project_name || 'بدون پروژه'} - ${doc.status})`;
        select.appendChild(opt);
      });

      inspectDocsLoaded = true;
      await onInspectDocSelected();
    } catch (err) {
      console.error(err);
      alert('خطا در بارگذاری لیست اسناد: ' + err.message);
    } finally {
      loading.style.display = 'none';
    }
  }

  async function onInspectDocSelected() {
    const select = document.getElementById('doc-inspect-select');
    const docId = select.value;
    if (!docId) return;

    const loading = document.getElementById('docs-loading-state');
    const view = document.getElementById('docs-content-view');
    loading.style.display = 'block';
    view.style.display = 'none';

    try {
      const resp = await fetch(`${DOCS_API_BASE}/${docId}`);
      if (!resp.ok) throw new Error('خطا در دریافت جزئیات و صفحات سند');
      currentInspectDoc = await resp.json();

      document.getElementById('docs-kpi-project').textContent = currentInspectDoc.project_name || 'عمومی';
      document.getElementById('docs-kpi-status').textContent = `${currentInspectDoc.status} (${currentInspectDoc.chunk_count} چانک)`;
      document.getElementById('docs-kpi-pages').textContent = `${currentInspectDoc.total_pages} صفحه`;
      document.getElementById('docs-kpi-cache').textContent = `${currentInspectDoc.ocr_cache_count || 0} صفحه`;

      const pageSelect = document.getElementById('doc-inspect-page-select');
      pageSelect.innerHTML = '';

      if (!currentInspectDoc.pages || currentInspectDoc.pages.length === 0) {
        pageSelect.disabled = true;
        pageSelect.innerHTML = '<option value="1">بدون صفحه</option>';
        document.getElementById('docs-page-text').textContent = '(هیچ متنی برای این سند ذخیره نشده است)';
        document.getElementById('doc-text-length').textContent = '۰ کاراکتر';
        document.getElementById('docs-kpi-layer').textContent = 'بدون لایه متنی';
        document.getElementById('docs-page-img').style.display = 'none';
        document.getElementById('docs-img-placeholder').style.display = 'block';
        view.style.display = 'block';
        return;
      }

      pageSelect.disabled = false;
      currentInspectDoc.pages.forEach((p, idx) => {
        const opt = document.createElement('option');
        opt.value = idx;
        opt.textContent = `صفحه ${p.page} (${p.text_len || 0} حرف)`;
        pageSelect.appendChild(opt);
      });

      currentInspectPageIndex = 0;
      pageSelect.value = 0;
      renderInspectPage(0);
      view.style.display = 'block';
    } catch (err) {
      console.error(err);
      alert('خطا در بارگذاری سند: ' + err.message);
    } finally {
      loading.style.display = 'none';
    }
  }

  function onInspectPageSelected() {
    const pageSelect = document.getElementById('doc-inspect-page-select');
    const idx = parseInt(pageSelect.value, 10);
    renderInspectPage(idx);
  }

  function prevInspectPage() {
    if (!currentInspectDoc || !currentInspectDoc.pages) return;
    if (currentInspectPageIndex > 0) {
      currentInspectPageIndex -= 1;
      document.getElementById('doc-inspect-page-select').value = currentInspectPageIndex;
      renderInspectPage(currentInspectPageIndex);
    }
  }

  function nextInspectPage() {
    if (!currentInspectDoc || !currentInspectDoc.pages) return;
    if (currentInspectPageIndex < currentInspectDoc.pages.length - 1) {
      currentInspectPageIndex += 1;
      document.getElementById('doc-inspect-page-select').value = currentInspectPageIndex;
      renderInspectPage(currentInspectPageIndex);
    }
  }

  function renderInspectPage(idx) {
    if (!currentInspectDoc || !currentInspectDoc.pages || !currentInspectDoc.pages[idx]) return;
    currentInspectPageIndex = idx;
    const pageData = currentInspectDoc.pages[idx];

    document.getElementById('doc-img-page-num').textContent = `صفحه ${pageData.page}`;
    const imgEl = document.getElementById('docs-page-img');
    const placeholder = document.getElementById('docs-img-placeholder');
    imgEl.style.display = 'none';
    placeholder.style.display = 'block';
    placeholder.textContent = 'در حال فراخوانی تصویر صفحه...';
    imgEl.src = `${DOCS_API_BASE}/${currentInspectDoc.id}/page-image/${pageData.page}`;

    const textEl = document.getElementById('docs-page-text');
    textEl.textContent = pageData.text || '(این صفحه بدون متن است)';
    document.getElementById('doc-text-length').textContent = `${(pageData.text || '').length} کاراکتر`;

    const layerMeta = (pageData.metadata && pageData.metadata.text_layer) || 'استاندارد (OK)';
    const layerEl = document.getElementById('docs-kpi-layer');
    layerEl.textContent = layerMeta;
    if (layerMeta === 'ocr') {
      layerEl.style.color = '#38bdf8';
    } else if (layerMeta === 'garbled' || layerMeta === 'visual_persian') {
      layerEl.style.color = '#ef4444';
    } else {
      layerEl.style.color = '#22c55e';
    }
  }

  function copyCurrentPageText() {
    const text = document.getElementById('docs-page-text').textContent;
    navigator.clipboard.writeText(text);
    alert('متن صفحه با موفقیت کپی شد!');
  }

  async function purgeDocOcrCache() {
    if (!currentInspectDoc || !currentInspectDoc.id) return;
    if (!confirm(`آیا مطمئن هستید که می‌خواهید کش OCR ذخیره‌شده برای فایل «${currentInspectDoc.filename}» را حذف کنید؟\n\nبا این کار، اگر سند دوباره پردازش شود، از کش استفاده نخواهد شد و تصویر صفحات مجدداً توسط هوش مصنوعی خوانده می‌شود.`)) return;

    try {
      const resp = await fetch(`${DOCS_API_BASE}/${currentInspectDoc.id}/purge-ocr-cache`, { method: 'POST' });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'خطا در حذف کش OCR');
      alert(data.message || 'کش OCR این سند با موفقیت حذف شد.');
    } catch (err) {
      alert('خطا: ' + err.message);
    }
  }

  async function reprocessFreshDoc() {
    if (!currentInspectDoc || !currentInspectDoc.id) return;
    if (!confirm(`آیا از پردازش مجدد «بدون کش» برای سند «${currentInspectDoc.filename}» اطمینان دارید؟\n\nاین عملیات ابتدا تمام کش OCR این سند را پاک می‌کند و سپس فایل را برای پردازش تازه در صف قرار می‌دهد.`)) return;

    try {
      const resp = await fetch(`${DOCS_API_BASE}/${currentInspectDoc.id}/reprocess-fresh`, { method: 'POST' });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'خطا در درخواست پردازش مجدد');
      alert(data.message || 'کش OCR حذف شد و سند برای پردازش تازه در صف قرار گرفت! لطفاً لاگ ورکر را مشاهده فرمایید.');
      await loadInspectDocsList();
    } catch (err) {
      alert('خطا: ' + err.message);
    }
  }

  async function reprocessCurrentDoc() {
    if (!currentInspectDoc || !currentInspectDoc.id) return;
    if (!confirm(`آیا از ارسال مجدد سند «${currentInspectDoc.filename}» به پایپ‌لاین Ingestion و OCR اطمینان دارید؟`)) return;

    try {
      const resp = await fetch(`${DOCS_API_BASE}/${currentInspectDoc.id}/reprocess`, { method: 'POST' });
      if (!resp.ok) throw new Error('خطا در درخواست پردازش مجدد');
      alert('سند با موفقیت در صف پردازش مجدد قرار گرفت! لطفاً لاگ کانتینر worker را بررسی کنید.');
      await loadInspectDocsList();
    } catch (err) {
      alert('خطا: ' + err.message);
    }
  }

  // --- OCR Debugger Methods ---

  async function loadDocumentsList() {
    try {
      const resp = await fetch(`${API_BASE}/list`);
      if (!resp.ok) throw new Error('خطا در فراخوانی لیست اسناد');
      const docs = await resp.json();
      const select = document.getElementById('doc-select');
      select.innerHTML = '';

      if (!docs || docs.length === 0) {
        document.getElementById('empty-state').style.display = 'block';
        document.getElementById('content-view').style.display = 'none';
        select.innerHTML = '<option value="">سندی یافت نشد</option>';
        return;
      }

      document.getElementById('empty-state').style.display = 'none';
      docs.forEach((d, idx) => {
        const opt = document.createElement('option');
        opt.value = d.document_id;
        opt.textContent = `${idx + 1}. سند ${d.document_id.slice(0, 8)}... (${d.pages_count} صفحه)`;
        select.appendChild(opt);
      });

      onDocumentSelected();
    } catch (err) {
      console.error(err);
      alert('خطا در بارگذاری لیست اسناد دیباگ: ' + err.message);
    }
  }

  async function onDocumentSelected() {
    const docId = document.getElementById('doc-select').value;
    if (!docId) return;

    document.getElementById('loading-state').style.display = 'block';
    document.getElementById('content-view').style.display = 'none';

    try {
      const resp = await fetch(`${API_BASE}/${docId}`);
      if (!resp.ok) throw new Error('سند یافت نشد');
      currentDocTrace = await resp.json();

      const pageSelect = document.getElementById('page-select');
      pageSelect.innerHTML = '';
      const pageNumbers = Object.keys(currentDocTrace.pages || {}).sort((a,b) => Number(a) - Number(b));

      if (pageNumbers.length === 0) {
        pageSelect.disabled = true;
        document.getElementById('loading-state').style.display = 'none';
        return;
      }

      pageSelect.disabled = false;
      pageNumbers.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p;
        opt.textContent = `صفحه ${p}`;
        pageSelect.appendChild(opt);
      });

      document.getElementById('loading-state').style.display = 'none';
      document.getElementById('content-view').style.display = 'block';
      renderPageDetails(pageNumbers[0]);
    } catch (err) {
      document.getElementById('loading-state').style.display = 'none';
      console.error(err);
    }
  }

  function onPageSelected() {
    const pageNum = document.getElementById('page-select').value;
    if (pageNum && currentDocTrace) {
      renderPageDetails(pageNum);
    }
  }

  function renderPageDetails(pageNum) {
    const pageData = currentDocTrace.pages[pageNum];
    if (!pageData) return;

    const docId = currentDocTrace.document_id;
    document.getElementById('kpi-dims').textContent = `${pageData.width} × ${pageData.height} px`;
    document.getElementById('kpi-mistral-time').textContent = `${(pageData.mistral_duration_ms / 1000).toFixed(2)} ثانیه`;
    document.getElementById('kpi-blocks-count').textContent = `${pageData.blocks_count || (pageData.blocks || []).length} بلوک`;
    document.getElementById('kpi-total-time').textContent = `${(pageData.total_duration_ms / 1000).toFixed(2)} ثانیه`;

    // Annotated image
    const annotatedUrl = `${API_BASE}/${docId}/image/${pageData.annotated_image}`;
    document.getElementById('annotated-img').src = annotatedUrl;

    // Render Blocks
    const container = document.getElementById('blocks-container');
    container.innerHTML = '';
    const blocks = pageData.blocks || [];
    document.getElementById('blocks-badge').textContent = `${blocks.length} بلوک`;

    blocks.forEach(b => {
      const typeClean = (b.block_type || 'text').toLowerCase();
      const cropUrl = `${API_BASE}/${docId}/image/${b.crop_image}`;

      const card = document.createElement('div');
      card.className = `block-card ${typeClean}`;
      card.innerHTML = `
        <div class="block-header">
          <div>
            <span class="block-badge ${typeClean}">#${b.block_index} ${b.block_type.toUpperCase()}</span>
            <span style="color: var(--text-muted); margin-right: 0.5rem;">[${b.box.join(', ')}] (${b.width}×${b.height} px)</span>
          </div>
          <div style="color: #38bdf8; font-size: 0.75rem;">
            زمان پردازش: ${(b.duration_ms / 1000).toFixed(2)}s
          </div>
        </div>
        <div class="block-body">
          <div class="crop-thumb" onclick="window.open('${cropUrl}', '_blank')">
            <img src="${cropUrl}" alt="برش ${b.block_index}" title="کلیک برای مشاهده اندازه واقعی">
          </div>
          <div class="block-text">${escapeHtml(b.text || '(متنی استخراج نشد یا خالی)')}</div>
        </div>
      `;
      container.appendChild(card);
    });

    // Final Assembled Text
    document.getElementById('final-text-box').textContent = pageData.final_text || '(خالی)';

    // Structured JSON Trace Log
    document.getElementById('json-trace-box').textContent = JSON.stringify(pageData, null, 2);
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function copyFinalText() {
    const text = document.getElementById('final-text-box').textContent;
    navigator.clipboard.writeText(text);
    alert('متن نهایی با موفقیت کپی شد!');
  }

  function copyJsonTrace() {
    const text = document.getElementById('json-trace-box').textContent;
    navigator.clipboard.writeText(text);
    alert('لاگ JSON با موفقیت کپی شد!');
  }

  // Initial load
  loadInspectDocsList();
</script>

</body>
</html>
"""

