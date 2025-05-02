# Kubernetes settings
K8S_TEST_DIR=kubernetes/test
K8S_PROD_DIR=kubernetes/prod
KUBECTL=kubectl

.PHONY: k k-up k-down k-status \
        k-prod k-prod-up k-prod-down k-prod-status \
        docker-up docker-down docker-api docker-worker docker-redis

# --- Test environment (default) ---
k: k-up k-status

k-up:
	@echo "Applying Kubernetes test configs..."
	$(KUBECTL) apply -f $(K8S_TEST_DIR)

k-down:
	@echo "Deleting Kubernetes test configs..."
	$(KUBECTL) delete -f $(K8S_TEST_DIR)

k-status:
	@echo "Checking Kubernetes test pod and service status..."
	$(KUBECTL) get pods
	$(KUBECTL) get services
	$(KUBECTL) get ingress

# --- Production environment ---
k-prod: k-prod-up k-prod-status

k-prod-up:
	@echo "Applying Kubernetes production configs..."
	$(KUBECTL) apply -f $(K8S_PROD_DIR)

k-prod-down:
	@echo "Deleting Kubernetes production configs..."
	$(KUBECTL) delete -f $(K8S_PROD_DIR)

k-prod-status:
	@echo "Checking Kubernetes production pod and service status..."
	$(KUBECTL) get pods
	$(KUBECTL) get services
	$(KUBECTL) get ingress

# --- Docker environment ---
docker-up:
	docker compose down
	curl -o ./data/WPP2024_Demographic_Indicators_Medium.csv.gz "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_Demographic_Indicators_Medium.csv.gz"
	docker compose up --build -d

docker-down:
	docker compose down

docker-api:
	docker compose down flask-app
	curl -o ./data/WPP2024_Demographic_Indicators_Medium.csv.gz "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_Demographic_Indicators_Medium.csv.gz"
	docker compose up --build -d flask-app

docker-worker:
	docker compose down worker
	docker compose up --build -d worker

docker-redis:
	docker compose down redis-db
	docker compose up --build -d redis-db
