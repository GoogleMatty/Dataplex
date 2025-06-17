import argparse
import json
import subprocess
import os
import re

def create_metadata_resource(project_id, location, api_resource_type, resource_id, definition_file_path):
    """
    Creates a Dataplex metadata resource (specifically an Aspect Type in this version)
    using the provided definition file.

    Args:
        project_id: The Google Cloud project ID.
        location: The Dataplex location (e.g., "global").
        api_resource_type: The type of metadata resource being created, fixed as "aspectTypes" in this script.
        resource_id: The ID for the specific resource (e.g., aspect_type_id), derived from the filename.
        definition_file_path: Full path to the JSON file containing the resource definition.
    """

    print(f"Processing '{definition_file_path}' for {api_resource_type} ID: '{resource_id}'...")

    try:
        with open(definition_file_path, 'r') as f:
            definition = f.read()
    except FileNotFoundError:
        print(f"Error: Definition file not found: {definition_file_path}")
        return
    except Exception as e:
        print(f"Error reading file {definition_file_path}: {e}")
        return

    # Construct the API URL. For aspectTypes, the ID parameter is consistently "aspect_type_id".
    id_param_name = "aspect_type_id"
    api_url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{location}/{api_resource_type}?{id_param_name}={resource_id}"

    # Obtain a Google Cloud access token using gcloud CLI.
    # IMPORTANT: Ensure gcloud CLI is installed and you are authenticated
    # (e.g., by running `gcloud auth application-default login` or `gcloud auth login`).
    try:
        access_token_command = ['gcloud', 'auth', 'print-access-token']
        access_token_process = subprocess.run(access_token_command, capture_output=True, text=True, check=True)
        access_token = access_token_process.stdout.strip()
        if not access_token:
            raise ValueError("Empty access token received from gcloud. Please ensure gcloud CLI is configured correctly.")
    except subprocess.CalledProcessError as e:
        print("Error: Could not obtain Google Cloud access token.")
        print(f"Please ensure gcloud CLI is installed and authenticated (e.g., `gcloud auth application-default login`).")
        print(f"Stderr: {e.stderr}")
        return
    except ValueError as e:
        print(f"Error obtaining access token: {e}")
        return

    # Construct the curl command to make the API call.
    command = [
        'curl',
        '--silent', # Suppress progress meter
        '--fail',   # Fail silently on server errors (HTTP status >= 400)
        '--location', api_url,
        '--header', 'Content-Type: application/json',
        '--header', f'Authorization: Bearer {access_token}',
        '--data', definition
    ]

    # Execute the curl command.
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f"Successfully created {api_resource_type} with ID: {resource_id}")
        print(result.stdout) # Print the API response on success
    except subprocess.CalledProcessError as e:
        print(f"\n--- ERROR Creating {api_resource_type} with ID: {resource_id} ---")
        print(f"  API URL: {api_url}")
        print(f"  Definition File: {definition_file_path}")
        print(f"  Return Code: {e.returncode}")
        print(f"  Stdout: {e.stdout}") # API error message often in stdout
        print(f"  Stderr: {e.stderr}")
        print("--------------------------------------------------\n")
    except Exception as e:
        print(f"An unexpected error occurred while calling curl for {resource_id}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Creates Dataplex Aspect Types from JSON definition files found in a specified folder."
    )
    parser.add_argument(
        "project_id",
        help="The Google Cloud project ID where the Aspect Types will be created."
    )
    parser.add_argument(
        "location",
        help="The Dataplex location (e.g., 'global', 'us-central1')."
    )
    parser.add_argument(
        "definitions_dir", # This is the 3rd required positional argument
        help="The path to the folder containing the JSON definition files for the Aspect Types. "
             "Each '.json' file is expected to contain the full API request body for one Aspect Type, "
             "and its filename (e.g., 'my-aspect.json') will determine the Aspect Type ID ('my-aspect')."
    )

    args = parser.parse_args()

    # The API resource type is hardcoded as 'aspectTypes' for this script version,
    # as per your specific use case.
    api_resource_type = "aspectTypes"

    # Validate that the provided definitions directory exists.
    if not os.path.isdir(args.definitions_dir):
        print(f"Error: Definitions directory not found: '{args.definitions_dir}'")
        return

    # Find all JSON files in the specified directory.
    json_files = [f for f in os.listdir(args.definitions_dir) if f.endswith('.json')]

    if not json_files:
        print(f"No .json files found in '{args.definitions_dir}'. Please ensure your definition files are present and end with '.json'. Exiting.")
        return

    print(f"Found {len(json_files)} JSON definition file(s) in '{args.definitions_dir}'.")

    # Process each JSON file to create an Aspect Type.
    for filename in sorted(json_files): # Sort for consistent processing order
        # Derive the resource_id (Aspect Type ID) from the filename.
        # Example: "my_data_contract.json" -> "my-data-contract"
        base_name = os.path.splitext(filename)[0] # Remove .json extension
        resource_id = re.sub(r'[^a-z0-9]+', '-', base_name.lower()) # Replace non-alphanumeric with hyphen
        resource_id = resource_id.strip('-') # Remove leading/trailing hyphens

        if not resource_id:
            print(f"Warning: Could not derive a valid resource ID from filename '{filename}'. Skipping this file.")
            continue

        definition_file_path = os.path.join(args.definitions_dir, filename)

        # Call the function to create the Dataplex metadata resource.
        create_metadata_resource(
            args.project_id,
            args.location,
            api_resource_type, # This is "aspectTypes"
            resource_id,
            definition_file_path
        )


if __name__ == "__main__":
    main()
