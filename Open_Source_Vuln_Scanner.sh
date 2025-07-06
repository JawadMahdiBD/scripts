#!/bin/bash

# Define input file
input_file=$1

# Start httpx first
httpx -l $input_file >> httpx.txt

# Function to gather URLs using gau and process them
gather_urls() {
    echo -e "\nFinding URLS using gau"
    cat httpx.txt | gau --threads 5 >> gauurls.txt
    printf "urls have been fetched from gau"

    echo -e "\nremoving duplicates"
    cat gauurls.txt | sort -u > validurls.txt
    printf "Duplicate Remove done"

    echo -e "\nScraping parameters for fuzzing"
    cat validurls.txt | grep "=" > fuzzing.txt
    printf "Scrapping done"
}

# Function to run Katana
run_katana() {
    echo -e "\nKatana"
    cat httpx.txt | katana -nc -silent -d 5 -jc -ef "ttf,woff,svg,jpeg,jpg,png,ico,gif,css,js,woff2" -f qurl -no-sandbox >> fuzzing.txt
    cat fuzzing.txt >> maro.txt
    cat maro.txt | uro > fuzzing.txt
    sort -u fuzzing.txt -o fuzzing.txt
    echo -e "Gathering active endpoints"
    cat fuzzing.txt > gf.txt
}

# Function to find vulnerable endpoints
find_vulnerable_endpoints() {
    echo -e "Find Vulnerable Endpoints via gf"
    cat gf.txt | gf ssrf >> livevulnerableendpoints.txt
    cat gf.txt | gf redirect >> livevulnerableendpoints.txt
    cat gf.txt | gf rce >> livevulnerableendpoints.txt
    cat gf.txt | gf idor >> livevulnerableendpoints.txt
    cat gf.txt | gf sqli >> livevulnerableendpoints.txt
    cat gf.txt | gf lfi >> livevulnerableendpoints.txt
    cat gf.txt | gf ssti >> livevulnerableendpoints.txt
    cat gf.txt | gf debug_logic >> livevulnerableendpoints.txt
    cat gf.txt | gf xss >> livevulnerableendpoints.txt
    cat gf.txt | gf img-traversal >> livevulnerableendpoints.txt
    cat livevulnerableendpoints.txt | uro >> parameters.txt
}

# Function to extract file extensions and keywords
extract_data() {
    extensions=(".js" ".json" ".sql" ".zip" ".txt" ".php" ".aspx" ".env")
    > ext.txt
    for ext in "${extensions[@]}"; do
        echo "Extracting lines containing extension: $ext"
        grep -i "$ext" validurls.txt >> ext.txt
        echo "Lines containing extension saved to ext.txt"
    done

    keywords=("redirect=" "redir=" "uri=" ".zip" ".sql" "uuid=" "id=" "refer=" "token=" "verification" "source=" "example=" "sample=" "test=" "users" "password" "jwt" "code" "verification_code" "=false" "=true" "private" "username" "debug" "file=" "path=" "target=" "tar.gz" ".pdf" "return_to=" "apikey" ".js")
    mkdir -p databug
    for keyword in "${keywords[@]}"; do
        echo "Extracting lines containing keyword: $keyword"
        grep -i "$keyword" validurls.txt > "databug/$keyword.txt"
        echo "Lines containing keyword saved to databug/$keyword.txt"
    done
}

# Function to run Naabu
run_naabu() {
    echo -e "Naabu Scanning"
    naabu -list $input_file -p - -exclude-ports 80,443,8443 -ec -c 50 -rate 1500 -retries 1 > topnaabuports.txt
    cat topnaabuports.txt | httpx | nuclei -s critical,high,medium -mhe 3 >> nuclei_all_results.txt
    printf "Naabu Scanning done"
}

# Function to run Masscan
run_masscan() {
    echo -e "\nMasscan scanning"
    dnsx -resp-only -silent -l $input_file > hosts.txt
    masscan -iL hosts.txt -p 1-65535 --max-rate 10000 -oJ results.json
    cat results.json | sed -e '/^\[/d' -e '/^\]/d' -e 's/,$//' | jq -r '[.ip, .ports[0].port] | @tsv' | sed 's/\t/:/' | sort -u | tee -a masscan.txt | httpx -silent | nuclei -s critical,high,medium -mhe 3 >> nuclei_all_results.txt
    printf "Masscan completed"
}

# Function to run Uncover
run_uncover() {
    echo "[+] Uncover [+]"
    cat $input_file | uncover -e shodan -l 950 >> nonhttpxshodan.txt
    cat nonhttpxshodan.txt | httpx | nuclei -s critical,high,medium -mhe 3 >> nuclei_all_results.txt
}

# Function to run Nuclei on ext.txt
run_nuclei_ext() {
    echo -e "Running Nuclei on ext.txt..."
    nuclei -l ext.txt -t /root/nuclei-templates/http/exposures/ -s critical,high,medium -mhe 3 >> nuclei_all_results.txt
    echo -e "Nuclei scan completed and results saved in ExposeX"
}

# Function to perform full Nuclei scanning
run_nuclei_full() {
    echo -e "\nNuclei full scanning"
    nuclei -l httpx.txt -s critical,high -mhe 3 >> nuclei_all_results.txt
    printf "Full scanning completed"
}

# Function to check vulnerabilities with Nuclei
run_nuclei_vuln_check() {
    echo -e "\nNuclei Vuln checking against URLS"
    nuclei -l parameters.txt -c 60 -dast -mhe 3 >> nuclei_all_results.txt
    printf "Nuclei Vuln checking against URLS Completed"
}

# Function to gather JS endpoints using Katana
gather_js_endpoints() {
    echo -e "\nJsendpoints using Katana"
    cat httpx.txt | katana -d 5 -fx -jc -jsl -kf all -retry 2 -c 10 -p 10 -rl 150 -hl -do -ef "ttf,woff,svg,jpeg,jpg,png,ico,gif,css" -silent --no-sandbox  | grep -v -e "=" >> final-endpoint.txt
    printf "Katana done"
}

# Function to scan valid URLs and paths
scan_valid_urls() {
    echo "[+] Scan path results [+]"
    cat final-endpoint.txt | grep -i -v -E ".css|.gif|.woff|.woff2|.eot|.ttf|.tiff|.tif" >> validurls.txt
    sort -u validurls.txt -o validurls.txt
    cat validurls.txt | grep -v -e "=" | uro | tee -a onlypath.txt | httpx -t 50 | nuclei -s critical,high -mhe 3 >> nuclei_all_results.txt
    printf "Scan all results completed"
}

# Main execution
# Running the first portion of tasks sequentially
gather_urls
run_katana
find_vulnerable_endpoints
extract_data

# Running Naabu, Masscan, and Uncover concurrently
run_naabu &
run_masscan &
run_uncover &
wait

# Running Nuclei tasks concurrently
run_nuclei_ext &
run_nuclei_full &
run_nuclei_vuln_check &
wait

# Final portion
gather_js_endpoints
scan_valid_urls

# Cleanup
rm "gauurls.txt" "final-endpoint.txt" "fuzzing.txt" "maro.txt" "gf.txt" "livevulnerableendpoints.txt" "results.json"
