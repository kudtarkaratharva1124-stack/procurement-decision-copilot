/* ============================================================
   PROCUREMENT DECISION COPILOT
   Frontend
   ============================================================ */

let cases = [];
let selectedCaseKey = null;


/* ============================================================
   GENERAL HELPERS
   ============================================================ */

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function htmlToPlainText(value) {
    if (!value) return "";

    let html = String(value);

    html = html.replace(/\\</g, "<");
    html = html.replace(/\\>/g, ">");

    html = html.replace(/<br\s*\/?>/gi, "\n");
    html = html.replace(/<\/div>/gi, "\n");
    html = html.replace(/<\/p>/gi, "\n");
    html = html.replace(/<\/li>/gi, "\n");

    html = html.replace(
        /<style[\s\S]*?<\/style>/gi,
        ""
    );

    html = html.replace(
        /<script[\s\S]*?<\/script>/gi,
        ""
    );

    html = html.replace(
        /<head[\s\S]*?<\/head>/gi,
        ""
    );

    const temp = document.createElement("div");
    temp.innerHTML = html;

    let text =
        temp.textContent ||
        temp.innerText ||
        "";

    return text
        .replace(/\r/g, "")
        .replace(/[ \t]+\n/g, "\n")
        .replace(/\n[ \t]+/g, "\n")
        .replace(/\n{3,}/g, "\n\n")
        .trim();
}


function parsePossibleJson(value) {
    if (value === null || value === undefined) {
        return null;
    }

    if (typeof value === "object") {
        return value;
    }

    if (typeof value !== "string") {
        return value;
    }

    const text = value.trim();

    if (
        (text.startsWith("{") && text.endsWith("}")) ||
        (text.startsWith("[") && text.endsWith("]"))
    ) {
        try {
            return JSON.parse(text);
        } catch (e) {
            return value;
        }
    }

    return value;
}


function formatDate(value) {
    if (!value) return "—";

    try {
        const d = new Date(value);

        if (Number.isNaN(d.getTime())) {
            return String(value);
        }

        return d.toLocaleString();
    } catch (e) {
        return String(value);
    }
}


function getStatusLabel(status) {
    const s = String(status || "pending").toLowerCase();

    if (s === "approved") {
        return "Approved";
    }

    if (s === "rejected") {
        return "Rejected";
    }

    if (s === "revision_requested") {
        return "Clarification Requested";
    }

    if (s === "pending") {
        return "Pending";
    }

    if (s === "new") {
        return "New";
    }

    return s.replace(/_/g, " ");
}


function getStatusClass(status) {
    const s = String(status || "pending").toLowerCase();

    if (s === "approved") return "approved";
    if (s === "rejected") return "rejected";
    if (s === "revision_requested") return "revision_requested";

    return "pending";
}


/* ============================================================
   API HELPER
   ============================================================ */

async function api(url, options = {}) {

    const response = await fetch(url, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    });

    let data = null;

    try {
        data = await response.json();
    } catch (e) {
        data = null;
    }

    if (!response.ok) {

        throw new Error(
            data?.error ||
            data?.message ||
            `Request failed: ${response.status}`
        );
    }

    return data;
}


/* ============================================================
   LOAD CASES
   ============================================================ */

async function load() {

    try {

        const data =
            await api("/api/cases");

        cases =
            Array.isArray(data)
                ? data
                : [];

        updateStats();
        renderCases();

        if (selectedCaseKey) {

            const selected =
                cases.find(
                    c => c.case_key === selectedCaseKey
                );

            if (selected) {

                renderCase(selected);

            } else {

                selectedCaseKey = null;
                renderEmpty();
            }

        }

    } catch (error) {

        console.error(
            "Failed to load cases:",
            error
        );

        const container =
            document.getElementById("cases");

        if (container) {

            container.innerHTML = `
                <div class="empty">
                    Unable to load cases.
                    <br><br>
                    ${escapeHtml(error.message)}
                </div>
            `;
        }
    }
}


