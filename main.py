import io
import os
from pprint import pprint as pp

from base64 import b64encode
from operator import itemgetter

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
LOCATION = "europe-west1"

default_model = "Gemini-1.5-Flash"

models = {
    "Gemini-1.5-Flash": {
        "model":"gemini-1.5-flash-001",
        "description": "Gemini 1.5 Flash",
        "icon": "https://picsum.photos/300",
    },
    "Claude-3.5-sonnet": {
        "model": "claude-3-5-sonnet@20240620",
        "description": "Claude 3.5 Sonnet",
        "icon": "https://picsum.photos/390",
    },
}

@cl.set_chat_profiles
async def chat_profile():
    profiles = []
    for key, value in models.items():
        profiles.append(
            cl.ChatProfile(
                name=key,
                markdown_description=value["description"],
                icon=value["icon"],
            )
        )
    pp(profiles)
    return profiles

@cl.on_chat_start
async def main():
    settings = await cl.ChatSettings(
        [
            Select(
                id="Model",
                label="Vertex AI - Model",
                values= models.keys(),
                initial_index=0,
            ),
            Slider(
                id="MAX_TOKEN_SIZE",
                label="Max Token Size",
                initial=1024,
                min=1024,
                max=0,
                step=512,
            ),
            Slider(
                id="Temperature",
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

    cl.user_session.set(
        "memory", ConversationBufferMemory(return_messages=True)
    )

    memory = cl.user_session.get("memory")

    chat_profile = cl.user_session.get("chat_profile")

    pp(settings)
    pp(chat_profile)

    if settings["Model"] != default_model and chat_profile != default_model:

        llm = ChatVertexAI(
            model_name=models["Gemini-1.5-Flash"]["model"],
            project=PROJECT_ID,
            location=LOCATION,
            temperature=settings["Temperature"],
            max_output_tokens=settings["MAX_TOKEN_SIZE"],
        )
    else:

        llm = ChatAnthropicVertex(
            model_name=models["Claude-3.5-sonnet"]["model"],
            project=PROJECT_ID,
            location=LOCATION,
            temperature=settings["Temperature"],
            max_output_tokens=settings["MAX_TOKEN_SIZE"],
        )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are the smartest chat bot"),
            MessagesPlaceholder(variable_name="history"),
            MessagesPlaceholder(variable_name="human_message")
        ]
    )

    runnable = (
        RunnablePassthrough.assign(
            history=RunnableLambda(memory.load_memory_variables) | itemgetter("history")
        ) | prompt | llm | StrOutputParser()
    )
    cl.user_session.set("runnable", runnable)

def encode_image_to_base64(image, image_format):
    buffer = io.BytesIO()
    image.save(buffer, format=image_format)
    return b64encode(buffer.getvalue()).decode("utf-8")

@cl.on_message
async def on_message(message: cl.Message):
    memory = cl.user_session.get("memory")
    runnable = cl.user_session.get("runnable")

    content = []

    for file in (message.elements or []):
        if file.path and "image" in file.mime:
            image = Image.open(file.path)
            bs64 = encode_image_to_base64(
                image,
                file.mime.split('/')[-1].upper()  # Pass the image format
            )
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": file.mime,
                    "data": bs64
                }
            })

    content_text = {"type": "text", "text": message.content}
    content.append(content_text)
    runnable_message_data = {"human_message": [HumanMessage(content=content)]}

    res = cl.Message(content="", author=f'Chatbot: Claude-3.5-sonnet')

    async for chunk in runnable.astream(
        runnable_message_data,
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await res.stream_token(chunk)

    await res.send()
    memory.chat_memory.add_user_message(message.content)
    memory.chat_memory.add_ai_message(res.content)
