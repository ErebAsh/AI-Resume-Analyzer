# Load Testing Documentation

## 📋 Overview

This directory contains load and stress testing for the AI Resume Analyzer's analysis pipeline. Tests are implemented using **k6** and **Locust**.

## 🎯 Test Types

### 1. Smoke Test
- **Purpose**: Verify system works under minimal load
- **Users**: 1-2 VUs
- **Duration**: 2 minutes
- **Command**: `npm run test:load:smoke`

### 2. Load Test
- **Purpose**: Test normal operation under expected load
- **Users**: 10-50 VUs
- **Duration**: 10 minutes
- **Command**: `npm run test:load`

### 3. Stress Test
- **Purpose**: Find breaking point
- **Users**: 10-300 VUs
- **Duration**: 15 minutes
- **Command**: `npm run test:load:stress`

### 4. Spike Test
- **Purpose**: Test sudden traffic spikes
- **Users**: 5-200 VUs
- **Duration**: 5 minutes
- **Command**: `npm run test:load:spike`

### 5. Soak Test
- **Purpose**: Test long-term stability
- **Users**: 20-50 VUs
- **Duration**: 1 hour
- **Command**: `npm run test:load:soak`

## 🚀 Running Tests

### With k6

```bash
# Install k6
# macOS: brew install k6
# Linux: sudo apt-get install k6
# Windows: choco install k6

# Run smoke test
k6 run scripts/smoke-test.js

# Run load test
k6 run scripts/analysis-test.js

# Run stress test
k6 run scripts/stress-test.js

# Run spike test
k6 run scripts/spike-test.js

# Run soak test
k6 run scripts/soak-test.js

# With environment variables
BASE_URL=http://localhost:8000 k6 run scripts/analysis-test.js