
.PHONY: deploy
deploy:
	gcloud run deploy chatapp \
	--source=. \
	--region=asia-northeast1 \
	--cpu=2 --memory=1G \
	--min-instances=1
