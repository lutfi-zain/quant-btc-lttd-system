/// <reference types="@testing-library/jest-dom" />
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { OnChainPanel } from './OnChainPanel'
import { SynchronizedChartProvider } from './SynchronizedChartContext'

describe('OnChainPanel', () => {
  it('renders loading state when data is empty', () => {
    render(
      <SynchronizedChartProvider>
        <OnChainPanel data={[]} />
      </SynchronizedChartProvider>
    )
    expect(screen.getByText(/Short-Term Holder MVRV/i)).toBeInTheDocument()
  })

  it('renders data correctly', () => {
    const mockData = [
      {
        date: '2025-01-01',
        sth_mvrv: 1.5,
        sth_nupl: 0.5,
        sth_sopr: 1.05,
        supply_in_profit: 0.8
      }
    ]
    render(
      <SynchronizedChartProvider>
        <OnChainPanel data={mockData} />
      </SynchronizedChartProvider>
    )
    expect(screen.getByText('1.50')).toBeInTheDocument()
    expect(screen.getByText('0.50')).toBeInTheDocument()
  })
})
