import requests
import time
import logging

API_URL = "http://worldpop.coe332.tacc.cloud"

def test_full_job_lifecycle():
    # Step 1: Submit a job
    payload = {
        "start": '2000',
        "end": '2010',
    }
    res = requests.post(f"{API_URL}/jobs", json=payload)
    assert res.status_code == 201
    job_id = res.json().get("job", {}).get("id")
    assert job_id
    print(f"Job ID: {job_id}")

    # Step 2: Poll until job is done
    for _ in range(10):
        time.sleep(1)
        result = requests.get(f"{API_URL}/jobs/{job_id}")
        if result.status_code == 200:
            data = result.json()
            assert data["status"] == "complete"
            return
        data = requests.get(f"{API_URL}/results/{job_id}")
        if data.status_code == 200:
            result_data = data.json()
            assert result_data["result"] is not None
            assert len(result_data["result"]) == payload["end"] - payload["start"] + 1 
            assert result_data["job"]["status"] == "complete"
            assert result_data["result"]["World"] is not None
