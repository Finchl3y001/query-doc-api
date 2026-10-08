# AI Document Intelligence & Knowledge API

A production-ready, asynchronous backend API built with **FastAPI**, **PostgreSQL**, and **SQLModel** that allows businesses to upload spreadsheets and text documents, extract and index their contents in the background, chunk the data, and perform intelligent Q&A queries against their knowledge bases using **Mistral AI** integration.

---

## 🚀 Key Features

*   **1. Multi-tenant / Organization Infrastructure**
    *   Robust multi-user model supporting **Users**, **Organizations**, **Memberships**, and **Roles** (*Admin*, *Manager*, *Member*).
    *   Strict, hierarchy-aware authorization tier checking workspace boundaries per request using an incoming `X-Organization-ID` gateway header.
*   **2. Secure Authentication Engine**
    *   Password hashing protection matching standard security protocols.
    *   Dual-token infrastructure generating secure JWT Access Tokens and Refresh Tokens.
*   **3. Advanced Document Ingestion Pipeline**
    *   Accepts `.pdf`, `.txt`, and `.docx` extensions up to a tight **5MB restriction limit**.
    *   Performs dual-validation via file extensions and underlying `libmagic` binary buffer MIME type extraction to combat malicious content injection.
*   **4. Non-Blocking Background Tasks**
    *   Asynchronous background extraction utilizing decoupled worker processing cycles.
    *   Performs sequential formatting: File Processing Job Creation → Raw Text Extraction → Document Chunking → Semantic Text Indexing.
*   **5. Semantic Intelligence via Mistral AI**
    *   Basic retrieval-augmented generation (RAG) architecture: Isolates relevant document text chunks first, then passes optimal contexts downstream to the **Mistral AI** model to protect context windows.
    *   *Note: Full-text database index scanning is currently omitted and planned for a future release layer.*
*   **6. API Usage Limit Enforcements**
    *   Tracks system footprints dynamically: Documents uploaded, total storage bytes consumed, execution query rates, and AI token limits.

---

## 🛠 Tech Stack

*   **Framework:** FastAPI (Python 3.11)
*   **Database ORM:** SQLModel (SQLAlchemy 2.0 under asyncpg drivers)
*   **AI Integration:** Mistral AI Client SDK
*   **Migration Tool:** Asynchronous Alembic Pipeline
*   **Package Manager:** uv (written in Rust for lightning-fast installations)
*   **Containerization:** Docker & Docker Compose

---

## 📦 Setting Up Locally via Docker Compose

Follow these steps to launch the entire stack (FastAPI app, isolated PostgreSQL database container, and automated migrations tracking layers) instantly.

### 1. Configure Your Secrets Environment
Before spinning up the container cluster, you must instantiate your private local configuration variables. Copy the project's included repository template file to create your active `.env`:

```bash
cp .env.example .env
```

Open the newly created `.env` file on your host machine and update the placeholder keys with your actual values (such as your private database parameters, JWT secret strings, and your **`MISTRAL_API_KEY`** characters).

### 2. Boot Up the Containers
Run the single orchestration command to build your optimized application environment and establish database safety volumes:

```bash
docker compose up --build -d
```

### 3. Verify System Infrastructure Stability
Check whether the containers initialized smoothly and are active:

```bash
docker compose ps
```

To view the sequential backend execution flow, including automated Alembic database script executions (`alembic upgrade head`), inspect the live log tracking:

```bash
docker compose logs -f web
```

---

## 🔌 Interacting and Accessing the API

Once the container setup prints out an active startup confirmation, fire up your local browser to access these interfaces:

| Resource Gateway | Local URL Network Pointer | Description |
| :--- | :--- | :--- |
| **Interactive API Documentation** | `http://localhost:8000/docs` | Native Swagger UI. Best interface to authenticate users, configure header keys, and test endpoints interactively. |
| **Alternative API Blueprint Layout** | `http://localhost:8000/redoc` | Structural ReDoc documentation map. High readability formatting highlighting model types. |

### Accessing Workspace Actions (Required Authorization Headers)
When executing document updates, queries, or user audits inside the documentation UI, ensure the following parameters are provided:

1.  **Bearer Token:** Click the **Authorize** lock icon at the top right of the Swagger interface and submit a verified token string acquired from your `/login` route.
2.  **Organization Scope Header:** Protected workspace queries require passing the target entity context directly inside the request header block:
    *   Header Key: `X-Organization-ID`
    *   Header Value: `1` (or your matching generated database organization id integer)

---

## 🛠 Development Operations Maintenance

### Generating Fresh Database Schema Migrations Safely
If you alter your `SQLModel` fields or add new data tables locally during development, spin up a clean temporary application configuration container to generate your subsequent structural migration schemas cleanly without crashing current database mappings:

```bash
docker compose run --rm web uv run alembic revision --autogenerate -m "describe_your_changes_here"
```

### Shutting Down the Application Environment
To close active application loops for the day without losing any uploaded knowledge data entries or user workspaces tracking parameters saved inside your persistent Docker hard drive volume layer, run:

```bash
docker compose down
```
