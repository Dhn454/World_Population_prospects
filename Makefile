all: 
	docker compose down 
	curl -o ./data/WPP2024_Demographic_Indicators_Medium.csv.gz "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_Demographic_Indicators_Medium.csv.gz"
	docker compose up --build -d 

down: 
	docker compose down 

redis-up:
	docker compose up --build -d redis-db 

api-up: 
	curl -o ./data/WPP2024_Demographic_Indicators_Medium.csv.gz "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_Demographic_Indicators_Medium.csv.gz"
	docker compose up --build -d flask-app 

worker-up: 
	docker compose up --build -d worker 

