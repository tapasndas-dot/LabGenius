import { apiRequest } from './client'

export const SAMPLE_STATUSES = ['REGISTERED', 'IN_TESTING', 'REVIEW', 'FINALIZED', 'CANCELLED'] as const
export const SAMPLE_PRIORITIES = ['LOW', 'NORMAL', 'HIGH', 'URGENT'] as const
export type SampleStatus = typeof SAMPLE_STATUSES[number]
export type SamplePriority = typeof SAMPLE_PRIORITIES[number]
type Dates = { created_at: string; updated_at: string; version: number }
export type Sample = Dates & {
  id: string; organization_id: string; business_unit_id: string | null; division_id: string | null; department_id: string | null;
  sample_number: string; external_reference: string | null; material_id: string; specification_version_id: string;
  sample_description: string | null; quantity: string | null; quantity_unit: string | null; received_at: string | null;
  sampled_at: string | null; due_at: string | null; status: SampleStatus; priority: SamplePriority; notes: string | null
}
export type SampleTest = Dates & { id: string; sample_id: string; specification_test_id: string; test_id: string; method_version_id: string | null; sequence_number: number; status: string; is_required: boolean; display_name: string | null }
export type SampleTestAssignment = Dates & { id:string; sample_test_id:string; assigned_user_id:string; assigned_by_user_id:string|null; assigned_at:string; unassigned_at:string|null; unassigned_by_user_id:string|null; is_active:boolean; notes:string|null }
export type SampleTestAssignee = { id:string; display_name:string; account_status:string }
export type SampleTestAssignInput = { assigned_user_id:string; expected_sample_test_version:number; notes?:string|null }
export type SampleTestReassignInput = SampleTestAssignInput & { expected_assignment_version:number }
export type SampleTestUnassignInput = { expected_sample_test_version:number; expected_assignment_version:number }
export type SampleTestAssignmentMutation = { sample_test:SampleTest; assignment:SampleTestAssignment|null }
export type SampleInput = Omit<Sample, 'id'|'organization_id'|'status'|'version'|'created_at'|'updated_at'>
export type SampleListParams = Partial<{ limit:number; offset:number; search:string; status:string; priority:string; material_id:string; business_unit_id:string; division_id:string; department_id:string }>
const query=(params:SampleListParams={})=>{const q=new URLSearchParams();Object.entries(params).forEach(([k,v])=>{if(v!==undefined&&v!=='')q.set(k,String(v))});return q.size?`?${q}`:''}
export const samplesApi={
  list:(params:SampleListParams={})=>apiRequest<Sample[]>(`/samples${query(params)}`),
  get:(id:string)=>apiRequest<Sample>(`/samples/${id}`),
  create:(data:SampleInput)=>apiRequest<Sample>('/samples',{method:'POST',body:data}),
  update:(id:string,version:number,data:Partial<SampleInput>)=>apiRequest<Sample>(`/samples/${id}`,{method:'PUT',body:{...data,version}}),
  cancel:(id:string,version:number)=>apiRequest<Sample>(`/samples/${id}/cancel`,{method:'POST',body:{version}}),
  tests:(id:string)=>apiRequest<SampleTest[]>(`/samples/${id}/tests`),
  test:(id:string,testId:string)=>apiRequest<SampleTest>(`/samples/${id}/tests/${testId}`),
  generateTests:(id:string)=>apiRequest<SampleTest[]>(`/samples/${id}/generate-tests`,{method:'POST'}),
  assignmentUsers:()=>apiRequest<SampleTestAssignee[]>('/samples/assignment-users'),
  assignment:(id:string,testId:string)=>apiRequest<SampleTestAssignment>(`/samples/${id}/tests/${testId}/assignment`),
  assignmentHistory:(id:string,testId:string)=>apiRequest<SampleTestAssignment[]>(`/samples/${id}/tests/${testId}/assignment-history`),
  assign:(id:string,testId:string,data:SampleTestAssignInput)=>apiRequest<SampleTestAssignmentMutation>(`/samples/${id}/tests/${testId}/assign`,{method:'POST',body:data}),
  reassign:(id:string,testId:string,data:SampleTestReassignInput)=>apiRequest<SampleTestAssignmentMutation>(`/samples/${id}/tests/${testId}/reassign`,{method:'POST',body:data}),
  unassign:(id:string,testId:string,data:SampleTestUnassignInput)=>apiRequest<SampleTestAssignmentMutation>(`/samples/${id}/tests/${testId}/unassign`,{method:'POST',body:data}),
}
