import abc
from typing import override
import requests
from codebase.config import CONFIG


class ModelProvider(abc.ABC):

    @abc.abstractmethod
    def encode(self, text: str) -> list[float]:
        pass

    @abc.abstractmethod
    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        pass


class SentenceTransformerProvider(ModelProvider):

    def __init__(self, model_name_or_path: str):
        from sentence_transformers import SentenceTransformer

        self.model: SentenceTransformer = SentenceTransformer(model_name_or_path)

    @override
    def encode(self, text: str) -> list[float]:
        result = self.model.encode(text, convert_to_numpy=True, convert_to_tensor=False)
        return result.tolist()

    @override
    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        results = self.model.encode(
            texts, convert_to_numpy=True, convert_to_tensor=False
        )
        return [result.tolist() for result in results]


class OpenAICompatibleProvider(ModelProvider):

    __HEADERS = {"Content-Type": "application/json"}

    def __init__(
        self,
        model_name: str,
        url: str,
        endpoint: str = "/v1/embeddings",
        http_proxy: str | None = None,
        https_proxy: str | None = None,
    ):
        self.model_name: str = model_name
        self.url: str = url
        self.endpoint: str = endpoint
        self.proxies: dict[str, str | None] = {
            "http": http_proxy,
            "https": https_proxy,
        }

    @override
    def encode(self, text: str) -> list[float]:
        payload = {
            "input": text,
            "model": self.model_name,
            "encoding_format": "float",
        }
        try:
            # Send the POST request
            # Use the 'json' parameter for the payload, which automatically
            # serializes the dict to JSON and sets the Content-Type header.
            response = requests.post(
                self.url + self.endpoint,
                headers=self.__HEADERS,
                json=payload,
                timeout=10,
                proxies=self.proxies,
            )

            # Check for HTTP errors (e.g., 404, 500)
            response.raise_for_status()

            # print("Request was successful!")
            # print(f"Status Code: {response.status_code}")

            # The response is typically in JSON format
            response_data = response.json()
            # print("Response Body:")
            # print(json.dumps(response_data, indent=2))
            return response_data["data"][0]["embedding"]

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")

        return []

    @override
    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        return []


def __create_embedding_model():
    if CONFIG["model_provider"] == "openai":
        return OpenAICompatibleProvider(
            CONFIG["model"]["name"], CONFIG["openai"]["url"]
        )
    elif CONFIG["model_provider"] == "sentence_transformer":
        return SentenceTransformerProvider(CONFIG["model"]["name"])
    raise ValueError(f"Unsupported model provider: {CONFIG['model_provider']}")


EMBEDDING_MODEL = __create_embedding_model()

if __name__ == "__main__":
    openai_provider = OpenAICompatibleProvider(
        "/home/jiangyinzuo/Qwen3-Embedding-0.6B/", "http://localhost:8000"
    )
    embeddings = openai_provider.encode("Hello, world!")
    print(embeddings)
