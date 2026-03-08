import { NavLink } from 'react-router-dom'
import { 
  Home, 
  Search, 
  Bug, 
  Wand2, 
  BookOpen, 
  Settings,
  Zap,
  ChevronRight
} from 'lucide-react'

const links = [
  { to: '/', label: 'Dashboard', icon: Home },
  { to: '/query', label: 'Query', icon: Search },
  { to: '/diagnose', label: 'Diagnose', icon: Bug },
  { to: '/patch', label: 'Patch', icon: Wand2 },
  { to: '/docs', label: 'Docs', icon: BookOpen },
]

export default function Navbar() {
  return (
    <aside className="w-64 min-h-screen bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 border-r border-slate-700/50 flex flex-col relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-b from-indigo-500/5 to-transparent pointer-events-none" />
      <div className="absolute -bottom-20 -right-20 w-40 h-40 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
      
      {/* Logo */}
      <div className="px-4 py-5 border-b border-slate-700/50 relative">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg shadow-lg shadow-indigo-500/20">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-white font-bold text-xl tracking-tight">CodePilot</span>
        </div>
        <p className="text-slate-500 text-xs mt-1 ml-1">AI Code Companion</p>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 relative">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/25'
                  : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={`w-4 h-4 transition-transform duration-200 ${isActive ? '' : 'group-hover:scale-110'}`} />
                <span className="flex-1">{label}</span>
                {isActive && (
                  <ChevronRight className="w-3 h-3 opacity-60" />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      
      {/* Footer */}
      <div className="p-4 border-t border-slate-700/50 relative">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>v1.0.0</span>
          <div className="flex items-center gap-1.5">
            <Settings className="w-3 h-3" />
            <span>Settings</span>
          </div>
        </div>
        <div className="mt-2 h-1 bg-slate-800 rounded-full overflow-hidden">
          <div className="h-full w-1/3 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full" />
        </div>
      </div>
    </aside>
  )
}

