import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Bug, 
  Loader2, 
  AlertCircle, 
  FileCode,
  Percent,
  AlertTriangle,
  CheckCircle,
  XCircle
} from 'lucide-react'
import { listRepos, diagnose, type Repo, type DiagnoseResult } from '../api/client'

// Severity badge component
function SeverityBadge({ probability }: { probability: number }) {
  if (probability >= 0.7) {
    return (
      <span className="inline-flex items-center gap-1 text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full border border-red-200">
        <XCircle className="w-3 h-3" />
        High
      </span>
    )
  }
  if (probability >= 0.4) {
    return (
      <span className="inline-flex items-center gap-1 text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full border border-amber-200">
        <AlertTriangle className="w-3 h-3" />
        Medium
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full border border-green-200">
      <CheckCircle className="w-3 h-3" />
      Low
    </span>
  )
}

export default function DiagnosePage() {
  const [repos, setRepos] = useState<Repo[]>([])
  const [repoId, setRepoId] = useState('')
  const [errorText, setErrorText] = useState('')
  const [stacktrace, setStacktrace] = useState('')
  const [result, setResult] = useState<DiagnoseResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [repoLoadError, setRepoLoadError] = useState('')

  const loadRepos = () => {
    setRepoLoadError('')
    listRepos().then(setRepos).catch((e: any) => setRepoLoadError(e?.userMessage || 'Failed to load repositories'))
  }

  useEffect(() => { loadRepos() }, [])

  const handleSubmit = async () => {
    if (!repoId || !errorText.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await diagnose({ repo_id: repoId, error_text: errorText, stacktrace })
      setResult(res)
    } catch (e) {
      setError((e as any)?.userMessage || 'An unexpected error occurred')
    } finally {
      setLoading(false)
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
            <Bug className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Error Diagnosis</h1>
        </div>
        <p className="text-slate-500 text-sm ml-1">Identify the root cause of errors using AI-powered code analysis</p>
      </motion.div>

      {/* Form */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white border border-slate-200 rounded-xl p-5 mb-6 space-y-4"
      >
        <div>
          <label className="label flex items-center gap-2">
            <FileCode className="w-3.5 h-3.5 text-slate-400" />
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
            <AlertCircle className="w-3.5 h-3.5 text-slate-400" />
            Error Message
          </label>
          <textarea
            rows={2}
            placeholder="e.g. TypeError: Cannot read properties of undefined (reading 'map')"
            value={errorText}
            onChange={e => setErrorText(e.target.value)}
            className="input-field resize-none"
          />
        </div>
        
        <div>
          <label className="label">
            Stack Trace <span className="text-slate-500 font-normal">(optional)</span>
          </label>
          <textarea
            rows={5}
            placeholder="Paste the full stack trace here…"
            value={stacktrace}
            onChange={e => setStacktrace(e.target.value)}
            className="input-field resize-none font-mono text-xs"
          />
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
          disabled={loading || !repoId || !errorText.trim()}
          className="btn-primary inline-flex items-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing…
            </>
          ) : (
            <>
              <Bug className="w-4 h-4" />
              Diagnose
            </>
          )}
        </button>
      </motion.div>

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h2 className="text-sm font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              Suspects ({result.suspects.length})
            </h2>
            
            {result.suspects.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded-xl p-8 text-center">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
                <p className="text-slate-500">No suspects found for this error.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {result.suspects.map((s, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="bg-white border border-slate-200 rounded-xl p-4 hover:border-slate-300 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <FileCode className="w-4 h-4 text-slate-600" />
                        <span className="text-sm font-mono text-black">{s.file_path}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-slate-400">Lines {s.start_line}–{s.end_line}</span>
                        <SeverityBadge probability={s.probability} />
                      </div>
                    </div>
                    
                    {/* Probability bar */}
                    <div className="mb-3">
                      <div className="flex items-center justify-between text-xs mb-1.5">
                        <span className="text-slate-500 flex items-center gap-1">
                          <Percent className="w-3 h-3" />
                          Confidence
                        </span>
                        <span className={`font-medium ${
                          s.probability >= 0.7 ? 'text-red-600' : 
                          s.probability >= 0.4 ? 'text-amber-600' : 'text-green-600'
                        }`}>
                          {(s.probability * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-2 rounded-full transition-all duration-500 ${
                            s.probability >= 0.7 ? 'bg-red-500' : 
                            s.probability >= 0.4 ? 'bg-amber-500' : 
                            'bg-green-500'
                          }`}
                          style={{ width: `${s.probability * 100}%` }}
                        />
                      </div>
                    </div>
                    
                    <p className="text-xs text-slate-600 leading-relaxed">{s.explanation}</p>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

