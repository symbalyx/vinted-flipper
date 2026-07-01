"""Client n8n Public API avec validation locale et refus des nœuds risqués."""
from __future__ import annotations
import json
import os
import re
from urllib.parse import urlparse
import requests

_WORKFLOW_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

RISKY_NODE_TYPES = {
    "n8n-nodes-base.executeCommand",
    "n8n-nodes-base.ssh",
    "n8n-nodes-base.ftp",
    "n8n-nodes-base.readWriteFile",
    "n8n-nodes-base.localFileTrigger",
    "n8n-nodes-base.code",
    "n8n-nodes-base.function",
    "n8n-nodes-base.functionItem",
}


class N8NClient:
    def __init__(self, base_url=None, api_key=None, timeout=None, verify_tls=None):
        self.base_url = (base_url or os.getenv("N8N_URL", "http://127.0.0.1:5678")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("N8N_API_KEY", "")
        self.timeout = int(timeout or os.getenv("N8N_TIMEOUT", "15"))
        self.verify_tls = (os.getenv("N8N_VERIFY_TLS", "1") != "0") if verify_tls is None else bool(verify_tls)
        self.allow_risky = os.getenv("N8N_ALLOW_RISKY_NODES", "0") == "1"
        parsed = urlparse(self.base_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("N8N_URL invalide")

    @property
    def configured(self):
        return bool(self.api_key)

    def _headers(self):
        if not self.api_key:
            raise RuntimeError("N8N_API_KEY non configurée")
        return {"X-N8N-API-KEY": self.api_key, "Accept": "application/json", "Content-Type": "application/json"}

    def _request(self, method, path, **kwargs):
        response = requests.request(method, f"{self.base_url}{path}", headers=self._headers(),
                                    timeout=self.timeout, verify=self.verify_tls, **kwargs)
        response.raise_for_status()
        if not response.content:
            return {"ok": True}
        return response.json()

    def status(self):
        return {"configured": self.configured, "base_url": self.base_url,
                "allow_risky_nodes": self.allow_risky}

    def list_workflows(self, active=None, limit=50):
        params = {"limit": max(1, min(int(limit), 250))}
        if active is not None:
            params["active"] = "true" if bool(active) else "false"
        return self._request("GET", "/api/v1/workflows", params=params)

    @staticmethod
    def _workflow_id(value):
        value = str(value or "").strip()
        if not _WORKFLOW_ID.fullmatch(value):
            raise ValueError("Identifiant de workflow invalide")
        return value

    def get_workflow(self, workflow_id):
        workflow_id = self._workflow_id(workflow_id)
        return self._request("GET", f"/api/v1/workflows/{workflow_id}")

    def validate_workflow(self, workflow):
        if isinstance(workflow, str):
            if len(workflow) > 250_000:
                raise ValueError("Workflow trop volumineux")
            workflow = json.loads(workflow)
        if not isinstance(workflow, dict):
            raise ValueError("Workflow JSON invalide")
        name = str(workflow.get("name") or "").strip()
        nodes = workflow.get("nodes")
        connections = workflow.get("connections", {})
        if not name or len(name) > 160:
            raise ValueError("Nom de workflow invalide")
        if not isinstance(nodes, list) or not nodes or len(nodes) > 100:
            raise ValueError("Le workflow doit contenir 1 à 100 nœuds")
        if not isinstance(connections, dict):
            raise ValueError("Connections invalides")
        risky = []
        for node in nodes:
            if not isinstance(node, dict):
                raise ValueError("Nœud invalide")
            ntype = str(node.get("type") or "")
            if not ntype.startswith("n8n-nodes-"):
                raise ValueError(f"Type de nœud invalide : {ntype}")
            if ntype in RISKY_NODE_TYPES:
                risky.append(ntype)
        if risky and not self.allow_risky:
            raise PermissionError("Nœuds risqués refusés : " + ", ".join(sorted(set(risky))))
        clean = {"name": name, "nodes": nodes, "connections": connections,
                 "settings": workflow.get("settings") if isinstance(workflow.get("settings"), dict) else {}}
        if "staticData" in workflow and isinstance(workflow["staticData"], dict):
            clean["staticData"] = workflow["staticData"]
        return clean

    def create_workflow(self, workflow):
        clean = self.validate_workflow(workflow)
        return self._request("POST", "/api/v1/workflows", json=clean)

    def update_workflow(self, workflow_id, workflow):
        workflow_id = self._workflow_id(workflow_id)
        clean = self.validate_workflow(workflow)
        return self._request("PUT", f"/api/v1/workflows/{workflow_id}", json=clean)

    def activate_workflow(self, workflow_id):
        workflow_id = self._workflow_id(workflow_id)
        return self._request("POST", f"/api/v1/workflows/{workflow_id}/activate")

    def deactivate_workflow(self, workflow_id):
        workflow_id = self._workflow_id(workflow_id)
        return self._request("POST", f"/api/v1/workflows/{workflow_id}/deactivate")
