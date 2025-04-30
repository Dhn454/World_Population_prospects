import redis 
import json 
from collections import Counter 
import os
import argparse 
import socket 
import logging 
from hotqueue import HotQueue 
from jobs import update_job_status, get_job_by_id
from datetime import datetime
import time

_redis_port=6379 
_redis_host = os.environ.get("REDIS_HOST") # AI used to understand environment function 

rd = redis.Redis(host=_redis_host, port=_redis_port, db=0)
q = HotQueue("queue", host=_redis_host, port=_redis_port, db=1) 
resdb = redis.Redis(host=_redis_host, port=_redis_port, db=3) 

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level, logging.INFO)

logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
logger.info("Logging level set to %s", log_level)

@q.worker
def update(jobid: str): 
    """
    Uses the hotqueue decorator to get jobs off a queue and process them. It filters gene 
    entries based on the approved date range and counts their occurences by 'locus_type'. 
    The results are then stored in a results database, and the job is updated to 'completed' status.
    
    Args:
        jobid (str): A string representing the unique job ID to be processed.

    Returns:
        NONE
    """
    # logging.info(f"Started processing job: {jobid}")
    # try:
    #     update_job_status(jobid, 'in progress')

    #     # WORK STARTING  
    #     job_dict = get_job_by_id(jobid)
    #     if "error" in job_dict:
    #         raise Exception(f"Error retrieving job {jobid}: {job_dict['error']}")

    #     start = datetime.strptime(job_dict["start"], "%Y-%m-%d")
    #     end = datetime.strptime(job_dict["end"], "%Y-%m-%d") 
    #     keys = rd.keys()
    #     locus_types = []

    #     for item in keys:
    #         try:
    #             data = rd.get(item)
    #             if not data:
    #                 continue
    #             data_dict = json.loads(data.decode("utf-8"))
                
    #             date_str = data_dict.get("date_approved_reserved")
    #             if not date_str:
    #                 continue

    #             date = datetime.strptime(date_str, "%Y-%m-%d")
    #             if start <= date <= end:
    #                 locus_type = data_dict.get("locus_type")
    #                 if locus_type:
    #                     locus_types.append(locus_type)
    #         except Exception as e:
    #             logging.error(f"Error processing key {item}: {e}")

    #     if not locus_types:
    #         results = {"message": "No genes found in the specified date range."}
    #     else:
    #         results = Counter(locus_types)

    #     resdb.set(jobid, json.dumps(results))
    #     update_job_status(jobid, 'complete')

    # except Exception as e:
    #     update_job_status(jobid, 'error')  # If something goes wrong, mark job as error.
    #     logging.error(f"Error processing job {jobid}: {e}") 
    update_job_status(jobid, 'in progress') 
    time.sleep(15) # sleeps for 15 seconds to mock work being done 
    update_job_status(jobid, 'complete') 

update() 
