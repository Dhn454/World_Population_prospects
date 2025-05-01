import json
import uuid
import argparse 
import socket 
import redis
import os 
from hotqueue import HotQueue 
import logging 

_redis_host = os.environ.get("REDIS_HOST") 
_redis_port=6379 

rd = redis.Redis(host=_redis_host, port=_redis_port, db=0)
q = HotQueue("queue", host=_redis_host, port=_redis_port, db=1)
jdb = redis.Redis(host=_redis_host, port=_redis_port, db=2) 
resdb = redis.Redis(host=_redis_host, port=_redis_port, db=3) # database for storing results 

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level, logging.INFO)

logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logging.info("Logging level set to %s", log_level) 

def _generate_jid() -> str:
    """
    Generate a pseudo-random identifier for a job.
    """
    jid = str(uuid.uuid4())
    logging.debug(f"Generated job ID: {jid}")
    return jid

def _instantiate_job(jid, status, data_dict):
    """
    Create the job object description as a python dictionary.
    """
    job = {'id': jid, 'status': status, 'start': data_dict.get('start'), 'end': data_dict.get('end'), 
           'plot_type': data_dict.get('plot_type'), 'location': data_dict.get('Location'), 
           'query1': data_dict.get('query1'), 'query2': data_dict.get('query2'), 'animate': data_dict.get('animate')}
    job = {k: v for k, v in job.items() if v is not None} 
    logging.debug(f"Instantiated job: {job}")
    return job 

def _save_job(jid, job_dict):
    """Save a job object in the Redis database."""
    try:
        jdb.set(jid, json.dumps(job_dict))
        logging.info(f"Saved job {jid} to Redis.")
    except Exception as e:
        logging.error(f"Failed to save job {jid} to Redis: {e}")

def _queue_job(jid):
    """Add a job to the redis queue."""
    try:
        q.put(jid)
        logging.info(f"Queued job {jid}.")
    except Exception as e:
        logging.error(f"Failed to queue job {jid}: {e}")

def add_job(data_dict, status="submitted") -> dict:
    """Add a job to the redis queue."""
    logging.info(f"Adding new job.")
    jid = _generate_jid()
    job_dict = _instantiate_job(jid, status, data_dict) 
    _save_job(jid, job_dict)
    _queue_job(jid)
    return job_dict

def get_job_by_id(jid) -> dict:
    """Return job dictionary given jid"""
    try:
        job_data = jdb.get(jid)
        if job_data is None:
            logging.warning(f"Job ID '{jid}' not found in Redis.")
            return {"error": f"Job ID '{jid}' not found."}
        job = json.loads(job_data)
        logging.debug(f"Retrieved job {jid}: {job}")
        return job
    except Exception as e:
        logging.error(f"Error retrieving job {jid}: {e}")
        return {"error": f"Job ID '{jid}' not found."}

def update_job_status(jid, status):
    """Update the status of job with job id `jid` to status `status`."""
    logging.info(f"Updating status of job {jid} to '{status}'")
    job_dict = get_job_by_id(jid)
    if "error" not in job_dict:
        job_dict['status'] = status
        _save_job(jid, job_dict)
        logging.debug(f"Job {jid} status updated to '{status}'")
    else:
        logging.error(f"Cannot update status. {job_dict['error']}")
        raise Exception(f"Job ID '{jid}' not found.")

def get_all_jobs() -> list:
    """Returns all of the job ids including the in progress and completed jobs"""
    try:
        keys = jdb.keys()
        keys = [key.decode('utf-8') for key in keys]
        logging.debug(f"Retrieved all job IDs: {keys}")
        return keys
    except Exception as e:
        logging.error(f"Error fetching job keys: {e}")
        return []

def get_results(jid) -> dict:
    """Returns results of job with job id `jid`."""
    logging.info(f"Fetching results for job {jid}")
    job_dict = get_job_by_id(jid)
    if "error" in job_dict:
        logging.warning(f"Results request failed: {job_dict['error']}")
        return {"error": f"Job ID '{jid}' not found."}

    if job_dict['status'] == 'complete':
        try:
            result = resdb.get(jid)
            parsed_result = json.loads(result.decode('utf-8'))
            logging.debug(f"Results for job {jid}: {parsed_result}")
            return {"job": job_dict, "result": parsed_result}
        except Exception as e:
            logging.error(f"Error decoding result for job {jid}: {e}")
            return {"error": "Failed to retrieve job results."}

    logging.info(f"Job {jid} not complete yet.")
    return {"Job is not done yet!": job_dict}
