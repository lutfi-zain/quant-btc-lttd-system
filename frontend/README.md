# LTTD Trading System Frontend

This directory contains the React 18 + TypeScript SPA dashboard built for the Quantitative Bitcoin Long-Term Trend Direction (LTTD) Trading System. 

## Features
- **HMM Regime observability**: Displays BULL, BEAR, and SIDEWAYS regimes.
- **Ensemble Final Score**: Interactive metrics card reflecting values ∈ [-1.0, +1.0].
- **Causal Indicator Telemetry**: Audiable metrics view to verify technical and on-chain feature states.
- **Lookahead Bias Free Candlestick Charting**: Multi-pane synchronized price charting using TradingView Lightweight Charts, displaying OHLCV candlesticks, Final Score series overlay, and the first three PCA components over 120–350 day OU half-life epochs.

## Technology Stack
- **Framework**: React 18
- **Language**: TypeScript
- **Bundler**: Vite
- **Package Manager**: Bun
- **Styling**: Tailwind CSS v4
- **Charting**: TradingView Lightweight Charts
- **Data Querying**: @tanstack/react-query

## Development Setup

First, make sure the Hono API server is running on the default port. Then, execute the following commands in this directory:

### Install dependencies
```bash
bun install
```

### Start development server
```bash
bun run dev
```

### Build for production
```bash
bun run build
```

### Preview production build
```bash
bun run preview
```