/* ============================================================
   UPDATE DASHBOARD STATS
   ============================================================ */

function updateStats() {

    const caseCount =
        document.getElementById("caseCount");

    const pendingCount =
        document.getElementById("pendingCount");


    if (caseCount) {

        caseCount.textContent =
            cases.length;
    }


    if (pendingCount) {

        const pending =
            cases.filter(c => {

                const status =
                    String(
                        c.status || "pending"
                    ).toLowerCase();

                return (
                    status === "pending" ||
                    status === "new" ||
                    status === "revision_requested"
                );
            });

        pendingCount.textContent =
            pending.length;
    }
}


/* ============================================================
   RENDER CASE LIST
   ============================================================ */

function renderCases() {

    const container =
        document.getElementById("cases");

    if (!container) return;


    if (!cases.length) {

        container.innerHTML = `
            <div class="empty">
                No RFA cases found.
                <br><br>
                Click <strong>Refresh Inbox</strong>
                to scan Outlook.
            </div>
        `;

        return;
    }


    container.innerHTML =
        cases.map(c => {

            const selected =
                c.case_key === selectedCaseKey
                    ? "selected"
                    : "";

            const status =
                getStatusLabel(c.status);

            const statusClass =
                getStatusClass(c.status);


            return `
                <div
                    class="case ${selected}"
                    onclick="selectCase('${encodeURIComponent(c.case_key)}')"
                >

                    <div class="subject">
                        ${escapeHtml(
                            c.subject ||
                            "Untitled RFA"
                        )}
                    </div>

                    <small>
                        ${escapeHtml(
                            c.case_key || ""
                        )}
                    </small>

                    <div>

                        <span class="pill">
                            ${escapeHtml(
                                status
                            )}
                        </span>

                        <span class="pill category">
                            ${escapeHtml(
                                c.category ||
                                "RFA"
                            )}
                        </span>

                    </div>

                    <small>
                        ${escapeHtml(
                            formatDate(c.received_at)
                        )}
                    </small>

                </div>
            `;
        }).join("");
}


/* ============================================================
   SELECT CASE
   ============================================================ */

async function selectCase(encodedKey) {

    const caseKey =
        decodeURIComponent(encodedKey);

    selectedCaseKey =
        caseKey;

    /*
     * Immediately render from existing data.
     */
    const existing =
        cases.find(
            c => c.case_key === caseKey
        );

    if (existing) {

        renderCases();
        renderCase(existing);
    }


    /*
     * Then get the latest copy from backend.
     */
    try {

        const fresh =
            await api(
                `/api/cases/${encodeURIComponent(caseKey)}`
            );


        const index =
            cases.findIndex(
                c => c.case_key === caseKey
            );


        if (index >= 0) {
            cases[index] = fresh;
        }


        renderCases();
        renderCase(fresh);

    } catch (error) {

        console.error(
            "Failed to load selected case:",
            error
        );
    }
}


/* ============================================================
   EMPTY DETAIL
   ============================================================ */

function renderEmpty() {

    const detail =
        document.getElementById("detail");

    if (!detail) return;

    detail.innerHTML = `
        <div class="empty">
            Select a case to inspect its Decision Card.
        </div>
    `;
}


/* ============================================================
   ARRAY / LIST RENDERER
   ============================================================ */

function renderList(items, ordered = false) {

    if (!Array.isArray(items) || !items.length) {

        return `
            <div class="empty-inline">
                None identified.
            </div>
        `;
    }


    const tag =
        ordered ? "ol" : "ul";


    return `
        <${tag} class="decision-list">

            ${items.map(item => {

                let value =
                    item;

                if (
                    typeof item === "object"
                ) {

                    value =
                        item.text ||
                        item.description ||
                        item.name ||
                        JSON.stringify(
                            item
                        );
                }

                return `
                    <li>
                        ${escapeHtml(
                            value
                        )}
                    </li>
                `;
            }).join("")}

        </${tag}>
    `;
}


