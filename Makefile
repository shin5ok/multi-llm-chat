BUCKET_NAME?=$(PROJECT_ID)
SERVICE_NAME := multi-llm-chat

.PHONY: deploy
deploy:
	gcloud run deploy $(SERVICE_NAME) \
	--source=. \
	--region=asia-northeast1 \
	--cpu=1 --memory=1 \
	--cpu-boost \
	--session-affinity \
	--ingress=internal-and-cloud-load-balancing \
	--set-env-vars=BUCKET_NAME=$(BUCKET_NAME) \
	--min-instances=1

