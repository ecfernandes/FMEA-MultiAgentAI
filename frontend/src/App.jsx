import { useState, useEffect, useRef, Fragment } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8001'

const MODELS = [
  { value: 'RedHatAI/Qwen3.6-35B-A3B-NVFP4',                       label: 'Qwen3.6 · 35B A3B ★ (recommended)', recommended: true },
  { value: 'qwen36---35b-a3b--bias-important---exprimental',        label: 'Qwen3.6 · 35B A3B (experimental)' },
  { value: 'qwen3527b-no-think',                                    label: 'Qwen3.5 · 27B (legacy)' },
  { value: 'mistral-small3.2:latest',                               label: 'Mistral Small 3.2 · 24B' },
  { value: 'hf.co/unsloth/Magistral-Small-2509-GGUF:UD-Q4_K_XL',   label: 'Magistral Small 1.2 · 23.6B' },
  { value: 'glm-4.7-flash:latest',                                  label: 'GLM 4.7 Flash · 29.9B' },
  { value: 'nvidia/Gemma-4-31B-IT-NVFP4',                          label: 'Gemma 4 · 31B (new server test)' },
  { value: 'gemma4:31b',                                            label: 'Gemma 4 · 31B (experimental)' },
  { value: 'hf.co/unsloth/Olmo-3.1-32B-Instruct-GGUF:Q4_K_M',     label: 'Olmo 3.1 · 32B (experimental, open data)' },
  { value: 'hf.co/unsloth/Olmo-3.1-32B-Think-GGUF:Q4_K_M',        label: 'Olmo 3.1 Think · 32B (experimental, open data)' },
  { value: 'devstral-small-2:latest',                               label: 'Devstral Small 2 · 24B (coding-focused)' },
  { value: 'ministral-3:3b',                                        label: 'Ministral 3 · 3.8B ⚠ too small for FMEA extraction', weak: true },
]

function rpnCls(v) {
  if (!v) return 'bg-slate-100 text-slate-400'
  if (v > 100) return 'bg-red-100 text-red-700 font-bold'
  if (v > 40)  return 'bg-amber-100 text-amber-700 font-semibold'
  return 'bg-emerald-100 text-emerald-700'
}
function sodCls(v) {
  if (!v) return 'bg-slate-100 text-slate-400'
  if (v >= 8) return 'bg-red-100 text-red-700 font-bold'
  if (v >= 5) return 'bg-amber-100 text-amber-700 font-semibold'
  return 'bg-emerald-100 text-emerald-700'
}
function groupByFn(records) {
  const m = new Map()
  for (const r of records) {
    const k = r.function || r.component || 'Unknown'
    if (!m.has(k)) m.set(k, [])
    m.get(k).push(r)
  }
  return m
}

function fmtDate(iso) {
  if (!iso) return 'Unknown date'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString()
}

