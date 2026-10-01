from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()
model = "claude-sonnet-5"


def add_user_message(messages, text):
    messages.append({"role": "user", "content": text})


def add_assistant_message(messages, text):
    messages.append({"role": "assistant", "content": text})


def chat(messages):
    message = client.messages.create(
        model=model,
        max_tokens=1000,
        messages=messages,
    )
    # 블록 배열에서 text 블록만 골라서 합치기
    return "".join(
        block.text for block in message.content if block.type == "text"
    )


messages = []

add_user_message(messages, "AGV가 좁은 통로에서 경로 계획에 실패해. 원인 후보를 3가지만 간단히 알려줘.")
answer = chat(messages)
print("[1턴]\n", answer)

add_assistant_message(messages, answer)
add_user_message(messages, "첫 번째 원인을 Nav2 파라미터로 어떻게 확인하는지 알려줘.")
print("\n[2턴]\n", chat(messages))

print(f"\n메시지 개수: {len(messages)}")