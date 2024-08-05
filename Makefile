BUCKET_NAME?=$(PROJECT_ID)

.PHONY: deploy
deploy:
	gcloud run deploy chatapp \
	--source=. \
	--region=asia-northeast1 \
	--cpu=1 --memory=1G \
	--ingress=internal-and-cloud-load-balancing \
	--set-env-vars=BUCKET_NAME=$(BUCKET_NAME) \
	--min-instances=1
