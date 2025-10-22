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
        '--start-time',
        type=int,
        default=1735689600000,
        help='Start time in milliseconds (default: 1735669800000)'
    )
    parser.add_argument(
        '--end-time',
        type=int,
        default=1761125859000,
        help='End time in milliseconds (default: 1761157799999)'
    )
    
    args = parser.parse_args()
    
    # Validate that either auth-token or api-key is provided
    if not args.auth_token and not args.api_key:
        parser.error("Either --auth-token or --api-key must be provided")
    
    if args.auth_token and args.api_key:
        parser.error("Cannot use both --auth-token and --api-key. Please provide only one.")
    
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
        "myDeployments": False,
        "timeRange": {
            "startTime": start_time,
            "endTime": end_time
        },
        "moduleProperties": {
            "ci": {},
            "cd": {}
        }
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"\nError fetching pipeline executions: {e}", file=sys.stderr)
        print(f"\nSample curl command to debug:", file=sys.stderr)
        print(f"curl --location '{url}' \\", file=sys.stderr)
        print(f"  --header 'Authorization: <YOUR_AUTH_TOKEN>' \\", file=sys.stderr)
        print(f"  --header 'Content-Type: application/json' \\", file=sys.stderr)
        print(f"  --data '{json.dumps(payload)}'", file=sys.stderr)
        raise


def extract_stage_data(layout_node_map: Dict[str, Any], env_filter: str = "Production") -> List[Dict[str, Any]]:
    """
    Extract stage data from layoutNodeMap, filtering by environment type.
    
    Args:
        layout_node_map: The layoutNodeMap from the API response
        env_filter: Environment type to filter (default: "Production")
    
    Returns:
        List of stage data dictionaries
    """
    stages = []
    
    if not layout_node_map:
        return stages
    
    for node_id, node_data in layout_node_map.items():
        # Check if this is a stage node
        if node_data.get('nodeType') == 'Deployment' or node_data.get('nodeType') == 'stage':
            module_info = node_data.get('moduleInfo', {})
            
            # Filter by environment type
            env_type = module_info.get('cd', {}).get('infraExecutionSummary', {}).get('type')
            env_name = module_info.get('cd', {}).get('infraExecutionSummary', {}).get('name', '')
            
            # Check if it's a Production environment (not PreProduction)
            if env_type == env_filter:
                stage_info = {
                    'stage_name': node_data.get('name', ''),
                    'start_time': node_data.get('startTs'),
                    'end_time': node_data.get('endTs'),
                    'status': node_data.get('status', ''),
                    'environment_name': env_name,
                    'service_name': module_info.get('cd', {}).get('serviceInfo', {}).get('displayName', '')
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
    """Calculate duration between two timestamps."""
    if not start_ts or not end_ts:
        return ''
    
    duration_ms = end_ts - start_ts
    duration_seconds = duration_ms / 1000.0
    
    hours = int(duration_seconds // 3600)
    minutes = int((duration_seconds % 3600) // 60)
    seconds = round(duration_seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


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
        stages = extract_stage_data(layout_node_map)
        
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
            
            # Create Excel hyperlink formula
            excel_hyperlink = f'=HYPERLINK("{execution_url}", "URL")'
            
            record = {
                'Pipeline': execution.get('name', ''),
                'Project ID': project_id,
                'Execution URL': excel_hyperlink,
                'Service Name': stage['service_name'],
                'End Time': format_timestamp(execution_end_time),
                'Start Time': format_timestamp(execution_start_time),
                'Environment Name': stage['environment_name'],
                'Status': stage['status'],
                'Duration': calculate_duration(execution_start_time, execution_end_time)
            }
            records.append(record)
    
    return records


def write_to_csv(records: List[Dict[str, str]], output_file: str):
    """
    Write records to CSV file.
    
    Args:
        records: List of record dictionaries
        output_file: Output CSV file path
    """
    if not records:
        print("No records to write.")
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
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    
    print(f"Successfully wrote {len(records)} records to {output_file}")


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
    
    Args:
        base_url: Base URL for the API
        auth_token: Bearer authentication token
        account_id: Account identifier
        org_id: Organization identifier
        project_id: Project identifier
        page_size: Number of records per page
        start_time: Start time in milliseconds
        end_time: End time in milliseconds
    
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
            print(f"  Total pages: {total_pages}, Total executions: {total_elements}")
        
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
    print(f"Page size: {args.page_size}")
    print(f"Delay between calls: random 0.5-1.0s")
    print()
    
    all_records = []
    
    # Determine which projects to process
    if args.project_id:
        # Single project mode
        projects = [args.project_id]
    else:
        # Fetch all projects
        projects = fetch_all_projects(
            base_url=base_url,
            auth_token=args.auth_token,
            account_id=args.account_id,
            org_id=args.org_id,
            api_key=args.api_key
        )
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
        
        all_records.extend(project_records)
        print(f"  Found {len(project_records)} production stage records for project {project_id}")
        print()
        
        # Add random delay between projects (except for the last one)
        if idx < len(projects):
            delay = random.uniform(0.5, 1.0)
            time.sleep(delay)
    
    print(f"Total production stage records collected: {len(all_records)}")
    
    # Write to CSV
    write_to_csv(all_records, args.output)


if __name__ == '__main__':
    main()
