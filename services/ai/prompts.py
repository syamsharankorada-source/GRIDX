from pathlib import Path
from django.conf import settings

def get_system_prompt() -> str:
    prompt_file = Path(settings.BASE_DIR) / "prompts" / "system_prompt.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    return "You are GRIDX AI, a multilingual roadside, emergency SOS, safe-stay hotel finder, and mechanic assistant."

SYSTEM_PROMPT = get_system_prompt()
