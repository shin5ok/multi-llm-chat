import io, os
import re
from pprint import pprint as pp
from typing import Any, Dict, List, Optional, Union

from base64 import b64encode
from operator import itemgetter

from google.cloud import storage
from PIL import Image
import chainlit as cl
from chainlit.input_widget import Select, Slider
from chainlit.types import ChatProfile
from chainlit.user import User
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain.schema.runnable.config import RunnableConfig

import models_config

# 環境変数
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
LOCATION = os.environ.get("LOCATION", "europe-west1")

# 設定
models = models_config.models

class ChainlitChatMessageHistory(BaseChatMessageHistory):
    def __init__(self) -> None:
        self.messages: List[BaseMessage] = []

    def add_message(self, message: BaseMessage) -> None:
        self.messages.append(message)

    def add_user_message(self, message: Union[HumanMessage, str]) -> None:
        if isinstance(message, str):
            self.add_message(HumanMessage(content=message))
        else:
            self.add_message(message)

    def add_ai_message(self, message: Union[AIMessage, str]) -> None:
        if isinstance(message, str):
            self.add_message(AIMessage(content=message))
        else:
            self.add_message(message)

    def clear(self) -> None:
        self.messages = []

@cl.set_chat_profiles
async def chat_profile(user: Optional[User] = None) -> List[ChatProfile]:
    profiles = []
    for profile in models:
        profiles.append(
            cl.ChatProfile(
                name=profile,
                markdown_description=models[profile]["description"],
                icon=models[profile]["icon"],
            )
        )
    return profiles

@cl.on_chat_start
async def main() -> None:
    settings = await cl.ChatSettings(
        [
            Slider(
                id="MAX_TOKEN_SIZE",
                label="Max token size",
                initial=4096,
                min=1024,
                max=8192,
                step=512,
            ),
            Slider(
                id="TEMPARATURE",
                label="Temperature",
                initial=0.6,
                min=0.0,
                max=1.0,
                step=0.1,
            ),
        ]
    ).send()
    await setup_runnable(settings)

@cl.on_settings_update
async def setup_runnable(settings: Dict[str, Any]) -> None:
    profile = cl.user_session.get("chat_profile")
    if not profile:
        return

    memory = ChainlitChatMessageHistory()
    cl.user_session.set("memory", memory)

    class_name = models[profile]["class"]

    # モデルの初期化パラメータを設定
    model_params = {
        "model_name": models[profile]["model"],
        "project": PROJECT_ID,
        "location": LOCATION,
        "temperature": settings["TEMPARATURE"],
        "max_output_tokens": settings["MAX_TOKEN_SIZE"],
    }

    # ChatAnthropicVertexの場合は追加のパラメータを設定
    if class_name.__name__ == "ChatAnthropicVertex":
        model_params.update({
            "region": LOCATION,
            "project_id": PROJECT_ID,
        })

    llm = class_name(**model_params)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are the smartest chat bot"),
            MessagesPlaceholder(variable_name="history"),
            MessagesPlaceholder(variable_name="human_message")
        ]
    )

    chain = (
        RunnablePassthrough.assign(
            history=lambda x: memory.messages
        ) | prompt | llm | StrOutputParser()
    )
    cl.user_session.set("chain", chain)

def make_image_base64encoding(image, format):
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return b64encode(buffer.getvalue()).decode("utf-8")

def upload_image_to_gcs(bucket_name, source_file_name):

    import uuid
    destination_blob_name = f"{uuid.uuid4()}-{os.path.basename(source_file_name)}"
    print(f"Uploading {source_file_name} to {destination_blob_name}")

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)
    return f"gs://{bucket_name}/{destination_blob_name}"

@cl.on_message
async def on_message(message: cl.Message) -> None:
    memory = cl.user_session.get("memory")
    chain = cl.user_session.get("chain")
    if not memory or not chain:
        return

    content = []

    profile = cl.user_session.get("chat_profile")
    if not profile:
        return

    pp(message.elements)

    regex = re.compile("gemini", re.IGNORECASE)
    for file in message.elements:
        if file.path and file.mime and "image/" in file.mime:
            print("model_name", profile)
            if not re.search(regex,profile):
                image = Image.open(file.path)
                encoded = make_image_base64encoding(
                    image,
                    file.mime.split('/')[-1].upper()
                )
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": file.mime,
                        "data": encoded,
                    }
                })
            else:
                destination_path = upload_image_to_gcs(BUCKET_NAME, file.path)
                media_message = {
                    "type": "image_url",
                    "image_url": {
                        "url": destination_path,
                    }
                }
                pp(media_message)
                content.append(media_message)

    content_text = {"type": "text", "text": message.content}
    content.append(content_text)
    runnable_message_data = {"human_message": [HumanMessage(content=content)]}

    res = cl.Message(content="", author=f'Chatbot: Claude-3.5-sonnet')

    async for chunk in chain.astream(
        runnable_message_data,
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await res.stream_token(chunk)

    await res.send()
    memory.add_user_message(message.content)
    memory.add_ai_message(res.content)
