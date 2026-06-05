"""
Client for the Elastic Agent Builder `converse` API.

Sends an English question to the Bharat Bank agent and returns the agent's
final English answer. The agent internally calls its index_search tool, which
runs hybrid (BM25 + semantic) search over the knowledge base.

The endpoint streams Server-Sent Events; we parse the stream and keep the
`message_complete` content as the final answer.
"""
import os
import json
import requests


class AgentBuilderClient:
    def __init__(self):
        self.kibana_url = os.environ["KIBANA_URL"].rstrip("/")
        self.api_key = os.environ["KIBANA_API_KEY"]
        self.agent_id = os.getenv("AGENT_ID", "bharat-bank-support-agent")
        space = os.getenv("KIBANA_SPACE_ID", "").strip()
        base = self.kibana_url + (f"/s/{space}" if space and space != "default" else "")
        self.url = f"{base}/api/agent_builder/converse/async"
        self.headers = {
            "Authorization": f"ApiKey {self.api_key}",
            "Content-Type": "application/json",
            "kbn-xsrf": "true",
        }

    def ask(self, question_en: str, conversation_id: str | None = None) -> dict:
        """
        Ask the agent an English question.
        Returns {answer, conversation_id}.
        """
        payload = {"agent_id": self.agent_id, "input": question_en}
        if conversation_id:
            payload["conversation_id"] = conversation_id

        answer_parts = []
        final_message = None
        conv_id = conversation_id

        with requests.post(self.url, headers=self.headers, json=payload,
                          stream=True, timeout=120) as r:
            r.raise_for_status()
            event_type = ""
            for raw in r.iter_lines(decode_unicode=True):
                if raw is None:
                    continue
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="replace")
                line = raw.rstrip("\r")
                if line.startswith(":") or line == "":
                    continue
                if line.startswith("event: "):
                    event_type = line[7:]
                    continue
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:]).get("data", {})
                    except json.JSONDecodeError:
                        continue
                    if event_type == "conversation_id_set":
                        conv_id = data.get("conversation_id", conv_id)
                    elif event_type == "message_chunk":
                        # incremental tokens (if streamed)
                        chunk = data.get("text_chunk") or data.get("content")
                        if chunk:
                            answer_parts.append(chunk)
                    elif event_type == "message_complete":
                        final_message = data.get("message_content")
                    event_type = ""

        answer = final_message or "".join(answer_parts)
        return {"answer": (answer or "").strip(), "conversation_id": conv_id}
