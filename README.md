# Procurement Decision Copilot

An AI-powered Procurement Decision Copilot that connects Microsoft Outlook email, Microsoft Graph, document attachments, RFA reference knowledge, LangGraph, Azure OpenAI, and human-in-the-loop decision workflows.

The system detects procurement-related RFA emails, extracts relevant evidence from emails and attachments, retrieves applicable RFA guidance, analyzes the case using Azure OpenAI, generates an explainable Decision Card, and allows a human reviewer to approve, reject, or request clarification.

---

# 1. System Architecture

```text
Microsoft Outlook
       |
       v
Microsoft Graph API
       |
       v
RFA Detection
       |
       v
Case Creation
       |
       +----------------------+
       |                      |
       v                      v
Email Evidence        Attachments
                              |
                              v
                    Document Extraction
                              |
                              v
                     PDF / DOCX / XLSX
                     CSV / TXT / PPTX
                     JSON / XML / Images
       |                      |
       +----------+-----------+
                  |
                  v
          Context Aggregation
                  |
                  v
            LangGraph Workflow
                  |
        +---------+---------+
        |         |         |
        v         v         v
   Evidence    RFA      Historical
   Validation  Guidance  Context
        |         |         |
        +---------+---------+
                  |
                  v
            Azure OpenAI
                  |
                  v
          Decision Card
                  |
                  v
        Human Reviewer
          /      |      \
         /       |       \
    Approve    Reject   Clarify
         |
         v
    Outlook Draft
```

---

# 2. Requirements

Before running the project, install the following:

- Python 3.9+
- Git
- Microsoft account with access to Microsoft Graph
- Azure OpenAI resource
- Azure OpenAI model deployment
- macOS / Linux / Windows

Recommended:

- Python 3.11
- VS Code
- Docker Desktop
- Azure Functions Core Tools

---

# 3. Clone the Repository

Open a terminal and run:

```bash
git clone https://github.com/YOUR_USERNAME/procurement-decision-copilot.git
```

Move into the project:

```bash
cd procurement-decision-copilot
```

---

# 4. Create a Python Virtual Environment

## macOS / Linux

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

You should see:

```text
(.venv)
```

at the beginning of your terminal.

## Windows

```powershell
python -m venv .venv
```

Activate:

```powershell
.venv\Scripts\activate
```

---

# 5. Upgrade pip

```bash
python -m pip install --upgrade pip
```

---

# 6. Install Project Dependencies

Run:

```bash
pip install -r requirements.txt
```

The project uses packages for:

- Flask
- Microsoft Graph / MSAL
- Azure OpenAI
- LangChain
- LangGraph
- document processing
- database / persistence
- API integration
- testing

---

# 7. Document Extraction Dependencies

The application can process procurement attachments such as:

- PDF
- DOCX
- XLSX
- XLS
- CSV
- TXT
- Markdown
- JSON
- XML
- HTML
- RTF
- PPTX
- Images

Install the additional document-processing packages:

```bash
pip install python-pptx beautifulsoup4 striprtf xlrd pillow pytesseract
```

### macOS

For OCR support:

```bash
brew install tesseract
```

If you do not need image OCR, this step can be skipped.

---

# 8. Configure Environment Variables

Create a local `.env` file:

```bash
cp .env.example .env
```

On Windows:

```powershell
copy .env.example .env
```

Open `.env` and configure:

```env
# Microsoft Graph
GRAPH_CLIENT_ID=your-microsoft-graph-client-id

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1-mini

# Application
ENVIRONMENT=development
DEMO_MODE=true
```

## Important

Never commit `.env` to GitHub.

Do NOT put the following in the public repository:

```text
.env
Azure OpenAI API keys
Microsoft Graph tokens
Graph token cache
Private emails
Private attachments
Internal company documents
Passwords
Client secrets
```

The repository should only contain `.env.example`.

---

# 9. Microsoft Graph Configuration

The application uses Microsoft Graph to read Outlook messages and create Outlook reply drafts.

Create/register an application in Microsoft Entra ID and obtain the Application / Client ID.

The application requires delegated permissions appropriate for the implemented Outlook workflow, including:

```text
User.Read
Mail.ReadWrite
```

Set the client ID in:

```env
GRAPH_CLIENT_ID=your-client-id
```

---

# 10. Microsoft Graph Login

The application uses Microsoft device-code authentication.

When the application needs authentication, the terminal will display instructions similar to:

```text
To sign in, use a web browser to open the page ...
and enter the code ...
```

Open the provided Microsoft login page and enter the displayed code.

After successful authentication, the application can access the configured Outlook mailbox according to the granted permissions.

