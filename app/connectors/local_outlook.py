from __future__ import annotations

import os
import platform
from datetime import datetime, timezone
from pathlib import Path

OUTLOOK_INBOX = 6

class LocalOutlookClient:
    """Windows Outlook Desktop connector using pywin32/COM.

    This is intentionally local-first: it reads the mailbox from the Outlook
    profile already configured on the Windows workstation. No credentials are
    scraped or stored by this connector.
    """
    def __init__(self):
        self._outlook = None
        self._namespace = None

    @property
    def available(self) -> bool:
        return platform.system() == 'Windows'

    def connect(self):
        if not self.available:
            raise RuntimeError('Local Outlook connector requires Windows with Outlook Desktop installed.')
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            self._outlook = win32com.client.Dispatch('Outlook.Application')
            self._namespace = self._outlook.GetNamespace('MAPI')
            return self
        except Exception as e:
            raise RuntimeError(f'Could not connect to local Outlook: {e}') from e

    def inbox(self):
        if self._namespace is None:
            self.connect()
        return self._namespace.GetDefaultFolder(OUTLOOK_INBOX)

    def status(self) -> dict:
        try:
            self.connect()
            inbox = self.inbox()
            return {
                'available': True,
                'connected': True,
                'profiles': self._namespace.Folders.Count,
                'inbox_items': inbox.Items.Count,
            }
        except Exception as e:
            return {'available': self.available, 'connected': False, 'error': str(e)}

    @staticmethod
    def _sender(item) -> str:
        try:
            return str(item.SenderEmailAddress or '')
        except Exception:
            return ''

    @staticmethod
    def _received(item) -> str:
        try:
            value = item.ReceivedTime
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                return value.isoformat()
            return str(value)
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    def list_messages(self, top: int = 50) -> list[dict]:
        """Return recent Outlook mail as normalized dictionaries."""
        inbox = self.inbox()
        items = inbox.Items
        try:
            items.Sort('[ReceivedTime]', True)
        except Exception:
            pass

        messages = []
        limit = max(1, int(top))
        for i in range(1, min(items.Count, limit) + 1):
            try:
                item = items.Item(i)
                # 43 = olMail. Ignore calendar/tasks/etc. when mixed into Inbox.
                if getattr(item, 'Class', 43) != 43:
                    continue
                attachments = []
                try:
                    for j in range(1, item.Attachments.Count + 1):
                        a = item.Attachments.Item(j)
                        attachments.append({'name': str(a.FileName or ''), 'size': int(getattr(a, 'Size', 0) or 0)})
                except Exception:
                    pass
                messages.append({
                    'id': str(item.EntryID),
                    'internetMessageId': str(getattr(item, 'InternetMessageID', '') or ''),
                    'subject': str(getattr(item, 'Subject', '') or ''),
                    'from': {'emailAddress': {'address': self._sender(item)}},
                    'receivedDateTime': self._received(item),
                    'body': {'contentType': 'text', 'content': str(getattr(item, 'Body', '') or '')},
                    'hasAttachments': bool(getattr(item, 'Attachments', None) and item.Attachments.Count),
                    'attachments': attachments,
                })
            except Exception:
                continue
        return messages

    def create_reply_draft(self, entry_id: str, body: str) -> str:
        """Create and save a reply draft. Never sends the message."""
        self.connect()
        item = self._namespace.GetItemFromID(entry_id)
        reply = item.Reply()
        # Outlook COM Reply() creates an editable MailItem. Body is used here
        # deliberately so the connector remains dependency-light and local.
        reply.Body = body or ''
        reply.Save()
        return str(getattr(reply, 'EntryID', '') or '')

    def save_attachments(self, entry_id: str, target_dir: str) -> list[str]:
        """Save attachments for one local Outlook message without opening them."""
        self.connect()
        item = self._namespace.GetItemFromID(entry_id)
        out = Path(target_dir)
        out.mkdir(parents=True, exist_ok=True)
        saved = []
        for i in range(1, item.Attachments.Count + 1):
            a = item.Attachments.Item(i)
            name = os.path.basename(str(a.FileName or f'attachment_{i}'))
            path = out / name
            a.SaveAsFile(str(path))
            saved.append(str(path))
        return saved