/* ============================================================
   RENDER DECISION CARD
   ============================================================ */

function renderCase(c) {

    const detail =
        document.getElementById("detail");

    if (!detail) return;


    const explanation =
        c.explainability || {};


    const risks =
        Array.isArray(
            explanation.risks
        )
            ? explanation.risks
            : [];


    const nextActions =
        Array.isArray(
            explanation.next_actions
        )
            ? explanation.next_actions
            : [];


    const assumptions =
        Array.isArray(
            explanation.assumptions
        )
            ? explanation.assumptions
            : [];


    const evidenceQuestions =
        Array.isArray(
            explanation.evidence_questions
        )
            ? explanation.evidence_questions
            : [];


    const status =
        getStatusLabel(
            c.status
        );


    const statusClass =
        getStatusClass(
            c.status
        );


    detail.innerHTML = `

        <div class="decision-header">

            <div>

                <div class="eyebrow">
                    PROCUREMENT DECISION CARD
                </div>

                <h2>
                    ${escapeHtml(
                        c.subject ||
                        "Untitled Case"
                    )}
                </h2>

                <div class="case-meta">

                    Case:
                    <strong>
                        ${escapeHtml(
                            c.case_key || "—"
                        )}
                    </strong>

                    &nbsp; • &nbsp;

                    Category:
                    <strong>
                        ${escapeHtml(
                            c.category || "—"
                        )}
                    </strong>

                    &nbsp; • &nbsp;

                    Received:
                    <strong>
                        ${escapeHtml(
                            formatDate(
                                c.received_at
                            )
                        )}
                    </strong>

                </div>

            </div>


            <div
                class="decision-status ${statusClass}"
            >
                ${escapeHtml(status)}
            </div>

        </div>


        <!-- ==================================================
             PROBLEM
             ================================================== -->

        <div class="card">

            <div class="card-title">

                <span class="icon">
                    01
                </span>

                Problem Statement

            </div>

            <div class="answer">

                ${escapeHtml(
                    c.problem_statement ||
                    "AI analysis has not been run yet."
                )}

            </div>

        </div>


        <!-- ==================================================
             RECOMMENDATION
             ================================================== -->

        <div class="card recommendation-card">

            <div class="card-title">

                <span class="icon">
                    02
                </span>

                AI Recommendation

            </div>

            <div class="recommendation">

                ${escapeHtml(
                    c.recommendation ||
                    "AI analysis has not been run yet."
                )}

            </div>

        </div>


        <!-- ==================================================
             EXPLAINABILITY
             ================================================== -->

        <div class="two-column">


            <div class="card">

                <div class="card-title">

                    <span class="icon">
                        03
                    </span>

                    Key Risks

                </div>

                ${renderList(
                    risks
                )}

            </div>


            <div class="card">

                <div class="card-title">

                    <span class="icon">
                        04
                    </span>

                    Next Actions

                </div>

                ${renderList(
                    nextActions,
                    true
                )}

            </div>

        </div>


        <!-- ==================================================
             EVIDENCE QUESTIONS
             ================================================== -->

        <div class="card">

            <div class="card-title">

                <span class="icon">
                    05
                </span>

                Evidence Questions

            </div>

            ${renderList(
                evidenceQuestions
            )}

        </div>


        <!-- ==================================================
             ASSUMPTIONS
             ================================================== -->

        <div class="card">

            <div class="card-title">

                <span class="icon">
                    06
                </span>

                Assumptions

            </div>

            ${renderList(
                assumptions
            )}

        </div>


        <!-- ==================================================
             LIVE CASE EVIDENCE
             ================================================== -->

        <div class="card">

            <div class="card-title">

                <span class="icon">
                    07
                </span>

                Live Case Evidence

            </div>

            ${renderEvidence(
                c.evidence || [],
                c.extracted || {}
            )}

        </div>


        <!-- ==================================================
             DRAFT RESPONSE
             ================================================== -->

        <div class="card draft-card">

            <div class="card-title">

                <span class="icon">
                    08
                </span>

                Draft Response

            </div>

            <div class="helper">
                Review or edit the response before approval.
                Approval will save the final response directly
                to Outlook Drafts.
            </div>

            <br>

            <textarea
                id="draftResponse"
                placeholder="AI-generated draft response..."
            >${escapeHtml(
                c.draft_body || ""
            )}</textarea>

        </div>


        <!-- ==================================================
             HUMAN REVIEW
             ================================================== -->

        <div class="card">

            <div class="card-title">

                <span class="icon">
                    09
                </span>

                Human Review Note

            </div>

            <textarea
                id="reviewNote"
                style="min-height:100px"
                placeholder="Optional review note..."
            ></textarea>

        </div>


        <!-- ==================================================
             DECISION ACTIONS
             ================================================== -->

        <div class="card">

            <div class="card-title">

                Human Decision

            </div>

            <div class="decision-actions">

                <button
                    class="approve-button"
                    onclick="decide('approved')"
                >
                    ✓ Approve
                </button>

                <button
                    class="danger"
                    onclick="decide('rejected')"
                >
                    ✕ Reject
                </button>

                <button
                    class="primary-button"
                    onclick="analyze('${encodeURIComponent(c.case_key)}')"
                >
                    ↻ Regenerate
                </button>

                <button
                    class="clarify-button"
                    onclick="decide('revision_requested')"
                >
                    ? Clarify
                </button>

            </div>

        </div>
    `;
}


