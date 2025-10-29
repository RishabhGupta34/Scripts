# Harness Pipeline Execution Report Generator

A Python utility to extract pipeline execution data from Harness and generate comprehensive CSV reports for production deployments.

## Overview

This tool connects to the Harness API to retrieve pipeline execution history and generates detailed reports in CSV format. It's designed to help teams track deployment metrics, analyze execution patterns, and maintain audit records of production deployments.

## Key Features

- **Flexible Scope**: Fetch data from a single project or across all projects in an organization
- **Project Exclusion**: Exclude specific projects from organization-wide fetches
- **Automated Pagination**: Handles large datasets by automatically fetching all available pages
- **10k+ Record Handling**: Automatically splits time ranges into batches when total records exceed 10,000
- **Production Focus**: Filters to include only Production environment deployments
- **Detailed Metrics**: Captures execution-level timing, status, and service information
- **Incremental Writing**: Saves data to CSV after each project to prevent data loss on failures
- **Automatic Retry**: Retries failed API calls up to 3 times with exponential backoff
- **Rate Limiting**: Built-in delays between API calls to ensure system stability
- **Error Handling**: Provides detailed error messages with response bodies and sample curl commands
- **Excel-Ready Output**: Generates CSV files with direct URLs and formatted timestamps

## CSV Report Columns

- **Pipeline**: Pipeline name
- **Project ID**: Harness project identifier
- **Execution URL**: Clickable link to view execution in Harness UI
- **Service Name**: Deployed service name
- **Start Time**: Execution start timestamp (UTC)
- **End Time**: Execution end timestamp (UTC)
- **Environment Name**: Target environment
- **Status**: Execution status (Success, Failed, etc.)
- **Duration**: Total execution time (formatted as hours, minutes, seconds)

### Finding Your Identifiers

- **Account ID**: Found in your Harness URL: `https://app.harness.io/ng/account/{ACCOUNT_ID}/...`
- **Organization ID**: Navigate to Organization Settings in Harness UI
- **Project ID**: Navigate to Project Settings in Harness UI
- **Auth Token**: Generate from User Profile → My API Keys & Tokens
- **API Key**: Generate from Account Settings → Access Control → API Keys

## Handling Large Datasets (>10k Records)

When a project has more than 10,000 pipeline executions in the specified time range, the Harness API cannot return records beyond the 10,000th position. The script automatically handles this by:

1. **Detection**: Checks the `totalElements` count on the first API call
2. **Automatic Batching**: If >10k, splits the time range into 10-day batches
3. **Sequential Processing**: Processes each batch completely before moving to the next
4. **Progress Tracking**: Shows batch progress with date ranges

**Example Output:**
```
Total executions: 15000 (exceeds 10k limit)
Splitting time range into 10-day batches...

Batch 1: 2025-01-01 00:00:00 to 2025-01-10 23:59:59
Total pages: 50, Total executions: 2500
...
Batch 1 complete: 150 production stage records

Batch 2: 2025-01-11 00:00:00 to 2025-01-20 23:59:59
...
```

**Note:** The 10-day batch size is optimized for most use cases. If a single 10-day period still exceeds 10k records, consider using shorter date ranges.

## Prerequisites

- Python 3.7 or higher
- `requests` library (install with: `pip install requests`)
- Access to Harness API (Bearer token or API key)
- Network connectivity to Harness instance

## Installation

The script requires only the `requests` library. Install it using:

```bash
pip install requests
```

**Note:** All other dependencies (`csv`, `json`, `datetime`, `argparse`, etc.) are part of Python's standard library and require no additional installation.

## Usage

### Basic Usage - Single Project

Fetch execution data for a specific project using Bearer token authentication:

```bash
python pipeline_execution_fetcher.py \
  --auth-token "Bearer YOUR_AUTH_TOKEN" \
  --account-id "YOUR_ACCOUNT_ID" \
  --org-id "YOUR_ORG_ID" \
  --project-id "YOUR_PROJECT_ID"
```

### Using API Key Authentication

Alternatively, use API key authentication:

```bash
python pipeline_execution_fetcher.py \
  --api-key "YOUR_API_KEY" \
  --account-id "YOUR_ACCOUNT_ID" \
  --org-id "YOUR_ORG_ID" \
  --project-id "YOUR_PROJECT_ID"
```

### Fetch All Projects in Organization

Omit the `--project-id` parameter to fetch data from all projects:

```bash
python pipeline_execution_fetcher.py \
  --auth-token "Bearer YOUR_AUTH_TOKEN" \
  --account-id "YOUR_ACCOUNT_ID" \
  --org-id "YOUR_ORG_ID"
```

### Exclude Specific Projects

Exclude specific projects when fetching all projects in an organization:

```bash
python pipeline_execution_fetcher.py \
  --auth-token "Bearer YOUR_AUTH_TOKEN" \
  --account-id "YOUR_ACCOUNT_ID" \
  --org-id "YOUR_ORG_ID" \
  --exclude-projects project1 project2 project3
```

### Using Date Range (Recommended)

Specify time range using readable date format:

