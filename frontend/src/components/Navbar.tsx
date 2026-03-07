import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Dashboard', icon: '🏠' },
  { to: '/query', label: 'Query', icon: '🔍' },
  { to: '/diagnose', label: 'Diagnose', icon: '🐛' },
  { to: '/patch', label: 'Patch', icon: '🩹' },
  { to: '/docs', label: 'Docs', icon: '📚' },
]

export default function Navbar() {
  return (
    <aside className="w-56 min-h-screen bg-slate-900 border-r border-slate-700 flex flex-col">
      <div className="px-4 py-5 border-b border-slate-700">
        <span className="text-indigo-400 font-bold text-xl">⚡ CodePilot</span>
      </div>
      <nav className="flex-1 px-2 py-4 space-y-1">
        {links.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <span>{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-3 border-t border-slate-700 text-xs text-slate-500">
        AI Code Companion v1.0
      </div>
    </aside>
  )
}
