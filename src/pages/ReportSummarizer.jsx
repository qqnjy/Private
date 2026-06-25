import React, { useState, useRef } from 'react';
import JSZip from 'jszip';
import { FileText, Upload, Loader2, X, ClipboardCopy } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const STYLE_SOCIAL = `週報信件格式。嚴格照以下結構與順序輸出，固定句逐字保留，只能有這三段、不要加任何額外段落（不要「待確認」、不要「各平台詳述」）：

Dears

連結為 [期間，例 06/16-06/21] [品牌名] 週報

本週社群操作重點如下：

一、整體表現總結
● FB：[一段話，含粉絲數方向、平均觸及變化%、互動變化%，並一句帶出帶動原因或受眾觀察]
● IG：[同上格式]
● Threads：[同上，含單篇爆款瀏覽數與擴散度觀察]

二、後續規劃
● FB：[一句可執行的下期方向]
● IG：[同上]
● Threads：[同上]

三、月 KPI 達成狀況
[用 markdown 表格輸出，欄位固定為：平台 | 項目 | 目標 | 實際 | 達成率。每個平台的每一列第一欄都要填平台名（例如 FB 連續三列第一欄都寫 FB）。項目一般為 互動/觸及/追蹤（FB、IG）與 觸及/瀏覽（Threads）。達成率 = 實際 ÷ 目標 × 100%，四捨五入到小數點兩位後加 %。只在目標與實際都有資料時計算，缺的一律標「資料未提供」。]

如有需要調整的地方再跟我說，謝謝！

補充規則：期間與品牌若資料中可判斷就直接填，否則用 [請填] 佔位；絕不編造數字。`;

const STYLE_EXEC = '主管摘要：開頭一句 TL;DR，接著條列 3–6 個關鍵要點（成果、數據、進行中、風險、下期計畫），語氣寫給忙碌主管。';
const STYLE_PROSE = '段落敘述：用通順段落講清楚整份報告，不用條列符號。';

const LEN_MAP = {
  short: '盡量精簡，只留最核心。',
  std: '適中，涵蓋主要重點。',
  long: '較完整，保留具體數字、貼文主題、平台名。',
};

