from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv

from ..config import settings
from .voice import VoiceProfileService
from .rfa_knowledge import RFAKnowledgeService

load_dotenv()


SYSTEM = """
You are the Procurement Decision Copilot reasoning engine.

Your purpose is to support a human procurement decision-maker.

You MUST NOT make the final procurement decision.

You MUST NOT invent facts.

You MUST clearly distinguish between:

1. LIVE CASE EVIDENCE
Information actually present in the current procurement email,
its attachments, extracted attachment contents, project context,
or retrieved historical records.

2. REFERENCE GUIDANCE
RFA category guidance and procedural reference material.

3. INFERENCE
Reasoning derived from the available evidence.

REFERENCE GUIDANCE IS NOT EVIDENCE.

HISTORICAL CONTEXT IS CONTEXT, NOT CURRENT-CASE EVIDENCE.

ATTACHMENT CONTENT THAT HAS BEEN SUCCESSFULLY EXTRACTED IS
LIVE CASE EVIDENCE, provided it is clearly associated with the
current procurement email.

If an attachment exists but its content could not be extracted,
do NOT assume what it contains. Report that the attachment exists
but its content could not be verified.

=========================================================
STEP 1 — UNDERSTAND THE REQUEST
=========================================================

Identify, when available:

- project
- contractor/vendor
- RFA category
- requested action
- requested amount/value
- reason for request
- deadline
- commercial impact
- requested approval or response

Use both the email body and readable attachment contents.

If a field is unavailable, do not invent it.

=========================================================
STEP 2 — REVIEW EMAIL AND ATTACHMENTS
=========================================================

Treat the procurement email and its readable attachments as
the primary current-case evidence.

Review attachment contents for information such as:

- quotations
- BOQs
- cost breakdowns
- revised prices
- scope of work
- work orders
- contracts
- negotiation summaries
- approvals
- invoices
- technical specifications
- vendor information
- quantities
- rates
- dates
- payment terms
- commercial conditions
- supporting calculations

Do not assume that every attachment is relevant.

Identify which attachment supports which fact whenever possible.

If an attachment contradicts the email, explicitly identify
the contradiction.

If multiple attachments contain conflicting values, do not
choose one silently. Identify the conflict and recommend
verification.

=========================================================
STEP 3 — VALIDATE THE EVIDENCE
=========================================================

Determine whether the available evidence supports the requested
procurement action.

Identify:

- confirmed facts
- missing evidence
- contradictory evidence
- information requiring verification
- unsupported claims
- attachment extraction failures

Never fill missing information with assumptions.

A readable attachment can strengthen evidence, but the existence
of an attachment alone does NOT mean that the claim has been
verified.

=========================================================
STEP 4 — APPLY RFA GUIDANCE
=========================================================

Use the retrieved RFA reference material as procedural guidance.

Explain which category-specific checks are relevant.

Do NOT treat the reference documents as evidence that the current
procurement request is valid.

For example, if an RFA guideline says that a quotation is normally
required, that does not mean a quotation was actually provided.

Verify that requirement against the live email and attachments.

=========================================================
STEP 5 — USE HISTORICAL CONTEXT
=========================================================

Consider relevant historical procurement decisions.

Historical decisions may help identify:

- previously requested documentation
- recurring issues
- consistency questions
- useful comparison points

Historical decisions must NOT automatically determine the current
recommendation.

Do not state that a historical decision proves that the current
case should receive the same treatment.

=========================================================
STEP 6 — IDENTIFY RISKS
=========================================================

Consider relevant:

- commercial risk
- cost risk
- documentation risk
- scope risk
- vendor/supplier risk
- schedule risk
- compliance/process risk

Only identify risks supported by the available information or
clearly label them as potential risks.

=========================================================
STEP 7 — RECOMMENDATION
=========================================================

Provide a recommendation for human review.

If evidence is insufficient, the recommendation should focus on
obtaining the missing evidence rather than pretending that the
request is ready for approval.

If attachments provide sufficient evidence for some parts but
not others, explicitly explain what is supported and what remains
unverified.

Never convert "attachment exists" into "attachment proves the claim."

=========================================================
STEP 8 — EXPLAINABILITY
=========================================================

The reasoning must explain:

- what is known
- what is supported by the email
- what is supported by attachments
- what is missing
- what guidance applies
- what assumptions were made
- what contradictions exist
- what risks exist
- what should happen next
- why the recommendation follows from the evidence

=========================================================
STEP 9 — DRAFT RESPONSE
=========================================================

Prepare a professional Outlook response.

The draft must NOT claim that a procurement decision has already
been approved unless the human reviewer explicitly approves it.

If supporting documents are missing, request the specific documents.

If documents are present but contradictory or incomplete, request
the specific clarification required.

=========================================================
OUTPUT
=========================================================

Return valid JSON with exactly these keys:

problem_statement
confirmed_facts
evidence_sufficiency
missing_evidence
recommendation
decision_basis
risks
next_actions
assumptions
evidence_questions
historical_context
draft_reply

evidence_sufficiency must be one of:

SUFFICIENT
PARTIALLY_SUFFICIENT
INSUFFICIENT

decision_basis must contain:

live_evidence
reference_guidance
inference

live_evidence should distinguish email evidence from attachment
evidence when useful.

Never make the final human procurement decision.
"""


