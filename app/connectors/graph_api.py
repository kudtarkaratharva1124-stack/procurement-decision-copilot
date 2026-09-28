from __future__ import annotations

import os
from pathlib import Path

import requests
import msal

from dotenv import load_dotenv

load_dotenv()


class GraphClient:
    """
    Microsoft Graph client for delegated user authentication.

    Uses a persistent MSAL token cache so that after the first
    successful Microsoft login, subsequent application starts
    can normally authenticate silently without asking the user
    to log in again.

    Current flow:

        Outlook
            ↓
        Microsoft Graph /me
            ↓
        Inbox + Drafts
    """

    base = "https://graph.microsoft.com/v1.0"

    # Store the MSAL cache inside the project.
    # This file contains authentication cache data, so do not
    # commit it to Git or share it.
    CACHE_FILE = (
        Path(__file__).resolve().parents[2]
        / ".graph_token_cache.bin"
    )

    def __init__(self):
        self.token = self._get_token()

    # ------------------------------------------------------------------
    # TOKEN CACHE
    # ------------------------------------------------------------------

    def _load_cache(self):
        """
        Load the MSAL token cache from disk.
        """

        cache = msal.SerializableTokenCache()

        if self.CACHE_FILE.exists():

            try:
                cache.deserialize(
                    self.CACHE_FILE.read_text(
                        encoding="utf-8"
                    )
                )

            except Exception as exc:
                print(
                    "Warning: Could not load Microsoft "
                    f"token cache: {exc}"
                )

        return cache

    def _save_cache(self, cache):
        """
        Persist the MSAL token cache to disk if it changed.
        """

        if not cache.has_state_changed:
            return

        try:

            self.CACHE_FILE.write_text(
                cache.serialize(),
                encoding="utf-8"
            )

        except Exception as exc:

            print(
                "Warning: Could not save Microsoft "
                f"token cache: {exc}"
            )

    # ------------------------------------------------------------------
    # AUTHENTICATION
    # ------------------------------------------------------------------

    def _get_token(self):

        client_id = os.getenv(
            "GRAPH_CLIENT_ID"
        )

        if not client_id:
            raise RuntimeError(
                "GRAPH_CLIENT_ID is missing from .env"
            )

        authority = (
            "https://login.microsoftonline.com/common"
        )

        scopes = [
            "User.Read",
            "Mail.ReadWrite",
        ]

        # --------------------------------------------------------------
        # Load persistent MSAL cache.
        # --------------------------------------------------------------

        cache = self._load_cache()

        app = msal.PublicClientApplication(
            client_id,
            authority=authority,
            token_cache=cache,
        )

        # --------------------------------------------------------------
        # First try silent authentication.
        #
        # This is the important part:
        # if a valid cached refresh/access token exists,
        # Microsoft login will NOT be requested again.
        # --------------------------------------------------------------

        accounts = app.get_accounts()

        if accounts:

            result = app.acquire_token_silent(
                scopes,
                account=accounts[0],
            )

            if (
                result
                and "access_token" in result
            ):

                self._save_cache(cache)

                return result[
                    "access_token"
                ]

        # --------------------------------------------------------------
        # No usable cached token.
        #
        # Only now ask the user to authenticate.
        # --------------------------------------------------------------

        flow = app.initiate_device_flow(
            scopes=scopes
        )

        if "user_code" not in flow:
            raise RuntimeError(
                f"Could not start device login: {flow}"
            )

        print()
        print("=" * 60)
        print("MICROSOFT GRAPH LOGIN REQUIRED")
        print("=" * 60)
        print(flow["message"])
        print("=" * 60)
        print()

        result = app.acquire_token_by_device_flow(
            flow
        )

        if (
            not result
            or "access_token" not in result
        ):

            raise RuntimeError(
                "Graph authentication failed: "
                + str(
                    result.get(
                        "error_description",
                        result,
                    )
                )
            )

        # --------------------------------------------------------------
        # IMPORTANT:
        # Save the new authentication state.
        #
        # The next time the application starts,
        # MSAL can use this cache.
        # --------------------------------------------------------------

        self._save_cache(cache)

        return result[
            "access_token"
        ]

    # ------------------------------------------------------------------
    # GRAPH HTTP HELPERS
    # ------------------------------------------------------------------

    def headers(self):

        return {
            "Authorization":
                f"Bearer {self.token}",
            "Content-Type":
                "application/json",
        }

    def get(
        self,
        path: str,
        params: dict | None = None,
    ):

        response = requests.get(
            self.base + path,
            headers=self.headers(),
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def post(
        self,
        path: str,
        payload: dict,
    ):

        response = requests.post(
            self.base + path,
            headers=self.headers(),
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        return (
            response.json()
            if response.content
            else {}
        )

    def patch(
        self,
        path: str,
        payload: dict,
    ):

        response = requests.patch(
            self.base + path,
            headers=self.headers(),
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        return (
            response.json()
            if response.content
            else {}
        )

    # ------------------------------------------------------------------
    # OUTLOOK MAIL
    # ------------------------------------------------------------------

    def list_messages(self, top=25):
    """
    Get latest messages from the signed-in user's Inbox.

    Includes enough metadata to identify and later download
    attachments from Microsoft Graph.
    """

    path = "/me/mailFolders/inbox/messages"

    params = {
        "$top": top,
        "$orderby": "receivedDateTime desc",
        "$select": (
            "id,subject,body,from,receivedDateTime,"
            "hasAttachments,internetMessageId,bodyPreview"
        ),
    }

    messages = self.get(
        path,
        params,
    ).get("value", [])

    return messages

    def list_attachments(
    self,
    message_id: str,
    ):
    """
    Get all attachments belonging to an Outlook message.
    """

    return self.get(
        f"/me/messages/{message_id}/attachments",
        {
            "$top": 100,
        },
    ).get(
        "value",
        []
    )

    def create_reply_draft(
        self,
        message_id: str,
        html: str,
    ):
        """
        Create a reply draft for an existing email.
        """

        draft = self.post(
            f"/me/messages/"
            f"{message_id}/createReply",
            {},
        )

        draft_id = draft["id"]

        self.patch(
            f"/me/messages/"
            f"{draft_id}",
            {
                "body": {
                    "contentType":
                        "HTML",
                    "content":
                        html,
                }
            },
        )

        return draft_id

    # ------------------------------------------------------------------
    # ATTACHMENTS
    # ------------------------------------------------------------------

    def list_attachments(
        self,
        message_id: str,
    ):

        return self.get(
            f"/me/messages/"
            f"{message_id}/attachments",
            {
                "$top": 20
            },
        ).get(
            "value",
            []
        )

    def download_attachment(
    self,
    message_id: str,
    attachment_id: str,
    ):
    """
    Download a single Microsoft Graph attachment.

    Returns the Graph attachment object. For file attachments,
    the contentBytes field contains the base64 encoded file.
    """

    return self.get(
        f"/me/messages/"
        f"{message_id}/attachments/"
        f"{attachment_id}"
    )

    # ------------------------------------------------------------------
    # SHAREPOINT
    # ------------------------------------------------------------------

    def search_sharepoint(
        self,
        query: str,
    ):
        """
        SharePoint search can be enabled later.
        """

        return []