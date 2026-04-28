import { useState, useEffect } from 'react'
import { Box, CircularProgress, Container, Paper, Typography } from '@mui/material'
import { ResponsiveContainer, Treemap, Tooltip } from 'recharts'
import type { TreemapNode as RechartsTreemapNode } from 'recharts'
import apiClient from '../api/client'

type BrandDatum = {
  brand: string
  total_value: string
  weighted_avg_wtd: string | null
}

type TreemapNode = {
  name: string
  size: number
  fill: string
  wtd: number | null
}

function interpolateColor(t: number): string {
  const green = { r: 0x2e, g: 0x7d, b: 0x32 }
  const red = { r: 0xc6, g: 0x28, b: 0x28 }
  const r = Math.round(green.r + (red.r - green.r) * t)
  const g = Math.round(green.g + (red.g - green.g) * t)
  const b = Math.round(green.b + (red.b - green.b) * t)
  return `rgb(${r},${g},${b})`
}

function toChartData(data: BrandDatum[]): TreemapNode[] {
  const wtdValues = data
    .map((d) => (d.weighted_avg_wtd !== null ? parseFloat(d.weighted_avg_wtd) : null))
    .filter((v): v is number => v !== null)

  const minWtd = wtdValues.length ? Math.min(...wtdValues) : 0
  const maxWtd = wtdValues.length ? Math.max(...wtdValues) : 100
  const range = maxWtd - minWtd || 1

  return data.map((d) => {
    const wtd = d.weighted_avg_wtd !== null ? parseFloat(d.weighted_avg_wtd) : null
    const fill = wtd !== null ? interpolateColor((wtd - minWtd) / range) : '#9e9e9e'
    return { name: d.brand, size: parseFloat(d.total_value), fill, wtd }
  })
}

type CellProps = {
  x: number
  y: number
  width: number
  height: number
  name: string
  fill: string
  wtd: number | null
}

function CustomCell({ x, y, width, height, name, fill, wtd }: CellProps) {
  const showLabel = width > 60 && height > 40
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={fill} stroke="#fff" strokeWidth={2} />
      {showLabel && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - (wtd !== null ? 8 : 0)}
            textAnchor="middle"
            fill="white"
            fontSize={12}
            fontWeight={700}
          >
            {name}
          </text>
          {wtd !== null && (
            <text
              x={x + width / 2}
              y={y + height / 2 + 10}
              textAnchor="middle"
              fill="white"
              fontSize={11}
            >
              {wtd.toFixed(1)}%
            </text>
          )}
        </>
      )}
    </g>
  )
}

type TooltipPayload = { payload: TreemapNode }

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <Paper sx={{ p: 1.5 }}>
      <Typography variant="body2" sx={{ fontWeight: 700 }}>
        {d.name}
      </Typography>
      <Typography variant="body2">
        Sales:{' '}
        {d.size.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })}
      </Typography>
      {d.wtd !== null && (
        <Typography variant="body2">Wtd Dist: {d.wtd.toFixed(1)}%</Typography>
      )}
    </Paper>
  )
}

function Dominance() {
  const [data, setData] = useState<TreemapNode[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    apiClient
      .get<BrandDatum[]>('/market-data/dominance/')
      .then(({ data: raw }) => {
        if (!cancelled) {
          setData(toChartData(raw))
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <Container maxWidth="xl" className="py-8">
      <div className="pb-1">
        <Typography variant="h4" component="h1">
          Manufacturer Dominance
        </Typography>
      </div>
      <Typography variant="body2" color="text.secondary" className="pb-4">
        Box size = total sales value · Box color = sales-weighted distribution (green = lean, red = bloated)
      </Typography>
      <div className="flex items-center gap-2 pb-6">
        <Typography variant="caption" sx={{ color: '#2e7d32', fontWeight: 600 }}>
          Efficient
        </Typography>
        <div className="h-2.5 w-40 rounded [background:linear-gradient(to_right,#2e7d32,#66bb6a,#ef9a9a,#c62828)]" />
        <Typography variant="caption" sx={{ color: '#c62828', fontWeight: 600 }}>
          Bloated
        </Typography>
      </div>
      {loading && (
        <Box className="flex justify-center py-4">
          <CircularProgress />
        </Box>
      )}
      {!loading && data.length === 0 && (
        <Box className="flex justify-center py-4">
          <Typography>No data available</Typography>
        </Box>
      )}
      {!loading && data.length > 0 && (
        <Paper className="p-4">
          <ResponsiveContainer width="100%" height={500}>
            <Treemap
              data={data}
              dataKey="size"
              content={(props: RechartsTreemapNode) => (
                <CustomCell
                  x={props.x ?? 0}
                  y={props.y ?? 0}
                  width={props.width ?? 0}
                  height={props.height ?? 0}
                  name={props.name ?? ''}
                  fill={(props.fill as string) ?? '#9e9e9e'}
                  wtd={(props.wtd as number | null) ?? null}
                />
              )}
            >
              <Tooltip content={<CustomTooltip />} />
            </Treemap>
          </ResponsiveContainer>
        </Paper>
      )}
      <Typography variant="caption" color="text.secondary" className="block pt-3 text-right">
        Aggregated across all markets and periods
      </Typography>
    </Container>
  )
}

export default Dominance
