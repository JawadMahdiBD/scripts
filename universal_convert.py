import os
import re
import json
from urllib.parse import urlparse, urlunparse
from tkinter import Tk, filedialog, messagebox
from colorama import Fore, init
from datetime import datetime
import glob
from collections import defaultdict

# Initialize colorama
init(autoreset=True)

# ========== CONFIG ==========
output_dir = "output_json_chunks"
max_chunk_size = 800 * 1024 * 1024  # 800 MB
year = 2025
# ============================

def extract_passwords(input_file):
    patterns = [
        r"URL:\s*(.*?)\nUsername:\s*(.*?)\nPassword:\s*(.*?)\n",
        r"URL:\s*(.*?)\nUSER:\s*(.*?)\nPASS:\s*(.*?)\n",
        r"url:\s*(.*?)\nlogin:\s*(.*?)\npassword:\s*(.*?)\n",
        r"URL:\s*(.*?)\nLogin:\s*(.*?)\nPassword:\s*(.*?)\n",
        r"Host:\s*(.*?)\nUsername:\s*(.*?)\nPassword:\s*(.*?)\n"
    ]
    
    all_matches = []

    try:
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as infile:
            content = infile.read()
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    url, username, password = match
                    # Basic cleaning while preserving special chars
                    url = url.strip().replace('"', '').replace("'", "")
                    username = username.strip().replace('"', '').replace("'", "")
                    password = password.strip().replace('"', '').replace("'", "")
                    if url and username and password:
                        all_matches.append(f"{url}:{username}:{password}")

    except Exception as e:
        print(f"Error processing {input_file}: {str(e)}")
    
    return all_matches

def extract_date_from_folder(folder_path):
    """Extract date from various system information files with multiple format support"""
    possible_files = [
        "System.txt", "system.txt", "SYSTEM.TXT",
        "UserInformation.txt", "userinformation.txt", "USERINFORMATION.TXT",
        "Userinformation", "userinformation", "USERINFORMATION",
        "information.txt", "Information.txt", "INFORMATION.TXT",
        "System", "UserInfo", "info.txt"
    ]
    
    for filename in possible_files:
        file_path = os.path.join(folder_path, filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Comprehensive date pattern matching
                    date_patterns = [
                        # DD/MM/YYYY or D/M/YYYY with time
                        r"(?:Local|LOCAL) (?:Time|TIME|Date|DATE)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})",
                        # MM/DD/YYYY format (American style)
                        r"(?:Local|LOCAL) (?:Time|TIME|Date|DATE)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})",
                        # YYYY-MM-DD (ISO format)
                        r"(?:Local|LOCAL) (?:Time|TIME|Date|DATE)[:\s]*(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})",
                        # Free-form dates
                        r"(?:Date|DATE|Time|TIME)[:\s]*(\d{1,2}[\/\-\. ]\w{3,9}[\/\-\. ]\d{4})",
                        # Log date format (04 June 25)
                        r"Log [Dd]ate:\s*(\d{1,2}\s+\w{3,9}\s+\d{2,4})",
                        # New pattern for "Time: 07.05.2025 17:13:49"
                        r"Time:\s*(\d{2}\.\d{2}\.\d{4})"
                    ]
                    
                    for pattern in date_patterns:
                        date_match = re.search(pattern, content, re.IGNORECASE)
                        if date_match:
                            date_str = date_match.group(1).strip()
                            
                            # Handle "Log date" format (04 June 25)
                            if re.match(r"\d{1,2}\s+\w+\s+\d{2,4}", date_str):
                                try:
                                    date_obj = datetime.strptime(date_str, "%d %B %y") if len(date_str.split()[-1]) == 2 else \
                                              datetime.strptime(date_str, "%d %B %Y")
                                    return date_obj.strftime("%Y-%m-%d")
                                except:
                                    try:
                                        date_obj = datetime.strptime(date_str, "%d %b %y") if len(date_str.split()[-1]) == 2 else \
                                                  datetime.strptime(date_str, "%d %b %Y")
                                        return date_obj.strftime("%Y-%m-%d")
                                    except:
                                        continue
                            
                            # Handle "Time:" format (07.05.2025)
                            if re.match(r"\d{2}\.\d{2}\.\d{4}", date_str):
                                day, month, year = date_str.split('.')
                                return f"{year}-{month}-{day}"
                            
                            # Handle all other formats
                            if '/' in date_str:
                                parts = date_str.split('/')
                            elif '.' in date_str:
                                parts = date_str.split('.')
                            elif '-' in date_str:
                                parts = date_str.split('-')
                            else:
                                parts = date_str.split()
                            
                            if len(parts) == 3:
                                if len(parts[2]) == 4:
                                    if parts[2].isdigit():
                                        day, month, year = parts
                                    else:
                                        day, month_name, year = parts
                                        month = datetime.strptime(month_name[:3], '%b').month
                                else:
                                    month, day, year = parts
                                
                                if isinstance(month, str) and not month.isdigit():
                                    try:
                                        month = datetime.strptime(month[:3], '%b').month
                                    except:
                                        month = datetime.now().month
                                
                                day = day.zfill(2)
                                month = str(month).zfill(2)
                                if len(year) == 2:
                                    year = f"20{year}"
                                
                                if (1 <= int(month) <= 12) and (1 <= int(day) <= 31):
                                    return f"{year}-{month}-{day}"
                        
            except Exception as e:
                print(f"Error reading {file_path}: {str(e)}")
    
    return None

def is_valid_url(url):
    """Check if the URL has a valid structure and doesn't contain an email"""
    try:
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False
        if not parsed.hostname or '.' not in parsed.hostname:
            return False
        if '@' in url:
            return False
        valid_tlds = ['.com', '.net', '.org', '.io', '.gov', '.edu', '.co', '.uk', '.de', '.fr']
        if not any(tld in parsed.hostname.lower() for tld in valid_tlds):
            return False
        return True
    except:
        return False

def parse_line(line, leak_date):
    try:
        line = line.strip()
        if not line or line.count(':') < 2:
            return None

        last_colon = line.rfind(':')
        if last_colon == -1:
            return None
        second_last_colon = line.rfind(':', 0, last_colon - 1)
        if second_last_colon == -1:
            return None
            
        url_part = line[:second_last_colon].strip()
        username = line[second_last_colon+1:last_colon].strip()
        password = line[last_colon+1:].strip()

        if '@' in url_part and '.' in url_part:
            return None

        email_providers = ['@gmail.com', '@yahoo.com', '@hotmail.com', '@outlook.com', '@protonmail.com']
        if any(provider in url_part.lower() for provider in email_providers):
            return None

        if not all([url_part, username, password]):
            return None

        if not url_part.startswith(('http://', 'https://')):
            url_part = 'http://' + url_part

        if not is_valid_url(url_part):
            return None

        parsed = urlparse(url_part)
        domain = parsed.hostname
        if not domain or '.' not in domain:
            return None

        email_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'protonmail.com']
        if domain.lower() in email_domains:
            return None

        url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        )).rstrip('/')

        if not all([domain, url, username, password]):
            return None

        return {
            "domain": domain.lower(),
            "url": url,
            "username": username,
            "password": password,
            "year": year,
            "leak_date": leak_date
        }
    except Exception:
        return None

