import type { ReactNode } from 'react'
import { ApiError } from '../../api/client'

// eslint-disable-next-line react-refresh/only-export-components
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return 'You are authenticated but not authorized for this operation.'
    if (error.status === 404) return 'The requested record is unavailable.'
    if (error.status === 409) return error.message || 'The operation conflicts with current security rules.'
    if (error.status === null) return error.message
    return error.message || 'The operation could not be completed.'
  }
  return 'The operation could not be completed.'
}
export function AdminHeader({ title, description, actions }: { title: string; description: string; actions?: ReactNode }) {
  return <header className="admin-page-header"><div><h1>{title}</h1><p>{description}</p></div>{actions}</header>
}
export function LoadingState() { return <p className="admin-state">Loading…</p> }
export function EmptyState({ children }: { children: ReactNode }) { return <p className="admin-state">{children}</p> }
export function ErrorState({ message }: { message: string }) { return <p className="form-error" role="alert">{message}</p> }
export function ConfirmButton({ children, prompt, onConfirm, className = 'small-button danger' }: { children: ReactNode; prompt: string; onConfirm: () => void; className?: string }) {
  return <button type="button" className={className} onClick={() => { if (window.confirm(prompt)) onConfirm() }}>{children}</button>
}
