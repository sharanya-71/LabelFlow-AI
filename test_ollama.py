from openai import OpenAI

# Connect to local Ollama server
client = OpenAI(
    base_url="http://localhost:11434/v1/",
    api_key="ollama"
)

try:
    response = client.chat.completions.create(
        model="qwen2.5:7b",
        messages=[
            {
                "role": "user",
                "content": "Explain UDI in medical device labeling in 3 sentences."
            }
        ],
        temperature=0.2
    )

    print("\nQWEN RESPONSE:")
    print(response.choices[0].message.content)

except Exception as e:
    print("Error:", e)