def write_chunk(chunk_lines, index):
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"output_{index}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        for line in chunk_lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    print(f"✅ Saved: {filepath} ({len(chunk_lines)} entries)")

def is_valid_url_polish(url):
    url_pattern = re.compile(
        r'^(https?):\/\/'           # http:// or https://
        r'([\w\-\.]+)'              # domain
        r'(:\d+)?'                  # optional port
        r'(\/[\w\-\.\/\?\=\&\%\@\:]*)?$'  # optional path and query string
    )
    return bool(url_pattern.match(url))

def is_valid_username(username):
    if not isinstance(username, str):
        return False
    username = username.strip()
    username_pattern = re.compile(r'^[\w@\.\-]+$')
    return len(username) > 0 and username_pattern.match(username)

def is_valid_password(password):
    if not isinstance(password, str):
        return False
    password = password.strip()
    if len(password) < 5 or len(password) > 64:
        return False
    return all(c.isprintable() and c not in '\n\r' for c in password)

def polish_json_lines(file_path):
    polished_entries = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_number, line in enumerate(f, 1):
            line = line.strip().rstrip(',')
            if not line:
                continue
            try:
                entry = json.loads(line)
                url = entry.get('url')
                username = entry.get('username')
                password = entry.get('password')

                if not all([url, username, password]):
                    print(f"[Line {line_number}] Missing url, username or password.")
                    continue
                if not is_valid_url_polish(url):
                    print(f"[Line {line_number}] Invalid URL: {url}")
                    continue
                if not is_valid_username(username):
                    print(f"[Line {line_number}] Invalid username: {username}")
                    continue
                if not is_valid_password(password):
                    print(f"[Line {line_number}] Invalid password: {password}")
                    continue

                polished_entries.append(entry)
            except json.JSONDecodeError as e:
                print(f"[Line {line_number}] JSON parse error: {e}")

    return polished_entries

