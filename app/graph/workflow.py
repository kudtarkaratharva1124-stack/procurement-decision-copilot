from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from ..services.ai import AIService
from ..services.rfa_knowledge import RFAKnowledgeService


class State(TypedDict, total=False):
    case: dict
    evidence: list
    extracted: dict

    reference_guidance: list
    historical_context: list
    evidence_validation: dict

    analysis: dict
    status: str


class ProcurementGraph:

    def __init__(self, context_service):
        self.context = context_service
        self.ai = AIService()
        self.knowledge = RFAKnowledgeService()
        self.graph = self._build()

    def _build(self):

        g = StateGraph(State)

        g.add_node(
            "aggregate_context",
            self.aggregate_context
        )

        g.add_node(
            "validate_evidence",
            self.validate_evidence
        )

        g.add_node(
            "retrieve_guidance",
            self.retrieve_guidance
        )

        g.add_node(
            "reason_and_recommend",
            self.reason_and_recommend
        )

        g.add_node(
            "prepare_decision_card",
            self.prepare_decision_card
        )

        g.add_edge(
            START,
            "aggregate_context"
        )

        g.add_edge(
            "aggregate_context",
            "validate_evidence"
        )

        g.add_edge(
            "validate_evidence",
            "retrieve_guidance"
        )

        g.add_edge(
            "retrieve_guidance",
            "reason_and_recommend"
        )

        g.add_edge(
            "reason_and_recommend",
            "prepare_decision_card"
        )

        g.add_edge(
            "prepare_decision_card",
            END
        )

        return g.compile()

    # ---------------------------------------------------------
    # 1. AGGREGATE CONTEXT
    # ---------------------------------------------------------

    def aggregate_context(self, state):

        case = state["case"]

        ctx = self.context.collect(case)

        state["evidence"] = ctx.get(
            "evidence",
            []
        )

        state["extracted"] = ctx.get(
            "extracted",
            {}
        )

        return state

    # ---------------------------------------------------------
    # 2. VALIDATE EVIDENCE
    # ---------------------------------------------------------

    def validate_evidence(self, state):

        case = state["case"]

        evidence = state.get(
            "evidence",
            []
        )

        extracted = state.get(
            "extracted",
            {}
        )

        body = extracted.get(
            "body",
            ""
        )

        missing = []

        if not body.strip():
            missing.append(
                "Original procurement email content"
            )

        if not evidence:
            missing.append(
                "Supporting procurement evidence"
            )

        state["evidence_validation"] = {
            "evidence_count": len(evidence),
            "missing_initial_evidence": missing
        }

        return state

    # ---------------------------------------------------------
    # 3. RETRIEVE RFA GUIDANCE
    # ---------------------------------------------------------

    def retrieve_guidance(self, state):

        case = dict(
            state["case"]
        )

        retrieved = self.knowledge.retrieve(
            case,
            limit=3
        )

        state["reference_guidance"] = [
            {
                "name": item.get("name"),
                "category": item.get("category"),
                "content": item.get("content", "")
            }
            for item in retrieved
        ]

        return state

    # ---------------------------------------------------------
    # 4. REASON AND RECOMMEND
    # ---------------------------------------------------------

    def reason_and_recommend(self, state):

        case = dict(
            state["case"]
        )

        case["evidence"] = state.get(
            "evidence",
            []
        )

        case["extracted"] = state.get(
            "extracted",
            {}
        )

        case["reference_guidance"] = (
            state.get(
                "reference_guidance",
                []
            )
        )

        case["historical_context"] = (
            state.get(
                "historical_context",
                []
            )
        )

        case["evidence_validation"] = (
            state.get(
                "evidence_validation",
                {}
            )
        )

        state["analysis"] = self.ai.analyze(
            case
        )

        return state

    # ---------------------------------------------------------
    # 5. PREPARE DECISION CARD
    # ---------------------------------------------------------

    def prepare_decision_card(self, state):

        analysis = state.get(
            "analysis",
            {}
        )

        state["case"].update({

            "problem_statement":
                analysis.get(
                    "problem_statement",
                    ""
                ),

            "recommendation":
                analysis.get(
                    "recommendation",
                    ""
                ),

            "draft_body":
                analysis.get(
                    "draft_reply",
                    ""
                ),

            "explainability": {

                "confirmed_facts":
                    analysis.get(
                        "confirmed_facts",
                        []
                    ),

                "evidence_sufficiency":
                    analysis.get(
                        "evidence_sufficiency",
                        "UNKNOWN"
                    ),

                "missing_evidence":
                    analysis.get(
                        "missing_evidence",
                        []
                    ),

                "decision_basis":
                    analysis.get(
                        "decision_basis",
                        {}
                    ),

                "risks":
                    analysis.get(
                        "risks",
                        []
                    ),

                "next_actions":
                    analysis.get(
                        "next_actions",
                        []
                    ),

                "assumptions":
                    analysis.get(
                        "assumptions",
                        []
                    ),

                "evidence_questions":
                    analysis.get(
                        "evidence_questions",
                        []
                    ),

                "historical_context":
                    analysis.get(
                        "historical_context",
                        []
                    )
            },

            "evidence":
                state.get(
                    "evidence",
                    []
                ),

            "extracted":
                state.get(
                    "extracted",
                    {}
                ),

            "sources": [
                item.get("source")
                for item in state.get(
                    "evidence",
                    []
                )
                if isinstance(item, dict)
                and item.get("source")
            ]
        })

        return state

    # ---------------------------------------------------------

    def run(self, case):

        result = self.graph.invoke({
            "case": case
        })

        return result["case"]