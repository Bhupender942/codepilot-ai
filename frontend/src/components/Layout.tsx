import { ReactNode } from 'react'
import Navbar from './Navbar'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Navbar />
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  )
}