/* ============================================================
   EVIDENCE
   ============================================================ */

function renderEvidence(
    evidence,
    extracted
) {

    let html = "";


    const historical = [];
    const otherEvidence = [];


    function getSource(item) {

        return String(
            item?.source ||
            item?.title ||
            item?.type ||
            ""
        ).toLowerCase();
    }


    function getValue(item) {

        if (!item) {
            return null;
        }


        let value =
            item.content ??
            item.text ??
            item.value ??
            item.data ??
            item.evidence ??
            item;


        return parsePossibleJson(
            value
        );
    }


    function isHistorical(item) {

        const source =
            getSource(item);


        return (
            source.includes("historical") ||
            source.includes("history") ||
            source.includes("previous decision") ||
            source.includes("historical decision")
        );
    }


    function isOutlook(item) {

        const source =
            getSource(item);


        return (
            source.includes("outlook") ||
            source.includes("mailbox") ||
            source.includes("email")
        );
    }


    /*
     * Separate evidence categories.
     */
    (evidence || []).forEach(item => {

        if (isHistorical(item)) {

            historical.push(item);

        } else if (!isOutlook(item)) {

            otherEvidence.push(item);
        }
    });


    /* ========================================================
       HISTORICAL DECISIONS
       ======================================================== */

    historical.forEach(item => {

        let data =
            getValue(item);


        /*
         * Deal with nested historical data.
         */
        if (
            data &&
            typeof data === "object" &&
            !Array.isArray(data)
        ) {

            if (
                data.data &&
                typeof data.data === "object"
            ) {
                data =
                    data.data;
            }

            if (
                data.content &&
                typeof data.content === "object"
            ) {
                data =
                    data.content;
            }
        }


        /*
         * Sometimes historical context is
         * represented as a JSON string.
         */
        if (
            typeof data === "string"
        ) {

            const parsed =
                parsePossibleJson(
                    data
                );

            if (
                parsed &&
                typeof parsed === "object"
            ) {
                data = parsed;
            }
        }


        if (
            data &&
            typeof data === "object" &&
            !Array.isArray(data)
        ) {

            html += `

                <div class="evidence">

                    <div class="evidence-source">
                        Historical Decision
                    </div>

                    <div class="evidence-content">

                        <strong>
                            Problem
                        </strong>

                        <div style="margin:5px 0 15px;">
                            ${escapeHtml(
                                data.problem_statement ||
                                data.problem ||
                                "Not available"
                            )}
                        </div>


                        <strong>
                            Recommendation
                        </strong>

                        <div style="margin:5px 0 15px;">
                            ${escapeHtml(
                                data.recommendation ||
                                "Not available"
                            )}
                        </div>


                        ${
                            data.status
                                ? `
                                    <span class="pill">
                                        Status:
                                        ${escapeHtml(
                                            data.status
                                        )}
                                    </span>
                                  `
                                : ""
                        }

                    </div>

                </div>
            `;

        } else {

            html += `

                <div class="evidence">

                    <div class="evidence-source">
                        Historical Decision
                    </div>

                    <div class="evidence-content">
                        ${escapeHtml(
                            String(
                                data ||
                                "No historical details available."
                            )
                        )}
                    </div>

                </div>
            `;
        }
    });


    /* ========================================================
       OTHER EVIDENCE
       ======================================================== */

    otherEvidence.forEach(item => {

        let data =
            getValue(item);


        if (
            data === null ||
            data === undefined
        ) {
            return;
        }


        let text;


        if (
            typeof data === "object"
        ) {

            text =
                JSON.stringify(
                    data,
                    null,
                    2
                );

        } else {

            text =
                String(data);
        }


        if (!text.trim()) {
            return;
        }


        html += `

            <div class="evidence">

                <div class="evidence-source">

                    ${escapeHtml(
                        item.source ||
                        item.title ||
                        "Evidence"
                    )}

                </div>

                <div class="evidence-content">

                    <div class="mono">
                        ${escapeHtml(
                            text
                        )}
                    </div>

                </div>

            </div>
        `;
    });


    /* ========================================================
       LIVE OUTLOOK EMAIL
       ======================================================== */

    if (
        extracted &&
        extracted.body
    ) {

        const emailText =
            htmlToPlainText(
                extracted.body
            );


        if (
            emailText.trim()
        ) {

            html += `

                <div class="evidence live-email">

                    <div class="evidence-source">

                        Microsoft Outlook —
                        Live Email

                    </div>

                    <div class="evidence-content email-body">

                        ${escapeHtml(
                            emailText
                        )}

                    </div>

                </div>
            `;
        }
    }


    if (!html.trim()) {

        return `
            <div class="empty-inline">
                No live evidence available.
            </div>
        `;
    }


    return html;
}


