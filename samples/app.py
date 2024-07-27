import io
import os

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

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = "europe-west1"

model = "claude-3-5-sonnet@20240620"

@cl.on_chat_start
async def main():
    settings = await cl.ChatSettings(
        [
            Select(
                id="Model",
                label="Vertex AI - Model",
                values=[model],
                initial_index=0,
            ),
            Slider(
                id="Temperature",
                label="Temperature",
                initial=0.3,
                min=0,
                max=1,
                step=0.1,
            ),
            Slider(
                id="MAX_TOKEN_SIZE",
                label="Max Token Size",
                initial=1024,
                min=256,
                max=8192,
                step=256,
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

    llm = ChatAnthropicVertex(
        model_name=model,
        project=PROJECT_ID,
        location=LOCATION,
        temperature=settings["Temperature"],
        max_output_tokens=settings["MAX_TOKEN_SIZE"],
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful chatbot"),
            MessagesPlaceholder(variable_name="history"),
            MessagesPlaceholder(variable_name="human_message")
        ]
    )

    runnable = (
        RunnablePassthrough.assign(
            history=RunnableLambda(memory.load_memory_variables) | itemgetter("history")
        )
        | prompt
        | llm
        | StrOutputParser()
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
