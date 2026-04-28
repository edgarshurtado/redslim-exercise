import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import apiClient from './api/client'

jest.mock('./api/client', () => ({
  __esModule: true,
  default: { get: jest.fn() }
}))

beforeEach(() => {
  jest.mocked(apiClient.get).mockReset()
  jest.mocked(apiClient.get).mockReturnValue(new Promise(() => {}))
})

test('renders Landing page at /', () => {
  render(
    <MemoryRouter initialEntries={['/']}>
      <App />
    </MemoryRouter>
  )
  expect(screen.getByRole('heading', { name: /hello redslim/i })).toBeInTheDocument()
})

test('renders Explore page at /explore', () => {
  render(
    <MemoryRouter initialEntries={['/explore']}>
      <App />
    </MemoryRouter>
  )
  expect(screen.getByRole('heading', { name: /explore/i })).toBeInTheDocument()
})