/* ============================================================
   REFRESH INBOX
   ============================================================ */

async function refreshInbox() {

    const button =
        document.querySelector(
            'button[onclick="refreshInbox()"]'
        );


    const originalText =
        button
            ? button.textContent
            : "Refresh Inbox";


    try {

        if (button) {

            button.disabled =
                true;

            button.textContent =
                "Refreshing...";
        }


        /*
         * IMPORTANT:
         * Backend route is /api/refresh
         */
        const result =
            await api(
                "/api/refresh",
                {
                    method: "POST"
                }
            );


        await load();


        const count =
            result?.ingested ?? 0;


        alert(
            `Inbox refreshed successfully.\n\n` +
            `${count} new RFA case(s) detected.`
        );


    } catch (error) {

        console.error(
            "Refresh Inbox failed:",
            error
        );


        alert(
            "Unable to refresh Outlook inbox.\n\n" +
            error.message
        );


    } finally {

        if (button) {

            button.disabled =
                false;

            button.textContent =
                originalText;
        }
    }
}


/* ============================================================
   START AI ANALYSIS
   ============================================================ */

async function startAIAnalysis() {

    if (!cases.length) {

        alert(
            "No RFA cases are available.\n\n" +
            "Click Refresh Inbox first."
        );

        return;
    }


    /*
     * Cases that have not been analyzed.
     */
    const unanalyzed =
        cases.filter(c => {

            const recommendation =
                String(
                    c.recommendation || ""
                ).trim();

            return !recommendation;
        });


    let targets =
        unanalyzed;


    /*
     * If everything is already analyzed,
     * ask whether to regenerate all.
     */
    if (!targets.length) {

        const rerun =
            confirm(
                "All cases already have AI analysis.\n\n" +
                "Do you want to regenerate the analysis for all cases?"
            );


        if (!rerun) {
            return;
        }


        targets =
            [...cases];
    }


    const confirmed =
        confirm(
            `Start AI analysis for ${targets.length} case(s)?\n\n` +
            "Azure OpenAI will analyze the live email, " +
            "historical context and RFA guidance."
        );


    if (!confirmed) {
        return;
    }


    const button =
        document.querySelector(
            'button[onclick="startAIAnalysis()"]'
        );


    try {

        if (button) {

            button.disabled =
                true;

            button.textContent =
                "AI Analyzing...";
        }


        let success =
            0;

        let failed =
            0;


        for (
            const c of targets
        ) {

            try {

                const result =
                    await api(
                        `/api/cases/${encodeURIComponent(c.case_key)}/analyze`,
                        {
                            method: "POST"
                        }
                    );


                const index =
                    cases.findIndex(
                        x =>
                            x.case_key ===
                            c.case_key
                    );


                if (index >= 0) {

                    cases[index] =
                        result;
                }


                success++;


                /*
                 * Show each analyzed case
                 * when it is being processed.
                 */
                selectedCaseKey =
                    c.case_key;

                renderCases();
                renderCase(
                    result
                );


            } catch (error) {

                failed++;

                console.error(
                    `AI analysis failed for ${c.case_key}:`,
                    error
                );
            }
        }


        updateStats();
        renderCases();


        alert(
            `AI analysis completed.\n\n` +
            `Successful: ${success}\n` +
            `Failed: ${failed}`
        );


    } catch (error) {

        console.error(
            "AI analysis failed:",
            error
        );


        alert(
            "Unable to start AI analysis.\n\n" +
            error.message
        );


    } finally {

        if (button) {

            button.disabled =
                false;

            button.textContent =
                "Start AI Analysis";
        }
    }
}


