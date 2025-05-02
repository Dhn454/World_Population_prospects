import requests
import matplotlib.pyplot as plt 
import argparse
import gzip
import shutil 
import logging
from typing import List, Union 
from flask import Flask, request, jsonify, send_file 
from datetime import datetime
import redis 
import zipfile
from io import BytesIO
import json 
import re 
import os
import pandas as pd 
from collections import defaultdict 
from jobs import add_job, get_job_by_id, get_all_jobs, get_results, string_to_bool 

_redis_host = os.environ.get("REDIS_HOST") # AI used to understand environment function 
_redis_port = 6379
data_link = "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_Demographic_Indicators_Medium.csv.gz" 
local_data="cache/WPP2024_Demographic_Indicators_Medium.csv.gz" 

# Redis Database 
rd=redis.Redis(host=_redis_host, port=_redis_port, db=0) 
jdb = redis.Redis(host=_redis_host, port=_redis_port, db=2) 
resdb = redis.Redis(host=_redis_host, port=_redis_port, db=3) 

# Starting Flask App 
app = Flask(__name__) 

# Setting Log Level 
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level, logging.INFO)
logging.basicConfig(level=numeric_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logging.info("Logging level set to %s", log_level) 

def download_and_extract_gz():
    gz_path = "data.csv.gz"
    csv_path = "data.csv"

    if os.path.exists(local_data):
        logging.info(f"Using cached .gz file from: {local_data}")
        shutil.copyfile(local_data, gz_path)
    else:
        try:
            logging.info(f"Downloading data from: {data_link}")
            response = requests.get(data_link, stream=True)
            response.raise_for_status()  # Raise error for bad responses
            with open(gz_path, 'wb') as f_out:
                shutil.copyfileobj(response.raw, f_out)
            logging.info("Download successful.")
        except Exception as e:
            logging.error(f"Failed to download data: {e}")
            raise RuntimeError("No remote or local data available.")

    # Decompress .gz to .csv
    try:
        with gzip.open(gz_path, 'rb') as f_in:
            with open(csv_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        logging.info(f"Decompressed .gz to .csv at: {csv_path}")
    finally:
        if os.path.exists(gz_path):
            os.remove(gz_path)
            logging.info(f"Removed .gz file: {gz_path}")

    return csv_path

def decode_data(): # AI helped read csv file 
    path = download_and_extract_gz()
    try:
        df = pd.read_csv(path, low_memory=False)
        logging.info(f"Loaded CSV with {len(df)} rows")
    finally:
        if os.path.exists(path):
            os.remove(path)
            logging.info(f"Removed temporary CSV: {path}") 
    
    # Replace all NaNs with empty strings
    df.fillna("", inplace=True)
    df = df.astype(str) # Panda DataFrame structure 

    # Convert to list of dictionaries
    data = df.to_dict(orient='records') 
    
    # Replace spaces with underscores in all string values - AI used 
    for row in data:
        for key in row:
            if isinstance(row[key], str):
                # row[key] = row[key].replace(" ", "_") 
                row[key] = re.sub(r"[,\s]+", "_", row[key])

    grouped_by_year = defaultdict(list)

    for row in data:
        year = row.get("Time")  # assumes 'Time' is the column name for year
        if year:
            grouped_by_year[year].append(row) 

    return dict(grouped_by_year)  # convert defaultdict to normal dict if 

def fetch_latest_data(): 
    """
    This function fetches the latest HGNC data and updates 
    only if new data is available. Writes the most up to date data 
    to a redis database. 

    Args: 
        NONE 

    Returns: 
        NONE 
    """ 

    current_year = datetime.now().year 
    year_keys = [int(k.decode()) for k in rd.keys() if k.decode().isdigit()]
    if not year_keys or max(year_keys) < current_year-2: # most up to date was 2023 and we were in 2025 when writing program 
        logging.debug('Data was outdated, initializing update.') 
        data = decode_data() 
        # write data to database inside if statement
        rd.set('Last-Modified',current_year) # sets the last-modified value for reference 
        # for loop to write each dictionary to database for easier lookup 
        for year, entries in data.items(): # AI helped to correctly set data into redis 
            rd.set(year, json.dumps(entries))
        logging.info('Data has been updated.') 
    else: 
        logging.debug('Data was the same.') 

@app.route('/data', methods=['GET','POST','DELETE'])
def process_data() -> Union[list, str]: # used AI for Union type annotation option 
    """
    This route uses the GET method to retrieve the entire data set from 
    the Redis database. It also uses the POST method to write the entire 
    data set to the Redis database. It finally uses the DELETE method 
    to delete the entire data set from the Redis database. 

    Args: 
        NONE

    Returns: 
        data (list): Returns the list of dictionaries pertaining to 
                     the HGNC data when using the GET method. 
        OR 
        result (string): Returns update on what was done to the 
                         Redis database when using the POST and 
                         DELETE method. 
    """ 
    if request.method == 'GET':
        keys = [key.decode('utf-8') for key in rd.keys() if key.decode('utf-8') != "Last-Modified"] # check for last modified entry and dont include 
        data = [] 
        for item in keys:
            data.append(json.loads(rd.get(item).decode('utf-8'))) 
        return data 
    elif request.method == 'POST':
        logging.info("POST /data route hit — starting fetch")
        fetch_latest_data() 
        logging.debug('Loaded the world population data to a Redis database') 
        return 'Loaded the world population data to a Redis database\n' 
    elif request.method == 'DELETE':
        for item in rd.keys(): 
            rd.delete(item) 
        logging.debug('Deleted all data from Redis database')
        return 'Deleted all data from Redis database\n' 
    return {"error": f"Method Not Allowed."}, 405 

@app.route('/years', methods=['GET']) # make a case where epoch is nonexistent
def get_all_years() -> List[str]: 
    """
    This route uses the GET method to retrieve all of the hgnc_id fields 
    from the Redis database. 

    Args: 
        NONE

    Returns: 
        keys (list): Returns a list with all of the hgnc_id fields. 
    """
    # fetch_latest_data() # needs to fetch data to make sure database is not empty 
    try: 
        keys = [key.decode('utf-8') for key in rd.keys() if key.decode('utf-8') != "Last-Modified"] # AI used to check for last modified entry 
        if not keys: 
            logging.warning("GET /years returned an empty key list")
        keys.sort()
        return keys 
    except Exception as e:
        logging.error(f"Error fetching genes: {e}")
        return {"error": "Internal Server Error"}, 500

@app.route('/years/<years>/regions', methods=['GET']) 
def get_year(years:str, region_names=None) -> dict: 
    """
    This route uses the GET method to retrieve a certain hgnc_id field 
    and the dictionary with all of its key:value pairs. 

    Args: 
        hgnc_id (string): A string specifying the key of the certain 
                          hgnc_id you want to extract from the Redis
                          database. 

    Returns: 
        response (dict): Returns a dictionary with all of the key:value
                         pairs of the specified hgnc_id field. 
    """

    try:
        # Try to get region names from Flask request if available
        if region_names is None:
            region_names = request.args.get("names", "")
    except Exception as e:
        # We're not in a Flask request context
        if region_names is None:
            region_names = ""

    regions = region_names.split(",") if region_names else []

    try:
        if '-' in years:
            start_year, end_year = years.split('-')
        else:
            start_year = end_year = years  # Treat single year as both start and end
    except ValueError: 
        return {"error": "Invalid era format. Use YYYY-YYYY."}, 404
    
    if int(start_year) > int(end_year): 
        start_year, end_year = end_year, start_year

    data = []
    missing_years = []

    try: 
        if not regions: 
            for i in range(int(start_year),int(end_year)+1):
                # data.append(json.loads(rd.get(str(i))))
                raw = rd.get(str(i))
                if raw is None:
                    missing_years.append(str(i)) 
                    logging.warning(f"No data found for year: {i}") 
                    continue 
                year_data = json.loads(raw)
            if missing_years: 
                return {"data": year_data, "missing_years": missing_years} 
            return year_data 
        if regions:
            found_regions = set()
            for i in range(int(start_year),int(end_year)+1):
                raw = rd.get(str(i))
                if raw is None:
                    missing_years.append(str(i))
                    logging.warning(f"No data found for year: {i}")
                    continue 
                year_data = json.loads(raw)
                logging.info(f'gathered year data')
                logging.info(f'data is of type {type(year_data)}') 
                matches = [d for d in year_data if d.get("Location") in regions]
                found_regions.update(d.get("Location") for d in matches)
                data.extend(matches)
            missing_regions = set(regions) - found_regions
            if missing_regions and missing_years:
                logging.warning(f"Missing regions in data: {', '.join(missing_regions)}")
                return {"data": data, "missing_regions": list(missing_regions), "missing_years": missing_years} 
            if missing_regions: 
                return {"data": data, "missing_regions": list(missing_regions)} 
            if missing_years: 
                return {"data": data, "missing_years": missing_years} 
            return data 

    except TypeError: 
        logging.error(f"years '{years}' not found") 
        return {"error": f"years '{years}' not found"}, 404 

@app.route('/regions', methods=['GET']) 
def get_regions() -> dict: 
    """
    This route uses the GET method to retrieve a certain hgnc_id field 
    and the dictionary with all of its key:value pairs. 

    Args: 
        hgnc_id (string): A string specifying the key of the certain 
                          hgnc_id you want to extract from the Redis
                          database. 

    Returns: 
        response (dict): Returns a dictionary with all of the key:value
                         pairs of the specified hgnc_id field. 
    """
    try: 
        keys = [key.decode('utf-8') for key in rd.keys() if key.decode('utf-8') != "Last-Modified"] # AI used to check for last modified entry 
        if not keys: 
            logging.warning("GET /years returned an empty key list")
        locations_set = set() # sets update method avoids duplicates 
        for item in keys:
            locations_set.update(loc["Location"] for loc in json.loads(rd.get(item).decode('utf-8')))
        locations = list(locations_set)
        return locations 
    except TypeError as e: 
        logging.error(f"Raised exception '{e}'") 
        return {"error": f"Raised exception '{e}'"}, 404 
    
@app.route('/regions/<region>', methods=['GET']) 
def get_region(region:str) -> List[dict]: 
    """
    This route uses the GET method to retrieve a certain hgnc_id field 
    and the dictionary with all of its key:value pairs. 

    Args: 
        hgnc_id (string): A string specifying the key of the certain 
                          hgnc_id you want to extract from the Redis
                          database. 

    Returns: 
        response (dict): Returns a dictionary with all of the key:value
                         pairs of the specified hgnc_id field. 
    """
    try: 
        keys = [key.decode('utf-8') for key in rd.keys() if key.decode('utf-8') != "Last-Modified"] # AI used to check for last modified entry 
        if not keys: 
            logging.warning("GET /years returned an empty key list")
            return {"error": f"No data found for '{region}' region. Database was empty! "}, 404
        region_data = [] # list of dictionaries 
        for year in keys: # iterating through all years, each year has a list of dictionaries with different regions 
            item = json.loads(rd.get(year).decode('utf-8')) # get list of dictionaries
            region_data.extend([data_dict for data_dict in item if data_dict["Location"] == region]) # extend used to avoid TypeError 

        if not region_data:
            return {"error": f"No entries found for region '{region}'."}, 404
        
        return region_data 
    except Exception as e: 
        logging.error(f"Raised exception '{e}'") 
        return {"error": f"Raised exception '{e}'"}, 404 

@app.route('/regions/<region>/<eras>', methods=['GET']) 
def get_region_eras(eras:str, region:str) -> List[dict]: 
    """
    This route uses the GET method to retrieve a certain hgnc_id field 
    and the dictionary with all of its key:value pairs. 

    Args: 
        hgnc_id (string): A string specifying the key of the certain 
                          hgnc_id you want to extract from the Redis
                          database. 

    Returns: 
        response (dict): Returns a dictionary with all of the key:value
                         pairs of the specified hgnc_id field. 
    """    
    try:
        if '-' in eras:
            start_year, end_year = eras.split("-")
        else:
            start_year = end_year = eras
    except ValueError:
        return {"error": "Invalid era format. Use YYYY-YYYY."}, 404

    if int(start_year) > int(end_year):
        start_year, end_year = end_year, start_year

    try:
        keys = [key.decode('utf-8') for key in rd.keys()
                if key.decode('utf-8') != "Last-Modified"]

        if not keys:
            logging.warning("GET /region_eras returned an empty key list.")
            return {
                "error": f"No data found for '{region}' region. Database was empty!"
            }, 404

        region_data = []
        missing_years = []

        for year in range(int(start_year), int(end_year) + 1):
            str_year = str(year)
            if str_year not in keys:
                missing_years.append(str_year)
                logging.warning(f"No data found for year: {str_year}")
                continue

            raw = rd.get(str_year)
            if raw is None:
                missing_years.append(str_year)
                logging.warning(f"No data found for year: {str_year}")
                continue

            year_data = json.loads(raw)
            matches = [d for d in year_data if d.get("Location") == region]
            region_data.extend(matches)

        if not region_data and missing_years:
            return {
                "error": f"No data entries found for region '{region}'.",
                "missing_years": missing_years
            }, 404

        if not region_data:
            return {
                "error": f"No entries found for region '{region}' in any year from {start_year} to {end_year}."
            }, 404

        response = {"data": region_data}
        if missing_years:
            response["missing_years"] = missing_years

        return response, 206 if missing_years else 200

    except Exception as e:
        logging.error(f"Raised exception '{e}'")
        return {"error": f"Raised exception '{e}'"}, 500

@app.route('/help', methods=['GET']) 
def get_help(): 
    return """
submit a job:
curl localhost:5000/jobs -X POST -d '{"start": "1950", "end": "1975", "plot_type": "line"}' -H "Content-Type: application/json"

submit a job with specified regions:
curl localhost:5000/jobs -X POST -d '{"start": "1950", "end": "2023", "plot_type": "bar", "Location": "Asia,Europe,Mexico"}' -H "Content-Type: application/json"

submit a job with specified data for x and y:
curl localhost:5000/jobs -X POST -d '{"start": "1950", "end": "1975", "plot_type": "scatter", "Location": "Asia", "query1": "NRR", "query2": "TFR"}' -H "Content-Type: application/json"

submit a job with specified animation:
curl localhost:5000/jobs -X POST -d '{"start": "1950", "end": "1975", "plot_type": "line", "query1": "NRR", "query2": "TFR", "animation": "True"}' -H "Content-Type: application/json"
"""


@app.route('/jobs', methods=['GET', 'POST', 'DELETE']) 
def get_jobs() -> Union[list, str]: 
    if request.method == 'POST': 
        try: 
            data = request.get_json()
            logging.debug("POST data received: %s", data)

            if not data.get("start") or not data.get("end"):
                logging.error("Missing start or end date.")
                return jsonify({"error": "Please provide both start and end dates."}), 400  
            if not data.get("plot_type"):
                logging.error("Missing plot_type.")
                return jsonify({"error": "Please provide a plot type option."}), 400 

            job_info = add_job(data)
            logging.info(f"Job created: {job_info}")
            return jsonify({"message": "Job created", "job": job_info}), 201
        except Exception as e: 
            logging.error(f"Error creating job: {e}")
            return jsonify({"error": "Internal Server Error"}), 500 

    elif request.method == 'GET': 
        try: 
            jobs = get_all_jobs()
            logging.debug("Retrieved all job IDs")
            return jsonify(jobs), 200
        except Exception as e:
            logging.error(f"Error retrieving jobs: {e}")
            return jsonify({"error": "Internal Server Error"}), 500
    
    elif request.method == 'DELETE':
        for item in jdb.keys(): 
            jdb.delete(item) 
        logging.debug('Deleted all jobs from Redis database')
        return 'Deleted all jobs from Redis database\n' 

    logging.warning(f"Method {request.method} not allowed on /jobs")
    return jsonify({"error": f"Method {request.method} Not Allowed."}), 405


@app.route('/jobs/<jobid>', methods=['GET']) 
def get_job(jobid: str) -> Union[dict,tuple]: 
    """
    This route uses the GET method to retrieve a job's information
    from the Redis database, including its job ID, status, start date,
    and end date.

    Args:
        jobid (str): A string representing the unique job ID.

    Returns:
        dict: A dictionary containing job information if the job exists.
        OR
        tuple: A tuple with an error dictionary and HTTP status code 500
               if an exception occurs.
    """
    try: 
        job = get_job_by_id(jobid)
        logging.debug(f"Job fetched: {job}")
        return job
    except Exception as e: 
        logging.error(f"Error fetching job {jobid}: {e}")
        return {"error": "Internal Server Error"}, 500      

@app.route('/results', defaults={'jobid': None}, methods=['GET', 'DELETE']) # able to delete all results from database
@app.route('/results/<jobid>', methods=['GET', 'DELETE']) 
def results(jobid: str) -> Union[dict,tuple]: 
    """
    This route uses the GET method to retrieve the result of a given job ID
    from the Redis database. 

    Args:
        jobid (str): A string representing the unique job ID.

    Returns:
        dict: A dictionary containing the results for the specified job.
        OR
        tuple: A tuple with an error dictionary and HTTP status code 500
               if an exception occurs.
    """
    if request.method == 'GET':
        try:
            data = get_results(jobid)
            logging.debug(f"Results fetched: {data}")
            return data  
        except Exception as e:
            logging.error(f"Error retrieving results for job {jobid}: {e}")
            return {"error": "Internal Server Error"}, 500 
    elif request.method == "DELETE":
        for item in resdb.keys(): 
            resdb.delete(item) 
        logging.debug('Deleted all results from Redis database')
        return 'Deleted all results from Redis database\n' 

    logging.warning(f"Method {request.method} not allowed on /jobs")
    return jsonify({"error": f"Method {request.method} Not Allowed."}), 405

@app.route('/download/<jobid>', methods=['GET'])
def download(jobid):
    job_dict = get_job_by_id(jobid)
    flag = string_to_bool(job_dict.get("animate"))
    plot_type = job_dict.get("plot_type")
    logging.debug(f'job_dict is {job_dict}')
    logging.debug(f'job_dict animate option is {job_dict.get("animate")}')
    logging.debug(f'flag is {flag}')

    if flag: 
        logging.debug(f'animation was true')
        path = f'/app/{jobid}.gif'
        with open(path, 'wb') as f:
            f.write(resdb.hget(jobid, 'gif'))   # 'resdb' is a client to the results db
        return send_file(path, mimetype='image/gif', as_attachment=True)
    elif plot_type in ["bar", "scatter"] and not flag:
        logging.debug(f'Plot type was bar and animation was false')
        mem_zip = BytesIO()
        logging.debug(f'mem_zip is of type: {type(mem_zip)}')

        # Creating a ZipFile in memory
        with zipfile.ZipFile(mem_zip, 'w') as zipf:
            logging.debug(f'Preparing zip file')
            logging.debug(f'Keys for the {jobid} jobid are {resdb.hkeys(jobid)}')
            logging.debug(f'Keys in results database are {resdb.keys()}')

            # Loop through Redis keys to find image data
            for key in resdb.hkeys(jobid):
                logging.debug(f'Found key: {key}')
                if key.startswith(b'image_'):  # e.g., image_2020
                    logging.debug(f"Key '{key}' starts with image_")
                    year = key.decode().split('_')[1]
                    data = resdb.hget(jobid, key)  # Get the binary data from Redis
                    # Writing the image data to the zip file
                    zipf.writestr(f"{jobid}_{year}.png", data)
                    logging.debug(f"Added {jobid}_{year}.png to zip")

        # Seek to the beginning of the in-memory ZIP file before sending it
        mem_zip.seek(0)

        # Returning the ZIP file as a downloadable response
        return send_file(mem_zip, mimetype='application/zip', as_attachment=True, download_name=f'{jobid}_images.zip')

    else: 
        path = f'/app/{jobid}.png'
        with open(path, 'wb') as f:
            f.write(resdb.hget(jobid, 'image'))   # 'resdb' is a client to the results db
        return send_file(path, mimetype='image/png', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
