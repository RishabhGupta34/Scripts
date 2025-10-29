#!/usr/bin/env python3
"""
Pipeline Execution Data Fetcher
Fetches pipeline execution data from Harness API and generates a CSV report.
"""

import requests
import csv
import argparse
import sys
import time
import random
import json
from datetime import datetime, timezone
from typing import List, Dict, Any


def date_to_timestamp(date_str: str, end_of_day: bool = False) -> int:
    """
    Convert date string (YYYY-MM-DD) to millisecond timestamp.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        end_of_day: If True, returns end of day (23:59:59.999), else start of day (00:00:00.000)
    
    Returns:
        Timestamp in milliseconds
    """
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        if end_of_day:
            # Set to end of day: 23:59:59.999
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999000)
        else:
            # Set to start of day: 00:00:00.000
            dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Convert to UTC timestamp in milliseconds
        return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Fetch pipeline execution data and generate CSV report'
    )
    parser.add_argument(
        '--auth-token',
        required=False,
        help='Authorization header value (e.g., "Bearer TOKEN")'
    )
    parser.add_argument(
        '--api-key',
        required=False,
        help='API Key for x-api-key header authentication'
    )
    parser.add_argument(
        '--account-id',
        required=True,
        help='Account identifier'
    )
    parser.add_argument(
        '--org-id',
        required=True,
        help='Organization identifier'
    )
    parser.add_argument(
        '--project-id',
        required=False,
        help='Project identifier (optional - if not provided, will fetch all projects)'
    )
    parser.add_argument(
        '--page-size',
        type=int,
        default=50,
        help='Number of records per page (default: 50)'
    )
    parser.add_argument(
        '--output',
        default='pipeline_executions.csv',
        help='Output CSV file name (default: pipeline_executions.csv)'
    )
    parser.add_argument(
        '--exclude-projects',
        nargs='+',
        default=[],
        help='List of project IDs to exclude (space-separated)'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date in YYYY-MM-DD format (e.g., 2025-01-01). Will use start of day (00:00:00)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date in YYYY-MM-DD format (e.g., 2025-12-31). Will use end of day (23:59:59)'
    )
    parser.add_argument(
        '--start-time',
        type=int,
        help='Start time in milliseconds (alternative to --start-date)'
    )
    parser.add_argument(
        '--end-time',
        type=int,
        help='End time in milliseconds (alternative to --end-date)'
    )
    
    args = parser.parse_args()
    
    # Validate that either auth-token or api-key is provided
    if not args.auth_token and not args.api_key:
        parser.error("Either --auth-token or --api-key must be provided")
    
    if args.auth_token and args.api_key:
        parser.error("Cannot use both --auth-token and --api-key. Please provide only one.")
    
    # Convert dates to timestamps if provided
    if args.start_date:
        args.start_time = date_to_timestamp(args.start_date, end_of_day=False)
    elif not args.start_time:
        # Default to 30 days ago
        args.start_time = 1735689600000
    
    if args.end_date:
        args.end_time = date_to_timestamp(args.end_date, end_of_day=True)
    elif not args.end_time:
        # Default to current time
        args.end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    return args


def fetch_projects(
    base_url: str,
    auth_token: str,
    account_id: str,
    org_id: str,
    page_index: int = 0,
    page_size: int = 20,
    api_key: str = None
) -> Dict[str, Any]:
    """
    Fetch projects for a specific organization.
    
    Args:
        base_url: Base URL for the API
        auth_token: Bearer authentication token (optional if api_key is provided)
        account_id: Account identifier
        org_id: Organization identifier
        page_index: Page index (0-indexed)
        page_size: Number of records per page
        api_key: API key for x-api-key header (optional)
    
    Returns:
        API response as dictionary
    """
    url = (
        f"{base_url}/ng/api/aggregate/projects"
        f"?routingId={account_id}"
        f"&accountIdentifier={account_id}"
        f"&pageIndex={page_index}"
        f"&pageSize={page_size}"
        f"&sortOrders=lastModifiedAt,DESC"
        f"&onlyFavorites=false"
    )
    
    if org_id:
        url += f"&orgIdentifier={org_id}"
    
    # Build headers based on authentication method
    if api_key:
        headers = {'x-api-key': api_key}
    else:
        headers = {'Authorization': auth_token}
    
    try:
        response = requests.get(
            url,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"\nError fetching projects: {e}", file=sys.stderr)
        print(f"\nSample curl command to debug:", file=sys.stderr)
        print(f"curl --location '{url}' \\", file=sys.stderr)
        print(f"  --header 'Authorization: <YOUR_AUTH_TOKEN>'", file=sys.stderr)
        raise


