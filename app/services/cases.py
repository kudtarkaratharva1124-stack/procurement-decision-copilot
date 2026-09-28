from __future__ import annotations

import base64
import re
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import select

from ..models import SessionLocal, Case, AuditLog, Feedback
from ..config import settings
from ..connectors.graph_api import GraphClient
from ..graph.workflow import ProcurementGraph
from .context import ContextService


def classify(subject: str) -> str | None:
    """
    Detect an RFA/MOU category from the email subject.
    """

    subject_upper = (subject or "").upper()

    # Longest prefixes first so RFASTND/RFASP etc.
    # are checked before generic RFA.
    prefixes = sorted(
        settings.rfa_prefixes,
        key=len,
        reverse=True
    )

    for prefix in prefixes:
        if re.search(
            rf"(?<![A-Z0-9]){re.escape(prefix)}(?![A-Z0-9])",
            subject_upper
        ):
            return prefix

    return None


class CaseService:

    def __init__(self):
        self.context = ContextService()
        self.graph = ProcurementGraph(self.context)

    def _mailbox_messages(self, top=50):
        """
        Current demo path:
            Microsoft Graph delegated authentication

        This is the path we have verified against the real
        Outlook Inbox on the Mac.
        """

        if self.context.graph:
            try:
                return (
                    self.context.graph.list_messages(top),
                    "microsoft_graph"
                )
            except Exception as exc:
                print(
                    f"Microsoft Graph mailbox read failed: {exc}"
                )

        # Windows Outlook fallback, if explicitly enabled.
        if (
            settings.outlook_local_enabled
            and hasattr(settings, "outlook_local_enabled")
        ):
            try:
                from ..connectors.local_outlook import (
                    LocalOutlookClient
                )

                local = LocalOutlookClient()

                return (
                    local.list_messages(top),
                    "local_outlook"
                )

            except Exception as exc:
                print(
                    f"Local Outlook unavailable: {exc}"
                )

        if settings.demo_mode:
            return (
                [
                    {
                        "id": "demo-001",
                        "subject":
                            "RFA - Procurement Approval - DEMO-001",
                        "from": {
                            "emailAddress": {
                                "address": "demo@example.com"
                            }
                        },
                        "receivedDateTime":
                            datetime.now(
                                timezone.utc
                            ).isoformat(),
                        "body": {
                            "contentType": "text",
                            "content":
                                "Award value: 1260000. "
                                "Budget: 1000000. "
                                "Payment: delivery-based. "
                                "Please review and approve."
                        }
                    }
                ],
                "demo"
            )

        return [], "none"

    def _process_graph_attachments(
        self,
        message_id: str,
        case_key: str,
    ):
        """
        Download and extract every Outlook attachment available through
        Microsoft Graph.

        The extracted content becomes live case evidence for LangGraph
        and Azure OpenAI reasoning.
        """

        results = []

        if not self.context.graph or not message_id:
            return results

        try:
            attachments = self.context.graph.list_attachments(
                message_id
            )
        except Exception as exc:
            return [{
                "name": "ATTACHMENT_LIST_ERROR",
                "status": "attachment_list_failed",
                "error": str(exc),
            }]

        if not attachments:
            return results

        folder = (
            Path("data")
            / "attachments"
            / case_key
        )

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        from .documents import extract_file

        for attachment in attachments:

            name = (
                attachment.get("name")
                or "unnamed_attachment"
            )

            attachment_id = attachment.get("id")

            content_type = (
                attachment.get("contentType")
                or "application/octet-stream"
            )

            size = attachment.get("size") or 0

            attachment_type = (
                attachment.get("@odata.type")
                or ""
            )

            if attachment_type == "#microsoft.graph.itemAttachment":
                results.append({
                    "name": name,
                    "content_type": content_type,
                    "size": size,
                    "status": "unsupported_item_attachment",
                })
                continue

            if not attachment_id:
                results.append({
                    "name": name,
                    "content_type": content_type,
                    "size": size,
                    "status": "missing_attachment_id",
                })
                continue

            try:
                attachment_data = (
                    self.context.graph.download_attachment(
                        message_id,
                        attachment_id
                    )
                )

                content_bytes = attachment_data.get(
                    "contentBytes"
                )

                if not content_bytes:
                    results.append({
                        "name": name,
                        "content_type": content_type,
                        "size": size,
                        "status": "no_content_bytes",
                    })
                    continue

                raw = base64.b64decode(content_bytes)

                safe_name = Path(name).name

                if not safe_name:
                    safe_name = "attachment"

                path = folder / safe_name

                if path.exists():
                    stem = path.stem
                    suffix = path.suffix
                    counter = 2

                    while path.exists():
                        path = (
                            folder
                            / f"{stem}_{counter}{suffix}"
                        )
                        counter += 1

                path.write_bytes(raw)

                result = {
                    "name": path.name,
                    "original_name": name,
                    "path": str(path),
                    "content_type": content_type,
                    "size": len(raw),
                }

                try:
                    text = extract_file(
                        str(path)
                    )

                    if text and text.strip():
                        result["text"] = text[:50000]
                        result["status"] = "extracted"
                    else:
                        result["status"] = "no_text_extracted"

                except Exception as extract_error:
                    result["status"] = "extraction_failed"
                    result["error"] = str(
                        extract_error
                    )

                results.append(result)

            except Exception as attachment_error:
                results.append({
                    "name": name,
                    "content_type": content_type,
                    "size": size,
                    "status": "download_failed",
                    "error": str(attachment_error),
                })

        return results

    def ingest(self):
        """
        Read Outlook messages and create/update RFA cases.

        Important behavior:
        - Every Graph email stores its original message_id.
        - Existing cases are refreshed with Graph metadata.
        - New cases store Graph metadata immediately.
        - This allows every case to later create an Outlook reply draft.
        """

        messages, source = self._mailbox_messages(
            settings.outlook_poll_top
        )

        count = 0

        for message in messages:

            subject = message.get("subject", "")

            category = classify(subject)

            if not category:
                continue

            body = (
                message
                .get("body", {})
                .get("content", "")
            )

            # Avoid accidental test/demo messages unless demo mode
            # is explicitly enabled.
            if (
                any(
                    phrase in body.lower()
                    for phrase in [
                        "this is a demo",
                        "demo email",
                        "for testing"
                    ]
                )
                and not settings.demo_mode
            ):
                continue

            key = self.case_key(message)

            # ---------------------------------------------------------
            # IMPORTANT:
            # Always persist the original Outlook/Graph metadata.
            # This is what allows us to create a reply draft later.
            # ---------------------------------------------------------
            message_metadata = {
                "message_id": message.get("id"),
                "internet_message_id":
                    message.get(
                        "internetMessageId",
                        ""
                    ),
                "source": source,
                "attachments":
                    message.get(
                        "attachments",
                        []
                    )
            }

            with SessionLocal() as db:

                existing = db.scalar(
                    select(Case).where(
                        Case.case_key == key
                    )
                )

                # -----------------------------------------------------
                # EXISTING CASE
                # -----------------------------------------------------
                # Do NOT simply skip the case.
                #
                # Refresh the Outlook metadata every time the
                # polling process sees the email.
                # -----------------------------------------------------
                if existing:

                    extracted = dict(
                        existing.extracted or {}
                    )

                    # Preserve existing fields such as:
                    # body, attachment_text, attachment_paths, etc.
                    extracted.update(
                        message_metadata
                    )

                    # Also keep the latest body available.
                    if body:
                        extracted["body"] = body

                    existing.extracted = extracted

                    # If the original case somehow has missing
                    # basic email fields, refresh them too.
                    if not existing.subject:
                        existing.subject = subject

                    if not existing.category:
                        existing.category = category

                    if not existing.sender:
                        existing.sender = (
                            message
                            .get("from") or {}
                        ).get(
                            "emailAddress", {}
                        ).get(
                            "address",
                            ""
                        )

                    if (
                        source == "microsoft_graph"
                        and message.get("id")
                    ):
                        extracted[
                            "attachment_content"
                        ] = self._process_graph_attachments(
                            message.get("id"),
                            key
                        )

                    db.commit()

                    continue

                # -----------------------------------------------------
                # NEW CASE
                # -----------------------------------------------------

                sender = (
                    message
                    .get("from") or {}
                ).get(
                    "emailAddress", {}
                ).get(
                    "address",
                    ""
                )

                extracted = {
                    "body": body,
                    "message_id": message.get("id"),
                    "internet_message_id":
                        message.get(
                            "internetMessageId",
                            ""
                        ),
                    "source": source,
                    "attachments":
                        message.get(
                            "attachments",
                            []
                        )
                }

                # -------------------------------------------------------------
                # Microsoft Graph attachment processing
                # -------------------------------------------------------------
                #
                # Download and extract every file attached to the Outlook email.
                # The extracted content becomes part of the case evidence.
                # -------------------------------------------------------------

                if (
                    source == "microsoft_graph"
                    and message.get("id")
                ):
                    extracted[
                        "attachment_content"
                    ] = self._process_graph_attachments(
                        message.get("id"),
                        key
                    )
                else:
                    extracted[
                        "attachment_content"
                    ] = []

                # Keep attachment processing for Windows Outlook.
                if (
                    source == "local_outlook"
                    and message.get("id")
                    and message.get("attachments")
                ):
                    try:
                        from pathlib import Path

                        from ..connectors.local_outlook import (
                            LocalOutlookClient
                        )

                        from .documents import extract_file

                        local = LocalOutlookClient()

                        folder = (
                            Path(
                                settings.outlook_attachment_dir
                            ) / key
                        )

                        paths = local.save_attachments(
                            message["id"],
                            str(folder)
                        )

                        extracted[
                            "attachment_paths"
                        ] = paths

                        extracted[
                            "attachment_text"
                        ] = []

                        for path in paths:
                            try:
                                text = extract_file(path)

                                if text:
                                    extracted[
                                        "attachment_text"
                                    ].append(
                                        {
                                            "name":
                                                Path(
                                                    path
                                                ).name,
                                            "text":
                                                text[:20000]
                                        }
                                    )

                            except Exception as attachment_error:
                                extracted[
                                    "attachment_text"
                                ].append(
                                    {
                                        "name":
                                            Path(
                                                path
                                            ).name,
                                        "error":
                                            str(
                                                attachment_error
                                            )
                                    }
                                )

                    except Exception as attachment_error:
                        extracted[
                            "attachment_error"
                        ] = str(
                            attachment_error
                        )

                case = Case(
                    case_key=key,
                    category=category,
                    subject=subject,
                    sender=sender,
                    received_at=self.parse_dt(
                        message.get(
                            "receivedDateTime"
                        )
                    ),
                    extracted=extracted
                )

                db.add(case)
                db.commit()
                db.refresh(case)

                db.add(
                    AuditLog(
                        case_key=key,
                        event_type="INGESTED",
                        payload={
                            "message_id":
                                message.get("id"),
                            "category":
                                category,
                            "source":
                                source
                        }
                    )
                )

                db.commit()

                count += 1

        return count

    def process(self, case_key: str):

        with SessionLocal() as db:

            case_record = db.scalar(
                select(Case).where(
                    Case.case_key == case_key
                )
            )

            case = (
                self.to_dict(case_record)
                if case_record
                else None
            )

        if not case:
            raise KeyError(case_key)

        result = self.graph.run(case)

        with SessionLocal() as db:

            case_record = db.scalar(
                select(Case).where(
                    Case.case_key == case_key
                )
            )

            if not case_record:
                raise KeyError(case_key)

            case_record.problem_statement = (
                result.get(
                    "problem_statement",
                    ""
                )
            )

            case_record.recommendation = (
                result.get(
                    "recommendation",
                    ""
                )
            )

            case_record.draft_body = (
                result.get(
                    "draft_body",
                    ""
                )
            )

            case_record.explainability = (
                result.get(
                    "explainability",
                    {}
                )
            )

            case_record.evidence = (
                result.get(
                    "evidence",
                    []
                )
            )

            # ---------------------------------------------------------
            # IMPORTANT:
            # Preserve original Outlook/Graph metadata.
            #
            # The LangGraph result may contain its own "extracted"
            # dictionary. Never let that accidentally remove:
            #
            # message_id
            # internet_message_id
            # source
            # attachments
            #
            # These fields are required later when a human approves
            # the case and we create the Outlook reply draft.
            # ---------------------------------------------------------
            current_extracted = dict(
                case_record.extracted or {}
            )

            graph_extracted = dict(
                result.get("extracted") or {}
            )

            original_attachment_content = (
                current_extracted.get(
                    "attachment_content",
                    []
                )
            )

            current_extracted.update(
                graph_extracted
            )

            # Never allow LangGraph processing to accidentally
            # remove attachment evidence collected during ingestion.
            if original_attachment_content:
                current_extracted["attachment_content"] = (
                    original_attachment_content
                )

            # Keep message ID if it already exists.
            if not current_extracted.get("message_id"):
                current_extracted["message_id"] = (
                    current_extracted.get("id")
                )

            # Do not overwrite a valid source.
            if not current_extracted.get("source"):
                current_extracted["source"] = (
                    "microsoft_graph"
                    if self.context.graph
                    else "unknown"
                )

            case_record.extracted = current_extracted
            case_record.sources = (
                result.get(
                    "sources",
                    []
                )
            )

            case_record.status = "pending"

            db.add(
                AuditLog(
                    case_key=case_key,
                    event_type="ANALYZED",
                    payload={
                        "sources":
                            case_record.sources
                    }
                )
            )

            db.commit()

        return result

    def decide(
        self,
        case_key,
        decision,
        note='',
        edited_draft=''
    ):
        allowed = {
            'approved',
            'rejected',
            'revision_requested'
        }

        if decision not in allowed:
            raise ValueError(
                'decision must be approved, rejected or revision_requested'
            )

        # Read the case first.
        with SessionLocal() as db:

            c = db.scalar(
                select(Case).where(
                    Case.case_key == case_key
                )
            )

            if not c:
                raise KeyError(case_key)

            final_draft = (
                edited_draft
                or c.draft_body
                or ''
            )

            # ---------------------------------------------------------
            # APPROVE
            # ---------------------------------------------------------
            if decision == 'approved':

                if not final_draft.strip():
                    raise ValueError(
                        'Cannot approve a case without a draft response.'
                    )

                # Save the approved response directly to Outlook Drafts.
                draft_result = self.save_outlook_draft(
                    case_key,
                    final_draft
                )

                c.status = 'approved'
                c.draft_body = final_draft

                db.add(
                    Feedback(
                        case_key=case_key,
                        decision='approved',
                        note=note,
                        edited_draft=final_draft
                    )
                )

                db.add(
                    AuditLog(
                        case_key=case_key,
                        event_type='HUMAN_DECISION',
                        actor='human',
                        payload={
                            'decision':
                                'approved',
                            'note':
                                note,
                            'draft_saved':
                                True,
                            'draft_id':
                                draft_result.get(
                                    'draft_id'
                                ),
                            'draft_source':
                                draft_result.get(
                                    'source'
                                )
                        }
                    )
                )

                db.commit()

                result = self.get(case_key)

                result[
                    'draft_result'
                ] = draft_result

                return result

            # ---------------------------------------------------------
            # REJECT
            # ---------------------------------------------------------
            if decision == 'rejected':

                c.status = 'rejected'
                c.draft_body = final_draft

                db.add(
                    Feedback(
                        case_key=case_key,
                        decision='rejected',
                        note=note,
                        edited_draft=final_draft
                    )
                )

                db.add(
                    AuditLog(
                        case_key=case_key,
                        event_type='HUMAN_DECISION',
                        actor='human',
                        payload={
                            'decision':
                                'rejected',
                            'note':
                                note,
                            'stored_for_historical_reference':
                                True,
                            'recommendation':
                                c.recommendation
                        }
                    )
                )

                db.commit()

                return self.get(case_key)

            # ---------------------------------------------------------
            # CLARIFICATION REQUESTED
            # ---------------------------------------------------------
            if decision == 'revision_requested':

                c.status = 'revision_requested'
                c.draft_body = final_draft

                db.add(
                    Feedback(
                        case_key=case_key,
                        decision='revision_requested',
                        note=note,
                        edited_draft=final_draft
                    )
                )

                db.add(
                    AuditLog(
                        case_key=case_key,
                        event_type='CLARIFICATION_REQUESTED',
                        actor='human',
                        payload={
                            'decision':
                                'revision_requested',
                            'note':
                                note
                        }
                    )
                )

                db.commit()

                return self.get(case_key)

    def save_outlook_draft(
        self,
        case_key: str,
        body: str
    ):
        """
        Save the approved response as a reply draft in Outlook.

        Primary path:
            stored Microsoft Graph message_id

        Recovery path:
            If an older case has no message_id, search the current
            Graph Inbox by subject, recover the message ID, persist it,
            and then create the draft.
        """

        with SessionLocal() as db:

            case_record = db.scalar(
                select(Case).where(
                    Case.case_key == case_key
                )
            )

            if not case_record:
                raise KeyError(case_key)

            extracted = dict(
                case_record.extracted or {}
            )

            message_id = extracted.get(
                "message_id"
            )

            source = extracted.get(
                "source"
            )

            subject = (
                case_record.subject
                or ""
            )

        # -------------------------------------------------------------
        # PRIMARY GRAPH PATH
        # -------------------------------------------------------------
        #
        # Do NOT require source == "microsoft_graph".
        #
        # If a Graph client exists and we have a valid message_id,
        # that is enough to create the reply draft.
        # -------------------------------------------------------------
        if self.context.graph and message_id:

            draft_id = (
                self.context.graph
                .create_reply_draft(
                    message_id,
                    body
                )
            )

            with SessionLocal() as db:

                db.add(
                    AuditLog(
                        case_key=case_key,
                        event_type=
                            "OUTLOOK_DRAFT_CREATED",
                        actor="human",
                        payload={
                            "draft_id":
                                draft_id,
                            "source":
                                "microsoft_graph",
                            "message_id":
                                message_id
                        }
                    )
                )

                db.commit()

            return {
                "draft_id":
                    draft_id,
                "source":
                    "microsoft_graph",
                "status":
                    "saved_to_outlook_drafts"
            }

        # -------------------------------------------------------------
        # RECOVERY PATH FOR OLD CASES
        # -------------------------------------------------------------
        #
        # Some older cases may have been created before message_id
        # persistence was fixed.
        #
        # If so, search the current Graph mailbox and match by subject.
        # -------------------------------------------------------------
        if self.context.graph and not message_id:

            try:

                messages = (
                    self.context.graph
                    .list_messages(
                        settings.outlook_poll_top
                    )
                )

                subject_upper = (
                    subject.strip().upper()
                )

                matched_message = None

                for message in messages:

                    graph_subject = (
                        message.get(
                            "subject",
                            ""
                        )
                        or ""
                    ).strip().upper()

                    if (
                        graph_subject
                        == subject_upper
                    ):
                        matched_message = message
                        break

                if matched_message:

                    recovered_message_id = (
                        matched_message.get("id")
                    )

                    if recovered_message_id:

                        recovered_internet_id = (
                            matched_message.get(
                                "internetMessageId",
                                ""
                            )
                        )

                        recovered_attachments = (
                            matched_message.get(
                                "attachments",
                                []
                            )
                        )

                        with SessionLocal() as db:

                            case_record = db.scalar(
                                select(Case).where(
                                    Case.case_key
                                    == case_key
                                )
                            )

                            if case_record:

                                extracted = dict(
                                    case_record.extracted
                                    or {}
                                )

                                extracted.update({
                                    "message_id":
                                        recovered_message_id,
                                    "internet_message_id":
                                        recovered_internet_id,
                                    "source":
                                        "microsoft_graph",
                                    "attachments":
                                        recovered_attachments
                                })

                                case_record.extracted = (
                                    extracted
                                )

                                db.commit()

                        # Now create the Outlook reply draft.
                        draft_id = (
                            self.context.graph
                            .create_reply_draft(
                                recovered_message_id,
                                body
                            )
                        )

                        with SessionLocal() as db:

                            db.add(
                                AuditLog(
                                    case_key=case_key,
                                    event_type=
                                        "OUTLOOK_DRAFT_CREATED",
                                    actor="human",
                                    payload={
                                        "draft_id":
                                            draft_id,
                                        "source":
                                            "microsoft_graph",
                                        "message_id":
                                            recovered_message_id,
                                        "recovered":
                                            True
                                    }
                                )
                            )

                            db.commit()

                        return {
                            "draft_id":
                                draft_id,
                            "source":
                                "microsoft_graph",
                            "status":
                                "saved_to_outlook_drafts",
                            "recovered_message_id":
                                True
                        }

            except Exception as exc:
                print(
                    "Graph message ID recovery failed: "
                    f"{exc}"
                )

        raise RuntimeError(
            "No usable Microsoft Graph Outlook source "
            "is configured for this case."
        )

    def get(self, key):

        with SessionLocal() as db:

            case_record = db.scalar(
                select(Case).where(
                    Case.case_key == key
                )
            )

            return (
                self.to_dict(case_record)
                if case_record
                else None
            )

    def list(self):

        with SessionLocal() as db:

            return [
                self.to_dict(record)
                for record in db.scalars(
                    select(Case).order_by(
                        Case.received_at.desc()
                    )
                ).all()
            ]

    @staticmethod
    def to_dict(case_record):

        if not case_record:
            return None

        return {
            key: getattr(
                case_record,
                key
            )
            for key in [
                "case_key",
                "category",
                "subject",
                "sender",
                "received_at",
                "status",
                "problem_statement",
                "recommendation",
                "explainability",
                "draft_body",
                "evidence",
                "extracted",
                "sources"
            ]
        }

    @staticmethod
    def case_key(message):

        subject = (
            message.get(
                "subject",
                ""
            ) or ""
        ).upper()

        # Standard IDs such as RFACU-12345
        match = re.search(
            r"([A-Z]{2,}\-?\d{3,})",
            subject
        )

        if match:
            return match.group(1)

        # Subjects such as:
        # RFACU - Lakeview Residences - Cost Approval
        category_match = re.match(
            r"\s*(RFA[A-Z]*|MOU)\b",
            subject
        )

        if category_match:

            category = category_match.group(1)

            # Create a stable key from the Graph message ID.
            message_id = message.get("id")

            if message_id:
                return (
                    f"{category}-"
                    f"{message_id[:12]}"
                )

            return category

        return (
            message.get(
                "internetMessageId"
            )
            or message.get("id")
        )

    @staticmethod
    def parse_dt(value):

        try:
            return (
                datetime.fromisoformat(
                    value.replace(
                        "Z",
                        "+00:00"
                    )
                )
                if value
                else datetime.now(
                    timezone.utc
                )
            )

        except Exception:
            return datetime.now(
                timezone.utc
            )