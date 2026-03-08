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
    <aside className="w-64 min-h-screen bg-white border-r border-slate-200 flex flex-col relative">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-black rounded-lg">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-slate-900 font-bold text-xl tracking-tight">CodePilot</span>
        </div>
        <p className="text-slate-500 text-xs mt-1 ml-1">AI Code Companion</p>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-black text-white shadow-lg'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
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
      <div className="p-4 border-t border-slate-200">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>v1.0.0</span>
          <div className="flex items-center gap-1.5">
            <Settings className="w-3 h-3" />
            <span>Settings</span>
          </div>
        </div>
      </div>
    </aside>
  )
}