def fetch_pipeline_executions(
    base_url: str,
    auth_token: str,
    account_id: str,
    org_id: str,
    project_id: str,
    page: int,
    page_size: int,
    start_time: int,
    end_time: int,
    api_key: str = None
) -> Dict[str, Any]:
    """
    Fetch pipeline execution data for a specific page.
    
    Args:
        base_url: Base URL for the API
        auth_token: Bearer authentication token
        account_id: Account identifier
        org_id: Organization identifier
        project_id: Project identifier
        page: Page number (0-indexed)
        page_size: Number of records per page
        start_time: Start time in milliseconds
        end_time: End time in milliseconds
    
    Returns:
        API response as dictionary
    """
    url = (
        f"{base_url}/pipeline/api/pipelines/execution/summary"
        f"?routingId={account_id}"
        f"&accountIdentifier={account_id}"
        f"&projectIdentifier={project_id}"
        f"&orgIdentifier={org_id}"
        f"&page={page}"
        f"&size={page_size}"
        f"&sort=startTs,DESC"
        f"&myDeployments=false"
        f"&searchTerm="
        f"&module=cd"
    )
    
    # Build headers based on authentication method
    if api_key:
        headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }
    else:
        headers = {
            'Authorization': auth_token,
            'Content-Type': 'application/json'
        }
    
    payload = {
        "filterType": "PipelineExecution",
        "timeRange": {
            "startTime": start_time,
            "endTime": end_time
        }
    }
    
    # Retry logic with 3 attempts
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Try to get response body for more details
            error_details = ""
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.text
                    error_details = f"\nResponse body: {error_body[:500]}"
                except:
                    pass
            
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # 2, 4, 6 seconds
                print(f"\n  Warning: API call failed (attempt {attempt + 1}/{max_retries}): {e}{error_details}", file=sys.stderr)
                print(f"  Retrying in {wait_time} seconds...", file=sys.stderr)
                time.sleep(wait_time)
            else:
                print(f"\nError fetching pipeline executions after {max_retries} attempts: {e}{error_details}", file=sys.stderr)
                print(f"\nSample curl command to debug:", file=sys.stderr)
                print(f"curl --location '{url}' \\", file=sys.stderr)
                print(f"  --header 'Authorization: <YOUR_AUTH_TOKEN>' \\", file=sys.stderr)
                print(f"  --header 'Content-Type: application/json' \\", file=sys.stderr)
                print(f"  --data '{json.dumps(payload)}'", file=sys.stderr)
                raise


def extract_stage_data(layout_node_map: Dict[str, Any], env_filter: str = "Production", execution_id: str = "") -> List[Dict[str, Any]]:
    """
    Extract stage data from layoutNodeMap, filtering by environment type.
    
    Args:
        layout_node_map: The layoutNodeMap from the API response
        env_filter: Environment type to filter (default: "Production")
        execution_id: Execution ID for debugging
    
    Returns:
        List of stage data dictionaries
    """
    stages = []
    
    if not layout_node_map:
        return stages
    
    for node_id, node_data in layout_node_map.items():
        module_info = node_data.get('moduleInfo', {})
        
        # Check if this node has CD module info
        if 'cd' in module_info and module_info['cd']:
            # Filter by environment type
            env_type = module_info.get('cd', {}).get('infraExecutionSummary', {}).get('type')
            env_name = module_info.get('cd', {}).get('infraExecutionSummary', {}).get('name', '')
            
            # Check if it's a Production environment (not PreProduction)
            if env_type == env_filter:
                # Get service name, leave blank if serviceInfo is null/missing
                service_info = module_info.get('cd', {}).get('serviceInfo')
                if service_info and isinstance(service_info, dict):
                    service_name = service_info.get('displayName', '')
                else:
                    service_name = ''
                
                stage_info = {
                    'stage_name': node_data.get('name', ''),
                    'start_time': node_data.get('startTs'),
                    'end_time': node_data.get('endTs'),
                    'status': node_data.get('status', ''),
                    'environment_name': env_name,
                    'service_name': service_name
                }
                stages.append(stage_info)
    
    return stages


def format_timestamp(timestamp_ms: int) -> str:
    """Convert millisecond timestamp to readable format in UTC."""
    if not timestamp_ms:
        return ''
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return ''