```bash
python pipeline_execution_fetcher.py \
  --api-key "YOUR_API_KEY" \
  --account-id "YOUR_ACCOUNT_ID" \
  --org-id "YOUR_ORG_ID" \
  --project-id "YOUR_PROJECT_ID" \
  --start-date "2025-01-01" \
  --end-date "2025-12-31"
```

### Advanced Usage with Custom Options

Specify custom time range using epoch timestamps, output file, and page size:

```bash
python pipeline_execution_fetcher.py \
  --auth-token "Bearer YOUR_AUTH_TOKEN" \
  --account-id "YOUR_ACCOUNT_ID" \
  --org-id "YOUR_ORG_ID" \
  --project-id "YOUR_PROJECT_ID" \
  --page-size 50 \
  --output "my_report.csv" \
  --start-time 1704067200000 \
  --end-time 1735689599999
```

## Command-Line Parameters

### Authentication (Required - Choose One)

| Parameter | Description |
|-----------|-------------|
| `--auth-token` | Bearer token for authentication. Format: `"Bearer YOUR_TOKEN"` |
| `--api-key` | API key for authentication. Uses `x-api-key` header |

**Note:** Provide either `--auth-token` OR `--api-key`, not both.

### Required Parameters

| Parameter | Description |
|-----------|-------------|
| `--account-id` | Your Harness account identifier |
| `--org-id` | Organization identifier within your account |

### Optional Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--project-id` | None | Specific project to query. If omitted, fetches all projects in the organization |
| `--exclude-projects` | None | Space-separated list of project IDs to exclude (e.g., `project1 project2`) |
| `--page-size` | 50 | Number of records to fetch per API call (1-100) |
| `--output` | `pipeline_executions.csv` | Output CSV file name |
| `--start-date` | None | Start date in YYYY-MM-DD format (e.g., `2025-01-01`). Uses start of day (00:00:00) |
| `--end-date` | None | End date in YYYY-MM-DD format (e.g., `2025-12-31`). Uses end of day (23:59:59) |
| `--start-time` | Last 30 days | Start time in milliseconds since epoch (alternative to `--start-date`) |
| `--end-time` | Current time | End time in milliseconds since epoch (alternative to `--end-date`) |

**Notes:** 
- Use either `--start-date`/`--end-date` (recommended for readability) OR `--start-time`/`--end-time` (for precise millisecond control)
- `--exclude-projects` only works when fetching all projects (without `--project-id`)

## Output Format

The script generates a CSV file with the following structure:

| Column | Description | Example |
|--------|-------------|---------|
| Pipeline | Pipeline name | `production-deployment` |
| Project ID | Project identifier | `microservices` |
| Execution URL | Direct link to execution | `https://app.harness.io/ng/#/account/...` |
| Service Name | Deployed service | `payment-service` (or blank if not applicable) |
| End Time | Completion timestamp (UTC) | `2025-01-15 10:30:45` |
| Start Time | Start timestamp (UTC) | `2025-01-15 10:25:30` |
| Environment Name | Target environment | `Production` |
| Status | Execution result | `Success`, `Failed`, `Aborted` |
| Duration | Execution time (HH:MM:SS) | `00:05:15` |

**Note:** URLs are plain text and clickable in most spreadsheet applications.

## How It Works

1. **Authentication**: Connects to Harness API using provided credentials
2. **Project Discovery**: Fetches specified project or all projects in organization (with exclusions if specified)
3. **Large Dataset Detection**: Checks if total records exceed 10,000 for automatic batching
4. **Execution Retrieval**: Queries pipeline executions within the specified time range
   - If >10k records: Automatically splits into 10-day batches
   - If ≤10k records: Fetches all pages normally
5. **Filtering**: Extracts only Production environment deployments
6. **Data Processing**: Converts timestamps, calculates durations, formats data
7. **Incremental CSV Writing**: Saves data after each project to prevent data loss
8. **Error Recovery**: Retries failed API calls and continues with next project on errors

## Important Notes

### Core Behavior
- **API Endpoint**: The script connects to `https://app.harness.io` by default
- **Environment Filter**: Only Production environments are included
- **Time Format**: All timestamps are displayed in UTC timezone (YYYY-MM-DD HH:MM:SS)
- **Duration Format**: Displayed as HH:MM:SS (e.g., 01:23:45)

### Reliability Features
- **Automatic Retry**: Failed API calls are retried up to 3 times with 2, 4, 6 second delays
- **Incremental Saving**: Data is written to CSV after each project completes
- **Error Resilience**: Script continues processing remaining projects even if one fails
- **10k+ Handling**: Automatically splits time range into 10-day batches when records exceed 10,000

### Performance
- **Rate Limiting**: Automatic 0.5-1.0 second delays between API calls to prevent throttling
- **Pagination**: Automatically handles large datasets across multiple API pages
- **Memory Efficient**: Writes data incrementally instead of storing everything in memory

### Error Handling
- **Detailed Errors**: Shows HTTP status, response body, and retry attempts
- **Debug Support**: Provides sample curl commands for troubleshooting
- **Timeout Protection**: 30-second timeout on API calls to prevent hanging
