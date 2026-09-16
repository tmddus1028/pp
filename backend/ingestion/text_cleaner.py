import re
import unicodedata


def clean_text(text: str) -> str:
    """Normalize before assigning offsets; never alter text after evidence is created."""
    text = unicodedata.normalize("NFKC", text).replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00ad", "")
    text = re.sub(r"[\t\u00a0 ]+", " ", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()