def calculate_duration(start_ts: int, end_ts: int) -> str:
    """Calculate duration between two timestamps in HH:MM:SS format."""
    if not start_ts or not end_ts:
        return ''
    
    duration_ms = end_ts - start_ts
    duration_seconds = int(duration_ms / 1000.0)
    
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    seconds = duration_seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def parse_execution_data(response_data: Dict[str, Any], base_url: str, account_id: str, org_id: str, project_id: str) -> List[Dict[str, str]]:
    """
    Parse execution data from API response and extract relevant fields.
    
    Args:
        response_data: API response data
        base_url: Base URL for constructing execution URLs
        account_id: Account identifier
        org_id: Organization identifier
        project_id: Project identifier
    
    Returns:
        List of parsed execution records
    """
    records = []
    
    content = response_data.get('data', {}).get('content', [])
    
    for execution in content:
        pipeline_identifier = execution.get('pipelineIdentifier', '')
        execution_id = execution.get('planExecutionId', '')
        layout_node_map = execution.get('layoutNodeMap', {})
        
        # Get execution-level timestamps
        execution_start_time = execution.get('startTs')
        execution_end_time = execution.get('endTs')
        
        # Extract stages from layoutNodeMap
        stages = extract_stage_data(layout_node_map, execution_id=execution_id)
        
        # If no production stages found, skip this execution
        if not stages:
            continue
        
        # Create a record for each stage
        for stage in stages:
            # Construct execution URL (remove /gateway if present in base_url)
            url_base = base_url.replace('/gateway', '')
            execution_url = (
                f"{url_base}/ng/#/account/{account_id}/cd/orgs/{org_id}/projects/{project_id}"
                f"/pipelines/{pipeline_identifier}/executions/{execution_id}/pipeline"
            )
            
            record = {
                'Pipeline': execution.get('name', ''),
                'Project ID': project_id,
                'Execution URL': execution_url,
                'Service Name': stage['service_name'],
                'End Time': format_timestamp(execution_end_time),
                'Start Time': format_timestamp(execution_start_time),
                'Environment Name': stage['environment_name'],
                'Status': stage['status'],
                'Duration': calculate_duration(execution_start_time, execution_end_time)
            }
            records.append(record)
    
    return records