> Authentication may need to be repeated if the token expires, is revoked, or Microsoft requires reauthentication.

---

# 11. Start the Backend

From the project root:

```bash
python -m app
```

Alternatively:

```bash
python wsgi.py
```

The application should start on:

```text
http://127.0.0.1:8000
```

Open this URL in your browser:

```text
http://127.0.0.1:8000
```

---

# 12. Check Application Health

Open:

```text
http://127.0.0.1:8000/api/health
```

Or run:

```bash
curl http://127.0.0.1:8000/api/health
```

A healthy configuration should return information similar to:

```json
{
  "status": "ok",
  "environment": "development",
  "demo_mode": true,
  "graph_configured": true,
  "azure_openai_configured": true
}
```

---

# 13. Discover Outlook Procurement Emails

The application can discover messages from the configured Outlook inbox.

Run:

```bash
curl http://127.0.0.1:8000/api/discover
```

The system identifies potential procurement/RFA-related emails.

---

# 14. Refresh / Ingest New Emails

Run:

```bash
curl -X POST http://127.0.0.1:8000/api/refresh
```

This triggers the email ingestion process.

The system can:

1. Read Outlook messages
2. Detect procurement/RFA emails
3. Create case records
4. Read message content
5. Process available attachments
6. Extract document text
7. Store the extracted evidence
8. Prepare the case for AI analysis

---

# 15. Process Attachments

When an Outlook email contains attachments, the system attempts to download and extract their content.

Supported examples include:

```text
PDF
DOCX
XLSX
XLS
CSV
TXT
MD
JSON
XML
HTML
RTF
PPTX
PNG
JPG
JPEG
TIFF
BMP
WEBP
```

Extracted attachment information becomes part of the case evidence.

The AI should therefore distinguish between:

```text
Email Evidence
Attachment Evidence
Reference Guidance
Historical Context
Inference
```

---

# 16. Run Automated Procurement Processing

The project includes an automation endpoint that ingests new emails and analyzes pending cases.

Run:

```bash
curl -X POST http://127.0.0.1:8000/api/automation/run
```

Example response:

```json
{
  "status": "ok",
  "ingested": 1,
  "analyzed": 1,
  "failed": 0,
  "skipped": 0
}
```

The automation does not re-analyze cases that already have a human decision.

---

# 17. List Procurement Cases

Run:

```bash
curl http://127.0.0.1:8000/api/cases
```

This returns the procurement cases currently known to the application.

---

# 18. View a Specific Case

Each case has a `case_key`.

Example:

```bash
curl http://127.0.0.1:8000/api/cases/CASE_KEY
```

Replace:

```text
CASE_KEY
```

with the actual case key returned by `/api/cases`.

---

# 19. Analyze a Procurement Case

Run:

```bash
curl -X POST http://127.0.0.1:8000/api/cases/CASE_KEY/analyze
```

Replace `CASE_KEY` with the required case.

The analysis uses the LangGraph workflow.

---

# 20. LangGraph Workflow

The main reasoning workflow contains multiple stages:

```text
1. Aggregate Context
        |
        v
2. Validate Evidence
        |
        v
3. Retrieve RFA Guidance
        |
        v
4. Reason and Recommend
        |
        v
5. Prepare Decision Card
```

### Aggregate Context

Combines:

- email information
- sender
- subject
- body
- attachments
- extracted document content
- historical information

### Validate Evidence

Checks whether the information required for a procurement decision is available.

The system can identify:

```text
Missing evidence
Contradictory evidence
Incomplete documentation
Unsupported claims
Unreadable attachments
```

### Retrieve RFA Guidance

Retrieves relevant RFA reference material from:

```text
data/rfa_reference/
```

The reference material provides guidance to the AI.

It is not treated as evidence that the current procurement request is valid.

### Reason and Recommend

Azure OpenAI analyzes the available information and generates a structured recommendation for human review.

### Prepare Decision Card

The final result is converted into a structured decision card for the reviewer.

---

# 21. Decision Card

The AI analysis contains structured fields including:

```text
Problem Statement
Confirmed Facts
Evidence Sufficiency
Missing Evidence
Recommendation
Decision Basis
Risks
Next Actions
Assumptions
Evidence Questions
Historical Context
Draft Reply
```

Evidence sufficiency can be:

```text
SUFFICIENT
PARTIALLY_SUFFICIENT
INSUFFICIENT
```

The system does NOT treat the AI output as an automatic procurement approval.

A human reviewer remains responsible for the final decision.

---

# 22. Human Decision

A reviewer can submit a decision using:

```bash
curl -X POST http://127.0.0.1:8000/api/cases/CASE_KEY/decision \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "approved",
    "comment": "Reviewed and approved."
  }'
```

