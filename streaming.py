import os
from anthropic import AnthropicVertex

PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION="europe-west1" # or "us-east5"

client = AnthropicVertex(region=LOCATION, project_id=PROJECT_ID)

import query
with client.messages.stream(
  max_tokens=1024,
  messages=[
    {
      "role": "user",
      "content": query.message,
    }
  ],
  model="claude-3-5-sonnet@20240620",
) as stream:
  for text in stream.text_stream:
    print(text)
