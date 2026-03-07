import { useState } from 'react'

const MAX_URLS = 5

function CompanyCard({ company }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-white font-semibold text-base leading-snug">{company.title}</h3>
        <a
          href={company.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-400 hover:text-blue-300 shrink-0 mt-0.5 transition-colors"
        >
          Visit ↗
        </a>
      </div>
      <p className="text-xs text-gray-500 font-mono truncate">{company.url}</p>
      {company.highlights.length > 0 && (
        <ul className="flex flex-col gap-2">
          {company.highlights.map((h, i) => (
            <li key={i} className="text-sm text-gray-300 border-l-2 border-blue-500 pl-3 leading-relaxed">
              {h}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function ScrapedCard({ item }) {
  const [expanded, setExpanded] = useState(false)
  const preview = item.text.slice(0, 400)
  const hasMore = item.text.length > 400

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-white font-semibold text-base leading-snug">{item.title}</h3>
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-400 hover:text-blue-300 shrink-0 mt-0.5 transition-colors"
        >
          Visit ↗
        </a>
      </div>
      <p className="text-xs text-gray-500 font-mono truncate">{item.url}</p>
      {item.text && (
        <div className="text-sm text-gray-300 leading-relaxed">
          <p>{expanded ? item.text : preview}{!expanded && hasMore ? '…' : ''}</p>
          {hasMore && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-2 text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              {expanded ? 'Show less' : 'Read more'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function App() {
  const [query, setQuery] = useState('')
  const [urlInput, setUrlInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [results, setResults] = useState(null)

  const parseUrls = (raw) =>
    raw
      .split(/[\n,]+/)
      .map((u) => u.trim())
      .filter((u) => u.length > 0)
      .slice(0, MAX_URLS)

  const handleAnalyze = async () => {
    const urls = parseUrls(urlInput)
    if (!query.trim() && urls.length === 0) {
      setError('Enter a company name or at least one URL.')
      return
    }

    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const res = await fetch('/api/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim() || null, urls }),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}))
        throw new Error(detail.detail || `Request failed (${res.status})`)
      }
      const data = await res.json()
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const hasResults = results && (results.companies.length > 0 || results.scraped.length > 0)

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center gap-3">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
          MarketShift
        </h1>
        <span className="text-gray-500 text-sm">Competitor Intelligence</span>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10 flex flex-col gap-10">
        {/* Input panel */}
        <section className="flex flex-col gap-6">
          <div className="flex flex-col gap-1">
            <h2 className="text-xl font-semibold text-white">Research a Competitor</h2>
            <p className="text-gray-400 text-sm">
              Enter a company name to discover it, paste up to {MAX_URLS} competitor URLs to scrape their content, or both.
            </p>
          </div>

          <div className="flex flex-col gap-4">
            {/* Company name */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-300">Company name</label>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                placeholder="e.g. Linear, Notion, Vercel"
                className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors text-sm"
              />
            </div>

            {/* URLs */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-300">
                Competitor URLs <span className="text-gray-500 font-normal">(one per line, up to {MAX_URLS})</span>
              </label>
              <textarea
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder={`https://competitor.com\nhttps://another.com/pricing\nhttps://thirdone.com/blog`}
                rows={4}
                className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors text-sm font-mono resize-none"
              />
              {urlInput && (
                <p className="text-xs text-gray-500">
                  {parseUrls(urlInput).length} URL{parseUrls(urlInput).length !== 1 ? 's' : ''} detected
                </p>
              )}
            </div>

            {error && (
              <p className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-4 py-3">
                {error}
              </p>
            )}

            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="self-start px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 disabled:text-blue-400 rounded-lg font-semibold text-sm transition-colors cursor-pointer disabled:cursor-wait"
            >
              {loading ? 'Analyzing…' : 'Analyze'}
            </button>
          </div>
        </section>

        {/* Results */}
        {loading && (
          <div className="flex items-center gap-3 text-gray-400">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">Fetching data from Exa…</span>
          </div>
        )}

        {hasResults && (
          <section className="flex flex-col gap-8">
            {results.companies.length > 0 && (
              <div className="flex flex-col gap-4">
                <h2 className="text-lg font-semibold text-white">
                  Companies found
                  <span className="ml-2 text-sm font-normal text-gray-500">({results.companies.length})</span>
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {results.companies.map((c, i) => (
                    <CompanyCard key={i} company={c} />
                  ))}
                </div>
              </div>
            )}

            {results.scraped.length > 0 && (
              <div className="flex flex-col gap-4">
                <h2 className="text-lg font-semibold text-white">
                  Scraped pages
                  <span className="ml-2 text-sm font-normal text-gray-500">({results.scraped.length})</span>
                </h2>
                <div className="flex flex-col gap-4">
                  {results.scraped.map((item, i) => (
                    <ScrapedCard key={i} item={item} />
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {results && !hasResults && !loading && (
          <p className="text-gray-500 text-sm">No results returned. Try a different query or URL.</p>
        )}
      </main>
    </div>
  )
}

export default App
