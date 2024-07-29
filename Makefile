BUCKET_NAME:=$(BUCKET_NAME)

.PHONY: deploy
deploy:
	gcloud run deploy chatapp \
	--source=. \
	--region=asia-northeast1 \
	--cpu=2 --memory=1G \
	--set-env-vars=BUCKET_NAME=$(BUCKET_NAME) \
	--min-instances=1
