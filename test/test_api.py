import pytest
import json
from collections import Counter
from datetime import datetime
import sys
import os
import redis
from unittest.mock import patch

# Add the src directory to sys.path so that worker.py can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # AI used 

import api 

@pytest.fixture # AI used to get this mock api going on 
def client():
    api.app.config['TESTING'] = True
    with api.app.test_client() as client:
        yield client

def test_get_data_success():
    mock_response = {
        'response': {
            'docs': [{'hgnc_id': 'HGNC:5', 'symbol': 'A1BG'}]
        }
    }
    headers = {'Last-Modified': 'Mon, 15 Apr 2025 00:00:00 GMT'}

    with patch('api.requests.get') as mock_get, \
         patch('api.requests.head') as mock_head:
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = json.dumps(mock_response).encode('utf-8')
        mock_head.return_value.headers = headers

        from api import get_data  # Import inside to apply mocks
        last_modified, data = get_data()

        assert last_modified == headers['Last-Modified']
        assert data == mock_response['response']['docs']
        
def test_process_data_get(client, mocker):
    # Mock Redis keys and get
    mocker.patch('api.rd.keys', return_value=[b'HGNC:5'])
    mocker.patch('api.rd.get', return_value=json.dumps({'hgnc_id': 'HGNC:5', 'symbol': 'A1BG'}).encode('utf-8'))

    response = client.get('/data')
    assert response.status_code == 200
    assert response.get_json() == [{'hgnc_id': 'HGNC:5', 'symbol': 'A1BG'}]

def test_process_data_post(client, mocker):
    # Mock fetch_latest_data
    mocker.patch('api.fetch_latest_data', return_value=None)

    response = client.post('/data')
    assert response.status_code == 200
    assert b'Loaded the HGNC data to a Redis database' in response.data

def test_process_data_delete(client, mocker):
    # Mock Redis keys and delete
    mocker.patch('api.rd.keys', return_value=[b'HGNC:5'])
    mocker.patch('api.rd.delete', return_value=1)

    response = client.delete('/data')
    assert response.status_code == 200
    assert b'Deleted all data from Redis database' in response.data
    
def test_get_all_genes(client, mocker):
    mocker.patch('api.rd.keys', return_value=[b'HGNC:5'])

    response = client.get('/genes')
    assert response.status_code == 200
    assert response.get_json() == ['HGNC:5']

def test_get_gene(client, mocker):
    gene_data = {'hgnc_id': 'HGNC:5', 'symbol': 'A1BG'}
    mocker.patch('api.rd.get', return_value=json.dumps(gene_data).encode('utf-8'))
    mocker.patch('api.count_keys', return_value=set(gene_data.keys()))

    response = client.get('/genes/HGNC:5')
    assert response.status_code == 200
    assert response.get_json() == gene_data

def test_get_jobs_get(client, mocker):
    mocker.patch('api.get_all_jobs', return_value=['job1', 'job2'])

    response = client.get('/jobs')
    assert response.status_code == 200
    assert response.get_json() == ['job1', 'job2']

def test_get_jobs_post(client, mocker):
    mocker.patch('api.is_valid_date', return_value=True)
    mocker.patch('api.add_job', return_value='job123')

    response = client.post('/jobs', json={
        'date_approved_start': '2025-01-01',
        'date_approved_end': '2025-12-31'
    })
    assert response.status_code == 200
    assert b'Job created: job123' in response.data

def test_get_job(client, mocker):
    job_data = {'job_id': 'job123', 'status': 'completed'}
    mocker.patch('api.get_job_by_id', return_value=job_data)

    response = client.get('/jobs/job123')
    assert response.status_code == 200
    assert response.get_json() == job_data

def test_results(client, mocker):
    result_data = {'job_id': 'job123', 'result': 'success'}
    mocker.patch('api.get_results', return_value=result_data)

    response = client.get('/results/job123')
    assert response.status_code == 200
    assert response.get_json() == result_data
