import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import RepoPage from './pages/RepoPage'
import QueryPage from './pages/QueryPage'
import DiagnosePage from './pages/DiagnosePage'
import PatchPage from './pages/PatchPage'
import DocsPage from './pages/DocsPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/repos" element={<Dashboard />} />
        <Route path="/repos/:repoId" element={<RepoPage />} />
        <Route path="/query" element={<QueryPage />} />
        <Route path="/diagnose" element={<DiagnosePage />} />
        <Route path="/patch" element={<PatchPage />} />
        <Route path="/docs" element={<DocsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

