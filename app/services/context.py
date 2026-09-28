from __future__ import annotations

from ..config import settings
from ..connectors.graph_api import GraphClient
from ..connectors.project_systems import (
    PegaConnector,
    ServiceNowConnector,
    MondayConnector,
)
from ..models import SessionLocal, Case
from sqlalchemy import select


class ContextService:

    def __init__(self):

        # Microsoft Graph is now our primary mailbox source.
        # GraphClient handles delegated authentication.
        try:
            self.graph = GraphClient()
        except Exception as exc:
            print(
                f"Microsoft Graph unavailable: {exc}"
            )
            self.graph = None

        self.pega = PegaConnector()
        self.snow = ServiceNowConnector()
        self.monday = MondayConnector()

    def collect(self, case):

        key = case["case_key"]

        evidence = []

        extracted = {
            "subject": case.get(
                "subject",
                ""
            ),
            "sender": case.get(
                "sender",
                ""
            ),
            "body": (
                case.get("extracted") or {}
            ).get(
                "body",
                ""
            ),
        }

        source = (
            case.get("extracted") or {}
        ).get(
            "source"
        )

        msg_id = (
            case.get("extracted") or {}
        ).get(
            "message_id"
        )

        # -------------------------------------------------
        # MICROSOFT GRAPH / OUTLOOK
        # -------------------------------------------------

        if self.graph and msg_id:

            try:

                messages = self.graph.list_messages(
                    settings.outlook_poll_top
                )

                target = None

                for message in messages:

                    if message.get("id") == msg_id:
                        target = message
                        break

                # Fallback: match by subject.
                if not target:

                    subject = case.get(
                        "subject",
                        ""
                    ).lower()

                    for message in messages:

                        if (
                            subject
                            and subject
                            == (
                                message.get(
                                    "subject",
                                    ""
                                )
                                .lower()
                            )
                        ):
                            target = message
                            break

                if target:

                    evidence.append(
                        {
                            "source": "Outlook",
                            "title":
                                target.get(
                                    "subject"
                                ),
                            "content":
                                target.get(
                                    "body",
                                    {}
                                ).get(
                                    "content",
                                    ""
                                )[:10000],
                        }
                    )

                    # Attachments
                    if (
                        target.get("id")
                        and target.get(
                            "hasAttachments"
                        )
                    ):

                        attachments = (
                            self.graph
                            .list_attachments(
                                target["id"]
                            )
                        )

                        for attachment in attachments:

                            evidence.append(
                                {
                                    "source":
                                        "Outlook Attachment",
                                    "title":
                                        attachment.get(
                                            "name"
                                        ),
                                    "content":
                                        "Attachment discovered "
                                        "through Microsoft Graph.",
                                    "attachment_id":
                                        attachment.get(
                                            "id"
                                        ),
                                }
                            )

                else:

                    evidence.append(
                        {
                            "source": "Outlook",
                            "title":
                                case.get(
                                    "subject",
                                    ""
                                ),
                            "content":
                                "Original Outlook message "
                                "was ingested successfully, "
                                "but the message could not "
                                "be reloaded during context "
                                "aggregation.",
                        }
                    )

            except Exception as exc:

                evidence.append(
                    {
                        "source": "Outlook",
                        "error": str(exc),
                    }
                )

        # -------------------------------------------------
        # HISTORICAL DECISIONS
        # -------------------------------------------------

        with SessionLocal() as db:

            prior = db.scalars(
                select(Case)
                .where(
                    Case.case_key != key
                )
                .order_by(
                    Case.updated_at.desc()
                )
                .limit(5)
            ).all()

            for previous_case in prior:

                evidence.append(
                    {
                        "source":
                            "Historical Decisions",
                        "title":
                            previous_case.case_key,
                        "content":
                            {
                                "status":
                                    previous_case.status,
                                "problem_statement":
                                    previous_case.problem_statement,
                                "recommendation":
                                    previous_case.recommendation,
                            },
                    }
                )

        # -------------------------------------------------
        # PROJECT SYSTEMS
        # -------------------------------------------------

        for name, connector in [
            ("Pega", self.pega.search),
            ("ServiceNow", self.snow.search),
            ("Monday.com", self.monday.search),
        ]:

            try:

                rows = connector(key)

                for row in rows[:10]:

                    evidence.append(
                        {
                            "source": name,
                            "content": row,
                        }
                    )

            except Exception as exc:

                evidence.append(
                    {
                        "source": name,
                        "error": str(exc),
                    }
                )

        # -------------------------------------------------
        # SHAREPOINT
        # -------------------------------------------------

        if (
            settings.sharepoint_site_id
            and self.graph
        ):

            try:

                rows = self.graph.search_sharepoint(
                    key
                )

                for row in rows[:10]:

                    evidence.append(
                        {
                            "source":
                                "SharePoint",
                            "content":
                                row,
                        }
                    )

            except Exception as exc:

                evidence.append(
                    {
                        "source":
                            "SharePoint",
                        "error":
                            str(exc),
                    }
                )

        return {
            "evidence": evidence,
            "extracted": extracted,
        }