"""Envoi SMTP explicite. Aucun message n'est envoyé sans outil CRITICAL approuvé."""
from __future__ import annotations
import os
import re
import smtplib
import ssl
from email.message import EmailMessage

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class EmailService:
    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("SMTP_USERNAME", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.sender = os.getenv("SMTP_FROM", self.username)
        self.use_tls = os.getenv("SMTP_TLS", "1") != "0"
        self.use_ssl = os.getenv("SMTP_SSL", "0") == "1"
        self.timeout = int(os.getenv("SMTP_TIMEOUT", "20"))

    @property
    def configured(self):
        return bool(self.host and self.sender)

    @staticmethod
    def _addresses(value):
        if isinstance(value, str):
            items = [x.strip() for x in value.split(",") if x.strip()]
        elif isinstance(value, list):
            items = [str(x).strip() for x in value if str(x).strip()]
        else:
            items = []
        if not items or len(items) > 20 or any(not _EMAIL.match(x) for x in items):
            raise ValueError("Adresse e-mail invalide")
        return items

    def preview(self, to, subject, body, cc=""):
        recipients = self._addresses(to)
        cc_list = self._addresses(cc) if cc else []
        subject = str(subject or "").strip()
        body = str(body or "")
        if not subject or len(subject) > 200:
            raise ValueError("Objet invalide")
        if not body or len(body) > 100_000:
            raise ValueError("Corps invalide")
        return {"from": self.sender or "non configuré", "to": recipients, "cc": cc_list,
                "subject": subject, "body": body, "configured": self.configured}

    def send(self, to, subject, body, cc=""):
        if not self.configured:
            raise RuntimeError("SMTP non configuré")
        data = self.preview(to, subject, body, cc)
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = ", ".join(data["to"])
        if data["cc"]:
            msg["Cc"] = ", ".join(data["cc"])
        msg["Subject"] = data["subject"]
        msg.set_content(data["body"])
        recipients = data["to"] + data["cc"]
        if self.use_ssl:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout,
                                   context=ssl.create_default_context()) as smtp:
                if self.username:
                    smtp.login(self.username, self.password)
                smtp.send_message(msg, to_addrs=recipients)
        else:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
                if self.use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                if self.username:
                    smtp.login(self.username, self.password)
                smtp.send_message(msg, to_addrs=recipients)
        return {"ok": True, "to": data["to"], "cc": data["cc"], "subject": data["subject"]}
