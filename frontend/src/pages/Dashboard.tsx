import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  GitBranch, 
  Plus, 
  Trash2, 
  Database, 
  Search, 
  AlertCircle, 
  CheckCircle2,
  ExternalLink,
  Loader2
} from 'lucide-react'
import { listRepos, connectRepo, deleteRepo, startIndex, type Repo } from '../api/client'

// Loading skeleton component
function RepoCardSkeleton() {
  return (
    <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-4 animate-pulse">
      <div className="flex items-start justify-between mb-3">
        <div className="h-5 w-32 bg-slate-700 rounded" />
        <div className="h-5 w-16 bg-slate-700 rounded" />
      </div>
      <div className="h-3 w-full bg-slate-700/50 rounded mb-2" />
      <div className="h-3 w-24 bg-slate-700/50 rounded mb-4" />
      <div className="flex gap-2">
        <div className="h-7 w-16 bg-slate-700 rounded" />
        <div className="h-7 w-16 bg-slate-700 rounded" />
      </div>
    </div>
  )
}

// Empty state component
function EmptyState({ onConnect }: { onConnect: () => void }) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="text-center py-20"
    >
      <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 mb-6">
        <GitBranch className="w-10 h-10 text-indigo-400" />
      </div>
      <h3 className="text-xl font-semibold text-white mb-2">No repositories connected</h3>
      <p className="text-slate-400 mb-6 max-w-md mx-auto">
        Connect your first repository to start using AI-powered code analysis, debugging, and documentation generation.
      </p>
      <button 
        onClick={onConnect}
        className="btn-primary inline-flex items-center gap-2"
      >
        <Plus className="w-4 h-4" />
        Connect Repository
      </button>
    </motion.div>
  )
}

export default function Dashboard() {
  const [repos, setRepos] = useState<Repo[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ name: '', git_url: '', default_branch: 'main' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [indexingRepoId, setIndexingRepoId] = useState<string | null>(null)

  const fetchRepos = async () => {
    setLoading(true)
    setError('')
    try {
      const repos = await listRepos()
      setRepos(repos)
    } catch (e: any) {
      setError(e?.userMessage || e?.response?.data?.detail || 'Failed to load repositories — check backend and CORS settings')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchRepos() }, [])

  const handleConnect = async () => {
    if (!form.name.trim() || !form.git_url.trim()) return
    setSubmitting(true)
    try {
      await connectRepo(form)
      setShowModal(false)
      setForm({ name: '', git_url: '', default_branch: 'main' })
      fetchRepos()
    } catch (e: any) {
      setError(e?.userMessage || e?.response?.data?.detail || 'Failed to connect repo')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this repository? This action cannot be undone.')) return
    try { 
      await deleteRepo(id); 
      fetchRepos() 
    } catch (e: any) { 
      setError(e?.userMessage || 'Failed to delete repo') 
    }
  }

  const handleIndex = async (id: string) => {
    setIndexingRepoId(id)
    try { 
      await startIndex(id); 
      alert('Indexing started! The repository is being processed.')
    } catch (e: any) { 
      setError(e?.userMessage || 'Failed to start index') 
    } finally {
      setIndexingRepoId(null)
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <motion.h1 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-3xl font-bold text-white"
          >
            Dashboard
          </motion.h1>
          <p className="text-slate-400 mt-1">Manage your repositories and AI analysis</p>
        </div>
        <motion.button 
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setShowModal(true)} 
          className="btn-primary inline-flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Connect Repo
        </motion.button>
      </div>

      {/* Error Alert */}
      <AnimatePresence>
        {error && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-rose-900/20 border border-rose-700/50 text-rose-300 px-4 py-3 rounded-xl mb-6 flex items-center gap-3"
          >
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span className="text-sm">{error}</span>
            <button 
              onClick={() => setError('')}
              className="ml-auto text-rose-400 hover:text-rose-200"
            >
              ×
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading State */}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <RepoCardSkeleton key={i} />
          ))}
        </div>
      ) : repos.length === 0 ? (
        <EmptyState onConnect={() => setShowModal(true)} />
      ) : (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
        >
          {repos.map((r, index) => (
            <motion.div
              key={r.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="card card-hover group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 bg-indigo-500/20 rounded-lg">
                    <GitBranch className="w-4 h-4 text-indigo-400" />
                  </div>
                  <h3 className="font-semibold text-white truncate max-w-[150px]">{r.name}</h3>
                </div>
                <span className="inline-flex items-center gap-1.5 text-xs bg-emerald-900/30 text-emerald-400 px-2.5 py-1 rounded-full border border-emerald-700/30">
                  <CheckCircle2 className="w-3 h-3" />
                  Active
                </span>
              </div>
              <p className="text-xs text-slate-400 truncate mb-2 font-mono bg-slate-800/50 px-2 py-1 rounded">{r.git_url}</p>
              <p className="text-xs text-slate-500 mb-4">Branch: <span className="text-slate-400">{r.default_branch}</span></p>
              
              <div className="flex gap-2">
                <button 
                  onClick={() => handleIndex(r.id)}
                  disabled={indexingRepoId === r.id}
                  className="flex-1 btn-primary text-xs py-2 inline-flex items-center justify-center gap-2"
                >
                  {indexingRepoId === r.id ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Database className="w-3 h-3" />
                  )}
                  Index
                </button>
                <button 
                  onClick={() => handleDelete(r.id)}
                  className="px-3 py-2 bg-slate-800/50 hover:bg-rose-900/30 text-slate-400 hover:text-rose-400 rounded-lg transition-colors border border-slate-700/50 hover:border-rose-700/30"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Modal */}
      <AnimatePresence>
        {showModal && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
            onClick={() => setShowModal(false)}
          >
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-slate-900 border border-slate-700/50 rounded-2xl p-6 w-full max-w-md shadow-2xl"
            >
              <h2 className="text-xl font-semibold text-white mb-6">Connect Repository</h2>
              <div className="space-y-4">
                <div>
                  <label className="label">Repository Name</label>
                  <input 
                    placeholder="my-awesome-project" 
                    value={form.name} 
                    onChange={e => setForm({...form, name: e.target.value})}
                    className="input-field" 
                  />
                </div>
                <div>
                  <label className="label">Git URL</label>
                  <input 
                    placeholder="https://github.com/user/repo.git" 
                    value={form.git_url} 
                    onChange={e => setForm({...form, git_url: e.target.value})}
                    className="input-field font-mono text-sm" 
                  />
                </div>
                <div>
                  <label className="label">Default Branch</label>
                  <input 
                    placeholder="main" 
                    value={form.default_branch} 
                    onChange={e => setForm({...form, default_branch: e.target.value})}
                    className="input-field" 
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6 justify-end">
                <button 
                  onClick={() => setShowModal(false)} 
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleConnect} 
                  disabled={submitting || !form.name.trim() || !form.git_url.trim()}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                  Connect
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

