"""
Client for the Elastic Agent Builder `converse` API.

Sends an English question to the Pratham Bank agent and returns the agent's
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
        self.agent_id = os.getenv("AGENT_ID", "pratham-bank-support-agent")
        # Optional: chat-completion inference endpoint for the agent's LLM
        # (e.g. a Groq endpoint). If unset, Agent Builder uses its default model.
        self.inference_id = os.getenv("AGENT_INFERENCE_ID", "").strip()
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
        if self.inference_id:
            # Selects the chat-completion model the agent reasons with.
            payload["inference_id"] = self.inference_id

        answer_parts = []
        final_message = None
        error_msg = None
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
                        obj = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    etype = (event_type or obj.get("type") or "").lower()
                    data = obj.get("data", obj) if isinstance(obj, dict) else {}
                    if not isinstance(data, dict):
                        data = {}

                    # conversation id (any event that carries it)
                    conv_id = data.get("conversation_id", conv_id)

                    # error events — capture the reason instead of silently failing
                    if "error" in etype or obj.get("error") or data.get("error"):
                        err = (data.get("message") or data.get("error")
                               or obj.get("error") or json.dumps(obj))
                        error_msg = str(err)[:500]

                    # final answer (tolerant to event-name differences across versions)
                    if data.get("message_content"):
                        final_message = data["message_content"]
                    elif "message_complete" in etype and data.get("message"):
                        final_message = data["message"]

                    # incremental streamed tokens
                    chunk = data.get("text_chunk") or data.get("text")
                    if chunk and "chunk" in etype:
                        answer_parts.append(chunk)

                    event_type = ""

        answer = (final_message or "".join(answer_parts) or "").strip()
        if not answer and error_msg:
            raise RuntimeError(f"Agent Builder error: {error_msg}")
        return {"answer": answer, "conversation_id": conv_id, "error": error_msg}
