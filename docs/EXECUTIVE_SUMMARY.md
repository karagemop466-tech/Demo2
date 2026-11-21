# Executive Summary: Kalshi Demo Dashboard Project

## Project Overview
This project collects, organizes, and analyzes data from the Kalshi Demo Trade API to create an interactive dashboard tracking the highest dollar amount live events across five specific topics: **Gas Prices, Elections, Culture, Crypto, and Golf**. The system operates as a live alerting mechanism for contract price swings ≥ $0.10 in either direction, tracks events until resolution (Yes/No), automates simulated trading strategies, and analyzes portfolio performance.

## Core Components

### 1. Live Alerting System
- **Scrolling Chats**: Two real-time feeds
  - **All Events Feed**: Tracks every price swing ≥ $0.10 across all in-scope markets
  - **High-ROI Filter Feed**: Selective filter based on model-calculated ROI potential (liquidity + tightness + price action heuristic)
- **Price Movement Tracking**: Graphs with X-axis (time: seconds/minutes/hours) and Y-axis (contract price)
- **Liquidity Monitoring**: Real-time contract availability at each price level
- **Resolution Tracking**: Continuous monitoring until events resolve (Yes/No)

### 2. Trading & Portfolio Analysis
- **Automated Simulated Trades**: Multiple strategy testing (momentum, mean-revert, longshot, favorite)
- **Performance Tracking**: Portfolio metrics, trade categorization, strategy analysis
- **Execution Framework**: V2 API compliance (`POST /portfolio/events/orders`) with security safeguards
- **Strategy Categorization**: Trades grouped by topic, side, price band, and strategy type

### 3. Technical Architecture
- **REST API Integration**: `https://external-api.demo.kalshi.co/trade-api/v2` and `https://demo-api.kalshi.co/trade-api/v2`
- **WebSocket Support**: `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2` (authenticated handshake required)
- **Data Collection**: GitHub Actions pipeline with 10-minute refresh cycles
- **GitHub Pages Deployment**: Static site hosting with live data integration
- **Verification Framework**: Line-by-line source verification against official Kalshi documentation

### 4. Topic Coverage
- **Gas Prices**: AAA gasoline family, natural gas, oil & energy series
- **Elections**: Political events and market outcomes
- **Culture**: Entertainment and cultural event markets
- **Crypto**: Cryptocurrency and blockchain-related events
- **Golf**: Professional golf tournament markets

## Key Features
- **Highest Dollar Ranking**: Live events sorted by estimated dollar volume
- **Interactive Charts**: Time-window selectable price graphs (seconds to hours)
- **Orderbook Depth**: Full liquidity visualization (bids + derived asks)
- **Resolution Tracking**: Official Yes/No settlement recording
- **Strategy Lab**: Simulated trading with performance analysis
- **Source Verification**: Every data point linked to official Kalshi documentation

## Compliance & Security
- **Official Sources Only**: All data verified against `docs.kalshi.com`
- **No Manual Input**: Fully automated collection and processing
- **Security Safeguards**: Browser-side credential protection, V2 API compliance
- **Flagged Irregularities**: Documented limitations and unverified items
- **Continuous Improvement**: Automated link checking and build validation

## Deployment Status
- **Live Site**: https://karagemop466-tech.github.io/Demo2/
- **GitHub Pages**: Automated deployment on main branch pushes
- **Data Pipeline**: Continuous 10-minute refresh cycles
- **Verification**: Automated CI/CD checks and source validation

## Sources & References
- Official Kalshi API Documentation: https://docs.kalshi.com
- Demo Environment Endpoints: https://external-api.demo.kalshi.co/trade-api/v2
- Market Data Endpoints: Verified line-by-line against official specs
- Order Execution: V2 API compliance with security protocols

## Current Status
- **All Core Requirements Met**: Dashboard, alerts, trading simulation, analysis
- **Continuous Integration**: Automated testing and deployment
- **Verification Complete**: Line-by-line source validation
- **Live Monitoring**: Real-time price swing detection and resolution tracking
