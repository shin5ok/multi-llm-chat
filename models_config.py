from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from langchain_google_vertexai import ChatVertexAI

models = {
    "Gemini-2.5-Flash": {
        "model": "gemini-2.5-flash-preview-04-17",
        "description": "Gemini 2.5 Flash (Preview)",
        "icon": "https://picsum.photos/301",
        "class": ChatVertexAI,
        "region": "us-central1",
    },
    "Gemini-2.5-Pro": {
        "model": "gemini-2.5-pro-preview-03-25",
        "description": "Gemini 2.5 Pro (Preview)",
        "icon": "https://picsum.photos/300",
        "class": ChatVertexAI,
        "region": "us-central1",
    },
    "Claude-3.7-sonnet-v2": {
        "model": "claude-3-5-sonnet-v2@20241022",
        "description": "Claude 3.5 Sonnet",
        "icon": "https://picsum.photos/390",
        "class": ChatAnthropicVertex,
        "region": "us-east5",
    },
}
