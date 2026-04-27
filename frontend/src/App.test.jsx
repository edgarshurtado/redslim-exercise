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
  apiClient.get.mockResolvedValue({ data: { message: 'Hello Redslim' } })
})

test('renders Hello Redslim heading', () => {
  render(<App />)
  expect(screen.getByRole('heading', { name: /hello redslim/i })).toBeInTheDocument()
})

test('displays API response message', async () => {
  render(<App />)
  await waitFor(() => {
    expect(screen.getByTestId('api-message')).toHaveTextContent('Hello Redslim')
  })
})
