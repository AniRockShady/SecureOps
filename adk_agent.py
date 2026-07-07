from dotenv import load_dotenv
import asyncio

load_dotenv()

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.genai import types

from orchestrator import run_secureops_pipeline
from config import MODEL_FLASH


def secureops_tool(raw_request: str) -> dict:
    """
    Submits an IT support request to the SecureOps pipeline. The request
    passes through security validation, classification, knowledge
    retrieval, and resolution or escalation.

    Args:
        raw_request: the IT support request or incident description,
        in the user's own words.

    Returns:
        A dictionary describing the outcome, including whether the
        request was rejected, auto-resolved, or escalated.
    """
    return run_secureops_pipeline(raw_request=raw_request)


secureops_agent = Agent(
    name="secureops_agent",
    model=MODEL_FLASH,
    instruction=(
        "You are the front door to the SecureOps ITSM system. When the user "
        "describes an IT problem or support request, call the secureops_tool "
        "with their request text. After receiving the result, summarize the "
        "outcome for the user in plain language: whether the request was "
        "rejected, resolved automatically with the given resolution, or "
        "escalated to a human with the given reason. Do not fabricate "
        "outcomes; only report what the tool actually returned."
    ),
    tools=[FunctionTool(func=secureops_tool)],
)

runner = InMemoryRunner(agent=secureops_agent, app_name="secureops_app")


async def run_through_adk(user_text: str):
    session = await runner.session_service.create_session(
        app_name="secureops_app", user_id="demo_user"
    )
    user_message = types.Content(role="user", parts=[types.Part(text=user_text)])

    async for event in runner.run_async(
        user_id="demo_user", session_id=session.id, new_message=user_message
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text)


if __name__ == "__main__":
    asyncio.run(run_through_adk("The shared printer on the third floor is offline and not printing."))