// ── Header ───────────────────────────────────────────────────────────────────
function Header({ model, setModel, dark, toggleDark, onMyFmeas }) {
  const weakModel = MODELS.find(m => m.value === model)?.weak
  return (
    <header className="flex items-center justify-between mb-8">
      <h1 className="text-2xl font-bold tracking-tight">
        AI-Driven FMEA <span className="text-blue-600">5.0</span>
      </h1>
      <div className="flex items-center gap-3">
        <button onClick={onMyFmeas} className="text-sm px-3 py-2 rounded-lg bg-blue-500 text-white font-medium hover:bg-blue-600 transition-colors">
          My FMEAs
        </button>
        <button disabled className="text-sm px-3 py-2 rounded-lg bg-amber-500 text-white font-medium cursor-not-allowed opacity-75">
          Standards
        </button>
        <button disabled className="text-sm px-3 py-1.5 rounded-lg bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-600 cursor-not-allowed opacity-75">
          System Telemetry
        </button>
        <div className="flex flex-col items-end gap-0.5">
          <select
            value={model} onChange={e => setModel(e.target.value)}
            className={`border ${
              weakModel ? 'border-amber-400 ring-1 ring-amber-400' : 'border-slate-200 dark:border-slate-600'
            } bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer`}
          >
            {MODELS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
          {weakModel && (
            <span className="text-xs text-amber-600 font-medium">
              ⚠ This model (3.8B) is too small for extraction — use Qwen3.5 27b
            </span>
          )}
        </div>
        <button
          onClick={toggleDark}
          className="border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded-full px-4 py-2 text-sm hover:border-blue-500 transition-colors"
        >
          {dark ? '☀ Light' : '🌙 Dark'}
        </button>
      </div>
    </header>
  )
}

// ── Accordion ────────────────────────────────────────────────────────────────
function Accordion({ title, open, onToggle, badge, children }) {
  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-2xl bg-white dark:bg-slate-800 shadow-sm mb-4 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-5 py-4 bg-slate-50 dark:bg-slate-800/80 hover:bg-white dark:hover:bg-slate-700/60 border-b border-slate-200 dark:border-slate-700 text-left transition-colors"
      >
        <span className="font-semibold text-slate-700 dark:text-slate-200 text-[1.05rem] flex items-center gap-2">
          {title}
          {badge && <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full font-medium">{badge}</span>}
        </span>
        <span className={`text-slate-400 transition-transform duration-300 ${open ? 'rotate-180' : ''}`}>▼</span>
      </button>
      {open && <div className="p-5">{children}</div>}
    </div>
  )
}

// ── UploadSection ────────────────────────────────────────────────────────────
function UploadSection({ open, onToggle, model, onExtracted }) {
  const [file, setFile]           = useState(null)
  const [loading, setLoad]        = useState(false)
  const [error, setError]         = useState('')
  const [dragging, setDrag]       = useState(false)
  const [progress, setProgress]   = useState(null)
  const [pageRange, setPageRange] = useState('')
  const [elapsed, setElapsed]     = useState(0)
  const inputRef = useRef()

  useEffect(() => {
    if (!loading) { setElapsed(0); return }
    const id = setInterval(() => setElapsed(s => s + 1), 1000)
    return () => clearInterval(id)
  }, [loading])

  const setF = f => { setFile(f); setError('') }

  async function doExtract() {
    if (!file) return
    setLoad(true); setError(''); setProgress(null)
    const ctrl    = new AbortController()
    const isPDF   = file.name.toLowerCase().endsWith('.pdf')
    const timeout = isPDF ? 5 * 60 * 1000 : 3 * 60 * 1000
    const timerId = setTimeout(() => ctrl.abort(), timeout)
    try {
      const form = new FormData()
      form.append('file', file)
      if (isPDF) {
        const headers = { 'X-Model-Name': model }
        if (pageRange.trim()) headers['X-Page-Range'] = pageRange.trim()
        const res = await fetch(`${API}/extract/stream`, {
          method: 'POST', headers, body: form, signal: ctrl.signal,
        })
        if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `Server error ${res.status}`) }
        const reader  = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop()
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            let evt; try { evt = JSON.parse(line.slice(6)) } catch { continue }
            if (evt.type === 'start')  { setProgress({ page: 0, total: evt.total_pages, records: 0 }) }
            else if (evt.type === 'page')   { setProgress({ page: evt.page, total: evt.total_pages, records: evt.total_records }) }
            else if (evt.type === 'done')   { if (evt.columns) evt.document._columns = evt.columns; onExtracted(evt.document, file); clearTimeout(timerId); setLoad(false); setProgress(null); return }
            else if (evt.type === 'error')  { throw new Error(evt.message) }
          }
        }
      } else {
        const res = await fetch(`${API}/extract`, {
          method: 'POST', headers: { 'X-Model-Name': model }, body: form, signal: ctrl.signal,
        })
        if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `Server error ${res.status}`) }
        const data = await res.json()
        onExtracted(data.document, file)
      }
    } catch (e) {
      if (e.name === 'AbortError') setError(`Timeout: extraction took more than ${isPDF ? '5 min' : '3 min'}. Try a faster model.`)
      else setError(e.message)
    } finally { clearTimeout(timerId); setLoad(false); setProgress(null) }
  }

  return (
    <Accordion title="Step 1 — Upload FMEA Document" open={open} onToggle={onToggle}>
      <div
        onClick={() => inputRef.current.click()}
        onDragOver={e => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={e => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) setF(f) }}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
          dragging ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
          : file   ? 'border-emerald-400 bg-emerald-50 dark:bg-emerald-900/20'
          : 'border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900/40 hover:border-blue-400 hover:bg-blue-50/40'}`}
      >
        <input ref={inputRef} type="file" accept=".pdf,.xlsx,.xls" className="hidden"
          onChange={e => { if (e.target.files[0]) setF(e.target.files[0]) }} />
        <div className="text-4xl mb-2">{file ? '📄' : '📂'}</div>
        <p className="font-semibold text-slate-700 dark:text-slate-300">{file ? file.name : 'Drop your FMEA file here'}</p>
        <p className="text-sm text-slate-400 mt-1">{file ? `${(file.size / 1024).toFixed(1)} KB` : 'or click to browse — PDF or Excel'}</p>
      </div>

      {file && file.name.toLowerCase().endsWith('.pdf') && (
        <div className="mt-3 flex items-center gap-3">
          <label className="text-sm font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">Page range (optional):</label>
          <input
            type="text" value={pageRange} onChange={e => setPageRange(e.target.value)}
            placeholder="e.g. 2-32, 40-42  (leave blank for all pages)"
            disabled={loading}
            className="flex-1 text-sm px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50"
          />
        </div>
      )}

      {error && (
        <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-xl text-sm text-red-600">{error}</div>
      )}

      {loading && progress && (
        <div className="mt-4">
          <div className="flex justify-between items-center mb-1">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {progress.page > 0
                ? `Page ${progress.page} of ${progress.total} — ${progress.records} record${progress.records !== 1 ? 's' : ''} found`
                : `Analyzing structure… (${progress.total} pages)`}
            </p>
            <p className="text-xs font-bold text-blue-600 dark:text-blue-400">
              {progress.page > 0 ? `${Math.round(progress.page / Math.max(progress.total, 1) * 100)}%` : '0%'}
            </p>
          </div>
          <div className="h-3 rounded-full overflow-hidden bg-slate-200 dark:bg-slate-700">
            <div className="h-3 bg-blue-600 rounded-full transition-all duration-500"
              style={{ width: progress.page > 0 ? `${Math.round(progress.page / Math.max(progress.total, 1) * 100)}%` : '2%' }} />
          </div>
        </div>
      )}

      <button
        onClick={doExtract} disabled={!file || loading}
        className="mt-4 w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition-colors"
      >
        {loading
          ? <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin-slow inline-block" />
              {progress && progress.page > 0
                ? `Page ${progress.page}/${progress.total} — ${progress.records} records… (${elapsed}s)`
                : `Extracting… (${elapsed}s)`}
            </>
          : '⚡ Extract FMEA'}
      </button>
    </Accordion>
  )
}

// ── NewFmeaSection ───────────────────────────────────────────────────────────
function NewFmeaSection({ open, onToggle, onCreated }) {
  const [part, setPart]         = useState('')
  const [supplier, setSupplier] = useState('')
  const [rows, setRows]         = useState([])

  const addRow    = () => setRows(r => [...r, { component:'', function:'', failure_mode:'', effect:'', cause:'', severity:'', occurrence:'', detection:'', current_controls_prevention:'', current_controls_detection:'', recommended_action:'' }])
  const removeRow = i => setRows(r => r.filter((_, idx) => idx !== i))
  const updateRow = (i, f, v) => setRows(r => r.map((row, idx) => idx === i ? { ...row, [f]: v } : row))

  function create() {
    if (!rows.length) { alert('Add at least one failure mode row.'); return }
    const doc = {
      part_name: part || 'New FMEA', supplier: supplier || '—', source_file: 'manual entry',
      records: rows.map(r => ({ ...r, severity: +r.severity || null, occurrence: +r.occurrence || null, detection: +r.detection || null,
        rpn: (+r.severity && +r.occurrence && +r.detection) ? +r.severity * +r.occurrence * +r.detection : null }))
    }
    onCreated(doc); setRows([]); setPart(''); setSupplier('')
  }

  const inp = "w-full border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
  const lbl = "block text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1"

  return (
    <Accordion title="Step 1 — New FMEA" open={open} onToggle={onToggle}>
      <div className="grid grid-cols-2 gap-4 mb-5">
        <div><label className={lbl}>Part / System Name</label>
          <input className={inp} value={part} onChange={e => setPart(e.target.value)} placeholder="e.g. Window Lifting Mechanism" />
        </div>
        <div><label className={lbl}>Supplier / Team</label>
          <input className={inp} value={supplier} onChange={e => setSupplier(e.target.value)} placeholder="e.g. Engineering Team A" />
        </div>
      </div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-slate-600 dark:text-slate-300">Failure Mode Rows</span>
        <button onClick={addRow} className="text-sm border border-slate-300 dark:border-slate-600 px-3 py-1.5 rounded-lg hover:border-blue-500 hover:text-blue-600 dark:text-slate-300 transition-colors">+ Add Row</button>
      </div>
      {!rows.length && <p className="text-center text-slate-400 text-sm py-4">No rows yet. Click + Add Row.</p>}
      {rows.map((row, i) => (
        <div key={i} className="border border-slate-200 dark:border-slate-600 rounded-xl p-4 mb-3 bg-slate-50 dark:bg-slate-900/40">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-bold text-slate-500">Row {i + 1}</span>
            <button onClick={() => removeRow(i)} className="text-red-400 hover:text-red-600 text-xl leading-none">×</button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-3">
            {[['component','Component'],['function','Function'],['failure_mode','Failure Mode'],['effect','Effect'],['cause','Cause']].map(([f,l]) => (
              <div key={f}><label className={lbl}>{l}</label>
                <input className={inp} value={row[f]} onChange={e => updateRow(i,f,e.target.value)} placeholder={l} />
              </div>
            ))}
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
            {[['severity','S'],['occurrence','O'],['detection','D']].map(([f,l]) => (
              <div key={f}><label className={lbl}>{l} (1-10)</label>
                <input type="number" min="1" max="10" className={`${inp} text-center`} value={row[f]} onChange={e => updateRow(i,f,e.target.value)} placeholder="—" />
              </div>
            ))}
            {[['current_controls_prevention','Prev. Controls'],['current_controls_detection','Det. Controls'],['recommended_action','Action']].map(([f,l]) => (
              <div key={f}><label className={lbl}>{l}</label>
                <input className={inp} value={row[f]} onChange={e => updateRow(i,f,e.target.value)} placeholder={l} />
              </div>
            ))}
          </div>
        </div>
      ))}
      {rows.length > 0 && (
        <button onClick={create} className="w-full mt-2 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition-colors">
          Create FMEA
        </button>
      )}
    </Accordion>
  )
}

// ── EditableCell ─────────────────────────────────────────────────────────────
function EditableCell({ value, gi, field, onEdit, onAI, isSOD, isCritical = false }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft]     = useState(value ?? '')
  const inputRef = useRef()

  useEffect(() => { if (editing && inputRef.current) { inputRef.current.focus(); inputRef.current.select() } }, [editing])

  function commit() {
    onEdit(gi, field, isSOD ? (+draft || null) : draft)
    setEditing(false)
  }

  if (editing) return (
    <td className="px-3 py-2 align-middle">
      <input ref={inputRef} type={isSOD ? 'number' : 'text'}
        min={isSOD ? 1 : undefined} max={isSOD ? 10 : undefined}
        className="w-full border border-blue-500 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        value={draft} onChange={e => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={e => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') setEditing(false) }}
      />
    </td>
  )

  if (isSOD) return (
    <td className="px-3 py-2 align-middle text-center">
      <div className="flex items-center justify-center gap-1">
        <span className={`inline-block min-w-[2rem] text-center px-2 py-0.5 rounded-md text-xs ${isCritical ? 'bg-red-100 text-red-700 border border-red-400 font-bold' : sodCls(value)}`}>{value ?? '—'}</span>
        <button onClick={() => { setDraft(value ?? ''); setEditing(true) }} className="opacity-0 group-hover:opacity-100 text-xs hover:text-blue-600 transition-all" title="Edit">✏️</button>
        <button onClick={() => onAI(gi, field)} className="opacity-0 group-hover:opacity-100 text-xs hover:text-violet-500 transition-all" title="AI Suggestion">✨</button>
      </div>
    </td>
  )

  return (
    <td className="px-3 py-2 align-middle max-w-[240px]">
      <div className="flex items-start gap-1 group">
        <span className="flex-1 text-sm leading-relaxed break-words">{String(value ?? '—')}</span>
        <div className="flex flex-col gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={() => { setDraft(value ?? ''); setEditing(true) }} className="text-xs hover:text-blue-600" title="Edit">✏️</button>
          <button onClick={() => onAI(gi, field)} className="text-xs hover:text-violet-500" title="AI Suggestion">✨</button>
        </div>
      </div>
    </td>
  )
}

// ── FmeaTable ─────────────────────────────────────────────────────────────────
function FmeaTable({ records, docRecords, colOrder, onEdit, onAI, onDelete }) {
  if (!records.length) return <p className="text-center text-slate-400 text-sm py-4">No records for this function.</p>

  const SKIP_KEYS = new Set(['function','item_function','component_function','fonction','component','source_file','sheet_name','row_number','_aiEdited','_aiNew'])
  const SOD_SET   = new Set(['severity','occurrence','detection'])
  const allKeys   = colOrder.length > 0
    ? [...new Set([...colOrder, ...records.flatMap(r => Object.keys(r))])]
    : [...new Set(records.flatMap(r => Object.keys(r)))]
  const allCols = allKeys.filter(k => !SKIP_KEYS.has(k))
  const toLabel = k => k.split('_').map(w => w[0].toUpperCase() + w.slice(1)).join(' ')

  const scrollRef = useRef(null)
  const drag      = useRef({ active: false, startX: 0, scrollLeft: 0 })
  const onMouseDown = e => {
    if (e.target.closest('button,input,textarea,select,a')) return
    drag.current = { active: true, startX: e.pageX, scrollLeft: scrollRef.current.scrollLeft }
    scrollRef.current.style.cursor = 'grabbing'
    scrollRef.current.style.userSelect = 'none'
  }
  const onMouseMove = e => {
    if (!drag.current.active) return
    e.preventDefault()
    scrollRef.current.scrollLeft = drag.current.scrollLeft - (e.pageX - drag.current.startX)
  }
  const stopDrag = () => {
    drag.current.active = false
    if (scrollRef.current) { scrollRef.current.style.cursor = 'grab'; scrollRef.current.style.userSelect = '' }
  }

  return (
    <div ref={scrollRef} className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 mt-1"
      style={{ cursor: 'grab' }} onMouseDown={onMouseDown} onMouseMove={onMouseMove} onMouseUp={stopDrag} onMouseLeave={stopDrag}>
      <table className="w-full text-sm bg-white dark:bg-slate-800">
        <thead>
          <tr className="bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-600">
            {allCols.map(k => (
              <th key={k} className={`px-3 py-2.5 text-xs font-bold uppercase tracking-wide text-slate-400 whitespace-nowrap ${SOD_SET.has(k) || k === 'rpn' ? 'text-center' : 'text-left'}`}>{toLabel(k)}</th>
            ))}
            <th className="px-2 py-2.5 w-8" />
          </tr>
        </thead>
        <tbody>
          {records.map(r => {
            const gi         = docRecords.indexOf(r)
            const rpn        = (r.severity && r.occurrence && r.detection) ? r.severity * r.occurrence * r.detection : (r.rpn || null)
            const isCritical = (r.severity ?? 0) >= 8 && (rpn ?? 0) > 36
            return (
              <Fragment key={gi}>
                {isCritical && (
                  <tr>
                    <td colSpan={allCols.length} className="px-3 py-1 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 text-red-600 dark:text-red-400 text-xs font-semibold">
                      ⚠ Exceeds the critical threshold of 36
                    </td>
                  </tr>
                )}
                <tr className="group border-b border-slate-100 dark:border-slate-700/50 last:border-0 hover:bg-blue-50/30 dark:hover:bg-slate-700/30 transition-colors">
                  {allCols.map(k => {
                    if (k === 'rpn') return (
                      <td key="rpn" className="px-3 py-2 align-middle text-center">
                        <span className={`inline-block px-2 py-0.5 rounded-md text-xs ${isCritical ? 'bg-red-100 text-red-700 border border-red-400 font-bold' : rpnCls(rpn)}`}>{rpn || '—'}</span>
                      </td>
                    )
                    return <EditableCell key={k} value={r[k]} gi={gi} field={k} onEdit={onEdit} onAI={onAI} isSOD={SOD_SET.has(k)} isCritical={isCritical && k === 'severity'} />
                  })}
                  <td className="px-2 py-2 align-middle">
                    <button
                      onClick={() => onDelete(gi)}
                      title="Delete row"
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-md text-slate-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30"
                    >
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                        <path d="M10 11v6"/><path d="M14 11v6"/>
                        <path d="M9 6V4h6v2"/>
                      </svg>
                    </button>
                  </td>
                </tr>
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── SuggestMissingPanel ───────────────────────────────────────────────────────
function SuggestMissingPanel({ doc, model, onAddFailure }) {
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error,  setError]  = useState('')

  async function analyze() {
    setStatus('loading'); setResult(null); setError('')
    const fnMap     = groupByFn(doc.records)
    const functions = [...fnMap.entries()].map(([fn, recs]) => ({ function: fn, existing_failures: recs.map(r => r.failure_mode).filter(Boolean) }))
    try {
      const res = await fetch(`${API}/suggest-missing-failures`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ part_name: doc.part_name, functions, model_name: model }),
      })
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `Server error ${res.status}`) }
      setResult(await res.json()); setStatus('done')
    } catch(e) { setError(e.message); setStatus('error') }
  }

  const reset = () => { setStatus('idle'); setResult(null); setError('') }

  return (
    <div className="mt-6 pt-5 border-t border-slate-200 dark:border-slate-700">
      {status === 'idle' && (
        <button onClick={analyze} className="w-full py-3 border-2 border-dashed border-blue-300 dark:border-blue-700 text-blue-600 dark:text-blue-400 rounded-xl hover:border-blue-500 hover:bg-blue-50/40 dark:hover:bg-blue-900/20 font-semibold text-sm transition-all flex items-center justify-center gap-2">
          🔍 Analyse Unreported Potential Failure Modes
        </button>
      )}
      {status === 'loading' && (
        <div className="flex items-center justify-center gap-3 py-8 text-slate-500 dark:text-slate-400">
          <span className="w-5 h-5 border-2 border-slate-200 border-t-blue-600 rounded-full animate-spin-slow inline-block" />
          <span className="text-sm font-medium">Consulting specialist agent…</span>
        </div>
      )}
      {status === 'error' && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-xl text-sm text-red-600 dark:text-red-400 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={reset} className="ml-3 text-red-400 hover:text-red-600 text-xl leading-none">×</button>
        </div>
      )}
      {status === 'done' && result && (
        <div>
          {result.all_covered ? (
            <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-300 dark:border-emerald-700 rounded-xl text-sm text-emerald-700 dark:text-emerald-400 font-semibold text-center">
              ✅ Maximum coverage reached — no additional significant failure modes identified.
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold text-slate-700 dark:text-slate-200 text-sm">Unreported Potential Failure Modes</h4>
                <span className="text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 px-2 py-0.5 rounded-full font-medium border border-amber-200 dark:border-amber-700">
                  {result.suggestions.length} suggestion{result.suggestions.length !== 1 ? 's' : ''}
                </span>
              </div>
              {result.suggestions.map((s, i) => {
                const normalize = x => (x || '').trim().toLowerCase()
                const alreadyAdded = (doc.records || []).some(r => normalize(r.failure_mode) === normalize(s.failure_mode))
                return (
                <div key={i} className="border border-amber-200 dark:border-amber-700 rounded-xl p-4 mb-3 bg-amber-50/50 dark:bg-amber-900/10">
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wide text-amber-500 mr-1.5">Function:</span>
                      <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">{s.function}</span>
                    </div>
                    {alreadyAdded ? (
                      <span className="shrink-0 text-xs px-3 py-1.5 bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400 rounded-lg font-semibold">
                        Already in FMEA
                      </span>
                    ) : (
                      <button onClick={() => onAddFailure(s)} className="shrink-0 text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors">
                        + Add to FMEA
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm mb-2">
                    {[['Failure Mode',s.failure_mode],['Effect',s.effect],['Cause',s.cause]].map(([lbl,val]) => (
                      <div key={lbl}>
                        <p className="text-xs font-bold uppercase tracking-wide text-slate-400 mb-0.5">{lbl}</p>
                        <p className="text-slate-700 dark:text-slate-300 leading-snug">{val}</p>
                      </div>
                    ))}
                  </div>
                  {s.justification && (
                    <div className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed border-t border-amber-100 dark:border-amber-800 pt-2 mt-1">
                      <span className="font-bold uppercase tracking-wide">Justification: </span>{s.justification}
                    </div>
                  )}
                </div>
                )
              })}
            </div>
          )}
          <button onClick={reset} className="mt-2 w-full py-2 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">↺ Run new analysis</button>
        </div>
      )}
    </div>
  )
}

// ── ResultsSection ────────────────────────────────────────────────────────────
function ResultsSection({ open, onToggle, doc, onReset, onEdit, onDelete, onAI, model, onAddSuggestedFailure, onShowStatus, onSaveSession, saveBusy, saveDirty, saveError, saveSuccess }) {
  const [activeFn, setActiveFn] = useState(0)
  useEffect(() => { setActiveFn(0) }, [doc?.source_file, doc?.part_name])

  if (!doc) return (
    <Accordion title="Step 2 — FMEA Analysis Results" open={open} onToggle={onToggle}>
      <p className="text-center text-slate-400 py-8 text-sm">Extract or create a document first.</p>
    </Accordion>
  )

  if (!doc.records || !Array.isArray(doc.records)) return (
    <Accordion title="Step 2 — FMEA Analysis Results" open={open} onToggle={onToggle}>
      <div className="text-center py-8">
        <p className="text-red-600 font-semibold mb-2">⚠️ Invalid document structure</p>
        <pre className="mt-4 p-4 bg-slate-100 dark:bg-slate-800 rounded text-xs text-left overflow-auto max-h-60">{JSON.stringify(doc, null, 2)}</pre>
      </div>
    </Accordion>
  )

  if (doc.records.length === 0) return (
    <Accordion title="Step 2 — FMEA Analysis Results" open={open} onToggle={onToggle} badge="0 records">
      <div className="text-center py-12">
        <div className="text-6xl mb-4">📭</div>
        <p className="text-slate-600 dark:text-slate-300 font-semibold mb-2">No FMEA records found</p>
        <p className="text-sm text-slate-500">The extraction completed but found 0 records in the document.</p>
        <button onClick={onReset} className="mt-6 text-sm border border-blue-500 text-blue-600 px-4 py-2 rounded-lg hover:bg-blue-50 transition-colors">← Try Another Document</button>
      </div>
    </Accordion>
  )

  const fnMap  = groupByFn(doc.records)
  const fnList = [...fnMap.keys()]

  return (
    <Accordion title="Step 2 — FMEA Analysis Results" open={open} onToggle={onToggle} badge={`${doc.records.length} records`}>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5 pb-4 border-b border-slate-100 dark:border-slate-700">
        <div className="flex flex-wrap gap-4 text-sm text-slate-700 dark:text-slate-300">
          {[['Part',doc.part_name],['Supplier',doc.supplier],['File',doc.source_file]].map(([l,v]) => (
            <span key={l}><span className="text-xs font-bold uppercase text-slate-400 mr-1">{l}</span>{v}</span>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onReset} className="text-sm border border-slate-300 dark:border-slate-600 px-3 py-1.5 rounded-lg hover:border-blue-500 hover:text-blue-600 dark:text-slate-300 transition-colors">← New Document</button>
          <button onClick={onSaveSession} disabled={saveBusy || !saveDirty} className="text-sm px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed text-white border border-amber-500 transition-colors">{saveBusy ? 'Saving...' : 'Save Session'}</button>
          <button onClick={onShowStatus} className="text-sm px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-800 text-white border border-slate-700 transition-colors">Failure Status</button>
          <button disabled className="text-sm px-3 py-1.5 rounded-lg bg-blue-500 text-white border border-blue-500 cursor-not-allowed opacity-75">FMEA Dashboards</button>
          <button disabled className="text-sm px-3 py-1.5 rounded-lg bg-green-600 text-white border border-green-600 cursor-not-allowed opacity-75">FMEA Report</button>
        </div>
      </div>

      {(saveError || saveSuccess || saveDirty) && (
        <div className={`mb-4 rounded-xl border px-4 py-3 text-sm ${
          saveError
            ? 'border-red-200 bg-red-50 text-red-700'
            : saveDirty
              ? 'border-amber-200 bg-amber-50 text-amber-800'
              : 'border-emerald-200 bg-emerald-50 text-emerald-700'
        }`}>
          {saveError || (saveDirty ? 'There are unsaved changes in this session.' : saveSuccess)}
        </div>
      )}

      {fnList.length > 1 && (
        <div className="flex flex-wrap gap-2 mb-5 p-3 bg-slate-50 dark:bg-slate-700/30 rounded-xl border border-slate-100 dark:border-slate-700">
          {fnList.map((fn, i) => (
            <button key={i} onClick={() => setActiveFn(i)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
                activeFn === i
                  ? 'bg-blue-600 border-blue-600 text-white shadow-md shadow-blue-200 dark:shadow-none'
                  : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-blue-400 hover:text-blue-600'}`}
            >
              <span className={`text-xs font-bold px-1.5 py-0.5 rounded-full ${activeFn === i ? 'bg-white/20' : 'bg-slate-100 dark:bg-slate-700 text-slate-500'}`}>F{i+1}</span>
              <span className="max-w-[200px] truncate">{fn}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded-full ${activeFn === i ? 'bg-white/20' : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400'}`}>{fnMap.get(fn).length}</span>
            </button>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-xl px-4 py-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-blue-600 font-bold text-sm">F{activeFn + 1}</span>
          <span className="font-semibold text-slate-700 dark:text-slate-200 text-sm">{fnList[activeFn]}</span>
        </div>
        <span className="text-xs text-slate-400">{fnMap.get(fnList[activeFn]).length} failure mode{fnMap.get(fnList[activeFn]).length !== 1 ? 's' : ''}</span>
      </div>

      <FmeaTable records={fnMap.get(fnList[activeFn])} docRecords={doc.records} colOrder={doc._columns || []} onEdit={onEdit} onAI={onAI} onDelete={onDelete} />
      <SuggestMissingPanel doc={doc} model={model} onAddFailure={onAddSuggestedFailure} />
    </Accordion>
  )
}

