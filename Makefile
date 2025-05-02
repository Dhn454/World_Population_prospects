K8S_DIR=kubernetes/test
KUBECTL=kubectl

.PHONY: all k k-up k-down k-status \
        docker-up docker-down docker-api docker-worker docker-redis \
        download-data clean-data

# -------- Default Target --------
all: k

# -------- Kubernetes Targets --------

k: k-up k-status

k-up:
	@echo "Applying Kubernetes manifests..."
	$(KUBECTL) apply -f $(K8S_DIR)

k-down:
	@echo "Deleting Kubernetes resources..."
	$(KUBECTL) delete -f $(K8S_DIR)

k-status:
	@echo "Showing Kubernetes status..."
	$(KUBECTL) get pods
	$(KUBECTL) get services
	$(KUBECTL) get ingress

# -------- Docker Targets --------

docker-up: download-data
	docker compose up --build -d

docker-down:
	docker compose down

docker-api: download-data
	docker compose down flask-app || true
	docker compose up --build -d flask-app

docker-worker:
	docker compose down worker || true
	docker compose up --build -d worker

docker-redis:
	docker compose down redis-db || true
	docker compose up --build -d redis-db

# -------- Data Management --------

download-data:
	curl -o ./data/WPP2024_Demographic_Indicators_Medium.csv.gz "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_Demographic_Indicators_Medium.csv.gz"

clean-data:
	rm -f ./data/WPP2024_Demographic_Indicators_Medium.csv.gz

