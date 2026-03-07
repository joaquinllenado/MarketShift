import { useState } from 'react'

function App() {
  const [message, setMessage] = useState(null)
  const [loading, setLoading] = useState(false)

  const fetchHello = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/hello')
      const data = await res.json()
      setMessage(data.message)
    } catch (err) {
      setMessage('Error connecting to backend: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center gap-8">
      <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
        MarketShift
      </h1>
      <p className="text-gray-400 text-lg">React + FastAPI + Prefect</p>

      <button
        onClick={fetchHello}
        disabled={loading}
        className="px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 rounded-lg font-semibold transition-colors cursor-pointer disabled:cursor-wait"
      >
        {loading ? 'Loading...' : 'Say Hello'}
      </button>

      {message && (
        <div className="mt-4 px-6 py-4 bg-gray-800 rounded-lg border border-gray-700 text-center max-w-md">
          <p className="text-green-400 font-mono text-lg">{message}</p>
        </div>
      )}
    </div>
  )
}

export default App
