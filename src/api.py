import requests
import matplotlib.pyplot as plt 
import argparse
import gzip
import shutil 
import logging
from typing import List, Union 
from flask import Flask, request 
from datetime import datetime
import redis 
import json 
import re 
import os
import pandas as pd 
from collections import defaultdict 
from jobs import add_job, get_job_by_id, get_all_jobs, get_results 

_redis_host = os.environ.get("REDIS_HOST") # AI used to understand environment function 
_redis_port = 6379
# data_link = "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_Demographic_Indicators_Medium.csv.gz" 
local_data="cache/WPP2024_Demographic_Indicators_Medium.csv.gz" 

# Redis Database 
rd=redis.Redis(host=_redis_host, port=_redis_port, db=0) 

# Starting Flask App 
app = Flask(__name__) 

# Setting Log Level 
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level, logging.INFO)
logging.basicConfig(level=numeric_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logging.info("Logging level set to %s", log_level) 

def download_and_extract_gz(): # AI helped extract gz file     
    gz_path = "data.csv.gz" 
    csv_path = "data.csv" 

    logging.debug(f"gathering data saved locally")
    if os.path.exists(local_data):
        logging.info(f"Using cached .gz file from: {local_data}")
        shutil.copyfile(local_data, gz_path)
    else:
        logging.error(f"No local cache available at {local_data}")
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
def get_year(years:str) -> dict: 
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
    region_names = request.args.get("names", "")
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


def is_valid_date(date_str:str) -> bool: # boolean function
    """
    This function checks if the input is a properly formatted string
    that represents time in the 'YYYY-MM-DD' format. 

    Args: 
        date_str (str): string representing time in 'YYYY-MM-DD' format. 

    Returns: 
        boolean: Returns a boolean (True or False)
    """
    if not isinstance(date_str, str): 
        logging.warning(f"Invalid type for date: {date_str} (type: {type(date_str)})")
        return False
    try: 
        datetime.strptime(date_str, "%Y-%m-%d") # AI helped to strip time to check if its a string
        return True 
    except ValueError: 
        logging.warning(f"Invalid date format for string: {date_str}")
        return False 

@app.route('/jobs', methods=['GET','POST']) 
def get_jobs() -> Union[list, str]: 
    """
    This route uses the GET method to retrieve all the job ids from  
    the Redis database. It also uses the POST method to create a new 
    job in the queue depending on the parameters provided. 

    Args: 
        NONE 

    Returns: 
        result (str): Returns a string specifying that a job was created 
                      and the information, including the ID, of that job. 
                      This is when using the POST method. 
        OR 
        result (list): Returns a list of strings of all the job ids 
                       when using the GET method. 
    """ 
    if request.method == 'POST': 
        try: 
            data = request.get_json()
            logging.debug(f"POST data received")
            start = data.get('date_approved_start') # AI helped to understand syntax 
            end = data.get('date_approved_end')
            if not (is_valid_date(start) and is_valid_date(end)):
                logging.error("Invalid date format received")
                return {"error": "Invalid date format. Dates must be strings in 'YYYY-MM-DD' format."
                        }, 400 
            start_num = datetime.strptime(start, "%Y-%m-%d") # AI helped convert it to compare 
            end_num = datetime.strptime(end, "%Y-%m-%d") 
            if end_num<start_num:
                logging.error("End date is before start date")
                return {"error": "date_approved_end must be the same as or after date_approved start." 
                        }, 400 
            job_info = add_job(start, end) 
            logging.info(f"Job created successfully: {job_info}")
            return f'Job created: {job_info}\n' 
        except Exception as e: 
            logging.error(f"Error creating job: {e}")
            return {"error": "Internal Server Error"}, 500 
    elif request.method == 'GET': 
        logging.debug("Retrieved all job IDs")
        try: 
            jobs = get_all_jobs()
            return jobs
        except Exception as e:
            logging.error(f"Error retrieving jobs: {e}")
            return {"error": "Internal Server Error"}, 500

    logging.warning(f"Method {request.method} not allowed on /jobs")
    return {"error": f"Method Not Allowed."}, 405 

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

@app.route('/results/<jobid>', methods=['GET']) 
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
    try:
        data = get_results(jobid)
        logging.debug(f"Results fetched: {data}")
        return data  
    except Exception as e:
        logging.error(f"Error retrieving results for job {jobid}: {e}")
        return {"error": "Internal Server Error"}, 500 

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
