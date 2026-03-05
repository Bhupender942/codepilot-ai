import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

export interface Repo {
  id: string; name: string; git_url: string; default_branch: string;
  status: string; file_count?: number; chunk_count?: number; created_at?: string;
}
export interface IndexJob { job_id: string; status: string; progress?: number; message?: string; }
export interface Citation { file_path: string; start_line: number; end_line: number; code: string; language: string; score: number; }
export interface QueryResult { answer: string; citations: Citation[]; cached: boolean; }
export interface Suspect { file_path: string; start_line: number; end_line: number; probability: number; explanation: string; }
export interface DiagnoseResult { suspects: Suspect[]; summary: string; }
export interface PatchResult { patch_id: string; diff: string; explanation: string; unit_test: string; file_path: string; }
export interface SandboxResult { job_id: string; status: string; stdout: string; stderr: string; exit_code: number; }
export interface ConfidenceEvidence { component: string; score: number; weight: number; details: string; }
export interface ConfidenceResult { score: number; evidence: ConfidenceEvidence[]; }
export interface DocsResult { content: string; file_path: string; }

export const connectRepo = (data: { name: string; git_url: string; default_branch?: string }) =>
  api.post<Repo>('/repos/connect', data).then(r => r.data)
export const listRepos = () => api.get<Repo[]>('/repos').then(r => r.data)
export const deleteRepo = (id: string) => api.delete(`/repos/${id}`).then(r => r.data)
export const startIndex = (repo_id: string) => api.post<IndexJob>('/index/start', { repo_id }).then(r => r.data)
export const getIndexStatus = (job_id: string) => api.get<IndexJob>(`/index/status/${job_id}`).then(r => r.data)
export const query = (data: { repo_id: string; question: string; top_k?: number }) =>
  api.post<QueryResult>('/query', data).then(r => r.data)
export const diagnose = (data: { repo_id: string; error_text: string; stacktrace?: string }) =>
  api.post<DiagnoseResult>('/diagnose', data).then(r => r.data)
export const proposePatch = (data: { repo_id: string; issue_description: string; file_path?: string }) =>
  api.post<PatchResult>('/patch/propose', data).then(r => r.data)
export const runSandbox = (data: { patch_id: string; repo_id: string }) =>
  api.post<SandboxResult>('/sandbox/run', data).then(r => r.data)
export const getSandboxResult = (job_id: string) => api.get<SandboxResult>(`/sandbox/result/${job_id}`).then(r => r.data)
export const generateDocs = (data: { repo_id: string; file_path?: string }) =>
  api.post<DocsResult>('/docs/generate', data).then(r => r.data)

export default api
