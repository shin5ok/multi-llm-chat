
.PHONY: deploy
deploy:
	gcloud run deploy chatapp --source=. --region=asia-northeast1 --allow-unauthenticated \
	--cpu=2 --memory=2G