Possible decision values include:

```text
approved
rejected
revision_requested
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/cases/CASE_KEY/decision \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "revision_requested",
    "comment": "Please provide the revised BOQ and vendor cost breakdown."
  }'
```

---

# 23. Create an Outlook Draft

After the human decision, an Outlook reply draft can be created.

Run:

```bash
curl -X POST http://127.0.0.1:8000/api/cases/CASE_KEY/outlook-draft
```

The system uses Microsoft Graph to create the reply draft.

The draft is created in Outlook for human review.

The system does not automatically send the email.

---

# 24. Audit History

View the case audit history:

```bash
curl http://127.0.0.1:8000/api/audit/CASE_KEY
```

This provides a history of important case actions and decisions.

---

# 25. RFA Knowledge Base

The repository contains demo/reference RFA knowledge files:

```text
data/rfa_reference/
```

Examples:

```text
01_RFA_General.md
02_RFAWO_Work_Order.md
03_RFACU_Cost_Upward.md
04_RFAMW_Material_Work.md
05_RFAPN_Price_Negotiation.md
06_RFASTND_Standard.md
07_RFASP_Special.md
08_MOU_Memorandum.md
09_RFA_Clarification.md
```

These documents are retrieved during the LangGraph workflow to provide contextual procurement guidance.

---

# 26. Azure OpenAI

The project uses Azure OpenAI for procurement reasoning.

Configure:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1-mini
```

The model is used to analyze:

```text
Email evidence
Attachment evidence
RFA guidance
Historical context
Missing information
Risks
Commercial information
Procurement requirements
```

The AI is instructed not to invent missing evidence.

---

# 27. MCP Server

The project also contains an MCP server:

```text
mcp_server/server.py
```

Create a separate environment if required:

```bash
cd mcp_server
python3 -m venv .venv
source .venv/bin/activate
pip install mcp
```

Run:

```bash
python server.py
```

The MCP server is designed to expose procurement-related capabilities to an MCP-compatible client.

---

# 28. Azure Functions Automation

The project contains an Azure Functions timer trigger:

```text
azure_function/function_app.py
```

Its purpose is to periodically call:

```text
/api/automation/run
```

The schedule is configured through:

```text
TIMER_SCHEDULE
```

Example:

```env
TIMER_SCHEDULE=0 */3 * * * *
```

This means the function is configured to run every 3 minutes when that schedule is used.

For local Azure Functions development:

```bash
cd azure_function
func start
```

The local function calls the backend automation endpoint.

---

# 29. Running Azure Functions Locally

Install Azure Functions Core Tools.

Then start the backend first:

```bash
cd ..
source .venv/bin/activate
python -m app
```

Open another terminal:

```bash
cd azure_function
func start
```

The timer function should appear in the Functions host output.

---

# 30. Docker

The project also contains:

```text
Dockerfile
docker-compose.yml
```

Build the application:

```bash
docker build -t procurement-decision-copilot .
```

Run:

```bash
docker run --env-file .env -p 8000:8000 procurement-decision-copilot
```

Then open:

```text
http://127.0.0.1:8000
```

If using Docker Compose:

```bash
docker compose up --build
```

---

# 31. Run Tests

From the project root:

```bash
pytest
```

Or:

```bash
python -m pytest
```

The tests are located in:

```text
tests/
```

---

# 32. Test Azure OpenAI Connection

The repository contains:

```text
test_azure.py
```

Run:

```bash
python test_azure.py
```

This can be used to verify Azure OpenAI configuration before running the complete application.

---

# 33. Test Microsoft Graph

The repository contains:

```text
test_graph.py
```

Run:

```bash
python test_graph.py
```

The first run may require Microsoft device-code authentication.

---

# 34. Recommended First Run

For someone setting up the project for the first time, the simplest sequence is:

```bash
git clone https://github.com/YOUR_USERNAME/procurement-decision-copilot.git

cd procurement-decision-copilot

python3 -m venv .venv

source .venv/bin/activate

python -m pip install --upgrade pip

pip install -r requirements.txt

