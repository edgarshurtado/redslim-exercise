import { useState, useEffect } from 'react'
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

type Category = 'brand' | 'product' | 'market' | ''

type ChartRow = {
  year: number
  total: number
}

function Evolution() {
  const [category, setCategory] = useState<Category>('')
  const [options, setOptions] = useState<string[]>([])
  const [selectedValue, setSelectedValue] = useState('')
  const [chartData, setChartData] = useState<ChartRow[]>([])
  const [loadingOptions, setLoadingOptions] = useState(false)
  const [loadingChart, setLoadingChart] = useState(false)
  const [hadChart, setHadChart] = useState(false)

  useEffect(() => {
    if (!category) return
    let cancelled = false
    setLoadingOptions(true)
    apiClient
      .get<string[]>(`/market-data/evolution/options/?category=${category}`)
      .then(({ data }) => {
        if (!cancelled) {
          setOptions(data)
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
          setHadChart(true)
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
  }

  const bothSelected = category !== '' && selectedValue !== ''

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
        <FormControl sx={{ minWidth: 220 }} disabled={!category || loadingOptions || (hadChart && !selectedValue)}>
          <InputLabel id="value-label">Value</InputLabel>
          <Select
            labelId="value-label"
            label="Value"
            value={selectedValue}
            onChange={(e) => setSelectedValue(e.target.value)}
          >
            {options.map((opt) => (
              <MenuItem key={opt} value={opt}>
                {opt}
              </MenuItem>
            ))}
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
              <YAxis
                tickFormatter={(v: number) =>
                  v.toLocaleString('en-US', {
                    style: 'currency',
                    currency: 'USD',
                    maximumFractionDigits: 0,
                  })
                }
              />
              <Bar dataKey="total" />
              <Tooltip
                formatter={(v) =>
                  typeof v === 'number'
                    ? v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
                    : String(v ?? '')
                }
              />
            </BarChart>
          </ResponsiveContainer>
        </Paper>
      )}
    </Container>
  )
}

export default Evolution
