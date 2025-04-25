import pytest
import redis
import json
from unittest.mock import patch
from datetime import datetime
import worker  # Import your worker module

REDIS_HOST = 'localhost'  # Ensure this matches your environment configuration
rd = redis.Redis(host=REDIS_HOST, port=6379, db=0)  # Gene data
resdb = redis.Redis(host=REDIS_HOST, port=6379, db=3)  # Results

# Test job ID
TEST_JOB_ID = 'test-job-123'

# Sample genes
GENE_DATA = {
    b'gene1': {
        "date_approved_reserved": "2023-06-15",
        "locus_type": "protein-coding"
    },
    b'gene2': {
        "date_approved_reserved": "2023-07-20",
        "locus_type": "non-coding"
    },
    b'gene3': {
        "date_approved_reserved": "2022-05-01",
        "locus_type": "other"
    }
}

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_redis():
    # SETUP: Insert sample gene entries into Redis
    for key, val in GENE_DATA.items():
        rd.set(key, json.dumps(val))

    # Create a test job manually
    job = {
        "id": TEST_JOB_ID,
        "start": "2023-01-01",
        "end": "2023-12-31"
    }
    rd.set(TEST_JOB_ID, json.dumps(job))

    yield  # Run the tests

    # TEARDOWN: Remove inserted keys
    rd.delete(TEST_JOB_ID)
    for key in GENE_DATA.keys():
        rd.delete(key)
    resdb.delete(TEST_JOB_ID)


def test_process_job_real_redis():
    # Mock the functions used in worker.py
    def mock_get_job_by_id(job_id):
        raw = rd.get(job_id)
        return json.loads(raw) if raw else {"error": "Not found"}

    def mock_update_job_status(job_id, status):
        print(f"[Mock] Status for {job_id}: {status}")

    # Patch the functions in worker module
    with patch.object(worker, 'get_job_by_id', side_effect=mock_get_job_by_id), \
         patch.object(worker, 'update_job_status', side_effect=mock_update_job_status):

        # Call the process_job function
        worker.process_job(TEST_JOB_ID)

        # Check the results in Redis
        result = resdb.get(TEST_JOB_ID)
        assert result is not None

        # Convert the result to a Python dictionary
        data = json.loads(result)
        
        # Assertions based on the expected results
        assert data["protein-coding"] == 1
        assert data["non-coding"] == 1
        assert "other" not in data  # 'other' is out of range based on the date filter
