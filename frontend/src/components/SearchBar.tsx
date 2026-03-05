import { useState, useEffect, useRef } from 'react'

interface SearchBarProps {
  onSearch: (query: string) => void
  placeholder?: string
  value?: string
  loading?: boolean
}

export default function SearchBar({ onSearch, placeholder = 'Search...', value = '', loading = false }: SearchBarProps) {
  const [query, setQuery] = useState(value)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => { if (query) onSearch(query) }, 300)
    return () => { if (timer.current) clearTimeout(timer.current) }
  }, [query, onSearch])

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') onSearch(query) }}
        placeholder={placeholder}
        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 pr-10 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
      />
      <div className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
        {loading ? <span className="animate-spin">⟳</span> : '🔍'}
      </div>
    </div>
  )
}
