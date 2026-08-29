import { Link } from 'react-router-dom'
export function NotFoundPage() {
  return <main className="status-page"><section className="status-card"><p className="status-code">404</p>
    <h1>Page not found</h1><p>The requested page is unavailable.</p>
    <Link className="button-link" to="/app">Return home</Link></section></main>
}
