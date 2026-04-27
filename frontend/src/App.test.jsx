import { render, screen, waitFor } from '@testing-library/react'
import App from './App'

jest.mock('./api/client', () => ({
  __esModule: true,
  default: {
    get: jest.fn()
  }
}))

import apiClient from './api/client'

beforeEach(() => {
  apiClient.get.mockReset()
})

test('renders Hello Redslim heading', () => {
  apiClient.get.mockReturnValue(new Promise(() => {}))
  render(<App />)
  expect(screen.getByRole('heading', { name: /hello redslim/i })).toBeInTheDocument()
})

test('displays API response message', async () => {
  apiClient.get.mockResolvedValue({ data: { message: 'Hello Redslim' } })
  render(<App />)
  await waitFor(() => {
    expect(screen.getByTestId('api-message')).toHaveTextContent('Hello Redslim')
  })
})

test('displays error message when API fails', async () => {
  apiClient.get.mockRejectedValue(new Error('Network Error'))
  render(<App />)
  await waitFor(() => {
    expect(screen.getByTestId('api-message')).toHaveTextContent('Could not reach the server.')
  })
})
