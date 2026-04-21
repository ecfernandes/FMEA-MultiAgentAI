import { useState, useRef, useCallback, Fragment } from 'react'
import s from './Dashboard.module.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ── Helpers ──────────────────────────────────────────────────────────────────

function rpnClass(rpn) {
  if (!rpn) return s.rpnEmpty
  if (rpn > 100) return s.rpnHigh
  if (rpn > 40)  return s.rpnMed
  return s.rpnLow
}

function sodClass(val) {
  if (!val) return s.sodEmpty
  if (val >= 8) return s.sodHigh
  if (val >= 5) return s.sodMed
  return s.sodLow
}

function groupByFunction(records) {
  const map = new Map()
  for (const r of records) {
    const fn = r.function || r.component || 'Unknown Function'
    if (!map.has(fn)) map.set(fn, [])
    map.get(fn).push(r)
  }
  return map
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Badge({ value, cls, empty = '—' }) {
  return (
    <span className={`${s.badge} ${cls}`}>
      {value ?? empty}
    </span>
  )
}

const SKIP_COLS  = new Set(['function', 'component', 'source_file', 'sheet_name', 'row_number'])
const SOD_COLS   = ['severity', 'occurrence', 'detection']
const FIXED_COLS = ['failure_mode', 'effect', 'cause']

function colLabel(k) {
  return k.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

function RecordTable({ records }) {
  if (!records.length)
    return <p className={s.empty}>No records for this function.</p>

  const allKeys    = [...new Set(records.flatMap(r => Object.keys(r)))]
  const skipAll    = new Set([...SKIP_COLS, ...SOD_COLS, 'rpn', ...FIXED_COLS])
  const extraCols  = allKeys.filter(k => !skipAll.has(k))
  const displayCols = [...FIXED_COLS, ...extraCols]

  return (
    <div className={s.tableWrap}>
      <table className={s.table}>
        <thead>
          <tr>
            {displayCols.map(k => <th key={k}>{colLabel(k)}</th>)}
            {SOD_COLS.map(k => <th key={k} className={s.center}>{k[0].toUpperCase()}</th>)}
            <th className={s.center}>RPN</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r, i) => {
            const isCritical = (r.severity ?? 0) >= 8 && (r.rpn ?? 0) > 36
            const totalCols  = displayCols.length + SOD_COLS.length + 1
            return (
              <Fragment key={i}>
                {isCritical && (
                  <tr>
                    <td colSpan={totalCols} className={s.criticalBanner}>
                      ⚠ Exceeds the critical threshold of 36
                    </td>
                  </tr>
                )}
                <tr>
                  {displayCols.map((k, ci) => (
                    <td key={k} className={ci === 0 ? s.bold : s.muted}>{r[k] || '—'}</td>
                  ))}
                  <td className={s.center}><Badge value={r.severity}   cls={isCritical ? s.criticalBadge : sodClass(r.severity)}   /></td>
                  <td className={s.center}><Badge value={r.occurrence} cls={sodClass(r.occurrence)} /></td>
                  <td className={s.center}><Badge value={r.detection}  cls={sodClass(r.detection)}  /></td>
                  <td className={s.center}><Badge value={r.rpn}        cls={isCritical ? s.criticalBadge : rpnClass(r.rpn)}        /></td>
                </tr>
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Main Dashboard ────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [apiKey, setApiKey]       = useState(() => sessionStorage.getItem('fmea_key') || '')
  const [file, setFile]           = useState(null)
  const [loading, setLoading]     = useState(false)
  const [result, setResult]       = useState(null)
  const [error, setError]         = useState(null)
  const [dragOver, setDragOver]   = useState(false)
  const [activeFunc, setActiveFunc] = useState(0)
  const fileInputRef = useRef()

  const handleApiKey = (v) => {
    setApiKey(v)
    sessionStorage.setItem('fmea_key', v)
  }

  const handleFile = (f) => {
    setFile(f)
    setResult(null)
    setError(null)
    setActiveFunc(0)
  }

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }, [])

  const extract = async () => {
    if (!file)   return setError('Please select a file (PDF or Excel).')
    if (!apiKey) return setError('Please enter your UTC platform API key.')

    setLoading(true)
    setError(null)

    try {
      const form = new FormData()
      form.append('file', file)

      const res = await fetch(`${API_URL}/extract`, {
        method: 'POST',
        headers: { 'X-API-Key': apiKey },
        body: form,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Server error ${res.status}`)
      }

      const data = await res.json()
      setResult(data)
      setActiveFunc(0)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // Build function groups from result
  const fnGroups = result ? groupByFunction(result.document.records) : new Map()
  const fnList   = [...fnGroups.keys()]
  const activeRecords = fnList.length ? fnGroups.get(fnList[activeFunc]) || [] : []

  return (
    <div className={s.shell}>
      {/* ── Header ── */}
      <header className={s.header}>
        <div className={s.headerInner}>
          <div>
            <h1 className={s.title}>AI-Driven FMEA <span className={s.version}>5.0</span></h1>
            <p className={s.subtitle}>UTFPR (Brazil) · UTC (France) · 2026</p>
          </div>
          <div className={s.headerControls}>
            <button className={s.btnTelemetry} disabled>
              System Telemetry
            </button>
            <input
            className={s.keyInput}
            type="password"
            placeholder="🔑  UTC API Key  (sk-)"
            value={apiKey}
            onChange={e => handleApiKey(e.target.value)}
            aria-label="UTC platform API key"
          />
          </div>
        </div>
      </header>

      <main className={s.main}>
        {/* ── Step 1: Upload ── */}
        {!result && (
          <section className={s.card}>
            <h2 className={s.stepTitle}>Step 1 — Upload FMEA Document</h2>
            <p className={s.hint}>Accepts PDF or Excel (.xlsx/.xls)</p>

            <div
              className={`${s.dropZone} ${dragOver ? s.dropActive : ''} ${file ? s.dropHasFile : ''}`}
              onDragOver={e => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current.click()}
              role="button"
              tabIndex={0}
              onKeyDown={e => e.key === 'Enter' && fileInputRef.current.click()}
              aria-label="File upload area"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.xlsx,.xls"
                hidden
                onChange={e => e.target.files[0] && handleFile(e.target.files[0])}
              />
              <div className={s.dropIcon}>{file ? '📄' : '📂'}</div>
              {file
                ? <><strong>{file.name}</strong><span className={s.fileSize}>{(file.size / 1024).toFixed(1)} KB</span></>
                : <><strong>Drop your FMEA file here</strong><span>or click to browse — PDF or Excel</span></>
              }
            </div>

            {error && <div className={s.errorBox}>{error}</div>}

            <button
              className={s.btnPrimary}
              onClick={extract}
              disabled={loading || !file}
            >
              {loading
                ? <><span className={s.spinner} />Extracting…</>
                : '⚡ Extract FMEA'}
            </button>
          </section>
        )}

        {/* ── Step 2: Results ── */}
        {result && (
          <>
            {/* Document banner */}
            <section className={s.docBanner}>
              <div className={s.docMeta}>
                <span className={s.metaItem}><span className={s.metaLabel}>Part</span>{result.document.part_name}</span>
                <span className={s.metaDivider} />
                <span className={s.metaItem}><span className={s.metaLabel}>Supplier</span>{result.document.supplier}</span>
                <span className={s.metaDivider} />
                <span className={s.metaItem}><span className={s.metaLabel}>Records</span>{result.document.records.length}</span>
                <span className={s.metaDivider} />
                <span className={s.metaItem}><span className={s.metaLabel}>File</span>{result.document.source_file}</span>
              </div>
              <div className={s.headerActions}>
                <button className={s.btnSecondary} onClick={() => { setResult(null); setFile(null) }}>
                  ← New Document
                </button>
                <button className={s.btnDashboard} disabled>
                  FMEA Dashboards
                </button>
                <button className={s.btnReport} disabled>
                  FMEA Report
                </button>
              </div>
            </section>

            {/* Function pills navigation */}
            {fnList.length > 1 && (
              <div className={s.pills}>
                {fnList.map((fn, i) => (
                  <button
                    key={i}
                    className={`${s.pill} ${i === activeFunc ? s.pillActive : ''}`}
                    onClick={() => setActiveFunc(i)}
                    title={fn}
                  >
                    <span className={s.pillIdx}>F{i + 1}</span>
                    <span className={s.pillLabel}>{fn.length > 45 ? fn.slice(0, 44) + '…' : fn}</span>
                    <span className={s.pillCount}>{fnGroups.get(fn).length}</span>
                  </button>
                ))}
              </div>
            )}

            {/* Active function header */}
            <div className={s.fnHeader}>
              <h3 className={s.fnTitle}>
                <span className={s.fnBadge}>F{activeFunc + 1}</span>
                {fnList[activeFunc]}
              </h3>
              <span className={s.fnCount}>{activeRecords.length} failure mode{activeRecords.length !== 1 ? 's' : ''}</span>
            </div>

            {/* FMEA table */}
            <RecordTable records={activeRecords} />
          </>
        )}
      </main>
    </div>
  )
}
