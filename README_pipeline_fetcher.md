# Harness Pipeline Execution Report Generator

A Python utility to extract pipeline execution data from Harness and generate comprehensive CSV reports for production deployments.

## Overview

This tool connects to the Harness API to retrieve pipeline execution history and generates detailed reports in CSV format. It's designed to help teams track deployment metrics, analyze execution patterns, and maintain audit records of production deployments.

## Key Features

- **Flexible Scope**: Fetch data from a single project or across all projects in an organization
- **Automated Pagination**: Handles large datasets by automatically fetching all available pages
- **Production Focus**: Filters to include only Production environment deployments
- **Detailed Metrics**: Captures execution-level timing, status, and service information
- **Rate Limiting**: Built-in delays between API calls to ensure system stability
- **Error Handling**: Provides diagnostic information and sample curl commands for troubleshooting
- **Excel-Ready Output**: Generates CSV files with clickable hyperlinks to execution details

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

### Advanced Usage with Custom Options

Specify custom time range, output file, and page size:

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
| `--page-size` | 50 | Number of records to fetch per API call (1-100) |
| `--output` | `pipeline_executions.csv` | Output CSV file name |
| `--start-time` | Last 30 days | Start time in milliseconds since epoch (Unix timestamp × 1000) |
| `--end-time` | Current time | End time in milliseconds since epoch (Unix timestamp × 1000) |

## Output Format

The script generates a CSV file with the following structure:

| Column | Description | Example |
|--------|-------------|---------|
| Pipeline | Pipeline name | `production-deployment` |
| Project ID | Project identifier | `microservices` |
| Execution URL | Clickable link to execution | `=HYPERLINK("https://...", "URL")` |
| Service Name | Deployed service | `payment-service` |
| End Time | Completion timestamp (UTC) | `2025-01-15 10:30:45` |
| Start Time | Start timestamp (UTC) | `2025-01-15 10:25:30` |
| Environment Name | Target environment | `Production` |
| Status | Execution result | `Success`, `Failed`, `Aborted` |
| Duration | Execution time | `5m 15s` |

**Note:** The Execution URL column uses Excel's HYPERLINK formula for clickable links when opened in Excel or Google Sheets.

## How It Works

1. **Authentication**: Connects to Harness API using provided credentials
2. **Project Discovery**: Fetches specified project or all projects in organization
3. **Execution Retrieval**: Queries pipeline executions within the specified time range
4. **Filtering**: Extracts only Production environment deployments
5. **Data Processing**: Converts timestamps, calculates durations, formats data
6. **CSV Generation**: Writes formatted data to CSV file with Excel-compatible hyperlinks

## Important Notes

- **API Endpoint**: The script connects to `https://app.harness.io` by default
- **Environment Filter**: Only Production environments are included
- **Time Format**: All timestamps are displayed in UTC timezone
- **Rate Limiting**: Automatic 0.5-1.0 second delays between API calls to prevent throttling
- **Pagination**: Automatically handles large datasets across multiple API pages
- **Error Handling**: Stops on errors and provides diagnostic curl commands for troubleshooting
