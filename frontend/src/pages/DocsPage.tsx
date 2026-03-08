import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  BookOpen, 
  Loader2, 
  AlertCircle, 
  FileCode,
  Sparkles,
  Clock,
  CheckCircle,
  XCircle,
  RefreshCw
} from 'lucide-react'
import { listRepos, generateDocs, getDocResult, type Repo, type DocEntry } from '../api/client'
import CodeBlock from '../components/CodeBlock'

// Status indicator component
function StatusBadge({ status }: { status: string }) {
  const getConfig = () => {
    switch (status) {
      case 'completed':
        return { icon: CheckCircle, bg: 'bg-emerald-900/30', text: 'text-emerald-400', border: 'border-emerald-700/30' }
      case 'failed':
        return { icon: XCircle, bg: 'bg-rose-900/30', text: 'text-rose-400', border: 'border-rose-700/30' }
      case 'pending':
      case 'processing':
      default:
        return { icon: Clock, bg: 'bg-amber-900/30', text: 'text-amber-400', border: 'border-amber-700/30' }
    }
  }
  
  const { icon: Icon, bg, text, border } = getConfig()
  
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${bg} ${text} ${border}`}>
      <Icon className="w-3 h-3" />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

export default function DocsPage() {
  const [repos, setRepos] = useState<Repo[]>([])
  const [repoId, setRepoId] = useState('')
  const [filePath, setFilePath] = useState('')
  const [docs, setDocs] = useState<DocEntry[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [statusMsg, setStatusMsg] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [repoLoadError, setRepoLoadError] = useState('')

  const loadRepos = () => {
    setRepoLoadError('')
    listRepos().then(setRepos).catch((e: any) => setRepoLoadError(e?.userMessage || 'Failed to load repositories'))
  }

  useEffect(() => {
    loadRepos()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const handleGenerate = async () => {
    if (!repoId) return
    setLoading(true)
    setError('')
    setDocs(null)
    setStatusMsg('Starting documentation generation…')
    try {
      const job = await generateDocs({ repo_id: repoId, file_path: filePath.trim() || undefined })
      setStatusMsg('Job queued, waiting for results…')
      pollRef.current = setInterval(async () => {
        try {
          const res = await getDocResult(job.job_id)
          if (res.status === 'completed') {
            clearInterval(pollRef.current!)
            setDocs(res.docs || [])
            setLoading(false)
            setStatusMsg('')
          } else if (res.status === 'failed') {
            clearInterval(pollRef.current!)
            setError(res.error || 'Documentation generation failed.')
            setLoading(false)
            setStatusMsg('')
          } else {
            setStatusMsg(`Status: ${res.status}…`)
          }
        } catch {
          clearInterval(pollRef.current!)
          setError('Failed to fetch job status.')
          setLoading(false)
          setStatusMsg('')
        }
      }, 2000)
    } catch (e) {
      setError((e as any)?.userMessage || 'An unexpected error occurred')
      setLoading(false)
      setStatusMsg('')
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
          <div className="p-2 bg-emerald-500/20 rounded-lg">
            <BookOpen className="w-5 h-5 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Documentation Generator</h1>
        </div>
        <p className="text-slate-400 text-sm ml-1">Generate AI-powered docstrings and documentation for your codebase</p>
      </motion.div>

      {/* Form */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-5 mb-6 space-y-4"
      >
        <div>
          <label className="label flex items-center gap-2">
            <FileCode className="w-3.5 h-3.5 text-slate-400" />
            Repository
          </label>
          {repoLoadError ? (
            <div className="flex items-center gap-3 p-3 bg-rose-900/20 border border-rose-700/30 rounded-lg">
              <AlertCircle className="w-4 h-4 text-rose-400" />
              <span className="text-sm text-rose-300">{repoLoadError}</span>
              <button onClick={loadRepos} className="ml-auto text-sm text-indigo-400 hover:text-indigo-300">Retry</button>
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
          <label className="label">
            File Path <span className="text-slate-500 font-normal">(optional — leave blank for entire repo)</span>
          </label>
          <input
            type="text"
            placeholder="e.g. src/utils/auth.py"
            value={filePath}
            onChange={e => setFilePath(e.target.value)}
            className="input-field font-mono text-sm"
          />
        </div>
        
        <AnimatePresence>
          {error && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-rose-900/20 border border-rose-700/30 text-rose-300 px-4 py-2.5 rounded-lg text-sm flex items-center gap-2"
            >
              <AlertCircle className="w-4 h-4" />
              {error}
            </motion.div>
          )}
        </AnimatePresence>
        
        {statusMsg && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 text-sm text-amber-400"
          >
            <Loader2 className="w-4 h-4 animate-spin" />
            {statusMsg}
          </motion.div>
        )}
        
        <button
          onClick={handleGenerate}
          disabled={loading || !repoId}
          className="btn-primary inline-flex items-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating…
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Generate Docs
            </>
          )}
        </button>
      </motion.div>

      {/* Results */}
      <AnimatePresence>
        {docs !== null && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-emerald-400" />
              Generated Documentation ({docs.length} chunks)
            </h2>
            
            {docs.length === 0 ? (
              <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-8 text-center">
                <FileCode className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400">No documentable code chunks found.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {docs.map((d, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="bg-slate-900/50 border border-slate-700/50 rounded-xl overflow-hidden hover:border-slate-600/50 transition-colors"
                  >
                    <div className="flex items-center justify-between px-4 py-3 bg-slate-800/50 border-b border-slate-700/30">
                      <div className="flex items-center gap-2">
                        <FileCode className="w-4 h-4 text-indigo-400" />
                        <span className="text-sm font-mono text-indigo-300">{d.file_path}</span>
                      </div>
                      <span className="text-xs text-slate-500">Lines {d.start_line}–{d.end_line}</span>
                    </div>
                    <div className="p-4 space-y-4">
                      {d.docstring && (
                        <div>
                          <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wide flex items-center gap-1.5 mb-2">
                            <BookOpen className="w-3 h-3" />
                            Docstring
                          </span>
                          <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed bg-slate-800/30 p-3 rounded-lg">{d.docstring}</p>
                        </div>
                      )}
                      
                      {d.example && (
                        <div>
                          <span className="text-xs font-semibold text-amber-400 uppercase tracking-wide flex items-center gap-1.5 mb-2">
                            <Sparkles className="w-3 h-3" />
                            Example
                          </span>
                          <div>
                            <CodeBlock code={d.example} language="python" showLineNumbers={false} />
                          </div>
                        </div>
                      )}
                      
                      {d.complexity && (
                        <div>
                          <span className="text-xs font-semibold text-purple-400 uppercase tracking-wide flex items-center gap-1.5 mb-2">
                            <RefreshCw className="w-3 h-3" />
                            Complexity
                          </span>
                          <p className="text-sm text-slate-400">{d.complexity}</p>
                        </div>
                      )}
                    </div>
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

