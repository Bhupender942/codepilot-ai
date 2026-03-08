import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Search, 
  Loader2, 
  AlertCircle, 
  MessageSquare,
  FileText,
  Zap,
  Copy,
  Check
} from 'lucide-react'
import { listRepos, query, type Repo, type QueryResult } from '../api/client'
import CodeBlock from '../components/CodeBlock'

// Loading skeleton for results
function ResultSkeleton() {
  return (
    <div className="space-y-4">
      <div className="bg-white border border-slate-200 rounded-xl p-5 animate-pulse">
        <div className="flex items-center gap-2 mb-3">
          <div className="h-4 w-20 bg-slate-200 rounded" />
          <div className="h-4 w-12 bg-slate-200 rounded" />
        </div>
        <div className="space-y-2">
          <div className="h-3 w-full bg-slate-100 rounded" />
          <div className="h-3 w-full bg-slate-100 rounded" />
          <div className="h-3 w-2/3 bg-slate-100 rounded" />
        </div>
      </div>
    </div>
  )
}

export default function QueryPage() {
  const [repos, setRepos] = useState<Repo[]>([])
  const [repoId, setRepoId] = useState('')
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<QueryResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [repoLoadError, setRepoLoadError] = useState('')
  const [copiedAnswer, setCopiedAnswer] = useState(false)

  const loadRepos = () => {
    setRepoLoadError('')
    listRepos().then(setRepos).catch((e: any) => setRepoLoadError(e?.userMessage || 'Failed to load repositories'))
  }

  useEffect(() => { loadRepos() }, [])

  const handleSubmit = async () => {
    if (!repoId || !question.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await query({ repo_id: repoId, question, top_k: 8 })
      setResult(res)
    } catch (e) {
      setError((e as any)?.userMessage || 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  const copyAnswer = () => {
    if (result?.answer) {
      navigator.clipboard.writeText(result.answer)
      setCopiedAnswer(true)
      setTimeout(() => setCopiedAnswer(false), 2000)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <motion.div 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2 bg-black rounded-lg">
            <Search className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">AI Query</h1>
        </div>
        <p className="text-slate-500 text-sm ml-1">Ask questions about your codebase using AI-powered retrieval</p>
      </motion.div>

      {/* Query Form */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white border border-slate-200 rounded-xl p-5 mb-6 space-y-4"
      >
        <div>
          <label className="label flex items-center gap-2">
            <FileText className="w-3.5 h-3.5 text-slate-400" />
            Repository
          </label>
          {repoLoadError ? (
            <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle className="w-4 h-4 text-red-500" />
              <span className="text-sm text-red-700">{repoLoadError}</span>
              <button onClick={loadRepos} className="ml-auto text-sm text-black hover:text-slate-700">Retry</button>
            </div>
          ) : (
            <select
              value={repoId}
              onChange={e => setRepoId(e.target.value)}
              className="input-field"
            >
              <option value="">Select a repository…</option>
              {repos.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          )}
        </div>
        
        <div>
          <label className="label flex items-center gap-2">
            <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
            Question
          </label>
          <textarea
            rows={3}
            placeholder="e.g. How does the authentication flow work? What are the main components?"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) handleSubmit() }}
            className="input-field resize-none"
          />
          <p className="text-xs text-slate-400 mt-1.5">Press Ctrl+Enter to submit</p>
        </div>
        
        <AnimatePresence>
          {error && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-red-50 border border-red-200 text-red-700 px-4 py-2.5 rounded-lg text-sm flex items-center gap-2"
            >
              <AlertCircle className="w-4 h-4" />
              {error}
            </motion.div>
          )}
        </AnimatePresence>
        
        <button
          onClick={handleSubmit}
          disabled={loading || !repoId || !question.trim()}
          className="btn-primary inline-flex items-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Searching…
            </>
          ) : (
            <>
              <Zap className="w-4 h-4" />
              Ask AI
            </>
          )}
        </button>
      </motion.div>

      {/* Results */}
      <AnimatePresence mode="wait">
        {loading && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <ResultSkeleton />
          </motion.div>
        )}

        {result && !loading && (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            {/* AI Answer */}
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-black rounded-lg">
                    <Zap className="w-3.5 h-3.5 text-white" />
                  </div>
                  <span className="text-sm font-semibold text-slate-900">AI Answer</span>
                  {result.cached && (
                    <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">cached</span>
                  )}
                </div>
                <button
                  onClick={copyAnswer}
                  className="text-xs text-slate-500 hover:text-black flex items-center gap-1.5 transition-colors"
                >
                  {copiedAnswer ? (
                    <>
                      <Check className="w-3 h-3 text-green-600" />
                      <span className="text-green-600">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      Copy
                    </>
                  )}
                </button>
              </div>
              <p className="text-slate-700 text-sm whitespace-pre-wrap leading-relaxed">{result.answer}</p>
            </div>

            {/* Citations */}
            {result.citations.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-slate-400" />
                  Citations ({result.citations.length})
                </h2>
                <div className="space-y-3">
                  {result.citations.map((c, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="bg-white border border-slate-200 rounded-xl overflow-hidden"
                    >
                      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-50 border-b border-slate-200">
                        <span className="text-xs text-black font-mono">{c.file_path}</span>
                        <span className="text-xs text-slate-400">
                          Lines {c.start_line}–{c.end_line} · score {c.score.toFixed(2)}
                        </span>
                      </div>
                      <CodeBlock
                        code={c.text}
                        language={c.file_path.split('.').pop() || 'text'}
                        startingLineNumber={c.start_line}
                      />
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

