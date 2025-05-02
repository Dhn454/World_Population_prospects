import requests
import json

BASE_URL = "http://worldpop.coe332.tacc.cloud"

def test_post_data():
    resp = requests.post(f"{BASE_URL}/data")
    assert resp.status_code == 200
    assert "Loaded the world population data" in resp.text

def test_get_data():
    resp = requests.get(f"{BASE_URL}/data")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0  # Should have some entries

def test_get_years():
    resp = requests.get(f"{BASE_URL}/years")
    assert resp.status_code == 200
    keys = resp.json()
    assert isinstance(keys, list)
    assert all(isinstance(k, str) for k in keys)

def test_get_regions_in_year():
    resp = requests.get(f"{BASE_URL}/years/2023/regions?names=World")
    assert resp.status_code == 200
    result = resp.json()
    if isinstance(result, dict):
        assert "data" in result
    else:
        assert isinstance(result, list)

def test_get_all_regions():
    resp = requests.get(f"{BASE_URL}/regions")
    assert resp.status_code == 200
    regions = resp.json()
    assert isinstance(regions, list)
    assert all(isinstance(region, str) for region in regions)
    assert "World" in regions  # Adjust based on known data

def test_get_specific_region_valid():
    region = "World"
    resp = requests.get(f"{BASE_URL}/regions/{region}")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert all(d.get("Location") == region for d in data)

def test_get_specific_region_invalid():
    region = "Atlantis"
    resp = requests.get(f"{BASE_URL}/regions/{region}")
    assert resp.status_code == 404
    assert "error" in resp.json()

def test_get_region_eras_valid_range():
    region = "World"
    eras = "2000-2005"
    resp = requests.get(f"{BASE_URL}/regions/{region}/{eras}")
    assert resp.status_code in (200, 206)
    json_resp = resp.json()
    assert "data" in json_resp
    assert all(entry["Location"] == region for entry in json_resp["data"])
    if "missing_years" in json_resp:
        assert isinstance(json_resp["missing_years"], list)

def test_get_region_eras_invalid_range():
    region = "World"
    eras = "3000-3010"  # Assume these years are not in DB
    resp = requests.get(f"{BASE_URL}/regions/{region}/{eras}")
    assert resp.status_code == 404
    assert "error" in resp.json()

def test_get_region_eras_invalid_format():
    region = "World"
    eras = "not-a-year"
    resp = requests.get(f"{BASE_URL}/regions/{region}/{eras}")
    assert resp.status_code == 404
    assert "error" in resp.json()

def test_get_help():
    resp = requests.get(f"{BASE_URL}/help")
    assert resp.status_code == 200
    assert "curl" in resp.text

def test_jobs_lifecycle():
    job_payload = {
        "start": "2000",
        "end": "2010",
        "plot_type": "line",
        "Location": "Asia"
    }

    # Create job
    post = requests.post(f"{BASE_URL}/jobs", json=job_payload)
    assert post.status_code == 201
    job = post.json()["job"]
    job_id = job["id"]

    # Fetch job by ID
    get = requests.get(f"{BASE_URL}/jobs/{job_id}")
    assert get.status_code == 200
    assert get.json().get("id") == job_id

    # Get all jobs
    all_jobs = requests.get(f"{BASE_URL}/jobs")
    assert all_jobs.status_code == 200
    assert isinstance(all_jobs.json(), list)

    # Delete all jobs
    delete = requests.delete(f"{BASE_URL}/jobs")
    assert delete.status_code == 200
    check = requests.get(f"{BASE_URL}/jobs")
    assert check.status_code == 200
    assert len(check.json()) == 0


def test_delete_data():
    resp = requests.delete(f"{BASE_URL}/data")
    assert resp.status_code == 200
    assert "Deleted all data" in resp.text
