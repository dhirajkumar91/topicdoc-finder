import { useState } from 'react'
import {
  Search,
  FileText,
  ChevronDown,
  ChevronUp,
  Loader2,
  Database,
} from 'lucide-react'
import { searchKnowledgeBase } from '../services/searchService'

function formatScore(score) {
  if (typeof score !== 'number') return 'N/A'
  return `${(score * 100).toFixed(1)}%`
}

function getTableRows(table) {
  const sourceRows = Array.isArray(table.table_data) ? table.table_data : []

  if (sourceRows.length === 0) {
    return { columns: [], rows: [] }
  }

  const declaredColumns =
    (Array.isArray(table.column_headers) && table.column_headers.length) ||
    Number(table.column_count) ||
    Number(table.validation_results?.column_count) ||
    Number(table.validation?.column_count) ||
    0

  const isFlatData = !Array.isArray(sourceRows[0]) && (
    sourceRows[0] === null || typeof sourceRows[0] !== 'object'
  )

  let rows = sourceRows

  // Some API responses serialize normalized cells as one flat array.
  // Rebuild the original rows using the table's stored dimensions.
  if (isFlatData) {
    let width = Number(declaredColumns) || 0

    if (!width && Number(table.row_count) > 0 &&
        sourceRows.length % Number(table.row_count) === 0) {
      width = sourceRows.length / Number(table.row_count)
    }

    if (!width) {
      // Fallback for flat arrays without dimensions: a header row is commonly
      // followed by the first numeric data cell. Use that boundary as width.
      const firstNumericIndex = sourceRows.findIndex((value, index) =>
        index > 1 && isNumericCell(value)
      )
      if (firstNumericIndex > 1) width = firstNumericIndex
    }

    if (!width || width < 1 || sourceRows.length % width !== 0) {
      width = 1
    }

    rows = []
    for (let index = 0; index < sourceRows.length; index += width) {
      rows.push(sourceRows.slice(index, index + width))
    }
  }

  // Normalize object-shaped rows.
  rows = rows.map((row) => {
    if (Array.isArray(row)) return row
    if (row && typeof row === 'object') return Object.values(row)
    return [row]
  })

  // Some PDFs use a two-column page layout. PyMuPDF can then return one
  // logical table spread across many mostly-empty columns. The state-wise
  // COVID table is recognizable by its four headers and state-name rows.
  // Compact only this clearly identifiable sparse layout; do not compact
  // ordinary tables, where empty cells may be meaningful.
  let normalizedDeclaredColumns = Number(declaredColumns) || 0
  const nonEmpty = (row) =>
    row.filter((cell) => cell !== null && cell !== undefined &&
      String(cell).trim() !== '')

  const rawHeaderCells = nonEmpty(rows[0] || []).map((cell) =>
    String(cell).trim()
  )
  const headerText = rawHeaderCells.join(' ').toLowerCase()
  const looksLikeStateCasesTable =
    rows.length >= 3 &&
    (rows[0]?.length || 0) >= 7 &&
    /state\s*name/.test(headerText) &&
    /confirmed/.test(headerText) &&
    /recovered/.test(headerText) &&
    /death/.test(headerText) &&
    rawHeaderCells.length === 4

  if (looksLikeStateCasesTable) {
    rows = rows.map((row, rowIndex) => {
      const cells = nonEmpty(row)

      // A stray single-character OCR fragment (for example "h") appears
      // in an otherwise numeric state row in this source PDF.
      if (rowIndex > 0) {
        return cells.filter((cell, index) => {
          const value = String(cell).trim()
          if (index > 0 && /^[A-Za-z]$/.test(value)) return false
          return true
        })
      }

      return cells
    })

    normalizedDeclaredColumns = 4
  }

  const width = Math.max(
    normalizedDeclaredColumns,
    ...rows.map((row) => row.length),
  )

  rows = rows.map((row) =>
    Array.from({ length: width }, (_, index) => row[index] ?? null)
  )

  const explicitHeaders = Array.isArray(table.column_headers)
    ? table.column_headers.map((header, index) => {
        if (typeof header === 'string') return header
        if (header && typeof header === 'object') {
          return String(
            header.name ?? header.label ?? header.title ?? `Column ${index + 1}`
          )
        }
        return `Column ${index + 1}`
      })
    : []

  const firstRow = rows[0] || []
  const followingRows = rows.slice(1)

  // When headers were stored as the first row of table_data, recognize them
  // only when subsequent rows contain numeric values in data columns.
  const firstRowLooksLikeHeader =
    !explicitHeaders.length &&
    firstRow.length > 1 &&
    firstRow.every((cell) => typeof cell === 'string' && cell.trim()) &&
    firstRow.some((cell) => /[a-z]/i.test(cell)) &&
    followingRows.some((row) =>
      row.slice(1).some((cell) =>
        cell != null && cell !== '' &&
        /^[-+]?[\d,.]+%?$/.test(String(cell).trim())
      )
    )

  const columns = explicitHeaders.length
    ? Array.from({ length: width }, (_, index) =>
        explicitHeaders[index] || `Column ${index + 1}`
      )
    : firstRowLooksLikeHeader
      ? firstRow.map((cell, index) => String(cell || `Column ${index + 1}`))
      : Array.from({ length: width }, (_, index) => `Column ${index + 1}`)

  if (firstRowLooksLikeHeader) {
    rows = followingRows

    // PyMuPDF can split a multi-line header across two columns while merging
    // the corresponding two data values into the first cell. For example:
    // headers: ["Total confirmed (increa cases", "sedno)"]
    // row:     ["3588 2601,,", ""]
    // should become headers ["Total confirmed cases", "(increased no)"]
    // and cells ["3588", "2601"].
    const splitHeaderPairs = []

    for (let index = 0; index < firstRow.length - 1; index += 1) {
      const currentHeader = String(firstRow[index] ?? '').toLowerCase()
      const nextHeader = String(firstRow[index + 1] ?? '').toLowerCase()
      const isSplitIncreaseHeader =
        /increa/.test(currentHeader) && /^\s*sed\s*no\b/.test(nextHeader)

      if (isSplitIncreaseHeader) {
        splitHeaderPairs.push(index)
      }
    }

    if (splitHeaderPairs.length > 0) {
      splitHeaderPairs.forEach((columnIndex) => {
        const baseHeader = String(columns[columnIndex] ?? '')
          .replace(/\s*\(?increa.*$/i, '')
          .trim()
        columns[columnIndex] = baseHeader || `Column ${columnIndex + 1}`
        columns[columnIndex + 1] = '(increased no)'
      })

      rows = rows.map((row) => {
        const repairedRow = [...row]

        splitHeaderPairs.forEach((columnIndex) => {
          const currentValue = repairedRow[columnIndex]
          const nextValue = repairedRow[columnIndex + 1]
          const nextCellIsEmpty =
            nextValue === null || nextValue === undefined || String(nextValue).trim() === ''

          if (!nextCellIsEmpty || currentValue === null || currentValue === undefined) {
            return
          }

          const valueText = String(currentValue).trim()
          // Match two distinct numeric values separated by whitespace. Commas
          // inside a number are allowed; trailing OCR punctuation is removed.
          const numericParts = valueText.match(/[-+]?\d[\d,]*(?:\.\d+)?%?/g) || []
          const remainder = valueText
            .replace(/[-+]?\d[\d,]*(?:\.\d+)?%?/g, '')
            .replace(/[\s,.;]/g, '')

          if (numericParts.length === 2 && remainder === '') {
            repairedRow[columnIndex] = numericParts[0].replace(/[,.;]+$/, '')
            repairedRow[columnIndex + 1] = numericParts[1].replace(/[,.;]+$/, '')
          }
        })

        return repairedRow
      })
    }
  }
  return { columns, rows }
}

function getCellValue(row, column, index) {
  let value

  if (Array.isArray(row)) {
    value = row[index]
  } else if (row && typeof row === 'object') {
    value = row[column]
  } else {
    value = row
  }

  if (value === null || value === undefined || value === '') return '—'

  if (typeof value === 'object') {
    return JSON.stringify(value)
  }

  // Format whole-number table cells with thousands separators without
  // changing percentages, decimals, dates, or other text values.
  if (typeof value === 'number' && Number.isSafeInteger(value)) {
    return new Intl.NumberFormat('en-US').format(value)
  }

  const text = String(value).trim()
  if (/^[-+]?\d[\d,]*[,.]?$/.test(text)) {
    // Remove OCR/extraction punctuation at the end (e.g. "2040,") and
    // normalize existing grouping before applying consistent formatting.
    const normalized = text.replace(/[,.]+$/, '').replace(/,/g, '')
    const numericValue = Number(normalized)

    if (Number.isSafeInteger(numericValue)) {
      return new Intl.NumberFormat('en-US').format(numericValue)
    }
  }

  return String(value)
}

function isNumericCell(value) {
  if (value === null || value === undefined || value === '') return false

  // PDF extraction can leave punctuation after numeric values, for example
  // "723%." or "577% -.". Ignore those trailing OCR marks when deciding
  // alignment, but keep the original displayed value unchanged.
  const normalized = String(value)
    .trim()
    .replace(/\s+/g, '')
    .replace(/[.,;:]+$/g, '')
    .replace(/-$/g, '')

  return /^[-+]?(?:\d[\d,]*(?:\.\d+)?|\.\d+)%?$/.test(normalized)
}
function normalizeTableValue(value) {
  return String(value ?? '')
    .toLowerCase()
    .replace(/[\u00a0\s]+/g, '')
    .replace(/[^a-z0-9%+-]/g, '')
}

function collectTableValues(value, output = []) {
  if (value == null) return output

  if (Array.isArray(value)) {
    value.forEach((item) => collectTableValues(item, output))
    return output
  }

  if (typeof value === 'object') {
    Object.values(value).forEach((item) => collectTableValues(item, output))
    return output
  }

  if (typeof value === 'string' || typeof value === 'number') {
    const text = String(value).trim()
    if (text) output.push(text)
  }

  return output
}

function passageOverlapsTablePage(passage, table) {
  const passageStart = Number(passage?.page_start)
  const passageEnd = Number(passage?.page_end ?? passage?.page_start)
  const tableStart = Number(table?.page_start)
  const tableEnd = Number(table?.page_end ?? table?.page_start)

  // If page metadata is missing, rely on content evidence instead.
  if (![passageStart, passageEnd, tableStart, tableEnd].every(Number.isFinite)) {
    return true
  }

  return passageStart <= tableEnd && tableStart <= passageEnd
}

function removeEmbeddedTableText(content, tables = [], passage = {}) {
  if (!content) return ''

  let cleaned = String(content)
  const relevantTables = tables.filter((table) =>
    passageOverlapsTablePage(passage, table)
  )

  if (!relevantTables.length) return cleaned.trim()

  const normalizeWithMap = (value) => {
    let normalized = ''
    const originalIndexes = []

    for (let index = 0; index < value.length; index += 1) {
      const character = value[index]
      if (/[a-z0-9]/i.test(character)) {
        normalized += character.toLowerCase()
        originalIndexes.push(index)
      }
    }

    return { normalized, originalIndexes }
  }

  // First handle chunks that contain the table caption. Keep the explanatory
  // text before the caption; the structured table is rendered below.
  const contentMap = normalizeWithMap(cleaned)
  let earliestTableStart = -1

  for (const table of relevantTables) {
    const title = String(table.table_title || '').trim()
    if (title.length >= 12) {
      const normalizedTitle = normalizeWithMap(title).normalized
      if (normalizedTitle.length >= 12) {
        const matchIndex = contentMap.normalized.indexOf(normalizedTitle)
        if (matchIndex !== -1) {
          const originalIndex = contentMap.originalIndexes[matchIndex]
          if (earliestTableStart === -1 || originalIndex < earliestTableStart) {
            earliestTableStart = originalIndex
          }
        }
      }
    }
  }

  if (earliestTableStart === -1) {
    for (const table of relevantTables) {
      const number = table.table_number ?? table.table_index
      if (number == null) continue
      const safeNumber = String(number).replace(/[^0-9]/g, '')
      if (!safeNumber) continue
      const captionPattern = new RegExp(
        `(?:^|\\n)\\s*Table\\s*${safeNumber}\\s*[:.]?`,
        'i'
      )
      const match = captionPattern.exec(cleaned)
      if (match) {
        const originalIndex = match.index + (match[0].startsWith('\n') ? 1 : 0)
        if (earliestTableStart === -1 || originalIndex < earliestTableStart) {
          earliestTableStart = originalIndex
        }
      }
    }
  }

  if (earliestTableStart !== -1) {
    cleaned = cleaned.slice(0, earliestTableStart)
    return cleaned.replace(/[\s|;,:-]+$/g, '').trim()
  }

  // Captions are often absent from PDF chunks. Build a vocabulary from the
  // structured cells so table values can still be recognized in flattened
  // (one-cell-per-line or column-major) extraction output.
  const tableValues = new Set()
  for (const table of relevantTables) {
    collectTableValues(table.column_headers, [])
      .concat(collectTableValues(table.table_data, []))
      .concat(collectTableValues(table.table_text, []))
      .forEach((value) => {
        const normalized = normalizeTableValue(value)
        if (normalized.length >= 2) tableValues.add(normalized)
      })
  }

  const lines = cleaned.split(/\r?\n/)
  const meaningfulLines = lines
    .map((line) => line.trim())
    .filter(Boolean)

  if (!meaningfulLines.length) return ''

  const normalizedLines = meaningfulLines.map(normalizeTableValue)
  const matchingCellLines = normalizedLines.filter((line) =>
    line && tableValues.has(line)
  ).length

  const cellMatchRatio = matchingCellLines / meaningfulLines.length
  const shortLineRatio =
    meaningfulLines.filter((line) => line.length <= 55).length /
    meaningfulLines.length
  const structuredLineRatio =
    meaningfulLines.filter((line) =>
      /^(?:[a-z]{3,}\s*)?\d{1,2}(?:st|nd|rd|th)?$|^[-+]?\d[\d,.]*%?[-.]?$|^[-+]?\d[\d,.]*\s*%$|^[a-z][a-z\s-]{1,24}$/i.test(line)
    ).length / meaningfulLines.length

  // Table-only chunks are commonly short, line-oriented lists of dates,
  // percentages, state names and numeric cells. Do not render them as prose.
  const isTableDominated =
    meaningfulLines.length >= 7 &&
    (
      (matchingCellLines >= 5 && cellMatchRatio >= 0.35) ||
      (shortLineRatio >= 0.78 && structuredLineRatio >= 0.62 &&
        matchingCellLines >= 3)
    )

  if (isTableDominated) return ''

  // For mixed prose/table chunks, remove individual lines that are exact
  // matches for structured cells while retaining the explanatory paragraphs.
  const filteredLines = lines.filter((line) => {
    const normalized = normalizeTableValue(line)
    return !normalized || !tableValues.has(normalized)
  })

  const remaining = filteredLines.join('\n').trim()

  // A final safeguard: if the remaining content still consists almost
  // entirely of short numeric/date fragments, suppress it as table content.
  const remainingLines = remaining.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  if (
    remainingLines.length >= 7 &&
    remainingLines.filter((line) => line.length <= 55).length / remainingLines.length >= 0.85 &&
    remainingLines.filter((line) => /[\d%]/.test(line)).length / remainingLines.length >= 0.6
  ) {
    return ''
  }

  return remaining
    .replace(/[\s|;,:-]+$/g, '')
    .trim()
}

function TablePreview({ table, compact = false }) {
  const { columns, rows } = getTableRows(table)

  if (rows.length === 0) {
    return (
      <p className="py-4 text-sm text-slate-500">
        No normalized table rows are available.
      </p>
    )
  }

  const visibleRows = compact ? rows.slice(0, 5) : rows

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-sm">
          <thead>
            <tr className="bg-slate-100">
              {columns.map((column, index) => (
                <th
                  key={`${column}-${index}`}
                  scope="col"
                  className={[
                    'border-b border-r border-slate-200 px-4 py-3.5',
                    'text-left text-xs font-semibold uppercase tracking-wide',
                    'text-slate-700 last:border-r-0',
                    index === 0 ? 'min-w-[180px]' : 'min-w-[130px]',
                  ].join(' ')}
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {visibleRows.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className={[
                  'transition-colors hover:bg-indigo-50/50',
                  rowIndex % 2 === 0 ? 'bg-white' : 'bg-slate-50/70',
                ].join(' ')}
              >
                {columns.map((column, columnIndex) => {
                  const value = row[columnIndex]
                  const displayValue = getCellValue(row, column, columnIndex)
                  const numeric = isNumericCell(value)

                  return (
                    <td
                      key={`${rowIndex}-${columnIndex}`}
                      className={[
                        'border-b border-r border-slate-100 px-4 py-3',
                        'text-slate-700 last:border-r-0 whitespace-nowrap',
                        columnIndex === 0
                          ? 'font-medium text-slate-800'
                          : 'tabular-nums',
                        numeric ? 'text-right' : 'text-left',
                      ].join(' ')}
                    >
                      {displayValue}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {compact && rows.length > visibleRows.length && (
        <div className="border-t border-slate-200 bg-slate-50 px-4 py-2.5 text-xs text-slate-500">
          Showing {visibleRows.length} of {rows.length} rows. Expand to view the complete table.
        </div>
      )}
    </div>
  )
}

export default function UserSearch() {
  const [query, setQuery] = useState('')

  const [results, setResults] = useState([])
  const [totalResults, setTotalResults] = useState(0)

  const [relevantTables, setRelevantTables] = useState([])

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)

  const [expandedPapers, setExpandedPapers] = useState({})
  const [expandedTables, setExpandedTables] = useState({})

  const handleSearch = async (e) => {
    e.preventDefault()

    if (!query.trim()) return

    setLoading(true)
    setError('')
    setHasSearched(false)

    setResults([])
    setTotalResults(0)

    setRelevantTables([])

    setExpandedPapers({})
    setExpandedTables({})

    try {
      const data = await searchKnowledgeBase(query.trim())

      setResults(data.results || [])
      setTotalResults(data.total_results || 0)

      setRelevantTables(data.relevant_tables || [])

      setHasSearched(true)
    } catch (err) {
      setError(err.message || 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  const togglePaper = (documentId) => {
    setExpandedPapers((prev) => ({
      ...prev,
      [documentId]: !prev[documentId],
    }))
  }

  const toggleTable = (tableId) => {
    setExpandedTables((prev) => ({
      ...prev,
      [tableId]: !prev[tableId],
    }))
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Page heading */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          Knowledge Base Search
        </h1>
        <p className="mt-2 text-slate-500">
          Discover relevant information from your indexed research documents.
        </p>
      </div>

      {/* Search form */}
      <form onSubmit={handleSearch}>
        <div className="flex items-center gap-3 bg-white border border-slate-200 rounded-2xl p-2 shadow-sm focus-within:ring-2 focus-within:ring-indigo-100 focus-within:border-indigo-400 transition">
          <Search className="ml-3 text-slate-400 shrink-0" size={20} />

          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question about your research documents..."
            className="flex-1 outline-none bg-transparent py-3 text-sm text-slate-700 placeholder:text-slate-400"
          />

          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-5 py-3 rounded-xl text-sm font-medium flex items-center gap-2 transition"
          >
            {loading ? (
              <Loader2 size={17} className="animate-spin" />
            ) : (
              <Search size={17} />
            )}
            Search
          </button>
        </div>
      </form>

      {/* Search info */}
      <div className="flex items-center justify-between mt-4 mb-8">
        <p className="text-xs text-slate-400">
          Semantic search across your locally indexed documents and tables
        </p>

        <span className="text-xs bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full">
          Knowledge Base
        </span>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 rounded-xl border border-red-200 bg-red-50 text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="py-20 flex flex-col items-center text-slate-500">
          <Loader2 size={32} className="animate-spin text-indigo-600 mb-4" />
          <p className="text-sm">Searching documents and tables...</p>
        </div>
      )}

      {!loading && hasSearched && (
        <div className="space-y-10">

          {/* Document results with their relevant tables displayed inline */}
      <section>
        <div className="mb-5">
          <h2 className="text-lg font-semibold text-slate-800">
            Relevant Research Documents
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            {totalResults} relevant {totalResults === 1 ? 'paper' : 'papers'} found
          </p>
        </div>

        {results.length > 0 ? (
          <div className="space-y-5">
            {results.map((paper) => {
              const isExpanded = expandedPapers[paper.document_id]
              const paperTables = relevantTables.filter(
                (table) => table.document_id === paper.document_id
              )
              const passages = (paper.relevant_passages || [])
                .map((passage) => ({
                  ...passage,
                  displayContent: removeEmbeddedTableText(
                    passage.content,
                    paperTables,
                    passage
                  ),
                }))
                .filter((passage) => passage.displayContent)

              const passageCount = passages.length

              return (
                <div
                  key={paper.document_id}
                  className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden"
                >
                  {/* Paper header */}
                  <div className="p-6">
                    <div className="flex items-start gap-4">
                      <div className="h-11 w-11 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
                        <FileText size={21} />
                      </div>

                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-slate-900 leading-snug">
                          {paper.title || 'Untitled Document'}
                        </h3>

                        <div className="flex flex-wrap items-center gap-3 mt-3">
                          <span className="text-xs text-slate-500">
                            {paper.source_name || 'Local Document'}
                          </span>

                          <span className="text-xs bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-full font-medium">
                            Relevance {formatScore(paper.similarity_score)}
                          </span>

                          <span className="text-xs text-slate-400">
                            {paper.retrieved_chunk_count} retrieved chunks
                          </span>

                          {paperTables.length > 0 && (
                            <span className="text-xs bg-purple-50 text-purple-700 px-2.5 py-1 rounded-full font-medium">
                              {paperTables.length} relevant {paperTables.length === 1 ? 'table' : 'tables'}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Expand button */}
                    <button
                      type="button"
                      onClick={() => togglePaper(paper.document_id)}
                      className="mt-5 flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-800 transition"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp size={17} />
                          Hide relevant content
                        </>
                      ) : (
                        <>
                          <ChevronDown size={17} />
                          View relevant content ({passageCount} passages, {paperTables.length} tables)
                        </>
                      )}
                    </button>
                  </div>

                  {/* Relevant passages and tables for this paper */}
                  {isExpanded && (
                    <div className="border-t border-slate-100 bg-slate-50 p-5 space-y-6">
                      {/* Show explanatory passages first, then their structured tables. */}
                      <section className="space-y-4">
                        {(() => {
                          return (
                            <>
                              {passages.length > 0 && (
                                <div className="space-y-3">
                                  <h4 className="text-sm font-semibold text-slate-800">
                                    Relevant passages
                                  </h4>

                                  {passages.map((passage, index) => (
                                    <article
                                      key={`passage-${passage.chunk_id || index}`}
                                      className="bg-white border border-slate-200 rounded-xl p-5"
                                    >
                                      <div className="flex flex-wrap items-center gap-2 mb-3">
                                        <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-md">
                                          {passage.section_title || 'Section'}
                                        </span>

                                        {passage.parent_section_title && (
                                          <span className="text-xs text-slate-500">
                                            {passage.parent_section_title}
                                          </span>
                                        )}

                                        {passage.page_start != null && (
                                          <span className="text-xs text-slate-400">
                                            Page {passage.page_start}
                                            {passage.page_end !== passage.page_start
                                              ? `–${passage.page_end}`
                                              : ''}
                                          </span>
                                        )}

                                        <span className="text-xs text-emerald-700 ml-auto">
                                          {formatScore(passage.similarity_score)}
                                        </span>
                                      </div>

                                      <p className="text-sm leading-7 text-slate-700 whitespace-pre-wrap">
                                        {passage.displayContent}
                                      </p>
                                    </article>
                                  ))}
                                </div>
                              )}

                              {paperTables.length > 0 && (
                                <div className="space-y-3">
                                  <h4 className="text-sm font-semibold text-slate-800">
                                    Relevant tables
                                  </h4>

                                  {paperTables.map((table) => {
                                    const tableId = table.table_id
                                    const isTableExpanded = expandedTables[tableId]

                                    return (
                                      <article
                                        key={`table-${tableId}`}
                                        className="bg-white border border-slate-200 rounded-xl overflow-hidden"
                                      >
                                        <div className="p-5">
                                          <div className="min-w-0">
                                            <h5 className="font-semibold text-slate-900 leading-snug">
                                              {table.table_title ||
                                                (table.table_number
                                                  ? `Table ${table.table_number}`
                                                  : `Table ${table.table_index}`)}
                                            </h5>

                                            <div className="flex flex-wrap items-center gap-2 mt-2">
                                              {table.page_start != null && (
                                                <span className="text-xs text-slate-500">
                                                  Page {table.page_start}
                                                  {table.page_end !== table.page_start
                                                    ? `–${table.page_end}`
                                                    : ''}
                                                </span>
                                              )}

                                              {table.section_title && (
                                                <span className="text-xs text-slate-500">
                                                  {table.section_title}
                                                </span>
                                              )}

                                              <span className="text-xs bg-purple-50 text-purple-700 px-2.5 py-1 rounded-full font-medium">
                                                Table relevance {formatScore(table.similarity_score)}
                                              </span>
                                            </div>
                                          </div>

                                          <div className="mt-4">
                                            <TablePreview table={table} />
                                          </div>

                                          {Array.isArray(table.footnotes) && table.footnotes.length > 0 && (
                                            <div className="mt-3 text-xs text-slate-500">
                                              <strong>Footnotes:</strong>{' '}
                                              {table.footnotes.map((note) =>
                                                typeof note === 'object' ? JSON.stringify(note) : String(note)
                                              ).join(' | ')}
                                            </div>
                                          )}

                                          <button
                                            type="button"
                                            onClick={() => toggleTable(tableId)}
                                            className="mt-4 flex items-center gap-2 text-sm font-medium text-purple-600 hover:text-purple-800 transition"
                                          >
                                            {isTableExpanded ? (
                                              <>
                                                <ChevronUp size={17} />
                                                Hide extraction details
                                              </>
                                            ) : (
                                              <>
                                                <ChevronDown size={17} />
                                                View extraction details
                                              </>
                                            )}
                                          </button>
                                        </div>

                                        {isTableExpanded && (
                                          <div className="border-t border-slate-100 bg-slate-50 p-5 space-y-4">
                                            {table.table_text && (
                                              <div>
                                                <h6 className="text-sm font-semibold text-slate-800 mb-2">
                                                  Searchable table text
                                                </h6>
                                                <p className="bg-white border border-slate-200 rounded-xl p-4 text-sm text-slate-600 whitespace-pre-wrap leading-6">
                                                  {table.table_text}
                                                </p>
                                              </div>
                                            )}

                                            <div>
                                              <div className="flex items-center gap-2 mb-3">
                                                <Database size={17} className="text-purple-600" />
                                                <h6 className="text-sm font-semibold text-slate-800">
                                                  Raw extracted data
                                                </h6>
                                              </div>

                                              {table.raw_table_data != null ? (
                                                <pre className="bg-slate-900 text-slate-100 rounded-xl p-4 text-xs leading-6 overflow-x-auto max-h-96 overflow-y-auto">
                                                  {JSON.stringify(table.raw_table_data, null, 2)}
                                                </pre>
                                              ) : (
                                                <p className="text-sm text-slate-500 bg-white border border-slate-200 rounded-xl p-4">
                                                  Original raw extraction data is not available for this table.
                                                </p>
                                              )}
                                            </div>
                                          </div>
                                        )}
                                      </article>
                                    )
                                  })}
                                </div>
                              )}
                            </>
                          )
                        })()}
                      </section>

                      {passageCount === 0 && paperTables.length > 0 && (
                        <p className="text-sm text-slate-500">
                          No separate explanatory passage was retrieved for this paper. The matching structured tables are shown below.
                        </p>
                      )}

                      {passageCount === 0 && paperTables.length === 0 && (
                        <p className="text-sm text-slate-500">
                          No relevant passages or tables are available for this paper.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="bg-white border border-slate-200 border-dashed rounded-xl p-8 text-center">
            <FileText size={28} className="mx-auto text-slate-400 mb-3" />
            <p className="text-sm font-medium text-slate-700">
              No matching research documents found.
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Try another query to find relevant research passages and tables.
            </p>
          </div>
        )}
      </section>
        </div>
      )}

      {/* Initial empty state */}
      {!loading && !hasSearched && !error && (
        <div className="mt-12 bg-white border border-slate-200 border-dashed rounded-2xl p-12 text-center">
          <div className="h-14 w-14 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Search size={24} className="text-slate-400" />
          </div>

          <h3 className="text-lg font-semibold text-slate-800">
            Search your research knowledge base
          </h3>

          <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto">
            Enter a question, concept or research topic to find relevant passages
            and tables from the documents stored in your knowledge base.
          </p>
        </div>
      )}
    </div>
  )
}
