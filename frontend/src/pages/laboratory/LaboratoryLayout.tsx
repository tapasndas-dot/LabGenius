import { Navigate, NavLink, Outlet } from 'react-router-dom'
import { useAuthorization } from '../../auth/useAuthorization'
const sections = [{to:'tests',label:'Tests',permission:'test.view'},{to:'methods',label:'Methods',permission:'method.view'},{to:'specifications',label:'Specifications',permission:'specification.view'}] as const
export function LaboratoryLayout(){ const {hasPermission}=useAuthorization(); if(!sections.some(s=>hasPermission(s.permission))) return <Navigate to="/not-authorized" replace/>; return <div className="admin-area"><nav className="admin-tabs" aria-label="Laboratory Masters sections">{sections.filter(s=>hasPermission(s.permission)).map(s=><NavLink key={s.to} to={s.to}>{s.label}</NavLink>)}</nav><Outlet/></div> }
export function LaboratoryIndex(){ const {hasPermission}=useAuthorization(); const first=sections.find(s=>hasPermission(s.permission)); return first?<Navigate to={first.to} replace/>:<Navigate to="/not-authorized" replace/> }
