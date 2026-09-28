# Reference Architecture

```text
Outlook / Microsoft Graph ─┐
SharePoint / Graph ─────────┤
Pega REST ──────────────────┤
ServiceNow REST ────────────┤──> Context Aggregator ─> LangGraph Reasoning
Monday.com GraphQL ─────────┘                              │
                                                          ├─ Recommendation
                                                          ├─ Explainability
                                                          └─ Tone/Voice Draft
                                                                  │
                                                        Decision Card / Console
                                                                  │
                                                     Human Approve/Edit/Reject/
                                                          Request Clarification
                                                                  │
                                                        Outlook Draft (Graph)
                                                                  │
                                                        Audit + Learning Loop
```

The design intentionally keeps deterministic validation/calculation outside the LLM. LLM output is advisory and evidence-grounded; the human owns the final procurement decision.