class AIService:

    def __init__(self):
        self.llm = None
        self.voice = VoiceProfileService()
        self.knowledge = RFAKnowledgeService()

    # ------------------------------------------------------------------
    # AZURE OPENAI CLIENT
    # ------------------------------------------------------------------

    def _llm(self):

        if self.llm:
            return self.llm

        endpoint = os.getenv(
            "AZURE_OPENAI_ENDPOINT"
        )

        api_key = os.getenv(
            "AZURE_OPENAI_API_KEY"
        )

        deployment = os.getenv(
            "AZURE_OPENAI_DEPLOYMENT_NAME"
        )

        if (
            not endpoint
            or not api_key
            or not deployment
        ):
            return None

        from openai import OpenAI

        self.llm = OpenAI(
            api_key=api_key,
            base_url=(
                endpoint.rstrip("/")
                + "/openai/v1/"
            )
        )

        return self.llm

    # ------------------------------------------------------------------
    # ATTACHMENT EVIDENCE
    # ------------------------------------------------------------------

    def _build_attachment_evidence(
        self,
        case: dict,
    ) -> str:
        """
        Convert extracted attachment information into a clear
        evidence section for the LLM.

        Only successfully extracted text is presented as readable
        attachment evidence.

        Failed/unsupported attachments are still reported so that
        the model knows the evidence may be incomplete.
        """

        extracted = (
            case.get("extracted")
            or {}
        )

        attachment_content = (
            extracted.get(
                "attachment_content",
                []
            )
            or []
        )

        # Backward compatibility with the older local-Outlook
        # extraction structure.
        legacy_attachment_text = (
            extracted.get(
                "attachment_text",
                []
            )
            or []
        )

        sections = []

        # --------------------------------------------------------------
        # New attachment_content structure
        # --------------------------------------------------------------

        for index, item in enumerate(
            attachment_content,
            start=1
        ):

            if not isinstance(
                item,
                dict
            ):
                continue

            name = (
                item.get("name")
                or f"Attachment {index}"
            )

            status = (
                item.get("status")
                or "unknown"
            )

            content_type = (
                item.get(
                    "content_type"
                )
                or "unknown"
            )

            size = item.get(
                "size"
            )

            text = (
                item.get("text")
                or ""
            )

            section = (
                f"--- ATTACHMENT {index}: "
                f"{name} ---\n"
                f"STATUS: {status}\n"
                f"CONTENT TYPE: {content_type}\n"
            )

            if size is not None:
                section += (
                    f"SIZE BYTES: {size}\n"
                )

            if text.strip():

                section += (
                    "EXTRACTED CONTENT:\n"
                    f"{text[:50000]}"
                )

            else:

                error = (
                    item.get("error")
                    or "No readable content extracted."
                )

                section += (
                    "EXTRACTED CONTENT: "
                    "NOT AVAILABLE\n"
                    f"DETAIL: {error}"
                )

            sections.append(section)

        # --------------------------------------------------------------
        # Backward compatibility with attachment_text
        # --------------------------------------------------------------

        if not attachment_content:

            for index, item in enumerate(
                legacy_attachment_text,
                start=1
            ):

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                name = (
                    item.get("name")
                    or f"Attachment {index}"
                )

                text = (
                    item.get("text")
                    or ""
                )

                error = (
                    item.get("error")
                    or ""
                )

                section = (
                    f"--- ATTACHMENT {index}: "
                    f"{name} ---\n"
                )

                if text.strip():

                    section += (
                        "STATUS: extracted\n"
                        "EXTRACTED CONTENT:\n"
                        f"{text[:50000]}"
                    )

                else:

                    section += (
                        "STATUS: extraction_failed\n"
                        "EXTRACTED CONTENT: NOT AVAILABLE\n"
                        f"DETAIL: {error or 'No readable content extracted.'}"
                    )

                sections.append(section)

        if not sections:

            return (
                "No attachment content was extracted "
                "for this case."
            )

        return "\n\n".join(
            sections
        )

    # ------------------------------------------------------------------
    # CASE EVIDENCE SUMMARY
    # ------------------------------------------------------------------

    def _build_live_evidence(
        self,
        case: dict,
    ) -> str:
        """
        Build a structured current-case evidence block.

        This makes it easier for the model to distinguish:
        email evidence,
        attachment evidence,
        and system metadata.
        """

        extracted = (
            case.get("extracted")
            or {}
        )

        body = (
            extracted.get(
                "body",
                ""
            )
            or ""
        )

        attachments = (
            extracted.get(
                "attachments",
                []
            )
            or []
        )

        attachment_content = (
            extracted.get(
                "attachment_content",
                []
            )
            or []
        )

        evidence = {
            "case_key":
                case.get("case_key"),

            "category":
                case.get("category"),

            "subject":
                case.get("subject"),

            "sender":
                case.get("sender"),

            "email_body":
                body,

            "attachment_metadata":
                attachments,

            "attachment_content":
                attachment_content,

            "existing_evidence":
                case.get(
                    "evidence",
                    []
                ),

            "evidence_validation":
                case.get(
                    "evidence_validation",
                    {}
                )
        }

        return json.dumps(
            evidence,
            ensure_ascii=False,
            default=str
        )[:80000]

    # ------------------------------------------------------------------
    # ANALYSIS
    # ------------------------------------------------------------------

    def analyze(
        self,
        case: dict
    ) -> dict:

        client = self._llm()

        if not client:
            return self.demo(
                case
            )

        voice = self.voice.get(
            case.get(
                "approver",
                "default"
            )
        )

        references = case.get(
            "reference_guidance",
            []
        )

        reference_block = (
            "\n\n".join(
                f"--- REFERENCE GUIDANCE: "
                f"{r.get('name', 'Unknown')} ---\n"
                f"{r.get('content', '')[:10000]}"
                for r in references
            )
        )

        attachment_block = (
            self._build_attachment_evidence(
                case
            )
        )

        live_evidence_block = (
            self._build_live_evidence(
                case
            )
        )

        prompt = (
            SYSTEM

            + "\n\nVOICE PROFILE:\n"
            + json.dumps(
                voice,
                ensure_ascii=False,
                default=str
            )

            + "\n\nREFERENCE RFA GUIDANCE:\n"
            + (
                reference_block
                if reference_block
                else "No RFA reference guidance was retrieved."
            )

            + "\n\nEVIDENCE VALIDATION:\n"
            + json.dumps(
                case.get(
                    "evidence_validation",
                    {}
                ),
                ensure_ascii=False,
                default=str
            )

            + "\n\nHISTORICAL CONTEXT:\n"
            + json.dumps(
                case.get(
                    "historical_context",
                    []
                ),
                ensure_ascii=False,
                default=str
            )

            + "\n\nCURRENT CASE EVIDENCE:\n"
            + live_evidence_block

            + "\n\nATTACHED DOCUMENT EVIDENCE:\n"
            + attachment_block

            + "\n\nFULL LIVE CASE DATA:\n"
            + json.dumps(
                case,
                ensure_ascii=False,
                default=str
            )[:50000]
        )

        try:

            response = client.chat.completions.create(
                model=os.getenv(
                    "AZURE_OPENAI_DEPLOYMENT_NAME"
                ),

                messages=[
                    {
                        "role":
                            "system",

                        "content":
                            SYSTEM
                    },
                    {
                        "role":
                            "user",

                        "content":
                            prompt
                    }
                ],

                temperature=0
            )

            text = (
                response
                .choices[0]
                .message
                .content
            )

            return self._parse_json(
                text
            )

        except Exception as exc:

            return self._error_result(
                str(exc)
            )

    # ------------------------------------------------------------------
    # JSON PARSING
    # ------------------------------------------------------------------

    def _parse_json(
        self,
        text: str
    ) -> dict:
        """
        Parse JSON returned by the model.

        Handles:
        - standard JSON
        - markdown JSON fences
        - accidental surrounding text
        """

        text = (
            text or ""
        ).strip()

        if not text:

            return self._invalid_json_result(
                "The Azure OpenAI response was empty."
            )

        # --------------------------------------------------------------
        # Remove markdown code fences.
        # --------------------------------------------------------------

        if text.startswith("```"):

            text = re.sub(
                r"^```(?:json)?\s*",
                "",
                text,
                flags=re.IGNORECASE
            )

            text = re.sub(
                r"\s*```$",
                "",
                text
            )

            text = text.strip()

        # --------------------------------------------------------------
        # First attempt: direct JSON.
        # --------------------------------------------------------------

        try:

            result = json.loads(
                text
            )

            if isinstance(
                result,
                dict
            ):
                return self._normalize_result(
                    result
                )

        except Exception:
            pass

        # --------------------------------------------------------------
        # Second attempt: locate the outermost JSON object.
        # --------------------------------------------------------------

        start = text.find("{")
        end = text.rfind("}")

        if (
            start >= 0
            and end > start
        ):

            candidate = text[
                start:end + 1
            ]

            try:

                result = json.loads(
                    candidate
                )

                if isinstance(
                    result,
                    dict
                ):
                    return self._normalize_result(
                        result
                    )

            except Exception:
                pass

        return self._invalid_json_result(
            "LLM output was not valid JSON."
        )

    # ------------------------------------------------------------------
    # OUTPUT NORMALIZATION
    # ------------------------------------------------------------------

    def _normalize_result(
        self,
        result: dict
    ) -> dict:
        """
        Ensure the decision-card response has all expected fields.

        This prevents a partially valid LLM response from breaking
        the dashboard.
        """

        expected = [
            "problem_statement",
            "confirmed_facts",
            "evidence_sufficiency",
            "missing_evidence",
            "recommendation",
            "decision_basis",
            "risks",
            "next_actions",
            "assumptions",
            "evidence_questions",
            "historical_context",
            "draft_reply"
        ]

        for key in expected:

            if key not in result:

                if key in {
                    "confirmed_facts",
                    "missing_evidence",
                    "risks",
                    "next_actions",
                    "assumptions",
                    "evidence_questions",
                    "historical_context"
                }:
                    result[key] = []

                elif key == "decision_basis":
                    result[key] = {
                        "live_evidence": [],
                        "reference_guidance": [],
                        "inference": []
                    }

                elif key == "evidence_sufficiency":
                    result[key] = "INSUFFICIENT"

                else:
                    result[key] = ""

        # --------------------------------------------------------------
        # Normalize evidence sufficiency.
        # --------------------------------------------------------------

        allowed = {
            "SUFFICIENT",
            "PARTIALLY_SUFFICIENT",
            "INSUFFICIENT"
        }

        if (
            result.get(
                "evidence_sufficiency"
            )
            not in allowed
        ):
            result[
                "evidence_sufficiency"
            ] = "INSUFFICIENT"

        # --------------------------------------------------------------
        # Normalize decision_basis.
        # --------------------------------------------------------------

        decision_basis = result.get(
            "decision_basis"
        )

        if not isinstance(
            decision_basis,
            dict
        ):
            decision_basis = {}

        decision_basis.setdefault(
            "live_evidence",
            []
        )

        decision_basis.setdefault(
            "reference_guidance",
            []
        )

        decision_basis.setdefault(
            "inference",
            []
        )

        result[
            "decision_basis"
        ] = decision_basis

        # --------------------------------------------------------------
        # Ensure list fields are actually lists.
        # --------------------------------------------------------------

        list_fields = [
            "confirmed_facts",
            "missing_evidence",
            "risks",
            "next_actions",
            "assumptions",
            "evidence_questions",
            "historical_context"
        ]

        for field in list_fields:

            if not isinstance(
                result.get(field),
                list
            ):

                value = result.get(
                    field
                )

                if value:
                    result[field] = [
                        str(value)
                    ]
                else:
                    result[field] = []

        return result

    # ------------------------------------------------------------------
    # ERROR RESULTS
    # ------------------------------------------------------------------

    def _error_result(
        self,
        error: str
    ) -> dict:

        return {
            "problem_statement":
                "Azure AI analysis could not be completed.",

            "confirmed_facts":
                [],

            "evidence_sufficiency":
                "INSUFFICIENT",

            "missing_evidence":
                [],

            "recommendation":
                "Human review required.",

            "decision_basis": {
                "live_evidence":
                    [],
                "reference_guidance":
                    [],
                "inference":
                    []
            },

            "risks": [
                f"AI service error: {error}"
            ],

            "next_actions": [
                "Check Azure AI connection",
                "Validate the live case evidence",
                "Review any attached documents",
                "Approve, edit, reject, or request clarification"
            ],

            "assumptions":
                [],

            "evidence_questions":
                [],

            "historical_context":
                [],

            "draft_reply":
                "Please review the procurement request "
                "and confirm the appropriate action."
        }

    def _invalid_json_result(
        self,
        reason: str
    ) -> dict:

        return {
            "problem_statement":
                reason,

            "confirmed_facts":
                [],

            "evidence_sufficiency":
                "INSUFFICIENT",

            "missing_evidence":
                [],

            "recommendation":
                "Human review required.",

            "decision_basis": {
                "live_evidence":
                    [],
                "reference_guidance":
                    [],
                "inference":
                    []
            },

            "risks": [
                reason
            ],

            "next_actions": [
                "Validate the case evidence",
                "Review the AI response",
                "Record the human decision"
            ],

            "assumptions":
                [],

            "evidence_questions":
                [],

            "historical_context":
                [],

            "draft_reply":
                "Please review the decision card "
                "and confirm the appropriate procurement action."
        }

    # ------------------------------------------------------------------
    # DEMO MODE
    # ------------------------------------------------------------------

    def demo(
        self,
        case
    ):

        extracted = (
            case.get(
                "extracted"
            )
            or {}
        )

        attachment_content = (
            extracted.get(
                "attachment_content",
                []
            )
            or []
        )

        readable_attachments = [
            item.get("name")
            for item in attachment_content
            if isinstance(
                item,
                dict
            )
            and item.get("text")
        ]

        attachment_note = (
            "Readable attachments are available for review: "
            + ", ".join(
                readable_attachments
            )
            if readable_attachments
            else
            "No readable attachment content is available."
        )

        return {
            "problem_statement":
                f"Review "
                f"{case.get('category', 'RFA')} "
                f"case "
                f"{case.get('case_key')} "
                f"and resolve the key "
                "budget, commercial, evidence or delivery concern "
                "before approval.",

            "confirmed_facts": [
                f"Case category: "
                f"{case.get('category', 'Unknown')}",

                f"Case key: "
                f"{case.get('case_key', 'Unknown')}",

                attachment_note
            ],

            "evidence_sufficiency":
                "PARTIALLY_SUFFICIENT",

            "missing_evidence": [
                "Validate all required procurement supporting documents."
            ],

            "recommendation":
                "Validate the identified variance and supporting "
                "evidence, including any available attachments, "
                "then approve, reject, or request clarification.",

            "decision_basis": {
                "live_evidence": [
                    "Current procurement email data",
                    attachment_note
                ],

                "reference_guidance": [
                    "Applicable RFA procedural guidance should be reviewed."
                ],

                "inference": [
                    "Incomplete external-system context can change "
                    "the recommendation."
                ]
            },

            "next_actions": [
                "Validate commercial figures",
                "Review the email and supporting attachments",
                "Confirm policy/approval requirements",
                "Record the human decision"
            ],

            "assumptions": [
                "Demo mode is active; external system evidence "
                "may not be fully connected."
            ],

            "risks": [
                "Incomplete external-system context can change "
                "the recommendation."
            ],

            "evidence_questions": [
                "Are the quoted values consistent with the "
                "source documents?",
                "Are payment terms and delivery terms aligned?",
                "Do the supporting attachments contain all "
                "required procurement evidence?"
            ],

            "historical_context":
                [],

            "draft_reply":
                f"Hello,\n\n"
                f"Please review the decision card for case "
                f"{case.get('case_key')}.\n\n"
                f"The case requires validation of the key "
                f"commercial and evidence points, including "
                f"any supporting documents, before a final "
                f"procurement decision.\n\n"
                f"Regards,\n"
                f"Procurement Team"
        }