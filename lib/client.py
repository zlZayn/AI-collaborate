from openai import OpenAI


class LLMClient:
    def __init__(self, api_key, base_url):
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def chat(self, messages, model, temperature=None):
        kwargs = {"model": model, "messages": messages}
        if temperature is not None:
            kwargs["temperature"] = temperature
        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def stream_to_file(self, messages, model, path, temperature=None):
        kwargs = {"model": model, "messages": messages, "stream": True}
        if temperature is not None:
            kwargs["temperature"] = temperature
        stream = self._client.chat.completions.create(**kwargs)
        with open(path, "w", encoding="utf-8") as f:
            for chunk in stream:
                if (
                    chunk.choices
                    and chunk.choices[0].delta
                    and chunk.choices[0].delta.content
                ):
                    f.write(chunk.choices[0].delta.content)
                    f.flush()

    def stream_print(self, messages, model, temperature=None):
        kwargs = {"model": model, "messages": messages, "stream": True}
        if temperature is not None:
            kwargs["temperature"] = temperature
        stream = self._client.chat.completions.create(**kwargs)
        for chunk in stream:
            if (
                chunk.choices
                and chunk.choices[0].delta
                and chunk.choices[0].delta.content
            ):
                print(chunk.choices[0].delta.content, end="", flush=True)
        print()
