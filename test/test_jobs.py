import fakeredis
import json
import jobs

def setup_module(module):
    """Setup fake Redis connections for all Redis instances in jobs.py"""
    fake_jdb = fakeredis.FakeRedis()
    fake_q = fakeredis.FakeRedis()
    fake_resdb = fakeredis.FakeRedis()

    # Override jobs.py redis instances
    jobs.rd = fakeredis.FakeRedis()  # not really used in jobs.py currently
    jobs.jdb = fake_jdb
    jobs.q = fake_q
    jobs.resdb = fake_resdb

def test_string_to_bool():
    assert jobs.string_to_bool("true") is True
    assert jobs.string_to_bool("TrUe") is True
    assert jobs.string_to_bool("1") is False
    assert jobs.string_to_bool("false") is False
    assert jobs.string_to_bool("") is False
    assert jobs.string_to_bool("invalid") is False

def test_add_and_get_job():
    data = {
        "start": "2024-01-01",
        "end": "2024-01-31",
        "plot_type": "bar",
        "location": "Africa",
        "query1": "IMR",
        "query2": "Q5",
        "animate": "true"
    }
    job = jobs.add_job(data)
    jid = job['id']

    retrieved = jobs.get_job_by_id(jid)

    assert retrieved["id"] == jid
    assert retrieved["location"] == "Africa"
    assert retrieved["plot_type"] == "bar"
    assert retrieved["status"] == "submitted"

def test_update_job_status():
    data = {
        "start": "2024-02-01",
        "end": "2024-02-28",
        "plot_type": "line",
        "location": "Argentina",
        "query1": "LEx",
        "query2": "TFR",
        "animate": "false"
    }
    job = jobs.add_job(data)
    jid = job['id']

    jobs.update_job_status(jid, "in_progress")
    updated = jobs.get_job_by_id(jid)

    assert updated["status"] == "in_progress"

def test_get_all_jobs():
    data1 = {"start": "2023-01-01", "end": "2023-01-31"}
    data2 = {"start": "2023-02-01", "end": "2023-02-28"}
    
    job1 = jobs.add_job(data1)
    job2 = jobs.add_job(data2)

    all_jobs = jobs.get_all_jobs()
    
    assert job1['id'] in all_jobs
    assert job2['id'] in all_jobs

def test_get_results_not_complete():
    data = {"start": "2023-03-01", "end": "2023-03-31"}
    job = jobs.add_job(data)
    jid = job['id']

    result = jobs.get_results(jid)
    assert "Job is not done yet!" in result

def test_get_results_complete():
    data = {"start": "2023-04-01", "end": "2023-04-30"}
    job = jobs.add_job(data)
    jid = job['id']
    jobs.update_job_status(jid, "complete")

    # Manually set a fake result
    result_data = {"message": "analysis complete", "value": 42}
    jobs.resdb.hset(jid, "data", json.dumps(result_data))

    result = jobs.get_results(jid)
    assert result["result"]["value"] == 42

