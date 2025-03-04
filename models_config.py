
from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from langchain_google_vertexai import ChatVertexAI

models = {
    "Claude-3.7-sonnet": {
        "model": "claude-3-7-sonnet@20250219",
        "description": "Claude 3.5 Sonnet",
        "icon": "https://picsum.photos/390",
        "class": ChatAnthropicVertex,
    },
    "Gemini-1.5-Flash 002": {
        "model":"gemini-1.5-flash-002",
        "description": "Gemini 1.5 Flash 002",
        "icon": "https://picsum.photos/303",
        "class": ChatVertexAI,
    },
    "Gemini-1.5-Flash 001": {
        "model":"gemini-1.5-flash-001 001",
        "description": "Gemini 1.5 Flash",
        "icon": "https://picsum.photos/300",
        "class": ChatVertexAI,
    },
}
