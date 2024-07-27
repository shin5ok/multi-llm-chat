import os
import chainlit as cl
from anthropic import AnthropicVertex

LOCATION="europe-west1" # or "us-east5"
PROJECT_ID = os.environ.get("PROJECT_ID")

client = AnthropicVertex(region=LOCATION, project_id=PROJECT_ID)

def get_message(query: str):
    message = client.messages.create(
      max_tokens=1024,
      messages=[
        {
          "role": "user",
          "content": query,
        }
      ],
      model="claude-3-5-sonnet@20240620",
    )
    print(dir(message))
    print(message.content)
    return message.content[0].text



@cl.step(type="tool")
async def tool():
    # # Fake tool
    # await cl.sleep(2)
    # return "Response from the tool!"
    return get_message("こんにちわ")





@cl.on_message  # this function will be called every time a user inputs a message in the UI
async def main(message: cl.Message):
    """
    This function is called every time a user inputs a message in the UI.
    It sends back an intermediate response from the tool, followed by the final answer.

    Args:
        message: The user's message.

    Returns:
        None.
    """

    final_answer = await cl.Message(content="").send()

    # Call the tool
    final_answer.content = await tool()

    await final_answer.update()
    