cp .env.example .env
```

Configure `.env`.

Then:

```bash
python test_azure.py
```

If Azure OpenAI works:

```bash
python test_graph.py
```

Authenticate with Microsoft if requested.

Then start the application:

```bash
python -m app
```

Open:

```text
http://127.0.0.1:8000
```

---

# 35. Complete Demo Flow

A complete local demonstration can be performed as follows:

### Step 1

Start the application:

```bash
python -m app
```

### Step 2

Check health:

```bash
curl http://127.0.0.1:8000/api/health
```

### Step 3

Discover Outlook messages:

```bash
curl http://127.0.0.1:8000/api/discover
```

### Step 4

Ingest new procurement emails:

```bash
curl -X POST http://127.0.0.1:8000/api/refresh
```

### Step 5

Run the procurement automation:

```bash
curl -X POST http://127.0.0.1:8000/api/automation/run
```

### Step 6

List cases:

```bash
curl http://127.0.0.1:8000/api/cases
```

### Step 7

Analyze a case:

```bash
curl -X POST http://127.0.0.1:8000/api/cases/CASE_KEY/analyze
```

### Step 8

Review the Decision Card in the web interface.

### Step 9

Submit the human decision.

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/cases/CASE_KEY/decision \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "approved",
    "comment": "Approved after review."
  }'
```

### Step 10

Create an Outlook draft:

```bash
curl -X POST http://127.0.0.1:8000/api/cases/CASE_KEY/outlook-draft
```

### Step 11

Open Outlook and review the generated draft.

---

# 36. Important Security Notes

This project can connect to real Outlook mailboxes and Azure OpenAI.

Before deploying or sharing the repository publicly:

### Never commit:

```text
.env
API keys
Access tokens
Refresh tokens
Graph token cache
Private email messages
Private attachments
Company documents
Passwords
Production credentials
```

### Use:

```text
.env.example
```

for configuration examples.

---

# 37. Human-in-the-Loop Principle

The system is designed as a decision-support system rather than an autonomous procurement approval system.

The AI:

```text
Reads evidence
       |
       v
Validates evidence
       |
       v
Retrieves relevant guidance
       |
       v
Identifies missing information
       |
       v
Analyzes risks
       |
       v
Generates recommendation
       |
       v
Human reviews
       |
       v
Human makes final decision
```

The final procurement decision remains with the authorized human reviewer.

---

# 38. Project Structure

```text
procurement-decision-copilot/
│
├── app/
│   ├── connectors/
│   │   ├── graph_api.py
│   │   ├── local_discovery.py
│   │   ├── local_outlook.py
│   │   └── project_systems.py
│   │
│   ├── graph/
│   │   └── workflow.py
│   │
│   ├── services/
│   │   ├── ai.py
│   │   ├── cases.py
│   │   ├── context.py
│   │   ├── documents.py
│   │   ├── rfa_knowledge.py
│   │   └── voice.py
│   │
│   ├── static/
│   ├── templates/
│   ├── app.py
│   ├── config.py
│   └── models.py
│
├── azure_function/
│   ├── function_app.py
│   ├── host.json
│   └── requirements.txt
│
├── data/
│   └── rfa_reference/
│
├── docs/
│   └── architecture.md
│
├── mcp_server/
│   └── server.py
│
├── tests/
│   ├── test_core.py
│   └── test_rfa_knowledge.py
│
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── run.sh
├── run_windows.bat
└── README.md
```

---

# 39. Troubleshooting

## Python command not found

Try:

```bash
python3 --version
```

Then create the environment using:

```bash
python3 -m venv .venv
```

---

## Virtual environment not activated

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

---

## Azure OpenAI configuration error

Check:

```bash
cat .env
```

Make sure the following are configured:

```env
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT_NAME=
```

Do not publish the values.

---

## Microsoft Graph authentication problem

Check:

```env
GRAPH_CLIENT_ID=
```

Then run:

```bash
python test_graph.py
```

Follow the Microsoft device-code authentication instructions.

---

## Port 8000 already in use

Find the process:

```bash
lsof -i :8000
```

Then stop it or use the appropriate application configuration.

---

## Dependency installation problem

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Then:

```bash
pip install -r requirements.txt
```

---

# 40. Quick Start

For a quick setup:

```bash
git clone https://github.com/YOUR_USERNAME/procurement-decision-copilot.git
cd procurement-decision-copilot

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
```

Configure `.env`.

Then:

```bash
python test_azure.py
python test_graph.py
python -m app
```

Open:

```text
http://127.0.0.1:8000
```

---

# 41. Core Technologies

```text
Python
Flask
Microsoft Graph API
Microsoft Outlook
Microsoft Entra ID
MSAL
Azure OpenAI
LangChain
LangGraph
MCP
Azure Functions
Docker
Document Extraction
Human-in-the-Loop AI
```

---

# 42. Purpose

The Procurement Decision Copilot demonstrates how enterprise procurement workflows can be augmented with AI while maintaining:

- Evidence-based reasoning
- Explainability
- Document awareness
- RFA knowledge retrieval
- Risk identification
- Human approval
- Outlook integration
- Auditability
- Automated workflow execution

The project is intended as a technical demonstration and should be adapted to an organization's security, compliance, authentication, data-retention, and procurement policies before production use.