// ── AIModal ───────────────────────────────────────────────────────────────────
function PencilBtn({ onClick, active }) {
  return (
    <button
      onClick={onClick}
      title={active ? 'Done editing' : 'Edit'}
      className={`p-1 rounded-md transition-colors ${
        active
          ? 'text-blue-600 bg-blue-100 dark:bg-blue-900/40'
          : 'text-slate-400 hover:text-blue-500 hover:bg-slate-100 dark:hover:bg-slate-700'
      }`}
    >
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
      </svg>
    </button>
  )
}

function AIModal({ modal, onApply, onDismiss, onClose }) {
  const [editedValue,         setEditedValue]         = useState('')
  const [editedJustification, setEditedJustification] = useState('')
  const [editedSources,       setEditedSources]       = useState([])
  const [editingValue,        setEditingValue]        = useState(false)
  const [editingJustif,       setEditingJustif]       = useState(false)
  const [editingSources,      setEditingSources]      = useState(false)
  const [newSource,           setNewSource]           = useState('')

  useEffect(() => {
    if (modal.data) {
      setEditedValue(String(modal.data.suggested_value ?? ''))
      setEditedJustification(modal.data.justification || '')
      setEditedSources([...(modal.data.sources || [])])
      setEditingValue(false)
      setEditingJustif(false)
      setEditingSources(false)
      setNewSource('')
    }
  }, [modal.data])

  useEffect(() => {
    const h = e => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', h)
    return () => document.removeEventListener('keydown', h)
  }, [onClose])

  if (!modal.open) return null
  const { field, functionName, failureMode, currentValue, loading, data, error } = modal
  const isEditing = editingValue || editingJustif || editingSources

  const addSource = () => {
    if (newSource.trim()) {
      setEditedSources(prev => [...prev, newSource.trim()])
      setNewSource('')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className={`bg-white dark:bg-slate-800 rounded-2xl w-full max-w-4xl shadow-2xl border border-slate-200 dark:border-slate-700 ${isEditing ? 'flex flex-col max-h-[90vh]' : ''}`}>
        <div className={`flex items-start justify-between px-6 py-5 border-b border-slate-100 dark:border-slate-700 ${isEditing ? 'shrink-0' : ''}`}>
          <div>
            <h2 className="text-lg font-bold text-slate-800 dark:text-white">Knowledge Engineering Audit</h2>
            {functionName && <p className="text-xs text-slate-500 mt-0.5">Function: <span className="font-semibold">{functionName}</span></p>}
            {failureMode  && <p className="text-xs text-slate-500 mt-0.5">Failure Mode: <span className="font-semibold">{failureMode}</span></p>}
            <p className="text-xs text-slate-400 mt-1">Field: <span className="font-semibold text-blue-600">{field}</span></p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-2xl leading-none mt-0.5">×</button>
        </div>

        <div className={`px-6 py-5 ${isEditing ? 'overflow-y-auto flex-1' : ''}`}>
          {loading && (
            <div className="flex items-center justify-center gap-3 py-12 text-slate-400">
              <span className="w-6 h-6 border-2 border-slate-200 border-t-blue-600 rounded-full animate-spin-slow inline-block" />
              Consulting specialist agent…
            </div>
          )}
          {error && <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 rounded-xl text-sm text-red-600">{error}</div>}
          {!loading && !error && data && (
            <>
              <div className="mb-5">
                <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-semibold border"
                  style={{ background: `${data.agent_color}18`, color: data.agent_color, borderColor: `${data.agent_color}44` }}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M12 8V4H8"/>
                    <rect width="16" height="12" x="4" y="8" rx="2"/>
                    <path d="M2 14h2"/>
                    <path d="M20 14h2"/>
                    <path d="M15 13v2"/>
                    <path d="M9 13v2"/>
                  </svg>
                  {data.agent_name}
                </span>
              </div>

              {/* Current value + AI Suggested Value */}
              <div className="grid grid-cols-2 gap-4 mb-5">
                <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4 border border-slate-200 dark:border-slate-600">
                  <p className="text-xs font-bold uppercase tracking-wide text-slate-400 mb-3">Current Value</p>
                  <p className="text-base font-semibold text-slate-600 dark:text-slate-300 break-words">{String(currentValue ?? '—')}</p>
                </div>
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4 border border-blue-200 dark:border-blue-700">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-xs font-bold uppercase tracking-wide text-blue-500">AI Suggested Value</p>
                    <PencilBtn onClick={() => setEditingValue(v => !v)} active={editingValue} />
                  </div>
                  {editingValue ? (
                    <textarea
                      rows={3}
                      value={editedValue}
                      onChange={e => setEditedValue(e.target.value)}
                      className="w-full text-sm font-semibold text-blue-600 dark:text-blue-400 bg-white dark:bg-slate-800 border border-blue-300 dark:border-blue-600 rounded-lg px-3 py-2 resize-y focus:outline-none focus:ring-2 focus:ring-blue-400"
                    />
                  ) : (
                    <p className="text-base font-semibold text-blue-600 dark:text-blue-400 break-words">{editedValue || '—'}</p>
                  )}
                </div>
              </div>

              {/* AI Engineering Justification */}
              <div className="mb-5">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-bold uppercase tracking-wide text-slate-400">AI Engineering Justification</p>
                  <PencilBtn onClick={() => setEditingJustif(v => !v)} active={editingJustif} />
                </div>
                {editingJustif ? (
                  <textarea
                    rows={7}
                    value={editedJustification}
                    onChange={e => setEditedJustification(e.target.value)}
                    className="w-full text-sm leading-relaxed text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-500 rounded-xl px-4 py-3 resize-y focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                ) : (
                  <div className="bg-slate-50 dark:bg-slate-700/40 rounded-xl p-4 text-sm leading-relaxed text-slate-700 dark:text-slate-300 border border-slate-100 dark:border-slate-600">
                    {editedJustification}
                  </div>
                )}
              </div>

              {/* Sources & References */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-bold uppercase tracking-wide text-slate-400">Sources & References</p>
                  <PencilBtn onClick={() => { setEditingSources(v => !v); setNewSource('') }} active={editingSources} />
                </div>
                {editingSources ? (
                  <div className="space-y-2">
                    {editedSources.map((s, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <input
                          value={s}
                          onChange={e => setEditedSources(prev => prev.map((x, j) => j === i ? e.target.value : x))}
                          className="flex-1 text-xs bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-500 rounded-lg px-3 py-1.5 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-400"
                        />
                        <button
                          onClick={() => setEditedSources(prev => prev.filter((_, j) => j !== i))}
                          className="text-red-400 hover:text-red-600 px-1 text-lg leading-none font-bold" title="Remove"
                        >×</button>
                      </div>
                    ))}
                    <div className="flex items-center gap-2 mt-2">
                      <input
                        value={newSource}
                        onChange={e => setNewSource(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addSource() } }}
                        placeholder="Add new source..."
                        className="flex-1 text-xs bg-white dark:bg-slate-700 border border-blue-300 dark:border-blue-600 rounded-lg px-3 py-1.5 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-400"
                      />
                      <button
                        onClick={addSource}
                        className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                      >Add</button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {editedSources.map((s, i) => (
                      <span key={i} className="inline-flex items-center bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400">{s}</span>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {!loading && !error && data && (
          <div className={`flex gap-3 px-6 py-4 border-t border-slate-100 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/60 rounded-b-2xl ${isEditing ? 'shrink-0' : ''}`}>
            <button
              onClick={() => onApply(editedValue, editedJustification, editedSources)}
              className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition-colors"
            >Apply Suggestion</button>
            <button onClick={onDismiss} className="px-6 py-2.5 bg-red-500 hover:bg-red-600 text-white font-medium rounded-xl transition-colors">Dismiss</button>
            <button disabled className="px-5 py-2.5 bg-orange-500 text-white font-semibold rounded-xl opacity-75 cursor-not-allowed">Interactive AI Meeting</button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── FailureStatusModal ────────────────────────────────────────────────────────
function failureColor(r) {
  if (r._aiNew)     return { fill: '#fee2e2', stroke: '#ef4444', text: '#b91c1c', label: 'New (AI)' }
  if (r._aiEdited)  return { fill: '#dcfce7', stroke: '#22c55e', text: '#15803d', label: 'Edited by AI' }
  return              { fill: '#fef3c7', stroke: '#f59e0b', text: '#92400e', label: 'Original' }
}

function FailureStatusModal({ doc, onClose }) {
  const [view, setView] = useState('radial') // 'radial' | 'list'

  useEffect(() => {
    const h = e => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', h)
    return () => document.removeEventListener('keydown', h)
  }, [onClose])

  if (!doc) return null
  const records = doc.records || []

  // ── Radial layout ────────────────────────────────────────────────────────
  const W = 860, H = 560, CX = W / 2, CY = H / 2, CR = 56
  const RW = 160, RH = 48, GAP = 14
  const count = records.length
  // radius of orbit: enough so rectangles don't overlap
  const orbitR = Math.max(180, Math.min(240, count * 22))

  const nodes = records.map((r, i) => {
    const angle = (2 * Math.PI * i) / count - Math.PI / 2
    return {
      x: CX + orbitR * Math.cos(angle),
      y: CY + orbitR * Math.sin(angle),
      r,
      label: (r.failure_mode || r.component || `Row ${i + 1}`).slice(0, 28),
      col: failureColor(r),
    }
  })

  const LEGEND = [
    { fill: '#dcfce7', stroke: '#22c55e', text: '#15803d', label: 'Original + edited by AI' },
    { fill: '#fef3c7', stroke: '#f59e0b', text: '#92400e', label: 'Original, no AI edit' },
    { fill: '#fee2e2', stroke: '#ef4444', text: '#b91c1c', label: 'New, created by AI' },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white dark:bg-slate-800 rounded-2xl w-full max-w-6xl shadow-2xl border border-slate-200 dark:border-slate-700 flex flex-col h-[90vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-700 shrink-0">
          <div>
            <h2 className="text-xl font-bold text-slate-800 dark:text-white">Failure Status Overview</h2>
            <p className="text-sm text-slate-400 mt-0.5">{doc.part_name} — {records.length} failure modes</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border border-slate-200 dark:border-slate-600 overflow-hidden">
              <button
                onClick={() => setView('radial')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${view === 'radial' ? 'bg-blue-600 text-white' : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50'}`}
              >Radial diagram</button>
              <button
                onClick={() => setView('list')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${view === 'list' ? 'bg-blue-600 text-white' : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50'}`}
              >List</button>
            </div>
            <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-2xl leading-none">x</button>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-6 px-6 py-3 bg-slate-50 dark:bg-slate-700/30 border-b border-slate-100 dark:border-slate-700 shrink-0">
          {LEGEND.map(l => (
            <span key={l.label} className="flex items-center gap-2 text-sm font-semibold" style={{ color: l.text }}>
              <span className="w-4 h-4 rounded border" style={{ background: l.fill, borderColor: l.stroke }} />
              {l.label}
            </span>
          ))}
        </div>

        {/* Body */}
        <div className={`flex-1 min-h-0 p-4 ${view === 'list' ? 'overflow-y-auto' : 'overflow-hidden flex flex-col'}`}>
          {records.length === 0 && (
            <p className="text-center text-slate-400 py-16 text-sm">No failure modes to display.</p>
          )}

          {records.length > 0 && view === 'radial' && (
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ flex: 1, minHeight: 0, display: 'block' }}>
              {/* Lines from center to each node */}
              {nodes.map((n, i) => (
                <line key={i}
                  x1={CX} y1={CY} x2={n.x} y2={n.y}
                  stroke={n.col.stroke} strokeWidth="1.5" strokeDasharray="5 3" opacity="0.6"
                />
              ))}

              {/* Center circle */}
              <circle cx={CX} cy={CY} r={CR} fill="#dbeafe" stroke="#3b82f6" strokeWidth="2" />
              <foreignObject x={CX - CR + 4} y={CY - CR + 4} width={(CR - 4) * 2} height={(CR - 4) * 2}>
                <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center', fontSize: 13, fontWeight: 700, color: '#1d4ed8', lineHeight: 1.2, padding: 2 }}>
                  {(doc.part_name || 'Product').slice(0, 24)}
                </div>
              </foreignObject>

              {/* Failure mode rectangles */}
              {nodes.map((n, i) => (
                <g key={i}>
                  <rect
                    x={n.x - RW / 2} y={n.y - RH / 2}
                    width={RW} height={RH} rx="6"
                    fill={n.col.fill} stroke={n.col.stroke} strokeWidth="1.8"
                  />
                  <foreignObject x={n.x - RW / 2 + 4} y={n.y - RH / 2 + 4} width={RW - 8} height={RH - 8}>
                    <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center', fontSize: 12, fontWeight: 600, color: n.col.text, lineHeight: 1.25, overflow: 'hidden' }}>
                      {n.label}
                    </div>
                  </foreignObject>
                </g>
              ))}
            </svg>
          )}

          {records.length > 0 && view === 'list' && (
            <div className="space-y-2">
              {records.map((r, i) => {
                const col = failureColor(r)
                return (
                  <div key={i} className="flex items-center gap-3 rounded-xl border px-4 py-3"
                    style={{ borderColor: col.stroke, background: col.fill }}>
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ background: col.stroke }} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold truncate" style={{ color: col.text }}>
                        {r.failure_mode || r.component || `Row ${i + 1}`}
                      </p>
                      <p className="text-xs text-slate-500 truncate mt-0.5">
                        {r.function || r.component || ''}{r.effect ? ` — ${r.effect}` : ''}
                      </p>
                    </div>
                    <span className="text-xs font-medium px-2 py-0.5 rounded-full border shrink-0"
                      style={{ color: col.text, borderColor: col.stroke, background: 'white' }}>
                      {col.label}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function MyFmeasModal({ sessions, onClose, onLoadRecords, onDeleteSession }) {
  const [loadingId, setLoadingId] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const h = e => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', h)
    return () => document.removeEventListener('keydown', h)
  }, [onClose])

  async function openSession(sessionId) {
    setLoadingId(sessionId)
    setError('')
    try {
      const res = await fetch(`${API}/sessions/${sessionId}/document`)
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || `Server error ${res.status}`)
      }
      const data = await res.json()
      onLoadRecords(data)
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoadingId(null)
    }
  }

  async function deleteSession(sessionId, label) {
    const confirmed = window.confirm(`Delete the session "${label}"? This will remove its persisted records.`)
    if (!confirmed) return

    setDeletingId(sessionId)
    setError('')
    try {
      const res = await fetch(`${API}/sessions/${sessionId}`, {
        method: 'DELETE',
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || `Server error ${res.status}`)
      }
      onDeleteSession(sessionId)
    } catch (e) {
      setError(e.message)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white dark:bg-slate-800 rounded-2xl w-full max-w-4xl shadow-2xl border border-slate-200 dark:border-slate-700 flex flex-col max-h-[85vh]">
        <div className="flex items-start justify-between px-6 py-5 border-b border-slate-100 dark:border-slate-700 shrink-0">
          <div>
            <h2 className="text-lg font-bold text-slate-800 dark:text-white">My FMEAs</h2>
            <p className="text-xs text-slate-500 mt-0.5">Persisted sessions available in the database</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-2xl leading-none mt-0.5">×</button>
        </div>

        <div className="px-6 py-5 overflow-y-auto flex-1">
          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-xl text-sm text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {sessions.length === 0 ? (
            <p className="text-center text-slate-400 py-10 text-sm">No persisted sessions found.</p>
          ) : (
            <div className="space-y-3">
              {sessions.map(session => (
                <div key={session.id} className="border border-slate-200 dark:border-slate-700 rounded-xl p-4 bg-slate-50 dark:bg-slate-900/30">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-700 dark:text-slate-200 truncate">
                        {session.part_name || 'Untitled FMEA'}
                      </p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 truncate">
                        {session.supplier || 'Unknown supplier'}
                      </p>
                      <div className="flex flex-wrap gap-3 mt-3 text-xs text-slate-500 dark:text-slate-400">
                        <span>{fmtDate(session.created_at)}</span>
                        <span>{session.record_count || 0} records</span>
                        <span>{session.source_file || 'Manual entry'}</span>
                        <span className="uppercase tracking-wide">{session.status}</span>
                      </div>
                    </div>

                    <div className="shrink-0 flex items-center gap-2">
                      <button
                        onClick={() => deleteSession(session.id, session.part_name || 'Untitled FMEA')}
                        disabled={deletingId === session.id || loadingId === session.id}
                        className="text-sm px-4 py-2 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50 font-medium transition-colors"
                      >
                        {deletingId === session.id ? 'Deleting...' : 'Delete'}
                      </button>
                      <button
                        onClick={() => openSession(session.id)}
                        disabled={loadingId === session.id || deletingId === session.id}
                        className="text-sm px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium transition-colors"
                      >
                        {loadingId === session.id ? 'Opening...' : 'Open'}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [dark,  setDark]  = useState(false)
  const [model, setModel] = useState('RedHatAI/Qwen3.6-35B-A3B-NVFP4')
  const [doc,   setDoc]   = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [myFmeasOpen, setMyFmeasOpen] = useState(false)
  const [myFmeas, setMyFmeas] = useState([])
  const [statusOpen, setStatusOpen] = useState(false)
  const [saveBusy, setSaveBusy] = useState(false)
  const [saveDirty, setSaveDirty] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [saveSuccess, setSaveSuccess] = useState('')

  const [openAbout, setOpenAbout] = useState(false)
  const [open1A,    setOpen1A]    = useState(true)
  const [open1B,    setOpen1B]    = useState(false)
  const [open2,     setOpen2]     = useState(false)

  const [modal, setModal] = useState({ open: false, recordIdx: null, field: '', currentValue: null, loading: false, data: null, error: '' })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    document.body.className = dark ? 'bg-slate-900 text-slate-100 transition-colors' : 'bg-slate-50 text-slate-900 transition-colors'
  }, [dark])

  const handleExtracted = async (newDoc, originalFile = null) => {
    setDoc(newDoc)
    setSaveDirty(false)
    setSaveError('')
    setSaveSuccess('')
    setOpen1A(false)
    setOpen1B(false)
    setOpen2(true)
    try {
      const res = await fetch(`${API}/sessions/from-extraction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          part_name: newDoc.part_name || 'Unknown',
          supplier: newDoc.supplier || 'Unknown',
          source_file: newDoc.source_file || newDoc.part_name || 'upload',
          records: newDoc.records || [],
          columns: newDoc._columns || [],
          document: newDoc,
          language: newDoc.language || 'en',
        }),
      })
      if (res.ok) {
        const d = await res.json()
        setSessionId(d.session_id)
        setSaveSuccess('Session saved from extraction.')
        if (originalFile) {
          const form = new FormData()
          form.append('file', originalFile)
          await fetch(`${API}/sessions/${d.session_id}/files`, {
            method: 'POST',
            body: form,
          })
        }
      }
    } catch (_) {}
  }
  const handleReset     = ()     => { setDoc(null); setSessionId(null); setSaveDirty(false); setSaveError(''); setSaveSuccess(''); setOpen1A(true); setOpen2(false) }

  function handleEdit(gi, field, value) {
    setSaveDirty(true)
    setSaveError('')
    setSaveSuccess('')
    setDoc(prev => ({
      ...prev,
      records: prev.records.map((r, i) => {
        if (i !== gi) return r
        const updated = { ...r, [field]: value }
        if (['severity','occurrence','detection'].includes(field)) {
          const s = +updated.severity, o = +updated.occurrence, d = +updated.detection
          updated.rpn = (s && o && d) ? s * o * d : null
        }
        return updated
      })
    }))
  }

  async function handleAI(gi, field) {
    const r = doc.records[gi]
    setModal({ open: true, recordIdx: gi, field, currentValue: r[field], functionName: r.function || r.component || '', failureMode: r.failure_mode || '', loading: true, data: null, error: '' })
    try {
      const res = await fetch(`${API}/analyze`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field, function: r.function || r.component || '', failure_mode: r.failure_mode || '', context: `Part: ${doc.part_name}. Component: ${r.component || ''}`, model_name: model }),
      })
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `Server error ${res.status}`) }
      const data = await res.json()
      setModal(m => ({ ...m, loading: false, data }))
    } catch(e) { setModal(m => ({ ...m, loading: false, error: e.message })) }
  }

  const applyAI = async (value, justification, sources) => {
    if (modal.recordIdx !== null) {
      const gi = modal.recordIdx
      const field = modal.field
      setSaveDirty(true)
      setSaveError('')
      setSaveSuccess('')
      setDoc(prev => ({
        ...prev,
        records: prev.records.map((r, i) => {
          if (i !== gi) return r
          const updated = { ...r, [field]: value, _aiEdited: true }
          if (['severity', 'occurrence', 'detection'].includes(field)) {
            const s = +updated.severity, o = +updated.occurrence, d = +updated.detection
            updated.rpn = (s && o && d) ? s * o * d : null
          }
          return updated
        })
      }))
    }
    setModal(m => ({ ...m, open: false }))
    if (sessionId && modal.data) {
      try {
        await fetch(`${API}/sessions/${sessionId}/suggestions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            field: modal.field,
            function: modal.functionName || '',
            failure_mode: modal.failureMode || '',
            current_value: modal.currentValue != null ? String(modal.currentValue) : null,
            suggested_value: value,
            justification: justification || modal.data.justification || '',
            agent_name: modal.data.agent_name || '',
            agent_color: modal.data.agent_color || '',
            sources: sources || modal.data.sources || [],
            judge_verdict: modal.data.judge_verdict || null,
            judge_correct_points: modal.data.judge_correct_points || null,
            judge_incorrect_points: modal.data.judge_incorrect_points || null,
            judge_confidence: modal.data.judge_confidence ?? null,
            human_verdict: 'accepted',
            model_name: model,
          }),
        })
      } catch (_) {}
    }
  }

  const dismissAI = async () => {
    if (sessionId && modal.data) {
      try {
        await fetch(`${API}/sessions/${sessionId}/suggestions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            field: modal.field,
            function: modal.functionName || '',
            failure_mode: modal.failureMode || '',
            current_value: modal.currentValue != null ? String(modal.currentValue) : null,
            suggested_value: String(modal.data.suggested_value ?? ''),
            justification: modal.data.justification || '',
            agent_name: modal.data.agent_name || '',
            agent_color: modal.data.agent_color || '',
            sources: modal.data.sources || [],
            judge_verdict: modal.data.judge_verdict || null,
            judge_correct_points: modal.data.judge_correct_points || null,
            judge_incorrect_points: modal.data.judge_incorrect_points || null,
            judge_confidence: modal.data.judge_confidence ?? null,
            human_verdict: 'rejected',
            model_name: model,
          }),
        })
      } catch (_) {}
    }
    setModal(m => ({ ...m, open: false }))
  }

  const openMyFmeas = async () => {
    try {
      const res = await fetch(`${API}/sessions`)
      if (res.ok) {
        const d = await res.json()
        setMyFmeas(d.sessions || [])
      }
    } catch (_) {}
    setMyFmeasOpen(true)
  }

  const handleDelete = gi => {
    setSaveDirty(true)
    setSaveError('')
    setSaveSuccess('')
    setDoc(prev => ({ ...prev, records: prev.records.filter((_, i) => i !== gi) }))
  }

  const handleAddSuggestedFailure = suggestion => {
    const normalize = s => (s || '').trim().toLowerCase()
    const alreadyExists = doc.records.some(
      r => normalize(r.failure_mode) === normalize(suggestion.failure_mode)
    )
    if (alreadyExists) return
    const existing  = doc.records.find(r => (r.function || r.component || '') === suggestion.function)
    const component = existing ? (existing.component || '') : ''
    setSaveDirty(true)
    setSaveError('')
    setSaveSuccess('')
    setDoc(prev => ({ ...prev, records: [...prev.records, {
      component, function: suggestion.function, failure_mode: suggestion.failure_mode,
      effect: suggestion.effect, cause: suggestion.cause,
      severity: null, occurrence: null, detection: null, rpn: null,
      current_controls_prevention: '', current_controls_detection: '', recommended_action: '',
      source_file: 'AI suggestion',
      _aiNew: true,
    }]}))
  }

  const handleSaveSession = async () => {
    if (!sessionId || !doc || saveBusy) return

    setSaveBusy(true)
    setSaveError('')
    setSaveSuccess('')
    try {
      const res = await fetch(`${API}/sessions/${sessionId}/document`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          part_name: doc.part_name || 'Unknown',
          supplier: doc.supplier || 'Unknown',
          source_file: doc.source_file || doc.part_name || 'upload',
          records: doc.records || [],
          columns: doc._columns || [],
          document: doc,
          language: doc.language || 'en',
          status: 'in_progress',
        }),
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || `Server error ${res.status}`)
      }
      setSaveDirty(false)
      setSaveSuccess('Session saved successfully.')
      setMyFmeas(prev => prev.map(session => (
        session.id === sessionId
          ? {
              ...session,
              part_name: doc.part_name || session.part_name,
              supplier: doc.supplier || session.supplier,
              source_file: doc.source_file || session.source_file,
              record_count: doc.records?.length || 0,
              status: 'in_progress',
            }
          : session
      )))
    } catch (e) {
      setSaveError(e.message)
    } finally {
      setSaveBusy(false)
    }
  }

  return (
    <div className="min-h-screen transition-colors duration-300">
      <div className="max-w-screen-xl mx-auto px-6 py-8">
        <Header model={model} setModel={setModel} dark={dark} toggleDark={() => setDark(d => !d)} onMyFmeas={openMyFmeas} />

        <Accordion title="About" open={openAbout} onToggle={() => setOpenAbout(o => !o)}>
          <ul className="space-y-2.5 text-sm">
            {['Multi-Agent Orchestration','Knowledge Engineering','Human-in-the-Loop (HITL)'].map(item => (
              <li key={item} className="flex items-center gap-2.5">
                <span className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
                <strong className="text-slate-700 dark:text-slate-300">{item}</strong>
              </li>
            ))}
          </ul>
        </Accordion>

        <div className="flex items-stretch gap-0">
          <div className="flex-1"><UploadSection  open={open1A} onToggle={() => setOpen1A(o => !o)} model={model} onExtracted={handleExtracted} /></div>
          <div className="flex items-center justify-center px-4">
            <span className="text-xs font-bold text-slate-400 bg-slate-100 dark:bg-slate-700 dark:text-slate-500 px-2 py-1 rounded-full border border-slate-200 dark:border-slate-600">OR</span>
          </div>
          <div className="flex-1"><NewFmeaSection open={open1B} onToggle={() => setOpen1B(o => !o)} onCreated={handleExtracted} /></div>
        </div>

        <ResultsSection open={open2} onToggle={() => setOpen2(o => !o)} doc={doc} onReset={handleReset} onEdit={handleEdit} onDelete={handleDelete} onAI={handleAI} model={model} onAddSuggestedFailure={handleAddSuggestedFailure} onShowStatus={() => setStatusOpen(true)} onSaveSession={handleSaveSession} saveBusy={saveBusy} saveDirty={saveDirty} saveError={saveError} saveSuccess={saveSuccess} />
        <AIModal modal={modal} onApply={applyAI} onDismiss={dismissAI} onClose={() => setModal(m => ({ ...m, open: false }))} />
        {statusOpen && <FailureStatusModal doc={doc} onClose={() => setStatusOpen(false)} />}
        {myFmeasOpen && (
          <MyFmeasModal
            sessions={myFmeas}
            onClose={() => setMyFmeasOpen(false)}
            onDeleteSession={deletedId => {
              setMyFmeas(prev => prev.filter(session => session.id !== deletedId))
              if (sessionId === deletedId) {
                setSessionId(null)
                setDoc(null)
                setOpen2(false)
                setOpen1A(true)
              }
            }}
            onLoadRecords={loaded => {
              setSessionId(loaded.session_id)
              setSaveDirty(false)
              setSaveError('')
              setSaveSuccess('Session loaded from persistence.')
              setDoc({
                part_name: loaded.part_name,
                supplier: loaded.supplier,
                source_file: loaded.source_file,
                _columns: loaded.columns || [],
                records: loaded.records || [],
              })
              setOpen2(true)
              setOpen1A(false)
              setOpen1B(false)
            }}
          />
        )}
      </div>
    </div>
  )
}
