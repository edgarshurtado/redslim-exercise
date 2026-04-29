import { AppBar, Toolbar } from '@mui/material'
import { Link as RouterLink, Outlet, useLocation } from 'react-router-dom'

function Layout() {
  const { pathname } = useLocation()

  return (
    <>
      <AppBar position="static" sx={{ backgroundColor: '#1a1a2e' }}>
        <Toolbar sx={{ px: 4 }}>
          <RouterLink
            to="/"
            aria-current={pathname === '/' ? 'page' : undefined}
            className="text-white font-bold text-base tracking-[0.3px] no-underline"
          >
            Edgar's ReadSlim Exercise
          </RouterLink>
          <RouterLink
            to="/explore"
            aria-current={pathname === '/explore' ? 'page' : undefined}
            className={`text-nav-accent no-underline ml-4 text-sm ${pathname === '/explore' ? 'border-b-2 border-nav-accent pb-0.5' : ''}`}
          >
            Explore
          </RouterLink>
          <RouterLink
            to="/dominance"
            aria-current={pathname === '/dominance' ? 'page' : undefined}
            className={`text-nav-accent no-underline ml-4 text-sm ${pathname === '/dominance' ? 'border-b-2 border-nav-accent pb-0.5' : ''}`}
          >
            Dominance
          </RouterLink>
          <RouterLink
            to="/evolution"
            aria-current={pathname === '/evolution' ? 'page' : undefined}
            className={`text-nav-accent no-underline ml-4 text-sm ${pathname === '/evolution' ? 'border-b-2 border-nav-accent pb-0.5' : ''}`}
          >
            Evolution
          </RouterLink>
        </Toolbar>
      </AppBar>
      <Outlet />
    </>
  )
}

export default Layout
