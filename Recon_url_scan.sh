#!/bin/bash

# Function to ask user if they want to run httpx
ask_httpx() {
    read -p "Do you want to run httpx on the input file? (yes/no): " run_httpx
    case $run_httpx in
        [yY]|[yY][eE][sS])
            return 0
            ;;
        [nN]|[nN][oO])
            return 1
            ;;
        *)
            echo "Invalid input, please enter yes or no"
            ask_httpx
            ;;
    esac
}

# Define input file
input_file=$1

# Ask user if they want to run httpx
if ask_httpx; then
    echo "Running httpx on input file..."
    httpx -l $input_file >> httpx.txt
else
    echo "Skipping httpx, using existing httpx.txt if available..."
    if [ ! -f "httpx.txt" ]; then
        echo "Error: httpx.txt not found and httpx not run. Please provide httpx.txt or run with httpx option."
        exit 1
    fi
fi

# Function to gather URLs using gau and process them
gather_urls() {
    echo -e "\nFinding URLS using gau"
    cat $input_file | gau --threads 5 >> gauurls.txt
    printf "urls have been fetched from gau"

    echo -e "\nremoving duplicates"
    cat gauurls.txt | sort -u | uro > validurls.txt
    printf "Duplicate Remove done"

    echo -e "\nScraping parameters for fuzzing"
    cat validurls.txt | grep "=" > fuzzing.txt
    printf "Scrapping done"
}

# Function to run Katana
run_katana() {
    echo -e "\nKatana"
    cat httpx.txt | katana -d 5 -jc -jsl -kf all -fx -retry 2 -c 5 -p 5 -rl 50 -ef "ttf,woff,svg,jpeg,jpg,png,ico,gif,css" -f qurl -no-sandbox >> fuzzing.txt
    cat fuzzing.txt >> maro.txt
    cat maro.txt | uro > fuzzing.txt
    sort -u fuzzing.txt -o fuzzing.txt
    echo -e "Gathering active endpoints"
    cat fuzzing.txt > gf.txt
}

# Function to find vulnerable endpoints
find_vulnerable_endpoints() {
    echo -e "Find Vulnerable Endpoints via gf"
    cat gf.txt | httpx > httpx_param.txt
    cat httpx_param.txt | gf ssrf | uro >> ssrf.txt
    cat httpx_param.txt | gf redirect | uro >> redirect.txt
    cat httpx_param.txt | gf rce | uro >> rce.txt
    cat httpx_param.txt | gf idor | uro >> idor.txt
    cat httpx_param.txt | gf sqli | uro >> sqli.txt
    cat httpx_param.txt | gf lfi | uro >> lfi.txt
    cat httpx_param.txt | gf ssti | uro >> ssti.txt
    cat httpx_param.txt | gf debug_logic | uro >> debug_logic.txt
    cat httpx_param.txt | gf xss | uro >> xss.txt
    cat httpx_param.txt | gf img-traversal | uro >> img-traversal.txt
    cat httpx_param.txt | gf interestingEXT | uro >> interestingEXT.txt
    cat httpx_param.txt | gf interestingparams | uro >> interestingparams.txt
    cat httpx_param.txt | gf interestingsubs | uro >> interestingsubs.txt
    cat httpx_param.txt | gf jsvar | uro >> jsvar.txt
    
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

# Function to gather JS endpoints using Katana
gather_js_endpoints() {
    echo -e "\nJsendpoints using Katana"
    cat httpx.txt | katana -jc -d 5 -c 50 -ef css,woff,woff2,eot,ttf,tiff,tif -kf all -no-sandbox | grep -v -e "=" >> final-endpoint.txt
    printf "Katana done"
}

# Function to scan valid URLs and paths
scan_valid_urls() {
    echo "[+] Scan path results [+]"
    cat final-endpoint.txt | grep -i -v -E ".css|.gif|.woff|.woff2|.eot|.ttf|.tiff|.tif" >> validurls.txt
    sort -u validurls.txt -o validurls.txt
    cat validurls.txt | grep -v -e "=" | uro | tee -a onlypath.txt
    cat onlypath.txt | httpx -sc > only_path_httpx.txt
    printf "Scan all results completed"
}

# Main execution
# Running the first portion of tasks sequentially
gather_urls
run_katana
find_vulnerable_endpoints
extract_data

# Final portion running sequentially
gather_js_endpoints
scan_valid_urls

# Cleanup
rm "gauurls.txt" "final-endpoint.txt" "fuzzing.txt" "maro.txt" "gf.txt"
