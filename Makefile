all: 
	docker compose down 
	docker compose up --build -d 

down: 
	docker compose down 

redis-up:
	docker compose up --build -d redis-db 

api-up: 
	docker compose up --build -d flask-app 

worker-up: 
	docker compose up --build -d worker 

