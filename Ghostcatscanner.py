import requests
import json
import os

def check_subdomain(api_url, subdomain, page=1):
    try:
        response = requests.get(f"{api_url}{subdomain}&page={page}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error checking {subdomain}: {e}")
        return None

def main():
    api_base = "https://ghostcat.cloud/api/ghostcat/?access_token=&search="
    
    # Get input file
    filename = input("Enter the path to your subdomains file (e.g., subdomains.txt): ").strip()
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        return
    
    # Ask about JSON output
    save_json = input("Do you want to save results to JSON? (y/n): ").lower() == 'y'
    output_file = None
    if save_json:
        output_file = input("Enter output JSON filename (e.g., results.json): ").strip()
        if not output_file.endswith('.json'):
            output_file += '.json'
    
    results = {}
    
    # Read subdomains and process
    with open(filename, 'r') as f:
        subdomains = [line.strip() for line in f if line.strip()]
    
    print(f"\nStarting scan for {len(subdomains)} subdomains...\n")
    
    for i, subdomain in enumerate(subdomains, 1):
        print(f"[{i}/{len(subdomains)}] Checking: {subdomain}")
        all_entries = []
        page = 1
        has_more = True
        
        while has_more:
            data = check_subdomain(api_base, subdomain, page)
            
            if not data:
                if page == 1:
                    print("  Error: No valid response from API\n")
                break
                
            if not data.get('success', False):
                if page == 1:
                    error_msg = data.get('message', 'Unknown error')
                    print(f"  API Error: {error_msg}\n")
                break
                
            if 'data' not in data or 'results' not in data['data']:
                if page == 1:
                    print("  Unexpected API response format\n")
                break
                
            current_results = data['data']['results']
            if current_results:
                print(f"  Page {page}: Found {len(current_results)} entries")
                all_entries.extend(current_results)
                page += 1
                
                # Check if there are more pages (using presence of results as indicator)
                # Alternatively, if API provides a 'has_more' or 'total_pages' field, use that instead
                has_more = len(current_results) > 0
            else:
                if page == 1:
                    print("  No data found for this subdomain.\n")
                has_more = False
        
        if all_entries:
            print(f"  TOTAL FOUND: {len(all_entries)} entries!")
            for entry in all_entries:
                print(f"    Username: {entry['username']}")
                print(f"    Password: {entry['password']}")
                print(f"    Leak Date: {entry['leak_date']}\n")
            results[subdomain] = all_entries
        elif page == 1 and (not data or not data.get('success', False)):
            results[subdomain] = None
    
    # Save to JSON if requested
    if save_json and output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    main()
