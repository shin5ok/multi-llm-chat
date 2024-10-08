import io
import os
from pprint import pprint as pp

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
from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from langchain_google_vertexai import ChatVertexAI

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
LOCATION = os.environ.get("LOCATION", "europe-west1")

# 設定
default_model = "Gemini-1.5-Flash"
models = {
    "Claude-3.5-sonnet": {
        "model": "claude-3-5-sonnet@20240620",
        "description": "Claude 3.5 Sonnet",
        "icon": "https://picsum.photos/390",
        "class": ChatAnthropicVertex,
    },
    "Gemini-1.5-Flash 002": {
        "model":"gemini-1.5-flash-002",
        "description": "Gemini 1.5 Flash",
        "icon": "https://picsum.photos/303",
        "class": ChatVertexAI,
    },
    "Gemini-1.5-Flash 001": {
        "model":"gemini-1.5-flash-001",
        "description": "Gemini 1.5 Flash",
        "icon": "https://picsum.photos/300",
        "class": ChatVertexAI,
    },
}

@cl.set_chat_profiles
async def chat_profile():
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
                min=0,
                max=1,
                step=0.1,
            ),
        ]
    ).send()
    await setup_runnable(settings)

@cl.on_settings_update
async def setup_runnable(settings):

    profile = cl.user_session.get("chat_profile")

    cl.user_session.set(
        "memory", ConversationBufferMemory(return_messages=True)
    )

    class_name = models[profile]["class"]

    llm = class_name(
        model_name=models[profile]["model"],
        project=PROJECT_ID,
        location=LOCATION,
        temperature=settings["TEMPARATURE"],
        max_output_tokens=settings["MAX_TOKEN_SIZE"],
    )

    memory = cl.user_session.get("memory")
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

def make_image_base64encoding(image, format):
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return b64encode(buffer.getvalue()).decode("utf-8")

def upload_image_to_gcs(bucket_name, source_file_name):

    import uuid
    destination_blob_name = f"{uuid.uuid4()}-{os.path.basename(source_file_name)}"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)
    return f"gs://{bucket_name}/{destination_blob_name}"

@cl.on_message
async def on_message(message: cl.Message):
    memory = cl.user_session.get("memory")
    chain = cl.user_session.get("chain")

    content = []

    profile = cl.user_session.get("chat_profile")

    for file in message.elements:
        if file.path and "image/" in file.mime:
            print("model_name", profile)
            if profile != "Gemini-1.5-Flash":
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
    memory.chat_memory.add_user_message(message.content)
    memory.chat_memory.add_ai_message(res.content)