function fmtNum(n) {
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

async function parsePptx(buf) {
  const zip = await JSZip.loadAsync(buf);
  const parser = new DOMParser();

  let paths = [];
  try {
    const pf = zip.file('ppt/presentation.xml');
    const rf = zip.file('ppt/_rels/presentation.xml.rels');
    if (pf && rf) {
      const pd = parser.parseFromString(await pf.async('string'), 'application/xml');
      const rd = parser.parseFromString(await rf.async('string'), 'application/xml');
      const map = {};
      Array.from(rd.getElementsByTagName('Relationship')).forEach((r) => {
        map[r.getAttribute('Id')] = r.getAttribute('Target');
      });
      Array.from(pd.getElementsByTagName('p:sldId')).forEach((s) => {
        const t = map[s.getAttribute('r:id')];
        if (t) paths.push(normPath('ppt/', t));
      });
    }
  } catch {}

  if (!paths.length) {
    paths = Object.keys(zip.files)
      .filter((p) => /^ppt\/slides\/slide\d+\.xml$/.test(p))
      .sort((a, b) => slideNum(a) - slideNum(b));
  }

  const out = [];
  for (let i = 0; i < paths.length; i++) {
    const sf = zip.file(paths[i]);
    if (!sf) continue;
    const text = extractText(parser, await sf.async('string'));
    let notes = '';
    try {
      notes = await readNotes(zip, parser, paths[i]);
    } catch {}
    out.push({ n: i + 1, text, notes });
  }
  return out;
}

async function readNotes(zip, parser, sp) {
  const m = sp.match(/^(.*\/)([^\/]+)$/);
  const dir = m ? m[1] : '';
  const file = m ? m[2] : sp;
  const rf = zip.file(dir + '_rels/' + file + '.rels');
  if (!rf) return '';
  const rd = parser.parseFromString(await rf.async('string'), 'application/xml');
  let tgt = null;
  Array.from(rd.getElementsByTagName('Relationship')).forEach((r) => {
    if ((r.getAttribute('Type') || '').indexOf('notesSlide') > -1) tgt = r.getAttribute('Target');
  });
  if (!tgt) return '';
  const nf = zip.file(normPath(dir, tgt));
  if (!nf) return '';
  return extractText(parser, await nf.async('string'));
}

function extractText(parser, xml) {
  const d = parser.parseFromString(xml, 'application/xml');
  return Array.from(d.getElementsByTagName('a:p'))
    .map((p) =>
      Array.from(p.getElementsByTagName('a:t'))
        .map((t) => t.textContent)
        .join('')
        .trim()
    )
    .filter(Boolean)
    .join('\n');
}

function normPath(base, t) {
  if (t.charAt(0) === '/') return t.slice(1);
  const st = base.replace(/\/$/, '').split('/');
  t.split('/').forEach((s) => {
    if (s === '..') st.pop();
    else if (s !== '.' && s !== '') st.push(s);
  });
  return st.join('/');
}

function slideNum(p) {
  const m = p.match(/slide(\d+)\.xml/);
  return m ? +m[1] : 0;
}

// ---------- markdown table rendering ----------

function splitRow(l) {
  return l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
}

function parsePct(s) {
  const m = s.match(/^([\d,.]+)\s*%$/);
  return m ? parseFloat(m[1].replace(/,/g, '')) : null;
}

function renderMarkdown(md) {
  const lines = md.split('\n');
  const blocks = [];
  const copyLines = [];
  let i = 0;
  while (i < lines.length) {
    const ln = lines[i];
    const isRow = /^\s*\|.*\|\s*$/.test(ln);
    const sepNext = i + 1 < lines.length && /^\s*\|[\s:\-|]+\|\s*$/.test(lines[i + 1]);
    if (isRow && sepNext) {
      const head = splitRow(ln);
      i += 2;
      const body = [];
      while (
        i < lines.length &&
        /^\s*\|.*\|\s*$/.test(lines[i]) &&
        !/^\s*\|[\s:\-|]+\|\s*$/.test(lines[i])
      ) {
        body.push(splitRow(lines[i]));
        i++;
      }
      blocks.push({ kind: 'table', head, body });
      copyLines.push(head.join('\t'));
      let fp = '';
      body.forEach((r) => {
        const rr = r.slice();
        if (!rr[0]) rr[0] = fp;
        else fp = rr[0];
        copyLines.push(rr.join('\t'));
      });
    } else {
      blocks.push({ kind: 'line', text: ln });
      copyLines.push(ln);
      i++;
    }
  }
  return { blocks, copyText: copyLines.join('\n') };
}

function TableBlock({ head, body }) {
  // Apply rowspan to repeating first column
  const rendered = [];
  for (let r = 0; r < body.length; r++) {
    const cells = [];
    for (let c = 0; c < body[r].length; c++) {
      const v = body[r][c];
      if (c === 0) {
        if (r > 0 && body[r - 1][0] === v && v !== '') continue;
        let span = 1;
        while (r + span < body.length && body[r + span][0] === v && v !== '') span++;
        cells.push(
          <td
            key={c}
            rowSpan={span}
            className="border border-[var(--border-color)] px-3 py-2 font-bold text-center bg-[var(--bg-base)] align-middle"
          >
            {v}
          </td>
        );
      } else {
        const pct = parsePct(v);
        const isNum = /^[\d,.\s%]+$/.test(v) && /\d/.test(v);
        const overshot = pct !== null && pct >= 100;
        const cls = [
          'border border-[var(--border-color)] px-3 py-2',
          isNum ? 'text-right tabular-nums' : '',
          overshot ? 'text-red-500 font-bold' : '',
        ]
          .filter(Boolean)
          .join(' ');
        cells.push(
          <td key={c} className={cls}>
            {v}
          </td>
        );
      }
    }
    rendered.push(<tr key={r}>{cells}</tr>);
  }
  return (
    <table className="my-3 w-full border-collapse text-sm">
      <thead>
        <tr>
          {head.map((c, i) => (
            <th
              key={i}
              className="border border-[var(--border-color)] px-3 py-2 text-left text-xs font-bold bg-[var(--accent)]/10 text-[var(--accent)]"
            >
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>{rendered}</tbody>
    </table>
  );
}

// ---------- main component ----------

export default function ReportSummarizer() {
  const [parsed, setParsed] = useState([]);
  const [pasteText, setPasteText] = useState('');
  const [type, setType] = useState('auto');
  const [style, setStyle] = useState('social');
  const [len, setLen] = useState('std');
  const [readNotesFlag, setReadNotesFlag] = useState(true);
  const [jp, setJp] = useState(false);
  const [custom, setCustom] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ text: '', kind: '' });
  const [output, setOutput] = useState('');
  const [copyText, setCopyText] = useState('');
  const [drag, setDrag] = useState(false);
  const fileInputRef = useRef(null);

  const handleFiles = async (fl) => {
    const arr = Array.from(fl).filter((f) => /\.pptx$/i.test(f.name));
    const skipped = Array.from(fl).length - arr.length;
    if (!arr.length) {
      setStatus({
        text: skipped ? '只接受 .pptx。舊版 .ppt 請先另存成 .pptx。' : '沒有可用的檔案。',
        kind: 'err',
      });
      return;
    }
    setStatus({ text: '解析中…', kind: '' });
    const next = [...parsed];
    for (const f of arr) {
      try {
        const slides = await parsePptx(await f.arrayBuffer());
        const chars = slides.reduce((s, sl) => s + sl.text.length + sl.notes.length, 0);
        next.push({ name: f.name, slides, chars });
      } catch (err) {
        setStatus({ text: `「${f.name}」解析失敗：${err.message || err}`, kind: 'err' });
      }
    }
    setParsed(next);
    const tot = next.reduce((s, p) => s + p.slides.length, 0);
    if (next.length) setStatus({ text: `已讀取 ${next.length} 份、共 ${tot} 頁。`, kind: 'ok' });
  };

  const removeFile = (i) => {
    const next = parsed.slice();
    next.splice(i, 1);
    setParsed(next);
  };

  const buildPrompt = () => {
    const typeLabel =
      type === 'weekly' ? '週報' : type === 'monthly' ? '月報' : '(請依內容自行判斷週報或月報)';
    const styleMap = { social: STYLE_SOCIAL, exec: STYLE_EXEC, prose: STYLE_PROSE };
    let body = '';
    parsed.forEach((p) => {
      body += `===== 簡報檔：${p.name} =====\n`;
      p.slides.forEach((s) => {
        body += `【投影片 ${s.n}】\n${s.text || '(本頁無文字)'}\n`;
        if (readNotesFlag && s.notes) body += `[備註] ${s.notes}\n`;
        body += '\n';
      });
    });
    const pasted = pasteText.trim();
    if (pasted) body += `===== 貼上的內容 =====\n${pasted}\n`;
    const customExtra = custom.trim() ? '\n額外指示：' + custom.trim() : '';
    const jpExtra = jp ? '\n- 總結完後，再附一份日文版（用於對日方/合作窗口回報）。' : '';
    return (
      `你是明星3缺1 / 金好運社群團隊的幕僚，把後台數據與簡報整理成可直接放進週報的社群操作總結。以下是${typeLabel}的內容。\n\n` +
      `【輸出要求】\n- 風格：${styleMap[style]}\n- 長度：${LEN_MAP[len]}\n- 繁體中文，台灣社群行銷用語。\n- 數據、品牌名、貼文主題、平台名照原樣保留，不要編造或推估任何數字，讀不到的標「資料未提供」。\n- 只輸出總結本身，不要前言。${jpExtra}${customExtra}\n\n【報告內容】\n${body}`
    );
  };

  const run = async () => {
    if (!parsed.length && !pasteText.trim()) {
      setStatus({ text: '請先上傳 .pptx 或貼上文字。', kind: 'err' });
      return;
    }
    setLoading(true);
    setOutput('');
    setStatus({ text: 'AI 正在閱讀並整理…', kind: '' });
    try {
      const res = await fetch(`${API_BASE}/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: buildPrompt() }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `伺服器錯誤 (${res.status})`);
      }
      const data = await res.json();
      const text = (data.text || '').trim();
      setOutput(text || '(沒有產生內容，請再試一次)');
      setStatus({ text: '完成 ✓', kind: 'ok' });
    } catch (err) {
      setStatus({ text: `失敗：${err.message || err}`, kind: 'err' });
    } finally {
      setLoading(false);
    }
  };

  // Update copyText whenever output changes (with table flattening)
  React.useEffect(() => {
    if (output) {
      const { copyText: ct } = renderMarkdown(output);
      setCopyText(ct);
    } else {
      setCopyText('');
    }
  }, [output]);

  const handleCopy = () => {
    const t = (copyText || output).trim();
    if (!t) return;
    navigator.clipboard.writeText(t).then(() => {
      setStatus({ text: '已複製到剪貼簿 ✓', kind: 'ok' });
    });
  };

  const SegBtn = ({ value, current, onClick, children }) => (
    <button
      type="button"
      onClick={() => onClick(value)}
      className={`flex-1 px-3 py-2 text-sm font-bold transition border-r border-[var(--border-color)] last:border-r-0 ${
        current === value
          ? 'bg-[var(--accent)] text-[var(--bg-base)]'
          : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
      }`}
    >
      {children}
    </button>
  );

  const { blocks } = output ? renderMarkdown(output) : { blocks: [] };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-3 bg-[var(--accent)]/10 rounded-xl">
          <FileText className="text-[var(--accent)]" size={24} />
        </div>
        <div>
          <h2 className="text-2xl font-black text-[var(--text-primary)]">報告文字化工具</h2>
          <p className="text-sm text-[var(--text-muted)] font-medium">
            把週報 .pptx 或後台數據丟進來，AI 自動產生可貼進信件的週報格式
          </p>
        </div>
      </div>

      {/* Input card */}
      <div className="bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)] p-5 shadow-sm">
        <label className="block text-sm font-bold text-[var(--text-secondary)] mb-3">輸入報告</label>
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragEnter={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            handleFiles(e.dataTransfer.files);
          }}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
            drag
              ? 'border-[var(--accent)] bg-[var(--accent)]/5'
              : parsed.length
              ? 'border-[var(--accent)] bg-[var(--accent)]/5'
              : 'border-[var(--border-color)] hover:border-[var(--accent)]'
          }`}
        >
          <Upload className="mx-auto mb-2 text-[var(--text-muted)]" size={28} />
          <div className="font-bold text-sm">拖進 .pptx，或點這裡選檔</div>
          <div className="text-xs text-[var(--text-muted)] mt-1">支援多檔。舊版 .ppt 請先另存成 .pptx</div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pptx"
          multiple
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
        {parsed.length > 0 && (
          <div className="mt-3 space-y-2">
            {parsed.map((p, i) => (
              <div
                key={i}
                className="flex items-center gap-3 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm"
              >
                <FileText size={16} className="text-[var(--accent)]" />
                <span className="flex-1 font-bold truncate">{p.name}</span>
                <span className="text-xs text-[var(--text-muted)] font-mono">
                  {p.slides.length} 頁 · {fmtNum(p.chars)} 字
                </span>
                <button
                  onClick={() => removeFile(i)}
                  className="text-[var(--text-muted)] hover:text-red-500 transition"
                >
                  <X size={16} />
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="my-4 text-center text-xs text-[var(--text-muted)] font-mono tracking-wider">
          — 或直接貼上文字 —
        </div>
        <textarea
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
          rows={4}
          placeholder="把後台數據或報告內容貼這裡也可以（可跟 pptx 並用）"
          className="w-full px-3 py-2 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none resize-y"
        />
      </div>

      {/* Settings card */}
      <div className="bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)] p-5 shadow-sm">
        <label className="block text-sm font-bold text-[var(--text-secondary)] mb-3">總結設定</label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="text-xs font-bold mb-2">報告類型</div>
            <div className="flex border border-[var(--border-color)] rounded-lg overflow-hidden">
              <SegBtn value="auto" current={type} onClick={setType}>自動</SegBtn>
              <SegBtn value="weekly" current={type} onClick={setType}>週報</SegBtn>
              <SegBtn value="monthly" current={type} onClick={setType}>月報</SegBtn>
            </div>
          </div>
          <div>
            <div className="text-xs font-bold mb-2">摘要風格</div>
            <div className="flex border border-[var(--border-color)] rounded-lg overflow-hidden">
              <SegBtn value="social" current={style} onClick={setStyle}>週報信件</SegBtn>
              <SegBtn value="exec" current={style} onClick={setStyle}>主管摘要</SegBtn>
              <SegBtn value="prose" current={style} onClick={setStyle}>段落敘述</SegBtn>
            </div>
          </div>
          <div>
            <div className="text-xs font-bold mb-2">長度</div>
            <div className="flex border border-[var(--border-color)] rounded-lg overflow-hidden">
              <SegBtn value="short" current={len} onClick={setLen}>簡短</SegBtn>
              <SegBtn value="std" current={len} onClick={setLen}>標準</SegBtn>
              <SegBtn value="long" current={len} onClick={setLen}>詳細</SegBtn>
            </div>
          </div>
          <div>
            <div className="text-xs font-bold mb-2">附加</div>
            <label className="flex items-center gap-2 text-sm cursor-pointer mb-1">
              <input
                type="checkbox"
                checked={readNotesFlag}
                onChange={(e) => setReadNotesFlag(e.target.checked)}
                className="w-4 h-4 accent-[var(--accent)]"
              />
              讀進 pptx 備註
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={jp}
                onChange={(e) => setJp(e.target.checked)}
                className="w-4 h-4 accent-[var(--accent)]"
              />
              附一份日文版
            </label>
          </div>
          <div className="md:col-span-2">
            <div className="text-xs font-bold mb-2">自訂指示（選填）</div>
            <textarea
              value={custom}
              onChange={(e) => setCustom(e.target.value)}
              rows={2}
              placeholder="例：聚焦數據成長與下期計畫、跨期比較、加競品對照…"
              className="w-full px-3 py-2 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none resize-y"
            />
          </div>
        </div>
      </div>

      <button
        onClick={run}
        disabled={loading}
        className="w-full py-3 bg-[var(--accent)] hover:opacity-90 text-[var(--bg-base)] rounded-xl font-bold transition flex items-center justify-center gap-2 disabled:opacity-50"
      >
        {loading ? <Loader2 size={20} className="animate-spin" /> : null}
        {loading ? '產生中…' : '產生總結'}
      </button>

      {status.text && (
        <div
          className={`text-center text-sm font-mono ${
            status.kind === 'err'
              ? 'text-red-500'
              : status.kind === 'ok'
              ? 'text-emerald-600'
              : 'text-[var(--text-muted)]'
          }`}
        >
          {status.text}
        </div>
      )}

      {/* Output card */}
      <div className="bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)] p-5 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <label className="text-sm font-bold text-[var(--text-secondary)]">總結結果</label>
          {output && (
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 border border-[var(--border-color)] hover:border-[var(--accent)] hover:text-[var(--accent)] rounded-lg transition"
            >
              <ClipboardCopy size={14} /> 複製
            </button>
          )}
        </div>
        <div className="text-sm leading-relaxed whitespace-pre-wrap text-[var(--text-primary)] min-h-[80px]">
          {output ? (
            blocks.map((b, i) =>
              b.kind === 'table' ? (
                <TableBlock key={i} head={b.head} body={b.body} />
              ) : (
                <div key={i}>{b.text || ' '}</div>
              )
            )
          ) : (
            <div className="text-[var(--text-muted)] italic">總結會出現在這裡。</div>
          )}
        </div>
      </div>
    </div>
  );
}
