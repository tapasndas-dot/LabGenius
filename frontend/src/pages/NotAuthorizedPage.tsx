import { Link } from 'react-router-dom'
export function NotAuthorizedPage() {
  return <main className="status-page"><section className="status-card"><p className="status-code">403</p>
    <h1>Not authorized</h1><p>Your session is active, but you do not have permission for this area.</p>
    <Link className="button-link" to="/app">Return home</Link></section></main>
}
