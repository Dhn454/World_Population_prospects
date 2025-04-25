#!/usr/bin/env python3
import requests
import matplotlib.pyplot as plt 
import argparse
import logging
import socket
from typing import List, Union 
from flask import Flask, request 
from datetime import datetime
import redis 
import json 
import os
from jobs import add_job, get_job_by_id, get_all_jobs, get_results

_redis_host = os.environ.get("REDIS_HOST") # AI used to understand environment function 
data_link = "https://storage.googleapis.com/public-download-files/hgnc/json/json/hgnc_complete_set.json" 

# Starting database 
rd=redis.Redis(host=_redis_host, port=6379, db=0) 

app = Flask(__name__) 

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level, logging.INFO)

logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logging.info("Logging level set to %s", log_level) 

def get_data() -> tuple: 
    """
    This function gets the HGNC data using the requests library. 

    Args: 
        NONE 

    Returns: 
        return (tuple): Returns a tuple with the first entry being the last
                        modified date as a string and the second entry being 
                        a list of dictionaries of the HGNC dictionaries. 
    """ 
    try: 
        response = requests.get(url=data_link) 
        response_head = requests.head(url=data_link) 
        if response.status_code!=200: # return status code --> 200 is success 
            logging.error(f'Status Error: {response.status_code}') 
            raise Exception(f'Status Error: {response.status_code}') 
        data = json.loads(response.content) 
        logging.debug(f'Data has been successfully written to data as a {type(data)}\n') 
        return response_head.headers['Last-Modified'], data['response']['docs'] # --> returns as tuple 
    except FileNotFoundError: 
        logging.error(f'The specified key does not exist\n') 
        raise Exception(f'The specified key does not exist\n') 

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
    response_head = requests.head(url=data_link) 
    header_time = response_head.headers['Last-Modified'] 
    # if header time is not the same or if number of keys 
    # is 0 (empty database) then request new data
    if len(rd.keys())==0 or rd.get('Last-Modified').decode('utf-8') != header_time: # order matters since an empty list cannot have a Last-modified time
        logging.debug('Data was not the same, initializing update.') 
        data = get_data() 
        # write data to database inside if statement
        rd.set('Last-Modified',data[0]) # sets the last-modified value for reference
        # for loop to write each EPOCH to database for easier lookup 
        for item in data[1]: 
            rd.set(item['hgnc_id'],json.dumps(item)) # redis saves it in random order 
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
        keys = [key.decode('utf-8') for key in rd.keys() if key.decode('utf-8') != "Last-Modified"] # AI used to check for last modified entry 
        data = [] 
        for item in keys:
            data.append(json.loads(rd.get(item).decode('utf-8'))) 
        return data
    elif request.method == 'POST':
        fetch_latest_data() 
        logging.debug('Loaded the HGNC data to a Redis database') 
        return 'Loaded the HGNC data to a Redis database\n' 
    elif request.method == 'DELETE':
        for item in rd.keys(): 
            rd.delete(item) 
        logging.debug('Deleted all data from Redis database')
        return 'Deleted all data from Redis database\n' 
    return {"error": f"Method Not Allowed."}, 405 

@app.route('/genes', methods=['GET']) # make a case where epoch is nonexistent
def get_all_genes() -> List[str]: 
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
            logging.warning("GET /genes returned an empty key list")
        return keys 
    except Exception as e:
        logging.error(f"Error fetching genes: {e}")
        return {"error": "Internal Server Error"}, 500

@app.route('/genes/<hgnc_id>', methods=['GET']) 
def get_gene(hgnc_id:str) -> dict: 
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
        response = json.loads(rd.get(hgnc_id)) 
        for key, value in response.items(): # https://www.w3schools.com/python/ref_dictionary_items.asp 
            if isinstance(value, list): # AI used to convert list to strings (aesthetic preference)
                response[key] = ", ".join(map(str, value))  # Join the elements into a single string 
        all_keys = count_keys() 
        missing_keys = all_keys - set(response.keys())
        for key in missing_keys: 
            response[key] = ""
        return response 
    except TypeError: 
        logging.error(f"hgnc_id '{hgnc_id}' not found")
        return {"error": f"hgnc_id '{hgnc_id}' not found"}, 404 

def count_keys() -> set: 
    """
    This function iterates through all the items in a Redis 
    database to get all the keys in a sparsely populated 
    list of dictionaries. 

    Args: 
        NONE

    Returns: 
        return (set): Returns a set of all the distinct keys 
                      in a sparsely populated list of dictionaries. 
    """
    logging.info("Counting distinct keys in Redis dataset")
    try: 
        keys = [key.decode('utf-8') for key in rd.keys() if key.decode('utf-8') != "Last-Modified"] # AI used to check for last modified entry 
        distinct_keys = set()
        for id in keys: 
            item = (json.loads(rd.get(id).decode('utf-8'))) 
            distinct_keys.update(set(item.keys())) 
        logging.debug(f"Found distinct keys: {distinct_keys}")
        return distinct_keys 
    except Exception as e:
        logging.error(f"Error counting keys: {e}")
        return set()

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
    app.run(debug=True, host='0.0.0.0')