def super_deduplicate(target_file):
    # Phase 1: First remove internal duplicates from target file
    internal_unique = []
    internal_dupes = 0
    seen_in_target = set()
    
    with open(target_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line)
                key = (entry.get('url'), entry.get('username'), entry.get('password'))
                
                if key not in seen_in_target:
                    seen_in_target.add(key)
                    internal_unique.append(entry)
                else:
                    internal_dupes += 1
            except json.JSONDecodeError:
                continue
    
    print(f"\nRemoved {internal_dupes} internal duplicates from {target_file}")

    # Phase 2: Now check against other files
    cross_dupes = 0
    final_unique = []
    master_dupes = set()

    # Build master list of duplicates from other files
    other_files = [f for f in glob.glob('*.json') if f != target_file]
    for file in other_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        key = (entry.get('url'), entry.get('username'), entry.get('password'))
                        master_dupes.add(key)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"⚠️ Error reading {file}: {str(e)}")

    # Check internal unique entries against master duplicates
    for entry in internal_unique:
        key = (entry.get('url'), entry.get('username'), entry.get('password'))
        if key not in master_dupes:
            final_unique.append(entry)
        else:
            cross_dupes += 1

    # Save final results with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"final_output_{timestamp}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in final_unique:
            json.dump(entry, f)
            f.write('\n')

    # Results
    print("\n" + "="*50)
    print(f"🔍 Final Deduplication Results for {target_file}")
    print(f"Original entries: {internal_dupes + len(internal_unique)}")
    print(f"Internal duplicates removed: {internal_dupes}")
    print(f"Cross-file duplicates removed: {cross_dupes}")
    print(f"Final unique entries saved: {len(final_unique)}")
    print(f"Output file: {output_file}")
    print("="*50)
    
    return output_file

def process_initial_data():
    print(Fore.RED + "RatClouds Credential Processor")
    Tk().withdraw()
    root_folder = filedialog.askdirectory(title="Select folder containing credential files")
    
    if not root_folder:
        print("No folder selected. Exiting.")
        return None
    
    password_files = ["All Passwords.txt", "passwords.txt", "Passwords.txt", "Credentials.txt"]
    all_credentials = []
    
    items = os.listdir(root_folder)
    for item in items:
        item_path = os.path.join(root_folder, item)
        
        if os.path.isdir(item_path):
            leak_date = extract_date_from_folder(item_path)
            if not leak_date:
                print(f"⚠️ No valid date found in system files in {item}, using current date")
                leak_date = datetime.now().strftime("%Y-%m-%d")
            
            for file_name in password_files:
                file_path = os.path.join(item_path, file_name)
                if os.path.exists(file_path):
                    credentials = extract_passwords(file_path)
                    all_credentials.extend((cred, leak_date) for cred in credentials)
        
        elif os.path.isfile(item_path) and item in password_files:
            leak_date = datetime.now().strftime("%Y-%m-%d")
            credentials = extract_passwords(item_path)
            all_credentials.extend((cred, leak_date) for cred in credentials)
    
    if not all_credentials:
        print("No credentials found.")
        return None
    
    chunk = []
    chunk_size = 0
    file_index = 1
    skipped_count = 0
    valid_count = 0
    
    for cred, leak_date in all_credentials:
        entry = parse_line(cred, leak_date)
        if entry:
            json_line = json.dumps(entry, ensure_ascii=False)
            line_size = len(json_line.encode('utf-8'))
            
            if chunk_size + line_size > max_chunk_size:
                write_chunk(chunk, file_index)
                file_index += 1
                chunk = []
                chunk_size = 0
                
            chunk.append(entry)
            chunk_size += line_size
            valid_count += 1
        else:
            skipped_count += 1
    
    if chunk:
        write_chunk(chunk, file_index)
    
    print(f"\n🎉 Processing complete. Output saved to: {os.path.abspath(output_dir)}")
    print(f"✅ Valid entries processed: {valid_count}")
    if skipped_count > 0:
        print(f"⚠️ Skipped {skipped_count} malformed entries")
    
    return os.path.abspath(output_dir)

def main():
    # Step 1: Process initial data
    output_path = process_initial_data()
    if not output_path:
        return
    
    # Ask if user wants to polish the data
    root = Tk()
    root.withdraw()
    polish = messagebox.askyesno("Processing Option", "Do you want to polish the data before output?")
    
    if polish:
        # Select the first output file to polish
        json_files = glob.glob(os.path.join(output_path, "*.json"))
        if not json_files:
            print("No JSON files found for polishing.")
            return
        
        # Polish the first file (you could modify this to process all files)
        polished_data = polish_json_lines(json_files[0])
        
        # Save polished data
        polished_path = os.path.join(output_path, "polished_output.json")
        with open(polished_path, 'w', encoding='utf-8') as out_file:
            for entry in polished_data:
                json_line = json.dumps(entry, ensure_ascii=False)
                out_file.write(json_line + '\n')
        
        print(f"Polished data saved to: {polished_path}")
        print(f"Total valid entries after polishing: {len(polished_data)}")
        
        # Update the path to the polished file for next step
        output_file = polished_path
    else:
        # Use the first output file as is
        json_files = glob.glob(os.path.join(output_path, "*.json"))
        if not json_files:
            print("No JSON files found.")
            return
        output_file = json_files[0]
    
    # Ask if user wants final output now or to deduplicate
    final_output = messagebox.askyesno("Output Option", "Do you want the final output now? (No will deduplicate)")
    
    if final_output:
        print(f"\nFinal output is available at: {output_file}")
    else:
        # Deduplicate the file
        print("\nStarting deduplication process...")
        final_output_file = super_deduplicate(output_file)
        print(f"\nFinal deduplicated output is available at: {final_output_file}")

if __name__ == "__main__":
    main()