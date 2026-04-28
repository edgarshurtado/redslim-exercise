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
            style={{
              color: '#fff',
              fontWeight: 700,
              fontSize: '16px',
              letterSpacing: '0.3px',
              textDecoration: 'none',
            }}
          >
            Edgar's ReadSlim Exercise
          </RouterLink>
          <RouterLink
            to="/explore"
            aria-current={pathname === '/explore' ? 'page' : undefined}
            style={{
              color: '#90caf9',
              textDecoration: 'none',
              marginLeft: '16px',
              fontSize: '14px',
              ...(pathname === '/explore' && { borderBottom: '2px solid #90caf9', paddingBottom: '2px' }),
            }}
          >
            Explore
          </RouterLink>
        </Toolbar>
      </AppBar>
      <Outlet />
    </>
  )
}

export default Layout
