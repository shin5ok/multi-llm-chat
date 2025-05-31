import io, os
import re
from pprint import pprint as pp
from typing import Dict, Any, Optional

from base64 import b64encode
from operator import itemgetter

from google.cloud import storage
from PIL import Image
import chainlit as cl
from chainlit.input_widget import Select, Slider
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain.schema.runnable.config import RunnableConfig
from langchain_core.messages import HumanMessage

import models_config

# 環境変数
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "default-bucket")  # デフォルト値を設定

# 設定
models: Dict[str, Dict[str, Any]] = models_config.models

@cl.set_chat_profiles
async def chat_profile(user: Optional[cl.User] = None) -> list[cl.ChatProfile]:
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
async def main():
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
async def setup_runnable(settings):
    profile = cl.user_session.get("chat_profile")
    if not profile or profile not in models:
        # プロファイルが見つからない場合は、Claudeをデフォルトに使用
        profile = "Claude-4-sonnet"
        cl.user_session.set("chat_profile", profile)

    cl.user_session.set(
        "memory", ConversationBufferMemory(return_messages=True)
    )

    class_name = models[profile]["class"]
    region = models[profile]["region"]

    llm = class_name(
        model_name=models[profile]["model"],
        project=PROJECT_ID,
        location=region,
        temperature=settings["TEMPARATURE"],
        max_output_tokens=settings["MAX_TOKEN_SIZE"],
    )

    memory = cl.user_session.get("memory")
    if not memory:
        raise ValueError("Memory not initialized")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are the smartest chat bot"),
            MessagesPlaceholder(variable_name="history"),
            MessagesPlaceholder(variable_name="human_message")
        ]
    )

    chain = (
        RunnablePassthrough.assign(
            history=RunnableLambda(memory.load_memory_variables) | itemgetter("history")
        ) | prompt | llm | StrOutputParser()
    )
    cl.user_session.set("chain", chain)

def make_image_base64encoding(image: Image.Image, format: str) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return b64encode(buffer.getvalue()).decode("utf-8")

def upload_image_to_gcs(bucket_name: str, source_file_name: str) -> str:
    import uuid
    destination_blob_name = f"{uuid.uuid4()}-{os.path.basename(source_file_name)}"
    print(f"Uploading {source_file_name} to {destination_blob_name}")

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)
    return f"gs://{bucket_name}/{destination_blob_name}"

@cl.on_message
async def on_message(message: cl.Message):
    memory = cl.user_session.get("memory")
    chain = cl.user_session.get("chain")
    profile = cl.user_session.get("chat_profile")

    if not memory or not chain or not profile:
        raise ValueError("Session not properly initialized")

    content = []
    pp(message.elements)

    regex = re.compile("gemini", re.IGNORECASE)
    for file in message.elements:
        if file.path and file.mime and "image/" in file.mime:
            print("model_name", profile)
            if not re.search(regex, str(profile)):
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

    res = cl.Message(content="", author=f'Chatbot: {profile}')

    async for chunk in chain.astream(
        runnable_message_data,
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await res.stream_token(chunk)

    await res.send()
    memory.chat_memory.add_user_message(message.content)
    memory.chat_memory.add_ai_message(res.content)
