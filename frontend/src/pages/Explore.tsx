import { useState, useEffect, useRef } from 'react'
import {
  Box,
  CircularProgress,
  Container,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Typography,
} from '@mui/material'
import apiClient from '../api/client'

interface DataRow {
  id: number
  market: string
  product: string
  brand: string
  sub_brand: string
  value: string
  date: string
  period_weeks: number
  weighted_distribution: string | null
}

type SortOrder = 'asc' | 'desc'

const COLUMNS: { key: keyof Omit<DataRow, 'id'>; label: string }[] = [
  { key: 'market', label: 'Market' },
  { key: 'product', label: 'Product' },
  { key: 'brand', label: 'Brand' },
  { key: 'sub_brand', label: 'Sub-Brand' },
  { key: 'value', label: 'Sales Value' },
  { key: 'date', label: 'Date' },
  { key: 'period_weeks', label: 'Period (Weeks)' },
  { key: 'weighted_distribution', label: 'Weighted Distribution' },
]

function Explore() {
  const [rows, setRows] = useState<DataRow[]>([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)
  const [sortField, setSortField] = useState<keyof Omit<DataRow, 'id'>>('date')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const sentinelRef = useRef<HTMLDivElement>(null)
  const canLoadMoreRef = useRef(false)

  useEffect(() => {
    let cancelled = false
    const ordering = `${sortOrder === 'desc' ? '-' : ''}${sortField}`
    setLoading(true)
    apiClient
      .get(`/market-data/table/?page=${page}&ordering=${ordering}`)
      .then(({ data }) => {
        if (!cancelled) {
          setRows((prev) => (page === 1 ? data.results : [...prev, ...data.results]))
          setHasMore(data.next !== null)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [page, sortField, sortOrder])

  const handleSort = (field: keyof Omit<DataRow, 'id'>) => {
    if (field === sortField) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
    setRows([])
    setPage(1)
  }

  canLoadMoreRef.current = !loading && hasMore

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel || typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && canLoadMoreRef.current) {
        setPage((prev) => prev + 1)
      }
    })
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [])

  return (
    <Container maxWidth="xl" className="py-8">
      <Typography variant="h4" component="h1" className="mb-4">
        Explore
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              {COLUMNS.map(({ key, label }) => (
                <TableCell key={key}>
                  <TableSortLabel
                    active={sortField === key}
                    direction={sortField === key ? sortOrder : 'asc'}
                    onClick={() => handleSort(key)}
                  >
                    {label}
                  </TableSortLabel>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell>{row.market}</TableCell>
                <TableCell>{row.product}</TableCell>
                <TableCell>{row.brand}</TableCell>
                <TableCell>{row.sub_brand}</TableCell>
                <TableCell>{row.value}</TableCell>
                <TableCell>{row.date}</TableCell>
                <TableCell>{row.period_weeks}</TableCell>
                <TableCell>{row.weighted_distribution ?? '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <div ref={sentinelRef} className="h-px" />
      {loading && (
        <Box className="flex justify-center py-4">
          <CircularProgress />
        </Box>
      )}
      {!loading && rows.length === 0 && (
        <Box className="flex justify-center py-4">
          <Typography>No data available</Typography>
        </Box>
      )}
    </Container>
  )
}

export default Explore
