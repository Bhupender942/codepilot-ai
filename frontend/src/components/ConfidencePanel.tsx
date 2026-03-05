interface Evidence {
  component: string
  score: number
  weight: number
  details: string
}

interface ConfidencePanelProps {
  score: number
  evidence?: Evidence[]
}

export default function ConfidencePanel({ score, evidence = [] }: ConfidencePanelProps) {
  const color = score >= 70 ? 'text-green-400' : score >= 40 ? 'text-yellow-400' : 'text-red-400'
  const ring = score >= 70 ? 'stroke-green-400' : score >= 40 ? 'stroke-yellow-400' : 'stroke-red-400'
  const circumference = 2 * Math.PI * 40
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">Confidence Score</h3>
      <div className="flex items-center gap-4 mb-4">
        <svg width="100" height="100" className="rotate-[-90deg]">
          <circle cx="50" cy="50" r="40" fill="none" stroke="#334155" strokeWidth="8" />
          <circle cx="50" cy="50" r="40" fill="none" strokeWidth="8"
            className={ring} strokeDasharray={circumference} strokeDashoffset={offset}
            strokeLinecap="round" style={{ transition: 'stroke-dashoffset 0.5s ease' }} />
        </svg>
        <span className={`text-4xl font-bold ${color}`}>{score}</span>
      </div>
      {evidence.length > 0 && (
        <div className="space-y-2">
          {evidence.map((e) => (
            <div key={e.component}>
              <div className="flex justify-between text-xs text-slate-400 mb-1">
                <span>{e.component}</span>
                <span>{e.score}/100</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-1.5">
                <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${e.score}%` }} />
              </div>
              {e.details && <p className="text-xs text-slate-500 mt-0.5">{e.details}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
