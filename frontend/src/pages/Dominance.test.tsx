import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Dominance from './Dominance'
import apiClient from '../api/client'

jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  Treemap: ({ data }: { data: Array<{ name: string }> }) => (
    <div data-testid="treemap">
      {data?.map((d) => (
        <div key={d.name} data-testid="treemap-cell">
          {d.name}
        </div>
      ))}
    </div>
  ),
  Tooltip: () => null,
}))

jest.mock('../api/client', () => ({
  __esModule: true,
  default: { get: jest.fn() },
}))
const mockedGet = apiClient.get as jest.Mock

const BRAND_DATA = [
  { brand: 'BRAND A', total_value: '4000.00', weighted_avg_wtd: '55.00' },
  { brand: 'BRAND B', total_value: '1000.00', weighted_avg_wtd: null },
]

function renderPage() {
  return render(
    <MemoryRouter>
      <Dominance />
    </MemoryRouter>
  )
}

describe('Dominance page', () => {
  beforeEach(() => {
    jest.mocked(apiClient.get).mockReset()
  })

  afterEach(() => jest.clearAllMocks())

  it('shows loading spinner while fetching', () => {
    mockedGet.mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
  })

  it('renders brand names after successful fetch', async () => {
    mockedGet.mockResolvedValue({ data: BRAND_DATA })
    renderPage()
    await waitFor(() => expect(screen.queryByRole('progressbar')).not.toBeInTheDocument())
    expect(screen.getByText('BRAND A')).toBeInTheDocument()
    expect(screen.getByText('BRAND B')).toBeInTheDocument()
  })

  it('shows no data message for empty response', async () => {
    mockedGet.mockResolvedValue({ data: [] })
    renderPage()
    await waitFor(() => expect(screen.getByText('No data available')).toBeInTheDocument())
  })
})