/* ============================================================
   REGENERATE ONE CASE
   ============================================================ */

async function analyze(
    encodedKey
) {

    const caseKey =
        decodeURIComponent(
            encodedKey
        );


    const confirmed =
        confirm(
            "Regenerate AI analysis for this case?"
        );


    if (!confirmed) {
        return;
    }


    try {

        const result =
            await api(
                `/api/cases/${encodeURIComponent(caseKey)}/analyze`,
                {
                    method: "POST"
                }
            );


        const index =
            cases.findIndex(
                c =>
                    c.case_key ===
                    caseKey
            );


        if (index >= 0) {

            cases[index] =
                result;
        }


        selectedCaseKey =
            caseKey;


        updateStats();
        renderCases();
        renderCase(
            result
        );


        alert(
            "AI analysis regenerated successfully."
        );


    } catch (error) {

        console.error(
            "Regeneration failed:",
            error
        );


        alert(
            "Unable to regenerate AI analysis.\n\n" +
            error.message
        );
    }
}


/* ============================================================
   HUMAN DECISION
   ============================================================ */

async function decide(
    decision
) {

    if (!selectedCaseKey) {

        alert(
            "Please select a case first."
        );

        return;
    }


    const draftElement =
        document.getElementById(
            "draftResponse"
        );


    const noteElement =
        document.getElementById(
            "reviewNote"
        );


    const editedDraft =
        draftElement
            ? draftElement.value
            : "";


    let note =
        noteElement
            ? noteElement.value.trim()
            : "";


    /* ========================================================
       APPROVE
       ======================================================== */

    if (
        decision === "approved"
    ) {

        if (!editedDraft.trim()) {

            alert(
                "The draft response is empty.\n\n" +
                "Please run AI analysis or enter the response " +
                "before approving."
            );

            return;
        }


        const confirmed =
            confirm(
                "Approve this response?\n\n" +
                "The final response will be saved directly " +
                "to Outlook Drafts."
            );


        if (!confirmed) {
            return;
        }
    }


    /* ========================================================
       REJECT
       ======================================================== */

    if (
        decision === "rejected"
    ) {

        const reason =
            prompt(
                "Why is this case being rejected?"
            );


        if (reason === null) {
            return;
        }


        if (!reason.trim()) {

            alert(
                "Please provide a rejection reason."
            );

            return;
        }


        note =
            reason.trim();


        const confirmed =
            confirm(
                "Reject this case?\n\n" +
                "The case and rejection reason will be " +
                "retained for historical reference."
            );


        if (!confirmed) {
            return;
        }
    }


    /* ========================================================
       CLARIFY
       ======================================================== */

    if (
        decision === "revision_requested"
    ) {

        const clarification =
            prompt(
                "What clarification or additional information is required?"
            );


        if (
            clarification === null
        ) {
            return;
        }


        if (!clarification.trim()) {

            alert(
                "Please enter the clarification required."
            );

            return;
        }


        note =
            clarification.trim();


        const confirmed =
            confirm(
                "Record this clarification request?"
            );


        if (!confirmed) {
            return;
        }
    }


    /* ========================================================
       SUBMIT
       ======================================================== */

    try {

        const result =
            await api(
                `/api/cases/${encodeURIComponent(selectedCaseKey)}/decision`,
                {
                    method: "POST",

                    body: JSON.stringify({

                        decision:
                            decision,

                        note:
                            note,

                        edited_draft:
                            editedDraft
                    })
                }
            );


        const index =
            cases.findIndex(
                c =>
                    c.case_key ===
                    selectedCaseKey
            );


        if (index >= 0) {

            cases[index] =
                result;
        }


        updateStats();
        renderCases();
        renderCase(
            result
        );


        /* ====================================================
           SUCCESS
           ==================================================== */

        if (
            decision === "approved"
        ) {

            alert(
                "Approved successfully.\n\n" +
                "The response has been saved to Outlook Drafts."
            );

        } else if (
            decision === "rejected"
        ) {

            alert(
                "Case rejected.\n\n" +
                "The case has been retained for historical reference."
            );

        } else if (
            decision === "revision_requested"
        ) {

            alert(
                "Clarification request recorded successfully."
            );
        }


    } catch (error) {

        console.error(
            "Decision failed:",
            error
        );


        alert(
            "Unable to save the decision.\n\n" +
            error.message
        );
    }
}


