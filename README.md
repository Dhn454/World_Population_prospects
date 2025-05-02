# Earth In Numbers 

## Table of Contents
1. [Description](README.md#description) 
2. [Software Diagram](README.md#software-diagram)
2. [World Population Prospects Data Set](README.md#world-population-prospects-data-set)
2. [Getting Started](README.md#getting-started)
3. [Building the Container](README.md#building-the-container)
4. [Running Docker Container](README.md#running-containerized-scripts)
5. [Accessing Microservice](README.md#accessing-microservice)
6. [Running Test Scripts](README.md#running-test-scripts)
5. [Clean Up](README.md#clean-up)
9. [Resources](README.md#resources)
10. [AI Usage](README.md#ai-usage)

## Makefile Commands

| Command             | Description                                                 |
|---------------------|-------------------------------------------------------------|
| `make k`            | Apply all Kubernetes configs and show status                |
| `make k-up`         | Apply Kubernetes manifests only                             |
| `make k-down`       | Delete Kubernetes resources                                 |
| `make k-status`     | Check Kubernetes pods, services, and ingress                |
| `make docker-up`    | Build and start all Docker services (includes data download)|
| `make docker-down`  | Stop and remove all Docker services                         |
| `make docker-api`   | Restart only the `flask-app` Docker service (includes data download) |
| `make docker-worker`| Restart only the `worker` Docker service                    |
| `make docker-redis` | Restart only the `redis-db` Docker service                  |



## Description 

This code features two routes in a containerized Flask API that communicates with a [Redis](https://redis.io) database. The ```api.py``` establishes connection with a redis database and checks if the database is empty. If it is empty or if the data is out of date, it injests the [HGNC Data](https://www.genenames.org/download/archive/) using the requests library and writes it to the redis database as ```key:value``` pairs. You are able to write the entire data set to the redis database, delete the entire data set from redis, and return the data set to the user. There is also a route which returns a JSON-formatted list of all hgnc_id fields as well as the entire dictionary of a specific hgnc_id field. 

The api script also contains three functions of the names: 
* get_data - Gets the list of dictionaries of the different genes from the [HGNC](https://www.genenames.org/download/archive/) website using the requests library. 
* fetch_latest_data - Fetches the latest [HGNC](https://www.genenames.org/download/archive/) data and updates redis database only if new data is available. 
* count_keys - Returns the list of all the distinct keys from a data set in a Redis database. 

This project now includes functionality for managing jobs through a queue system implemented using Redis and a results route that gives the user the results from their jobs. Jobs represent queries defined by a start and end date, and they move through a lifecycle: submitted → in-progress → complete. The updated worker script and a new route support this functionality:

* worker.py: Continuosly grabs the next job in line, it processes it and updates its status in the Redis database once completed. 
* jobs.py: Provides the main logic for managing job creation, queuing, storage, and updates. It generates job IDs, stores and retrieves job data from Redis, and queues jobs for the worker.py. 

Here is the full list of routes metioned above and their syntax: 

|  Route                              |  Method  | Functionality                                                                     | 
| ----------------------------------- | -------- | --------------------------------------------------------------------------------- | 
| /data                               | GET      | Put data into Redis                                                               | 
| /data                               | POST     | Return all data from Redis                                                        | 
| /data                               | DELETE   | Delete all data from Redis                                                        | 
| /years                              | GET      | Return json-formatted list of all the years available from the dataset            | 
| /years/{year}/regions               | GET      | Return all data associated with a specific year and all its regions               | 
| /years/{year}/regions?names=a,b,c   | GET      | Return data associated with a specific year and the specified regions             | 
| /regions                            | GET      | Return a list of all regions/countries in the dataset                             | 
| /regions/{region}                   | GET      | Return data of all the years for a specific {region}                              | 
| /results/{region}/{eras}            | GET      | Return data for a specific region and the specified eras/years                    | 
| /jobs                               | GET      | Return a list of all job IDs                                                      |
| /help                               | GET      | Returns instructions to post a job                                                | 
| /jobs                               | POST     | Submits a new job to the queue by sending a json dictionary in the request body   | 
| /jobs/{jobid}                       | GET      | Return all data associated with a {jobid}                                         | 
| /results/{jobid}                    | GET      | Return the results associated with a {jobid}                                      | 

This project illustrates how to ingest data from a Web API using the ```requests``` library and saving it to a persistent redis database using the ```redis``` library. It also helps facilitate the analysis of such data by using the five functions and three routes mentioned above. 

This code is necessary when you want to constantly have the updated data to your disposal for analysis. It facilitates looking up a certain gene from the database as well as a complete list of all genes in the database. It also helps in queuing jobs for data analysis as well as managing those jobs. 

## Software Diagram 
![Software Diagram](diagram.png "Software Diagram Flowchart")

This diagram shows the typical flow of data focused around the files of homework08. We can clearly see that the docker container pulls data from the HUGO Gene Nomenclature Committee Database using the ```requests``` library. The gene_api.py inside the docker container converts the response from the database into a json like list of dictionaries that we can analyze, illustrated by the data block. This is done inside the data/ route using the 'POST' method. Note that the 'POST' method requests the data from the Web API and writes it to the redis database. A local data backup is created to make the redis database persistent. We also have a ```Last-Modified``` dictionary with the time the last data request was modified, this allows us to be more efficient when updating the redis database. 

The user is able to interact with the containerised flask application using the ```curl``` command. Running the illustrated routes using the ```curl localhost:5000```, it allows the user to call each each containerized function and analyze the HUGO Gene Nomenclature Committee Data. 

Our API also features a queue methodology where each posted job will be added to the queue as a first come first serve. Each job once finished will be taken off the queue and the user will be able to see the results with the GET results route as illustrated in the diagram above. 

## HUGO Gene Nomenclature Committee (HGNC) Data Set

The [HGNC Data Set](https://www.genenames.org/download/archive/) is a comprehensive collection of human gene nomenclature maintained by the HUGO Gene Nomenclature Committee (HGNC). The dataset provides standardized gene symbols and unique identifiers for human genes, ensuring consistency in genetic research and data analysis.

Each entry in the dataset corresponds to a specific human gene and contains detailed information, including the gene’s approved symbol, name, previous symbols, aliases, and database cross-references. The dataset also includes various identifiers linking each gene to external databases such as Ensembl, Entrez, RefSeq, UniProt, and OMIM. 

The dataset is available in multiple formats, including JSON, TXT, and XML, allowing for easy integration into bioinformatics pipelines and applications. It is regularly updated to reflect the latest changes in gene nomenclature and new discoveries in the field of genetics.

| Acronym         | Description                                                                | How to Query                  |
|-----------------|----------------------------------------------------------------------------|-------------------------------|
| TPopulation1Jan | Total Population, as of 1 January (thousands)                              | "query1": "TPopulation1Jan"   |
| TPopulation1July| Total Population, as of 1 July (thousands)                                 | "query1": "TPopulation1July"  |
| TPopulationMale1July | Male Population, as of 1 July (thousands)                             | "query1": "TPopulationMale1July" |
| TPopulationFemale1July | Female Population, as of 1 July (thousands)                         | "query1": "TPopulationFemale1July" |
| PopDensity      | Population Density, as of 1 July (persons per square km)                   | "query1": "PopDensity"        |
| PopSexRatio     | Population Sex Ratio, as of 1 July (males per 100 females)                 | "query1": "PopSexRatio"       |
| MedianAgePop    | Median Age, as of 1 July (years)                                           | "query1": "MedianAgePop"      |
| NatChange       | Natural Change, Births minus Deaths (thousands)                            | "query1": "NatChange"         |
| NatChangeRT     | Rate of Natural Change (per 1,000 population)                              | "query1": "NatChangeRT"       |
| PopChange       | Population Change (thousands)                                              | "query1": "PopChange"         |
| PopGrowthRate   | Population Growth Rate (percentage)                                        | "query1": "PopGrowthRate"     |
| DoublingTime    | Population Annual Doubling Time (years)                                    | "query1": "DoublingTime"      |
| Births          | Births (thousands)                                                         | "query1": "Births"            |
| Births1519      | Births by women aged 15 to 19 (thousands)                                  | "query1": "Births1519"        |
| CBR             | Crude Birth Rate (births per 1,000 population)                             | "query1": "CBR"               |
| TFR             | Total Fertility Rate (live births per woman)                               | "query1": "TFR"               |
| NRR             | Net Reproduction Rate (surviving daughters per woman)                      | "query1": "NRR"               |
| MAC             | Mean Age Childbearing (years)                                              | "query1": "MAC"               |
| SRB             | Sex Ratio at Birth (males per 100 female births)                           | "query1": "SRB"               |
| Deaths          | Total Deaths (thousands)                                                   | "query1": "Deaths"            |
| DeathsMale      | Male Deaths (thousands)                                                    | "query1": "DeathsMale"        |
| DeathsFemale    | Female Deaths (thousands)                                                  | "query1": "DeathsFemale"      |
| CDR             | Crude Death Rate (deaths per 1,000 population)                             | "query1": "CDR"               |
| LEx             | Life Expectancy at Birth, both sexes (years)                               | "query1": "LEx"               |
| LExMale         | Male Life Expectancy at Birth (years)                                      | "query1": "LExMale"           |
| LExFemale       | Female Life Expectancy at Birth (years)                                    | "query1": "LExFemale"         |
| LE15            | Life Expectancy at Age 15, both sexes (years)                              | "query1": "LE15"              |
| LE15Male        | Male Life Expectancy at Age 15 (years)                                     | "query1": "LE15Male"          |
| LE15Female      | Female Life Expectancy at Age 15 (years)                                   | "query1": "LE15Female"        |
| LE65            | Life Expectancy at Age 65, both sexes (years)                              | "query1": "LE65"              |
| LE65Male        | Male Life Expectancy at Age 65 (years)                                     | "query1": "LE65Male"          |
| LE65Female      | Female Life Expectancy at Age 65 (years)                                   | "query1": "LE65Female"        |
| LE80            | Life Expectancy at Age 80, both sexes (years)                              | "query1": "LE80"              |
| LE80Male        | Male Life Expectancy at Age 80 (years)                                     | "query1": "LE80Male"          |
| LE80Female      | Female Life Expectancy at Age 80 (years)                                   | "query1": "LE80Female"        |
| InfantDeaths    | Infant Deaths, under age 1 (thousands)                                     | "query1": "InfantDeaths"      |
| IMR             | Infant Mortality Rate (infant deaths per 1,000 live births)                | "query1": "IMR"               |
| LBsurvivingAge1 | Live births Surviving to Age 1 (thousands)                                 | "query1": "LBsurvivingAge1"   |
| Under5Deaths    | Deaths under age 5 (thousands)                                             | "query1": "Under5Deaths"      |
| Q5              | Under-five Mortality Rate (deaths under age 5 per 1,000 live births)       | "query1": "Q5"                |
| Q0040           | Mortality before Age 40, both sexes (per 1,000 live births)                | "query1": "Q0040"             |
| Q0040Male       | Male mortality before Age 40                                               | "query1": "Q0040Male"         |
| Q0040Female     | Female mortality before Age 40                                             | "query1": "Q0040Female"       |
| Q0060           | Mortality before Age 60, both sexes                                        | "query1": "Q0060"             |
| Q0060Male       | Male mortality before Age 60                                               | "query1": "Q0060Male"         |
| Q0060Female     | Female mortality before Age 60                                             | "query1": "Q0060Female"       |
| Q1550           | Mortality between Age 15 and 50, both sexes                                | "query1": "Q1550"             |
| Q1550Male       | Male mortality between Age 15 and 50                                       | "query1": "Q1550Male"         |
| Q1550Female     | Female mortality between Age 15 and 50                                     | "query1": "Q1550Female"       |
| Q1560           | Mortality between Age 15 and 60, both sexes                                | "query1": "Q1560"             |
| Q1560Male       | Male mortality between Age 15 and 60                                       | "query1": "Q1560Male"         |
| Q1560Female     | Female mortality between Age 15 and 60                                     | "query1": "Q1560Female"       |
| NetMigrations   | Net Number of Migrants (thousands)                                         | "query1": "NetMigrations"     |
| CNMR            | Net Migration Rate (per 1,000 population)                                  | "query1": "CNMR"              |

For more information, visit: [HGNC Download Archive](https://www.genenames.org/download/archive/) 

_Disclaimer: The above description is based on publicly available information from the HGNC website._

## Getting Started 
Check which directory you are currently on by running
``` bash 
pwd
```

You should see you are in homework08 such as: 
``` bash
/home/guarneros/coe332-hw-guarneros/homework08 
```
If not change to homework08 folder by: 
``` bash
cd homework08/
```

### Configure docker-compose.yml file
Now we can proceed to configuring our docker-compose.yml file. 
As you may have noticed, you have a [docker-compose.yml](docker-compose.yml) file. You will have to modify this to be able to run docker compose. 

Using your favorite text editor (i.e vim, emacs, nano, etc), open this file and change 'rguarneros065' to your docker username. 

```bash
# Example
vim docker-compose.yml 

# Output
---
version: "3"

services:
    redis-db:
        image: redis:7 
        ports:
            - 6379:6379
        volumes:
            - ./data:/data 
        user: "1000:1000"
        command: ["--save", "1", "1"]
    flask-app:
        build:
            context: ./ 
            dockerfile: ./Dockerfile
        depends_on:
            - redis-db
        image: rguarneros065/flask-redis-gene_api:1.0 
        ports:
            - 5000:5000
        command: [api.py] # AI used to run the api 
        environment: # AI used to add environment 
        - REDIS_HOST=redis-db
        - LOG_LEVEL=WARNING
    worker: 
        build: 
            context: ./ 
            dockerfile: ./Dockerfile
        depends_on: 
            - redis-db
        image: rguarneros065/flask-redis-gene_api:1.0   
        command: [worker.py] 
        environment: 
        - REDIS_HOST=redis-db
        - LOG_LEVEL=WARNING
```
Please make sure to change 'rguarneros065' to your actual docker username. 

Also note that you have a loglevel environment variable that you can change. You will have to exec into the docker container to see these logs. 

### Installing packages for pytest 
You will also need to install a pytest plugin to be able to run the test scripts. To do that please do the following: 
```bash 
pip install pytest-mock
```

## Building the Container 
_Make sure to replace 'rguarneros065' with your Docker Hub username in the docker-compose.yml file as mentioned in the [previous section](README.md#configure-docker-composeyml-file)_

To build the image run: 
``` bash
docker compose build 

# Example Output
WARN[0000] /home/ubuntu/coe332-hw-guarneros/homework08/docker-compose.yml: `version` is obsolete 
[+] Building 23.1s (17/22)                                                                           docker:default
 => [worker internal] load build definition from Dockerfile                                                    0.0s
 => => transferring dockerfile: 292B                                                                           0.0s
...
```

To ensure you see a copy of your image that was built, run 
``` bash 
docker images 

# Example Output
REPOSITORY                              TAG       IMAGE ID       CREATED              SIZE
<none>                                  <none>    88b268f3c799   About a minute ago   1.04GB 
rguarneros065/flask-redis-gene_api      1.0       17c887dfe3fe   About a minute ago   1.04GB 
...
``` 
You should see your username in the repository name. You may also notice that there is a 'none' image, this is caused because the docker-compose.yml file uses the same Dockerfile and tag or both the flask-app and worker services. To delete the 'none' image you can run: 
```bash
docker image prune 
```

## Running Docker Container
First, let's make sure that we don't have any container using port 5000 by running: 
```bash
docker ps -a

# NO CONTAINERS LISTENING TO PORT 5000 EXAMPLE 
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
```
Under the PORTS section, no containers should be listening in to port 5000. If there are containers listening to port 5000 make sure to stop and remove them using the following commands: 
```bash 
docker stop <CONTAINER_ID> 

docker rm <CONTAINER_ID> 
``` 

Now you are ready to run docker compose. 
```bash 
docker compose up -d 

# Example Output
WARN[0000] /home/ubuntu/coe332-hw-guarneros/homework08/docker-compose.yml: `version` is obsolete 
[+] Running 4/4
 ✔ Network homework08_default        Created                                                                   0.1s 
 ✔ Container homework08-redis-db-1   Started                                                                   0.5s 
 ✔ Container homework08-worker-1     Started                                                                   0.7s 
 ✔ Container homework08-flask-app-1  Started                                                                   0.7s 
```
The -d flag allows you to start the service in the background. 

Make sure the containers are up and running:
```bash 
docker ps -a 

# Output
CONTAINER ID   IMAGE                                    COMMAND                  CREATED          STATUS          PORTS                                       NAMES
930cd6f203fa   rguarneros065/flask-redis-gene_api:1.0   "python worker.py"       25 seconds ago   Up 23 seconds                                               homework08-worker-1
214d6a015d7c   rguarneros065/flask-redis-gene_api:1.0   "python api.py"          25 seconds ago   Up 23 seconds   0.0.0.0:5000->5000/tcp, :::5000->5000/tcp   homework08-flask-app-1
b256c7fdeb20   redis:7                                  "docker-entrypoint.s…"   25 seconds ago   Up 24 seconds   0.0.0.0:6379->6379/tcp, :::6379->6379/tcp   homework08-redis-db-1
... 
``` 

You should see 3 containers are up and running. This is due to the api's and the worker's need to establish a connection with each other and the redis database while the API hosts the flask app. 

Your container list should have all the containers with an Up status, and the port mapping you specified in the docker-compose.yml file. If this is not the case, then you might have used the wrong ```docker-compose.yml``` file. 

## Accessing Microservice 
Now you are ready to run your Flask microservice! 

### Running _/data_ route with the _POST_ method
To put the entire data set into the Redis database you can run: 
``` bash 
curl -X POST "localhost:5000/data" 

# Output
Loaded the HGNC data to a Redis database 
```
The following command loaded the entire HGNC data to a Redis database using each dictionary's hgnc_id as the key for each dictionary. A _Last-Modified_ key was written to the database to make sure you are not rewriting a data set with itself. 

Note: This command might take a while since it is trying to fetch the [HGNC](https://www.genenames.org/download/archive/) data. 

### Running _/data_ route with the _GET_ method 
You can also return the entire data set from the Redis database by running the following: 
```bash
curl -X GET "localhost:5000/data"
```
OR 
```bash
curl "localhost:5000/data" 
```

Both of the following commands work exactly the same since GET is the default method. 

```bash
# Example Output
  {
    "agr": "HGNC:17767",
    "alias_symbol": [
      "bA513I15.2"
    ],
    "date_approved_reserved": "2004-03-26",
    "date_modified": "2014-11-19",
    "ensembl_gene_id": "ENSG00000271231",
    "entrez_id": "442205",
    "hgnc_id": "HGNC:17767",
    "location": "6p21.31",
    "location_sortable": "06p21.31",
    "locus_group": "pseudogene",
    "locus_type": "pseudogene",
    "name": "keratin 18 pseudogene 9",
    "pseudogene.org": "PGOHUM00000243597",
    "refseq_accession": [
      "NT_007592"
    ],
    "status": "Approved",
    "symbol": "KRT18P9",
    "uuid": "128e36a7-ed26-4394-af63-81c57bdac417",
    "vega_id": "OTTHUMG00000184543"
  }, 
  ...
```
The following command returned the entire data set stored in the redis database. You might notice that each of the dictionaries might not be uniform, meaning that some keys are not present in all of the dictionaries. 

### Running _/data_ route with the _DELETE_ method 
You are also able to delete the entire data set from the Redis database using the following route: 
``` bash
curl -X DELETE "localhost:5000/data" 

# Example Output 
Deleted all data from Redis database 
```

You can double-check that the Redis database was cleaned by running the following: 
```bash 
curl -X GET "localhost:5000/data"

# Example Output 
[]
```
You should see an output with an empty list, confirming we indeed deleted the data set from the database. 

### Running _/genes_ route 
If you want to get a list of all the hgnc_id fields in the data set, run the following: 
```bash
curl "localhost:5000/genes" 

# Example Output 
[]
```
You might get an empty list since we recently deleted all of the key:value pairs in the Redis database. To return all the keys, we first have to use the [POST method](README.md#running-data-route-with-the-post-method). Then we can run the _genes_ route. 

``` bash 
curl -X POST "localhost:5000/data" 

# Output
Loaded the HGNC data to a Redis database 
```
```bash
curl "localhost:5000/genes" 

# Example Output 
[
  "HGNC:47916",
  "HGNC:39671",
  "HGNC:24325",
  "HGNC:30533",
  "HGNC:56881",
  "HGNC:46398",
  "HGNC:54509",
  "HGNC:36246",
  "HGNC:1339", 
...
```
This route returned a list of all the hgnc_id fields in the data set. 

### Running _/genes/'hgnc_id'_ route 
Another functionality of the application is returning the dictionary of a specific hgnc_id. 
This is available with the following route:
```bash
curl "localhost:5000/genes/<hgnc_id>"

# Example 
curl "localhost:5000/genes/HGNC:46398"

# Example Output 
{
  "agr": "HGNC:46398",
  "alias_name": "",
  "alias_symbol": "",
  "bioparadigms_slc": "",
  "ccds_id": "",
  "cd": "",
  "cosmic": "",
  "curator_notes": "",
  "date_approved_reserved": "2013-04-02",
  "date_modified": "2013-04-02",
  "date_name_changed": "",
  "date_symbol_changed": "",
  "ena": "",
  "ensembl_gene_id": "ENSG00000240723",
  "entrez_id": "106481027",
  "enzyme_id": "",
  "gencc": "",
  "gene_group": "",
  "gene_group_id": "",
  "gtrnadb": "",
  "hgnc_id": "HGNC:46398",
  "homeodb": "",
  "horde_id": "",
  "imgt": "",
  "iuphar": "",
  "lncipedia": "",
  "lncrnadb": "",
  "location": "4q31.1",
  "location_sortable": "04q31.1",
  "locus_group": "pseudogene",
  "locus_type": "pseudogene",
  "lsdb": "",
  "mamit-trnadb": "",
  "mane_select": "",
  "merops": "",
  "mgd_id": "",
  "mirbase": "",
  "name": "RNA, 7SL, cytoplasmic 382, pseudogene",
  "omim_id": "",
  "orphanet": "",
  "prev_name": "",
  "prev_symbol": "",
  "pseudogene.org": "",
  "pubmed_id": "",
  "refseq_accession": "NG_043943",
  "rgd_id": "",
  "rna_central_id": "",
  "snornabase": "",
  "status": "Approved",
  "symbol": "RN7SL382P",
  "ucsc_id": "uc062zrr.1",
  "uniprot_ids": "",
  "uuid": "7cb32997-0e2b-47ab-891a-04bed461ad7b",
  "vega_id": ""
}
```
As mentioned above, this route returned the dictionary of a specific hgnc_id. We can see that some key:value pairs are missing values, this is due to the fact that the data set is non-uniform or sparsely-populated. We can also see that some values have multiple values, this is being displayed as a whole string for a better visual aesthetic. 

### Running _/jobs_ route with the _POST_ method
The new _jobs_ route allows you to create a new job with a unique identifier using the POST method. The inputs should be a start date and an end date for the date approved field. This will submit a job that will look through all of the data set and perform analysis on the data that is within the specified range of dates. This analysis will be explained in later routes. 

To submit a job, please do the following: 
```bash 
curl localhost:5000/jobs -X POST -d '{"date_approved_start": "YYYY-MM-DD", "date_approved_end": "YYYY-MM-DD"}' -H "Content-Type: application/json" 

# Example 
curl localhost:5000/jobs -X POST -d '{"date_approved_start": "2023-01-01", "date_approved_end": "2023-04-05"}' -H "Content-Type: application/json" 

# Example Output
Job created: {'id': 'c4e73a9b-0878-482e-b31b-c39ba0ba1cb3', 'status': 'submitted', 'start': '2023-01-01', 'end': '2023-04-05'} 
``` 

Please make sure to take note of the 'id' field. This will be the unique identifier for that specific job. You will be able to retrieve the details of that job with the [_/jobs/'jobid'_ route](README.md#running-jobsjobid-route) that will be discussed later. 

Note that the route will not allow unproperly formatted data packets. The dates should be strings in double quotes in 'YYYY-MM-DD' format. It also allows 'YYYY-M-D' format since the [datetime](https://docs.python.org/3/library/datetime.html) module converts both formats to the same value. 

If you submit a wrong data packet you will get an error like this: 
```bash
# Unproperly formatted data packet 
curl localhost:5000/jobs -X POST -d '{"date_approved_start": "2023-01", "date_approved_end": "2023-04-05"}' -H "Content-Type: application/json" 

# Example Output
{
  "error": "Invalid date format. Dates must be strings in 'YYYY-MM-DD' format."
}
``` 

Also note that the end time has to be greater than the start time, if not you will get an error: 
```bash 
# end time less than start time
curl localhost:5000/jobs -X POST -d '{"date_approved_start": "2023-01-01", "date_approved_end": "2022-04-05"}' -H "Content-Type: application/json"

# Example Output
{
  "error": "date_approved_end must be the same as or after date_approved start."
}
```

### Running _/jobs_ route with the _GET_ method
You are able to retrieve all the job IDs using the following command: 
```bash
curl localhost:5000/jobs

# Example Output
[
  "f5a9854c-1182-4951-9597-9ec70d37260a",
  "5f95942b-7f40-4dd5-99a2-c3241104b711",
  "e245a3cf-9c1c-49e8-9177-a51e77eb96f2",
  "c7d5ad07-8f2f-4584-9c9d-5614b8ee5cc6",
  "a80c2970-3867-4ffe-bd78-9f774ee95302",
  "5c97a5f7-31e9-4192-89a3-5aecd99d9db6",
  "7741cc99-ae72-40e1-aaf7-bbe78d96322c",
  "479f92aa-a572-4256-8592-0d7ea7fd4344",
  "375cd384-e77e-401a-97f0-1d43b85e4734",
  "87b09efc-a75d-40ff-b0c5-c6deedfb3ab4",
  "f7f521f8-032d-492e-ac3b-82a7456507a1",
  "69a2ae8f-1eca-497a-9e63-5203047e00cf",
  "3cab6133-4f40-4e88-bb60-60ce4fe638c6",
  "4a12907a-fed4-429e-b8c7-dbc11d93ea78",
  "02239c82-8ed0-4e2a-87e8-4486985faee6",
  "1fc70b25-8c54-4074-a3e0-72ea07753bfd",
  "f6cce5db-8ffa-44f3-9735-547ff5e31bcf",
  "f86ef2ed-d4d3-4782-a525-d01b4aebf8f8"
]
```
It should output a list of all the job IDs, which were created using the [uuid](https://docs.python.org/3/library/uuid.html) module in Python's standard library. 

### Running _/jobs/'jobid'_ route 
You are able to check the status of any job you have submitted by running the following: 
```bash
curl localhost:5000/jobs/<jobid>

# Example 
curl localhost:5000/jobs/f86ef2ed-d4d3-4782-a525-d01b4aebf8f8 

# Example Output
{
  "end": "2023-01-31",
  "id": "f86ef2ed-d4d3-4782-a525-d01b4aebf8f8",
  "start": "2023-01-01",
  "status": "complete"
}
```
You should have received a dictionary with the start and end dates you inputted as well as the id and status of your job. You can try and queue a few jobs and check each job's status using this route. 

### Running _/results/'jobid'_ route
Once you have submitted your job and you will like to check out the results of your jobs, you are able to do so with the following route. The only identifier you need is your unique 'jobid'. 

```bash
curl localhost:5000/results/<jobid>

# Example 
curl localhost:5000/results/4ebefcb7-9c8f-4954-92e4-0ce5afab4ce4 

# Example Output
{
  "job": {
    "end": "2023-04-05",
    "id": "4ebefcb7-9c8f-4954-92e4-0ce5afab4ce4",
    "start": "1930-01-01",
    "status": "complete"
  },
  "result": {
    "RNA, Y": 4,
    "RNA, cluster": 119,
    "RNA, long non-coding": 5607,
    "RNA, micro": 1912,
    "RNA, misc": 29,
    "RNA, ribosomal": 60,
    "RNA, small nuclear": 51,
    "RNA, small nucleolar": 568,
    "RNA, transfer": 591,
    "RNA, vault": 4,
    "T cell receptor gene": 205,
    "T cell receptor pseudogene": 38,
    "complex locus constituent": 69,
    "endogenous retrovirus": 109,
    "fragile site": 116,
    "gene with protein product": 19283,
    "immunoglobulin gene": 230,
    "immunoglobulin pseudogene": 203,
    "pseudogene": 14050,
    "readthrough": 147,
    "region": 38,
    "unknown": 69,
    "virus integration site": 8
  }
}
```

The following route returned the results of your query in the form of a dictionary. You have your job details and the results section. In the results we can see that we have a count for all the different locus types that were present in all of the genes from the given start date to the end date. 

Note that if you input a wrong 'jobid' you will get the same message from the jobs route. 
```bash
{
  "error": "Job ID '4ebefcb7-9c8f-4954-92e4-0ce5afab4ce' not found."
}
```

## Running Test Scripts 
To run the test scripts you will have to go to the test folder inside the src folder to access these scripts. To do so please do the following: 
```bash
cd src/test/

pytest 

# Please do CTRL-C to exit the infinite loop for the hotqueue. This will let the pytest do its tests properly. I still have not figured out a way to do it differently. 

# Example Output
=================================================== test session starts ====================================================
platform linux -- Python 3.12.3, pytest-8.3.4, pluggy-1.5.0
rootdir: /home/ubuntu/coe332-hw-guarneros/homework08/src/test
plugins: mock-3.14.0
collecting 10 items                                                                                                        ^collected 24 items                                                                                                         

test_api.py ..........                                                                                               [ 41%]
test_jobs.py .............                                                                                           [ 95%]
test_worker.py .                                                                                                     [100%]

==================================================== 24 passed in 9.63s ====================================================
```
You have successfully ran the test scripts and all test scripts have passed. You are welcome to look into the test scripts and which cases were tested by looking into each test script in this folder. 

## Clean Up 
Don't forget to stop your running containers and remove them when you are done. All you need to do is: 

```bash 
docker compose down 

# Output
WARN[0000] /home/ubuntu/coe332-hw-guarneros/homework08/docker-compose.yml: `version` is obsolete 
[+] Running 4/4
 ✔ Container homework08-worker-1     Removed                                                                  10.2s 
 ✔ Container homework08-flask-app-1  Removed                                                                   0.4s 
 ✔ Container homework08-redis-db-1   Removed                                                                   0.4s 
 ✔ Network homework08_default        Removed                                                                   0.1s 
```

You can double check that you successfully exited and removed the running container by running ```docker ps -a```. You should see that all the containers for this project are gone. 

## Resources 
* Converting XLSX to JSON: https://www.geeksforgeeks.org/convert-excel-to-json-with-python/
* Matrix Conversion: https://www.geeksforgeeks.org/how-to-convert-pandas-dataframe-into-a-list/

* Logging Documentation: https://docs.python.org/3/howto/logging.html 
* Requests Library: https://pypi.org/project/requests/ 
* HGNC Data: https://www.genenames.org/download/archive/
* COE 332 Spring 2025 Docs: https://coe-332-sp25.readthedocs.io/en/latest/ 
* Table Syntax for README: https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-tables 
* _.keys()_ function: https://www.w3schools.com/python/ref_dictionary_items.asp 
* Error Codes: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status 
* _update()_ method: https://www.w3schools.com/python/ref_set_update.asp 
* _uuid_ module: https://docs.python.org/3/library/uuid.html 
* _datetime_ module: https://docs.python.org/3/library/datetime.html 
* _append()_ module: https://www.w3schools.com/python/ref_list_append.asp 
* Counter python module function: https://docs.python.org/3/library/collections.html#collections.Counter 

## AI Usage