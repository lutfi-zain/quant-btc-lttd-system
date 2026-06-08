## 1. Project Initialization

- [ ] 1.1 Initialize Bun project in `backend/` directory (`bun init -y`)
- [ ] 1.2 Install Hono framework dependency (`bun add hono`)
- [ ] 1.3 Create main application entry point (`backend/index.ts`)

## 2. Database Connection

- [ ] 2.1 Setup read-only native SQLite connection using `bun:sqlite` targeting `database/lttd.db`
- [ ] 2.2 Create database service functions for safe, read-only SQL queries avoiding database locks
- [ ] 2.3 Verify `PRAGMA journal_mode=WAL;` is established or gracefully handle its absence

## 3. API Endpoint Implementation

- [ ] 3.1 Implement `GET /api/health` returning HTTP 200 and SQLite connection status boolean
- [ ] 3.2 Implement `GET /api/lttd/latest` serving the most recent record (`timestamp`, `final_score`, `regime`)
- [ ] 3.3 Implement `GET /api/lttd/history` with optional `start` and `end` query parameter bounds
- [ ] 3.4 Configure Hono CORS middleware for cross-origin frontend React SPA access

## 4. Verification and Testing

- [ ] 4.1 Create test setup with a mock SQLite database containing sample LTTD domain data
- [ ] 4.2 Write Bun tests for `/api/health` endpoint response payload
- [ ] 4.3 Write Bun tests for `/api/lttd/latest` verifying domain constraints (`final_score` ∈ [-1.0, +1.0], `regime` ∈ ["BULL", "BEAR", "SIDEWAYS"])
- [ ] 4.4 Write Bun tests for `/api/lttd/history` verifying time-ordered array format and boundary filtering
