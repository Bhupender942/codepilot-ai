interface DiffViewerProps {
  diff: string
  filename?: string
}

export default function DiffViewer({ diff, filename }: DiffViewerProps) {
  const lines = diff.split('\n')

  return (
    <div className="rounded-lg overflow-hidden border border-slate-700 font-mono text-xs">
      {filename && (
        <div className="bg-slate-800 px-3 py-2 text-slate-300 border-b border-slate-700">
          📄 {filename}
        </div>
      )}
      <div className="overflow-auto max-h-96">
        {lines.map((line, i) => {
          let cls = 'px-3 py-0.5 whitespace-pre'
          if (line.startsWith('+') && !line.startsWith('+++')) cls += ' bg-green-900/40 text-green-300'
          else if (line.startsWith('-') && !line.startsWith('---')) cls += ' bg-red-900/40 text-red-300'
          else if (line.startsWith('@@')) cls += ' bg-indigo-900/40 text-indigo-300'
          else if (line.startsWith('---') || line.startsWith('+++')) cls += ' bg-slate-800 text-slate-400'
          else cls += ' text-slate-300'
          return <div key={i} className={cls}>{line || ' '}</div>
        })}
      </div>
    </div>
  )
}
