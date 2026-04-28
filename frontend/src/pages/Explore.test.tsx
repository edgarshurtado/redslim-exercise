import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Explore from './Explore'
import apiClient from '../api/client'

jest.mock('../api/client', () => ({
  __esModule: true,
  default: { get: jest.fn() },
}))

const mockRow = {
  id: 1,
  market: 'MarketA',
  product: 'ProductA',
  brand: 'BrandA',
  sub_brand: 'SubBrandA',
  value: '100.00',
  date: '2023-01-15',
  period_weeks: 4,
  weighted_distribution: '50.00',
}

const mockPage = {
  data: { count: 1, next: null, previous: null, results: [mockRow] },
}

beforeEach(() => {
  jest.mocked(apiClient.get).mockReset()
  global.IntersectionObserver = jest.fn().mockImplementation(() => ({
    observe: jest.fn(),
    disconnect: jest.fn(),
    unobserve: jest.fn(),
  }))
})

afterEach(() => {
  delete (global as any).IntersectionObserver
})

test('renders all 8 column headers', async () => {
  jest.mocked(apiClient.get).mockResolvedValue(mockPage)
  render(<Explore />)
  await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(1))
  expect(screen.getByRole('columnheader', { name: 'Market' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Product' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Brand' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Sub-Brand' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Sales Value' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Date' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Period (Weeks)' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Weighted Distribution' })).toBeInTheDocument()
  expect(screen.getByText('MarketA')).toBeInTheDocument()
})

test('clicking inactive column fires request with correct ordering param', async () => {
  jest.mocked(apiClient.get).mockResolvedValue(mockPage)
  render(<Explore />)
  await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(1))
  await userEvent.click(screen.getByText('Market'))
  await waitFor(() => {
    const lastUrl = jest.mocked(apiClient.get).mock.calls.at(-1)?.[0] as string
    expect(lastUrl).toContain('ordering=market')
    expect(lastUrl).not.toContain('ordering=-market')
  })
  expect(apiClient.get).toHaveBeenCalledTimes(2)
})

test('clicking active column header toggles sort direction', async () => {
  jest.mocked(apiClient.get).mockResolvedValue(mockPage)
  render(<Explore />)
  await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(1))
  // Default active sort is date desc. Clicking Date toggles to asc (no leading minus).
  const firstUrl = jest.mocked(apiClient.get).mock.calls[0][0] as string
  expect(firstUrl).toContain('ordering=-date')
  await userEvent.click(screen.getByText('Date'))
  await waitFor(() => {
    const lastUrl = jest.mocked(apiClient.get).mock.calls.at(-1)?.[0] as string
    expect(lastUrl).toContain('ordering=date')
    expect(lastUrl).not.toContain('ordering=-date')
  })
  expect(apiClient.get).toHaveBeenCalledTimes(2)
})

test('shows CircularProgress during initial fetch', async () => {
  jest.mocked(apiClient.get).mockReturnValue(new Promise(() => {}))
  render(<Explore />)
  await waitFor(() => {
    expect(document.querySelector('[role="progressbar"]')).toBeInTheDocument()
  })
})

test('shows No data available when API returns empty list', async () => {
  jest.mocked(apiClient.get).mockResolvedValue({
    data: { count: 0, next: null, previous: null, results: [] },
  })
  render(<Explore />)
  await waitFor(() => {
    expect(screen.getByText('No data available')).toBeInTheDocument()
  })
})