/* ============================================================
   DETECT INTEGRATIONS
   ============================================================ */

async function discover() {

    try {

        const result =
            await api(
                "/api/discover"
            );


        const graph =
            result.graph_configured
                ? "Connected"
                : "Not configured";


        const azure =
            result.azure_openai_configured
                ? "Connected"
                : "Not configured";


        const mailbox =
            result.mailbox_source ||
            "Unknown";


        alert(
            "Integration Status\n\n" +
            `Mailbox: ${mailbox}\n` +
            `Microsoft Graph: ${graph}\n` +
            `Azure OpenAI: ${azure}`
        );


        await loadHealth();


    } catch (error) {

        console.error(
            "Discover failed:",
            error
        );


        alert(
            "Unable to detect integrations.\n\n" +
            error.message
        );
    }
}


/* ============================================================
   HEALTH
   ============================================================ */

async function loadHealth() {

    try {

        const result =
            await api(
                "/api/health"
            );


        const aiStatus =
            document.getElementById(
                "aiStatus"
            );


        const graphStatus =
            document.getElementById(
                "graphStatus"
            );


        if (aiStatus) {

            aiStatus.textContent =
                result.azure_openai_configured
                    ? "Connected"
                    : "Not configured";
        }


        if (graphStatus) {

            graphStatus.textContent =
                result.graph_configured
                    ? "Connected"
                    : "Not configured";
        }


    } catch (error) {

        console.error(
            "Health check failed:",
            error
        );
    }
}


/* ============================================================
   INITIALIZE
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    async function () {

        renderEmpty();

        await loadHealth();

        await load();
    }
);