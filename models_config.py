from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from langchain_google_vertexai import ChatVertexAI

models = {
    "Claude-4-sonnet": {
        "model": "claude-sonnet-4@20250514",
        "description": "Claude Sonnet 4",
        "icon": "https://picsum.photos/390",
        "class": ChatAnthropicVertex,
        "region": "us-east5",
    },
    "Gemini-2.5-Flash": {
        "model": "gemini-2.5-flash-preview-05-20",
        "description": "Gemini 2.5 Flash (Preview)",
        "icon": "https://picsum.photos/301",
        "class": ChatVertexAI,
        "region": "us-central1",
    },
    "Gemini-2.5-Pro": {
        "model": "gemini-2.5-pro-preview-05-06",
        "description": "Gemini 2.5 Pro (Preview)",
        "icon": "https://picsum.photos/300",
        "class": ChatVertexAI,
        "region": "us-central1",
    },
}
