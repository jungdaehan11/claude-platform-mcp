from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()
model = "claude-sonnet-5"


def chat(messages, system=None, effort=None):
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
    }
    if system:
        params["system"] = system
    if effort:
        params["output_config"] = {"effort": effort}

    message = client.messages.create(**params)
    return "".join(b.text for b in message.content if b.type == "text")


SYSTEM = "AGV 로그 한 줄을 CRITICAL / WARNING / INFO 중 하나로 분류한다. 그 단어 하나만 출력할 것."
LOG = "10:05 agv-03 localization lost near zone C, pose covariance spiked"

for effort in ["low", "high"]:
    print(f"\n=== effort {effort} ===")
    for i in range(2):
        messages = [{"role": "user", "content": LOG}]
        print(f"  {i+1}회차: {chat(messages, system=SYSTEM, effort=effort)}")