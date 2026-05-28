export type ModuleStatus = 'pending' | 'running' | 'completed' | 'failed'
export type JobStatus = 'pending' | 'running' | 'ambiguous' | 'completed' | 'failed'

export interface SearchModuleProgress {
  module_id: string
  module_name: string
  status: ModuleStatus
  started_at: string | null
  completed_at: string | null
  error: string | null
}

export interface SearchResult {
  module_id: string
  module_name: string
  status: ModuleStatus
  data: unknown
  error: string | null
  schema_errors: string[] | null
}

export interface RiskSummary {
  overall_risk_level: 'high' | 'medium' | 'low' | 'unknown'
  risk_score: number
  summary: string
}

export interface AssessmentResult {
  company_name: string | null
  registration_number: string | null
  jurisdiction: string
  risk_summary: RiskSummary
  warnings: string[]
}

export interface CandidateCompany {
  company_name: string
  registration_number: string
  jurisdiction: string
  company_status: string | null
  source: string
  warnings: string[]
}

export interface SearchContext {
  company_name: string | null
  registration_number: string | null
  jurisdiction: string
}

export interface JobSummary {
  job_id: string
  status: JobStatus
  created_at: string
  updated_at: string
  completed_at: string | null
  query: SearchContext
  resolved_context: SearchContext | null
  progress: SearchModuleProgress[]
  candidates: CandidateCompany[] | null
  error: string | null
}

export interface JobResponse extends JobSummary {
  finished_module_results: SearchResult[]
  final_assessment_result: AssessmentResult | null
}

export interface AssessmentRequest {
  company_name?: string
  registration_number?: string
  jurisdiction: string
}
