import os
from anthropic import AnthropicVertex

LOCATION="europe-west1" # or "us-east5"
PROJECT_ID = os.environ.get("PROJECT_ID")

client = AnthropicVertex(region=LOCATION, project_id=PROJECT_ID)

import query

def get_message(query: str):
    message = client.messages.create(
      max_tokens=1024,
      messages=[
        {
          "role": "user",
          "content": query.message,
        }
      ],
      model="claude-3-5-sonnet@20240620",
    )
    return message

print(get_message(query.message))
