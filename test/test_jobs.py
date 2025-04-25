import pytest
from unittest.mock import patch, MagicMock
import uuid
import json
import jobs

def test_generate_jid():
    jid = jobs._generate_jid()
    assert isinstance(jid, str)
    uuid.UUID(jid)  # This will raise ValueError if not a valid UUID

def test_instantiate_job():
    jid = 'test-jid'
    job = jobs._instantiate_job(jid, 'submitted', '2024-01-01', '2024-01-02')
    assert job['id'] == jid
    assert job['status'] == 'submitted'
    assert job['start'] == '2024-01-01'
    assert job['end'] == '2024-01-02'

@patch('jobs.jdb')
def test_save_job(mock_jdb):
    jid = 'test-jid'
    job_dict = {'id': jid, 'status': 'submitted', 'start': '2024-01-01', 'end': '2024-01-02'}
    jobs._save_job(jid, job_dict)
    mock_jdb.set.assert_called_once_with(jid, json.dumps(job_dict))

@patch('jobs.q')
def test_queue_job(mock_q):
    jid = 'test-jid'
    jobs._queue_job(jid)
    mock_q.put.assert_called_once_with(jid)

@patch('jobs._generate_jid', return_value='test-jid')
@patch('jobs._save_job')
@patch('jobs._queue_job')
def test_add_job(mock_queue, mock_save, mock_generate):
    result = jobs.add_job('2024-01-01', '2024-01-02')
    assert result['id'] == 'test-jid'
    assert result['status'] == 'submitted'
    assert result['start'] == '2024-01-01'
    assert result['end'] == '2024-01-02'
    mock_save.assert_called_once()
    mock_queue.assert_called_once()

@patch('jobs.jdb')
def test_get_job_by_id_success(mock_jdb):
    jid = 'test-jid'
    expected = {'id': jid, 'status': 'submitted', 'start': '2024-01-01', 'end': '2024-01-02'}
    mock_jdb.get.return_value = json.dumps(expected)
    result = jobs.get_job_by_id(jid)
    assert result == expected

@patch('jobs.jdb')
def test_get_job_by_id_not_found(mock_jdb):
    mock_jdb.get.return_value = None
    result = jobs.get_job_by_id('bad-id')
    assert "error" in result

@patch('jobs.get_job_by_id')
@patch('jobs._save_job')
def test_update_job_status_success(mock_save, mock_get_job):
    mock_get_job.return_value = {'id': 'test-jid', 'status': 'submitted', 'start': '2024-01-01', 'end': '2024-01-02'}
    jobs.update_job_status('test-jid', 'complete')
    updated = mock_save.call_args[0][1]
    assert updated['status'] == 'complete'

@patch('jobs.get_job_by_id')
def test_update_job_status_failure(mock_get_job):
    mock_get_job.return_value = {"error": "not found"}
    with pytest.raises(Exception):
        jobs.update_job_status('bad-id', 'complete')

@patch('jobs.jdb')
def test_get_all_jobs(mock_jdb):
    mock_jdb.keys.return_value = [b'job1', b'job2']
    result = jobs.get_all_jobs()
    assert result == ['job1', 'job2']

@patch('jobs.get_job_by_id')
@patch('jobs.resdb')
def test_get_results_complete(mock_resdb, mock_get_job):
    jid = 'test-jid'
    job = {'id': jid, 'status': 'complete', 'start': '2024-01-01', 'end': '2024-01-02'}
    mock_get_job.return_value = job
    mock_resdb.get.return_value = json.dumps({'result': '42'}).encode('utf-8')
    result = jobs.get_results(jid)
    assert 'job' in result
    assert 'result' in result

@patch('jobs.get_job_by_id')
def test_get_results_incomplete(mock_get_job):
    jid = 'test-jid'
    mock_get_job.return_value = {'id': jid, 'status': 'submitted', 'start': '2024-01-01', 'end': '2024-01-02'}
    result = jobs.get_results(jid)
    assert 'Job is not done yet!' in result

@patch('jobs.get_job_by_id')
def test_get_results_not_found(mock_get_job):
    mock_get_job.return_value = {"error": "Job not found"}
    result = jobs.get_results('bad-id')
    assert "error" in result
