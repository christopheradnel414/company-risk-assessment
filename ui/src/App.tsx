import { useEffect, useRef, useState } from 'react'
import type { AssessmentRequest, CandidateCompany, JobResponse } from './types'
import { fetchJob, fetchJobs, submitAssessment } from './api'
import SubmitForm from './components/SubmitForm'
import JobList from './components/JobList'
import JobDetail from './components/JobDetail'
import './App.css'

const ACTIVE_STATUSES = new Set<string>(['pending', 'running'])
const LIST_POLL_MS = 3000
const DETAIL_POLL_MS = 2000

function EmptyState() {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">◈</div>
      <h2>No job selected</h2>
      <p>Submit a company above or click a recent job to view results.</p>
    </div>
  )
}

export default function App() {
  const [jobs, setJobs] = useState<JobResponse[]>([])
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [selectedJob, setSelectedJob] = useState<JobResponse | null>(null)
  const [jobCache, setJobCache] = useState<Record<string, JobResponse>>({})

  // Ref so the detail-poll interval can check status without re-creating itself
  const jobRef = useRef<JobResponse | null>(null)
  jobRef.current = selectedJob

  // Poll job list every 3s
  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const list = await fetchJobs()
        if (alive) setJobs(list)
      } catch { /* ignore — backend may be starting up */ }
    }
    tick()
    const id = setInterval(tick, LIST_POLL_MS)
    return () => { alive = false; clearInterval(id) }
  }, [])

  // Poll selected job detail every 2s while it is active
  useEffect(() => {
    if (!selectedJobId) {
      setSelectedJob(null)
      return
    }
    let alive = true

    const tick = async () => {
      if (!alive) return
      try {
        const job = await fetchJob(selectedJobId)
        if (alive) {
          setSelectedJob(job)
          setJobCache(prev => ({ ...prev, [job.job_id]: job }))
        }
      } catch { /* ignore transient errors */ }
    }

    tick() // immediate first fetch
    const id = setInterval(() => {
      // Stop polling once the job reaches a terminal state
      if (!ACTIVE_STATUSES.has(jobRef.current?.status ?? 'pending')) return
      tick()
    }, DETAIL_POLL_MS)

    return () => { alive = false; clearInterval(id) }
  }, [selectedJobId])

  const handleSubmit = async (req: AssessmentRequest) => {
    const { job_id } = await submitAssessment(req)
    setSelectedJobId(job_id)
  }

  const handleSelectCandidate = async (candidate: CandidateCompany) => {
    const { job_id } = await submitAssessment({
      company_name: candidate.company_name,
      registration_number: candidate.registration_number,
      jurisdiction: candidate.jurisdiction,
    })
    setSelectedJobId(job_id)
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-brand">
          <div className="app-header-brand-icon">◈</div>
          Company Risk Assessment
        </div>
        <span className="app-header-sub">Due Diligence Dashboard</span>
      </header>

      <div className="app-body">
        <aside className="sidebar">
          <SubmitForm onSubmit={handleSubmit} />
          <JobList
            jobs={jobs}
            jobCache={jobCache}
            selectedJobId={selectedJobId}
            onSelect={setSelectedJobId}
          />
        </aside>

        <main className="main-content">
          {selectedJob
            ? <JobDetail job={selectedJob} onSelectCandidate={handleSelectCandidate} />
            : <EmptyState />
          }
        </main>
      </div>
    </div>
  )
}
