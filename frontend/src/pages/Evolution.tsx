import { useState, useEffect, useRef } from 'react'
import {
  Box,
  CircularProgress,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Typography,
} from '@mui/material'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import apiClient from '../api/client'
import { formatCurrency } from '../utils/currency'

type Category = 'brand' | 'product' | 'market' | ''

type ChartRow = {
  year: number
  total: number
}

type OptionsResponse = {
  count: number
  next: string | null
  previous: string | null
  results: string[]
}

const SCROLL_THRESHOLD_PX = 50

function Evolution() {
  const [category, setCategory] = useState<Category>('')
  const [options, setOptions] = useState<string[]>([])
  const [optionsPage, setOptionsPage] = useState(0)
  const [optionsHasMore, setOptionsHasMore] = useState(true)
  const [selectedValue, setSelectedValue] = useState('')
  const [chartData, setChartData] = useState<ChartRow[]>([])
  const [loadingOptions, setLoadingOptions] = useState(false)
  const [loadingChart, setLoadingChart] = useState(false)
  const categoryRef = useRef<Category>('')

  useEffect(() => {
    categoryRef.current = category
  }, [category])

  useEffect(() => {
    if (!category) return
    let cancelled = false
    setLoadingOptions(true)
    apiClient
      .get<OptionsResponse>(`/market-data/evolution/options/?category=${category}&page=1`)
      .then(({ data }) => {
        if (!cancelled) {
          setOptions(data.results)
          setOptionsPage(1)
          setOptionsHasMore(data.next !== null)
          setLoadingOptions(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoadingOptions(false)
      })
    return () => {
      cancelled = true
    }
  }, [category])

  useEffect(() => {
    if (!category || !selectedValue) return
    let cancelled = false
    setLoadingChart(true)
    apiClient
      .get<{ year: number; total: string }[]>(
        `/market-data/evolution/chart/?category=${category}&value=${encodeURIComponent(selectedValue)}`
      )
      .then(({ data }) => {
        if (!cancelled) {
          setChartData(data.map((r) => ({ year: r.year, total: parseFloat(r.total) })))
          setLoadingChart(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoadingChart(false)
      })
    return () => {
      cancelled = true
    }
  }, [category, selectedValue])

  const handleCategoryChange = (value: Category) => {
    setCategory(value)
    setSelectedValue('')
    setChartData([])
    setOptions([])
    setOptionsPage(0)
    setOptionsHasMore(true)
  }

  const loadMoreOptions = () => {
    if (!category || loadingOptions || !optionsHasMore) return
    const nextPage = optionsPage + 1
    const requestCategory = category
    setLoadingOptions(true)
    apiClient
      .get<OptionsResponse>(
        `/market-data/evolution/options/?category=${requestCategory}&page=${nextPage}`
      )
      .then(({ data }) => {
        if (categoryRef.current !== requestCategory) return
        setOptions((prev) => [...prev, ...data.results])
        setOptionsPage(nextPage)
        setOptionsHasMore(data.next !== null)
        setLoadingOptions(false)
      })
      .catch(() => {
        if (categoryRef.current === requestCategory) setLoadingOptions(false)
      })
  }

  const handleMenuScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const t = e.currentTarget
    if (t.scrollTop + t.clientHeight >= t.scrollHeight - SCROLL_THRESHOLD_PX) {
      loadMoreOptions()
    }
  }

  const bothSelected = category !== '' && selectedValue !== ''
  const valueDisabled = !category || (loadingOptions && options.length === 0)

  return (
    <Container maxWidth="xl" className="py-8">
      <Typography variant="h4" component="h1" className="pb-6">
        Sales Evolution
      </Typography>
      <div className="flex gap-4 pb-6">
        <FormControl sx={{ minWidth: 180 }}>
          <InputLabel id="category-label">Category</InputLabel>
          <Select
            labelId="category-label"
            label="Category"
            value={category}
            onChange={(e) => handleCategoryChange(e.target.value as Category)}
          >
            <MenuItem value="brand">Brand</MenuItem>
            <MenuItem value="product">Product</MenuItem>
            <MenuItem value="market">Market</MenuItem>
          </Select>
        </FormControl>
        <FormControl sx={{ minWidth: 220 }} disabled={valueDisabled}>
          <InputLabel id="value-label">Value</InputLabel>
          <Select
            labelId="value-label"
            label="Value"
            value={selectedValue}
            onChange={(e) => setSelectedValue(e.target.value)}
            displayEmpty
            MenuProps={{
              slotProps: {
                paper: {
                  onScroll: handleMenuScroll,
                  sx: { maxHeight: 300 },
                },
              },
            }}
          >
            {options.map((opt) => (
              <MenuItem key={opt} value={opt}>
                {opt}
              </MenuItem>
            ))}
            {loadingOptions && options.length > 0 && (
              <MenuItem
                disabled
                data-testid="value-loading-row"
                className="justify-center"
              >
                <CircularProgress size={20} />
              </MenuItem>
            )}
          </Select>
        </FormControl>
      </div>
      {!bothSelected && (
        <Box className="flex justify-center py-16">
          <Typography color="text.secondary">
            Select a category and a value to see the evolution chart.
          </Typography>
        </Box>
      )}
      {bothSelected && loadingChart && (
        <Box className="flex justify-center py-4">
          <CircularProgress />
        </Box>
      )}
      {bothSelected && !loadingChart && chartData.length === 0 && (
        <Box className="flex justify-center py-4">
          <Typography>No data available</Typography>
        </Box>
      )}
      {bothSelected && !loadingChart && chartData.length > 0 && (
        <Paper className="p-4">
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis tickFormatter={(v: number) => formatCurrency(v)} />
              <Bar dataKey="total" />
              <Tooltip
                formatter={(v) => (typeof v === 'number' ? formatCurrency(v) : String(v ?? ''))}
              />
            </BarChart>
          </ResponsiveContainer>
        </Paper>
      )}
    </Container>
  )
}

export default Evolution
