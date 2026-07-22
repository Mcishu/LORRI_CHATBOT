import os
import re
import xml.etree.ElementTree as ET
import requests

YOUR_NAME = "Ishika Singh" 
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"

SYSTEM_INSTRUCTION = (
    f"You are Lorri, a smart, friendly, and energetic AI chatbot created by {YOUR_NAME}. "
    f"If someone asks who created, founded, or built you, state that {YOUR_NAME} is "
    "your founder and creator. You are powered by an open-source AI model hosted by Groq. "
    "Stay helpful, clear, and conversational. Use web search when fresh or "
    "time-sensitive information is supplied to you, and cite those sources clearly."
)

NEWS_KEYWORDS = re.compile(
    r"\b(news|headlines?|current events?|latest|today|breaking|happening now|"
    r"what(?:'s| is) happening|update(?:s)? on)\b",
    re.IGNORECASE,
)


def wants_live_news(text):
    return text.lower().startswith("/news") or bool(NEWS_KEYWORDS.search(text))


def get_live_news(query):
    """Fetch fresh, linkable headlines without a separate news API key."""
    if query.lower().startswith("/news"):
        query = query[5:].strip() or "top stories"

    response = requests.get(
        GOOGLE_NEWS_RSS_URL,
        params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
        timeout=10,
    )
    response.raise_for_status()

    root = ET.fromstring(response.content)
    items = root.findall("./channel/item")[:5]
    if not items:
        return "No current headlines were returned for that search."

    return "\n".join(
        f"- {item.findtext('title', 'Untitled headline')} — "
        f"{item.findtext('source', 'Unknown source')} "
        f"({item.findtext('pubDate', '')})\n  {item.findtext('link', '')}"
        for item in items
    )


api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise SystemExit(
        "GROQ_API_KEY is not set. Add your GroqCloud API key, then run:\n"
        'export GROQ_API_KEY="your_groq_api_key_here"\n'
        "python3 chatbot.py"
    )

messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
print(f"Bot (Lorri): Hey there! I'm Lorri, created by {YOUR_NAME}! Type 'quit' to exit.\n")

while True:
    user_input = input("You: ").strip()

    if user_input.lower() == "quit":
        print(f"\nBot (Lorri): Catch you on the flip side! Keep building cool stuff, {YOUR_NAME}!")
        break

    if not user_input:
        continue

    messages.append({"role": "user", "content": user_input})
    request_messages = messages

    if wants_live_news(user_input):
        try:
            live_news = get_live_news(user_input)
            request_messages = messages + [{
                "role": "system",
                "content": "LIVE NEWS CONTEXT (fetched just now):\n" + live_news,
            }]
        except (requests.RequestException, ET.ParseError):
            request_messages = messages + [{
                "role": "system",
                "content": "Live news is unavailable. Be transparent that you cannot verify current events right now.",
            }]

    try:
        response = requests.post(
            GROQ_CHAT_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": request_messages,
                "temperature": 0.7,
            },
            timeout=120,
        )
        response.raise_for_status()

        reply = response.json()["choices"][0]["message"]["content"]
        print(f"\nBot (Lorri): {reply}\n")
        messages.append({"role": "assistant", "content": reply})

    except requests.RequestException as e:
        error_detail = ""
        if e.response is not None:
            error_detail = f"\n{e.response.text}"
        print(f"\nBot (Lorri): Error contacting Groq: {e}{error_detail}\n")
    except (KeyError, IndexError, TypeError, ValueError) as e:
        print(f"\nBot (Lorri): Error reading Groq's response: {e}\n")