def write_to_csv(records: List[Dict[str, str]], output_file: str, mode: str = 'w'):
    """
    Write records to CSV file.
    
    Args:
        records: List of record dictionaries
        output_file: Output CSV file path
        mode: File mode - 'w' for write (with header), 'a' for append (no header)
    """
    if not records:
        return
    
    fieldnames = [
        'Pipeline',
        'Project ID',
        'Execution URL',
        'Service Name',
        'End Time',
        'Start Time',
        'Environment Name',
        'Status',
        'Duration'
    ]
    
    with open(output_file, mode, newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if mode == 'w':
            writer.writeheader()
        writer.writerows(records)
    
    if mode == 'w':
        print(f"Created CSV file: {output_file}")
    else:
        print(f"Appended {len(records)} records to {output_file}")


def fetch_all_projects(base_url: str, auth_token: str, account_id: str, org_id: str, api_key: str = None) -> List[str]:
    """
    Fetch all projects for an organization.
    
    Args:
        base_url: Base URL for the API
        auth_token: Bearer authentication token
        account_id: Account identifier
        org_id: Organization identifier
        api_key: API key for x-api-key header (optional)
    
    Returns:
        List of project identifiers
    """
    all_projects = []
    page_index = 0
    
    print("Fetching all projects...")
    
    while True:
        response_data = fetch_projects(
            base_url=base_url,
            auth_token=auth_token,
            account_id=account_id,
            org_id=org_id,
            page_index=page_index,
            page_size=20,
            api_key=api_key
        )
        
        content = response_data.get('data', {}).get('content', [])
        page_info = response_data.get('data', {})
        total_pages = page_info.get('totalPages', 0)
        
        for project in content:
            project_identifier = project.get('projectResponse', {}).get('project', {}).get('identifier')
            if project_identifier:
                all_projects.append(project_identifier)
        
        print(f"  Page {page_index}: Found {len(content)} projects")
        
        if page_index >= total_pages - 1:
            break
        
        page_index += 1
        
        # Add random delay between 0.5 to 1 second
        if page_index < total_pages:
            delay = random.uniform(0.5, 1.0)
            time.sleep(delay)
    
    print(f"Total projects found: {len(all_projects)}")
    return all_projects


def fetch_project_executions_batch(
    base_url: str,
    auth_token: str,
    account_id: str,
    org_id: str,
    project_id: str,
    page_size: int,
    start_time: int,
    end_time: int,
    api_key: str = None,
    batch_label: str = ""
) -> List[Dict[str, str]]:
    """
    Fetch pipeline executions for a specific project within a time range batch.
    
    Args:
        base_url: Base URL for the API
        auth_token: Bearer authentication token
        account_id: Account identifier
        org_id: Organization identifier
        project_id: Project identifier
        page_size: Number of records per page
        start_time: Start time in milliseconds
        end_time: End time in milliseconds
        api_key: API key for authentication
        batch_label: Label for the batch (for logging)
    
    Returns:
        List of execution records
    """
    all_records = []
    page = 0
    total_pages = None
    total_elements = None
    
    while True:
        response_data = fetch_pipeline_executions(
            base_url=base_url,
            auth_token=auth_token,
            account_id=account_id,
            org_id=org_id,
            project_id=project_id,
            page=page,
            page_size=page_size,
            start_time=start_time,
            end_time=end_time,
            api_key=api_key
        )
        
        # Get pagination info
        page_info = response_data.get('data', {})
        total_pages = page_info.get('totalPages', 0)
        total_elements = page_info.get('totalElements', 0)
        
        # Print pagination info on first page
        if page == 0:
            batch_info = f" [{batch_label}]" if batch_label else ""
            print(f"  Total pages: {total_pages}, Total executions: {total_elements}{batch_info}")
        
        # Parse and collect records
        records = parse_execution_data(
            response_data,
            base_url,
            account_id,
            org_id,
            project_id
        )
        all_records.extend(records)
        
        # Print progress
        print(f"  Processing page {page + 1}/{total_pages} - Found {len(records)} production stage records on this page")
        
        # Check if this is the last page
        if page >= total_pages - 1 or total_pages == 0:
            break
        
        page += 1
        
        # Add random delay between 0.5 to 1 second
        if page < total_pages:
            delay = random.uniform(0.5, 1.0)
            time.sleep(delay)
    
    return all_records


def fetch_project_executions(
    base_url: str,
    auth_token: str,
    account_id: str,
    org_id: str,
    project_id: str,
    page_size: int,
    start_time: int,
    end_time: int,
    api_key: str = None
) -> List[Dict[str, str]]:
    """
    Fetch all pipeline executions for a specific project.
    Automatically splits into batches if total count exceeds 10k.
    
    Args:
        base_url: Base URL for the API
        auth_token: Bearer authentication token
        account_id: Account identifier
        org_id: Organization identifier
        project_id: Project identifier
        page_size: Number of records per page
        start_time: Start time in milliseconds
        end_time: End time in milliseconds
        api_key: API key for authentication
    
    Returns:
        List of execution records
    """
    # First, check the total count
    response_data = fetch_pipeline_executions(
        base_url=base_url,
        auth_token=auth_token,
        account_id=account_id,
        org_id=org_id,
        project_id=project_id,
        page=0,
        page_size=page_size,
        start_time=start_time,
        end_time=end_time,
        api_key=api_key
    )
    
    page_info = response_data.get('data', {})
    total_elements = page_info.get('totalElements', 0)
    
    # If total elements <= 10k, fetch normally
    if total_elements <= 10000:
        print(f"  Total executions: {total_elements} (within limit)")
        
        # Parse first page
        all_records = parse_execution_data(
            response_data,
            base_url,
            account_id,
            org_id,
            project_id
        )
        
        total_pages = page_info.get('totalPages', 0)
        print(f"  Processing page 1/{total_pages} - Found {len(all_records)} production stage records on this page")
        
        # Fetch remaining pages
        for page in range(1, total_pages):
            response_data = fetch_pipeline_executions(
                base_url=base_url,
                auth_token=auth_token,
                account_id=account_id,
                org_id=org_id,
                project_id=project_id,
                page=page,
                page_size=page_size,
                start_time=start_time,
                end_time=end_time,
                api_key=api_key
            )
            
            records = parse_execution_data(
                response_data,
                base_url,
                account_id,
                org_id,
                project_id
            )
            all_records.extend(records)
            
            print(f"  Processing page {page + 1}/{total_pages} - Found {len(records)} production stage records on this page")
            
            # Add random delay
            delay = random.uniform(0.5, 1.0)
            time.sleep(delay)
        
        return all_records
    
    # If total elements > 10k, split into 10-day batches
    print(f"  Total executions: {total_elements} (exceeds 10k limit)")
    print(f"  Splitting time range into 10-day batches...")
    
    all_records = []
    batch_size_ms = 10 * 24 * 60 * 60 * 1000  # 10 days in milliseconds
    current_start = start_time
    batch_num = 1
    
    while current_start < end_time:
        # Calculate batch end time (inclusive, so subtract 1ms from next batch start)
        current_end = min(current_start + batch_size_ms - 1, end_time)
        
        # Format dates for logging
        start_date = format_timestamp(current_start)
        end_date = format_timestamp(current_end)
        batch_label = f"Batch {batch_num}: {start_date} to {end_date}"
        
        print(f"\n  {batch_label}")
        
        # Fetch this batch
        batch_records = fetch_project_executions_batch(
            base_url=base_url,
            auth_token=auth_token,
            account_id=account_id,
            org_id=org_id,
            project_id=project_id,
            page_size=page_size,
            start_time=current_start,
            end_time=current_end,
            api_key=api_key,
            batch_label=batch_label
        )
        
        all_records.extend(batch_records)
        print(f"  Batch {batch_num} complete: {len(batch_records)} production stage records")
        
        # Move to next batch (add 1ms to avoid overlap since end_time is inclusive)
        current_start = current_end + 1
        batch_num += 1
        
        # Add delay between batches
        if current_start < end_time:
            delay = random.uniform(0.5, 1.0)
            time.sleep(delay)
    
    return all_records


def main():
    """Main function to orchestrate the data fetching and CSV generation."""
    args = parse_arguments()
    
    # Set base URL
    base_url = "https://app.harness.io"
    
    print(f"Fetching pipeline execution data...")
    print(f"Base URL: {base_url}")
    print(f"Account: {args.account_id}")
    print(f"Organization: {args.org_id}")
    print(f"Project: {args.project_id if args.project_id else 'ALL'}")
    if args.exclude_projects:
        print(f"Excluding projects: {', '.join(args.exclude_projects)}")
    print(f"Page size: {args.page_size}")
    print(f"Time range: {format_timestamp(args.start_time)} to {format_timestamp(args.end_time)}")
    print(f"Time range (epoch): {args.start_time} to {args.end_time}")
    print(f"Delay between calls: random 0.5-1.0s")
    print()
    
    total_records = 0
    csv_initialized = False
    
    # Determine which projects to process
    if args.project_id:
        # Single project mode
        projects = [args.project_id]
    else:
        # Fetch all projects
        all_projects = fetch_all_projects(
            base_url=base_url,
            auth_token=args.auth_token,
            account_id=args.account_id,
            org_id=args.org_id,
            api_key=args.api_key
        )
        # Filter out excluded projects
        projects = [p for p in all_projects if p not in args.exclude_projects]
        if args.exclude_projects:
            excluded_count = len(all_projects) - len(projects)
            print(f"Excluded {excluded_count} project(s)")
        print()
    
    # Process each project
    for idx, project_id in enumerate(projects, 1):
        print(f"[{idx}/{len(projects)}] Processing project: {project_id}")
        
        project_records = fetch_project_executions(
            base_url=base_url,
            auth_token=args.auth_token,
            account_id=args.account_id,
            org_id=args.org_id,
            project_id=project_id,
            page_size=args.page_size,
            start_time=args.start_time,
            end_time=args.end_time,
            api_key=args.api_key
        )
        
        # Write to CSV incrementally
        if project_records:
            if not csv_initialized:
                # First write - create file with header
                write_to_csv(project_records, args.output, mode='w')
                csv_initialized = True
            else:
                # Subsequent writes - append without header
                write_to_csv(project_records, args.output, mode='a')
            
            total_records += len(project_records)
        
        print(f"  Found {len(project_records)} production stage records for project {project_id}")
        print(f"  Total records written so far: {total_records}")
        print()
        
        # Add random delay between projects (except for the last one)
        if idx < len(projects):
            delay = random.uniform(0.5, 1.0)
            time.sleep(delay)
    
    print(f"Total production stage records collected: {total_records}")
    if total_records > 0:
        print(f"All records saved to: {args.output}")
    else:
        print("No records to write.")


if __name__ == '__main__':
    main()
