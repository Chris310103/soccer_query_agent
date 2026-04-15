from google import genai
from google.genai import types

from soccer_agent.core.config import get_gemini_api_key


class LLMClient:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class Gemini_LLM_Client(LLMClient):
    def __init__(self, model: str = "gemini-3-flash-preview", api_key: str | None = None):
        self.model = model
        final_key = api_key or get_gemini_api_key()

        if not final_key:
            raise ValueError(
                "No Gemini API key found. Set GEMINI_API_KEY in your environment or .env file."
            )

        self.client = genai.Client(api_key=final_key)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.0,
            ),
        )
        text = response.text or ""
        if not text.strip():
            raise ValueError("Gemini returned empty text output.")
        return text
    
class BadLLMClient(LLMClient):
    """
    Deliberately broken LLM client for testing fallback behavior.
    Always returns invalid non-JSON text.
    """
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return "this is not json"


