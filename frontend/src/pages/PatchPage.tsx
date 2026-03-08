import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Wand2, 
  Loader2, 
  AlertCircle, 
  FileCode,
  GitPullRequest,
  Lightbulb,
  TestTube,
  Check,
  X,
  Minus
} from 'lucide-react'
import { listRepos, proposePatch, type Repo, type PatchResult } from '../api/client'
import DiffViewer from '../components/DiffViewer'
import CodeBlock from '../components/CodeBlock'

// Confidence indicator component
function ConfidenceIndicator({ confidence }: { confidence: number }) {
  const getColor = () => {
    if (confidence >= 0.7) return { bg: 'bg-emerald-500', text: 'text-emerald-400', label: 'High' }
    if (confidence >= 0.4) return { bg: 'bg-amber-500', text: 'text-amber-400', label: 'Medium' }
    return { bg: 'bg-rose-500', text: 'text-rose-400', label: 'Low' }
  }
  
  const { bg, text, label } = getColor()
  
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1">
        {[...Array(5)].map((_, i) => {
          const threshold = (i + 1) * 0.2
          let status: 'fill' | 'half' | 'empty' = 'empty'
          if (confidence >= threshold) status = 'fill'
          else if (confidence >= threshold - 0.1) status = 'half'
          
          return (
            <div
              key={i}
              className={`w-2 h-4 rounded-sm ${
                status === 'fill' ? bg : 
                status === 'half' ? `${bg}/50` : 'bg-slate-700'
              }`}
            />
          )
        })}
      </div>
      <span className={`text-sm font-medium ${text}`}>{label}</span>
    </div>
  )
}

export default function PatchPage() {
  const [repos, setRepos] = useState<Repo[]>([])
  const [repoId, setRepoId] = useState('')
  const [issueDescription, setIssueDescription] = useState('')
  const [filePath, setFilePath] = useState('')
  const [result, setResult] = useState<PatchResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [repoLoadError, setRepoLoadError] = useState('')

  const loadRepos = () => {
    setRepoLoadError('')
    listRepos().then(setRepos).catch((e: any) => setRepoLoadError(e?.userMessage || 'Failed to load repositories'))
  }

  useEffect(() => { loadRepos() }, [])

  const handleSubmit = async () => {
    if (!repoId || !issueDescription.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await proposePatch({
        repo_id: repoId,
        issue_description: issueDescription,
        file_path: filePath.trim() || undefined,
      })
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
          <div className="p-2 bg-purple-500/20 rounded-lg">
            <Wand2 className="w-5 h-5 text-purple-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Patch Proposal</h1>
        </div>
        <p className="text-slate-400 text-sm ml-1">Generate AI-powered code patches for issues and bugs</p>
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
          <label className="label flex items-center gap-2">
            <Lightbulb className="w-3.5 h-3.5 text-slate-400" />
            Issue Description
          </label>
          <textarea
            rows={4}
            placeholder="Describe the bug or feature to implement…"
            value={issueDescription}
            onChange={e => setIssueDescription(e.target.value)}
            className="input-field resize-none"
          />
        </div>
        
        <div>
          <label className="label">
            Target File <span className="text-slate-500 font-normal">(optional)</span>
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
        
        <button
          onClick={handleSubmit}
          disabled={loading || !repoId || !issueDescription.trim()}
          className="btn-primary inline-flex items-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating patch…
            </>
          ) : (
            <>
              <Wand2 className="w-4 h-4" />
              Generate Patch
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
            className="space-y-4"
          >
            {/* Meta info */}
            <div className="flex flex-wrap items-center gap-4">
              <div className="bg-slate-900/50 border border-slate-700/50 rounded-lg px-4 py-2.5 flex items-center gap-2">
<GitPullRequest className="w-4 h-4 text-slate-400" />
                <span className="text-sm text-slate-400">Target: </span>
                <span className="font-mono text-sm text-indigo-300">{result.target_file || 'unknown'}</span>
              </div>
              <div className="bg-slate-900/50 border border-slate-700/50 rounded-lg px-4 py-2.5 flex items-center gap-3">
                <span className="text-sm text-slate-400">Confidence: </span>
                <ConfidenceIndicator confidence={result.confidence} />
              </div>
            </div>

            {/* Diff */}
            {result.raw_diff && (
              <div>
                <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
<GitPullRequest className="w-4 h-4 text-purple-400" />
                  Diff
                </h2>
                <DiffViewer diff={result.raw_diff} filename={result.target_file} />
              </div>
            )}

            {/* Explanation */}
            {result.explanation && (
              <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-4">
                <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-amber-400" />
                  Explanation
                </h2>
                <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{result.explanation}</p>
              </div>
            )}

            {/* Unit Test */}
            {result.unit_test && (
              <div>
                <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                  <TestTube className="w-4 h-4 text-emerald-400" />
                  Suggested Unit Test
                </h2>
                <CodeBlock code={result.unit_test} language="python" showLineNumbers={false} />
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

