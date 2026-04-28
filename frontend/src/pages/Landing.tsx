import { useState, useEffect } from 'react'
import { Typography, Container, Box } from '@mui/material'
import apiClient from '../api/client'

function Landing() {
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    apiClient.get('/redslim-hello')
      .then(res => setMessage(res.data.message))
      .catch(() => setMessage('Could not reach the server.'))
  }, [])

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8 }}>
        <Typography variant="h2" component="h1">
          Hello Redslim
        </Typography>
        {message && (
          <Typography variant="body1" data-testid="api-message">
            {message}
          </Typography>
        )}
      </Box>
    </Container>
  )
}

export default Landing
