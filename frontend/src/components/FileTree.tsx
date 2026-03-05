import { useState } from 'react'

interface FileTreeProps {
  files: string[]
  onFileSelect?: (path: string) => void
}

interface TreeNode {
  [key: string]: TreeNode | null
}

function buildTree(paths: string[]): TreeNode {
  const root: TreeNode = {}
  for (const path of paths) {
    const parts = path.split('/')
    let node = root
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      if (i === parts.length - 1) { node[part] = null }
      else { node[part] = node[part] || {}; node = node[part] as TreeNode }
    }
  }
  return root
}

function TreeNode({ name, node, depth, onSelect }: { name: string; node: TreeNode | null; depth: number; onSelect?: (p: string) => void }) {
  const [open, setOpen] = useState(depth < 2)
  const isFile = node === null
  const pad = depth * 12

  if (isFile) {
    return (
      <div style={{ paddingLeft: pad }} className="flex items-center gap-1 py-0.5 px-2 text-xs text-slate-300 hover:bg-slate-800 cursor-pointer rounded" onClick={() => onSelect?.(name)}>
        <span>📄</span> {name}
      </div>
    )
  }

  return (
    <div>
      <div style={{ paddingLeft: pad }} className="flex items-center gap-1 py-0.5 px-2 text-xs text-slate-400 hover:bg-slate-800 cursor-pointer rounded" onClick={() => setOpen(!open)}>
        <span>{open ? '▾' : '▸'}</span><span>📁</span> {name}
      </div>
      {open && node && Object.entries(node).map(([k, v]) => (
        <TreeNode key={k} name={k} node={v} depth={depth + 1} onSelect={onSelect} />
      ))}
    </div>
  )
}

export default function FileTree({ files, onFileSelect }: FileTreeProps) {
  const tree = buildTree(files)
  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 p-2 overflow-auto max-h-80">
      {Object.entries(tree).map(([k, v]) => (
        <TreeNode key={k} name={k} node={v} depth={0} onSelect={onFileSelect} />
      ))}
    </div>
  )
}
