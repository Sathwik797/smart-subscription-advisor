# Smart Subscription Advisor

<div align="center">

**An enterprise-grade, hybrid-intelligence personal subscription and financial management platform.**

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flask%203.1-black.svg?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/database-MySQL%208.0-4479A1.svg?style=flat-square&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![ORM](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-D71F00.svg?style=flat-square)](https://www.sqlalchemy.org/)
[![Security](https://img.shields.io/badge/auth-JWT%20Tokens-000000.svg?style=flat-square&logo=jsonwebtokens&logoColor=white)](https://jwt.io/)
[![AI Engine](https://img.shields.io/badge/AI-Groq%20LLM-F05A28.svg?style=flat-square)](https://groq.com/)
[![Test Suite](https://img.shields.io/badge/tests-109%20passed-brightgreen.svg?style=flat-square&logo=pytest&logoColor=white)](https://pytest.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)

[Key Features](#-key-features) •
[Architecture](#-system-architecture) •
[Tech Stack](#-technology-stack) •
[Getting Started](#-getting-started) •
[API Reference](#-api-reference) •
[Testing](#-quality-assurance--testing) •
[Security](#-security--data-protection) •
[Contributing](#-contributing)

</div>

---

## 📋 Executive Summary

In today's subscription-based economy, recurring billing models create financial blind spots. Organizations and individuals frequently experience subscription fatigue, unmonitored renewals, duplicate services, and inefficient recurring spend.

**Smart Subscription Advisor** solves this challenge through a high-performance web platform that merges **100% deterministic mathematical calculations** with **Generative Hybrid AI reasoning (Groq)**. The system tracks recurring commitments, predicts cash-flow impacts, calculates a tailored Subscription Health Score, identifies redundant or underutilized services, and provides real-time contextual recommendations to optimize expenditures.

Designed following strict production backend patterns, the application features an N-tier layered architecture, repository patterns, JWT-based stateless authentication, rate-limiting guards, centralized structured logging, and unified global exception handling.

---

## ✨ Key Features

### 💳 Subscription Lifecycle Management
* **Comprehensive Tracking:** Manage monthly, quarterly, semi-annual, and annual subscriptions with automatic renewal date calculations.
* **Granular Usage Profiling:** Track usage frequency (Daily, Weekly, Monthly, Rarely) and daily operational hours to compute an accurate value-for-money index.
* **Smart Financial Categorization:** Segment expenses across Entertainment, Utilities, Productivity, Cloud Services, Health & Fitness, Education, and Custom domains.
* **Currency Formatting:** Native INR (`₹`) formatting across all views with flexible currency utilities.
* **Data Portability:** Instant CSV export capability for spreadsheet modeling, auditing, and tax preparation.

### 🧠 Hybrid AI Advisory & Recommendation Engine
* **Deterministic Accounting:** Budget arithmetic, category breakdowns, and renewal countdowns are computed deterministically to eliminate hallucinations.
* **Intelligent Spend Health Score:** Dynamically assesses subscription portfolio risk on a 0–100 scale using usage frequency, prioritization algorithms, and spend thresholds.
* **Contextual AI Optimization:** Integrates high-speed Groq LLM inference to analyze spending habits against user occupation and financial preferences (e.g., *Money Saver*, *Balanced*, *Invest in Growth*).
* **Conversational AI Advisor:** An integrated domain-specific assistant protected by prompt guardrails and localized strictly to authenticated user records.

### 🔐 Enterprise Authentication & Access Control
* **Stateless Token Authentication:** Dual-mode JWT authentication supporting HTTP-only secure cookies for web browsers and Bearer authorization headers for REST clients.
* **Flexible Onboarding:** Streamlined user registration with intelligent username collision detection, real-time availability checks, and optional mobile contact profiling.
* **Account Security:** Strong password hashing via Werkzeug, brute-force protection through Flask-Limiter, and authenticated session management.

### 🎨 Modern FinTech Application Shell
* **Responsive Workspace:** Optimized application layout featuring a collapsible sidebar with persistent state across desktop and mobile viewports.
* **Separation of Concerns:** Dedicated, purpose-built workspaces for **Profile Overview** (viewing account status), **Edit Profile** (personal detail updates), and **Settings** (system preferences).
* **Financial Analytics Dashboard:** Interactive data visualizations powered by Chart.js displaying cost distributions, upcoming renewal queues, and prioritized action cards.

---

## 🏛️ System Architecture

Smart Subscription Advisor implements an N-tier layered design pattern that enforces clean separation of concerns and decoupled business logic:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Clients & Presentation                          │
│        Web Browser (HTML5 / Vanilla CSS / JS)  │  REST API Consumers   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │  HTTP(S)
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          Application Gateway                           │
│     Flask App Router  │  Rate Limiter (Flask-Limiter)  │  CORS         │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         Middleware & Security                          │
│     JWT Verification Engine  │  Request Logger  │  User Context        │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │                                 │
                   ▼                                 ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│          Web Controllers             │  │       REST Controllers       │
│  (Auth, Subscriptions, Profile, UI)  │  │   (JSON Envelopes, API v1)   │
└──────────────────┬───────────────────┘  └──────────────┬───────────────┘
                   │                                     │
                   └──────────────────┬──────────────────┘
                                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│                            Validation Layer                            │
│           AuthValidator  │  SubscriptionValidator  │  Sanitization     │
└─────────────────────────────────────┬──────────────────────────────────┘
                                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│                             Service Layer                              │
│  AuthService │ SubscriptionService │ IntelligenceService │ ChatService │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │                                 │
                   ▼                                 ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│           Repository Layer           │  │     External AI Services     │
│   UserRepository │ SubRepository     │  │       Groq Cloud LLM         │
└──────────────────┬───────────────────┘  └──────────────────────────────┘
                   │ SQLAlchemy ORM
                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Relational Persistence                          │
│                              MySQL 8.0                                 │
└────────────────────────────────────────────────────────────────────────┘
```

### Architectural Highlights
* **Controller-Service-Repository Flow:** Controllers handle HTTP transport; Services encapsulate business rules; Repositories execute database queries.
* **Deterministic Fail-Safe:** If external AI services experience latency or downtime, the core application seamlessly falls back to rule-based deterministic heuristics.
* **Unified Error Envelope:** Standardized error handling guarantees predictable responses across web templates and JSON endpoints.

---

## 🛠️ Technology Stack

| Layer | Technologies | Purpose |
| :--- | :--- | :--- |
| **Backend Core** | Python 3.11+, Flask 3.1, Werkzeug | Application engine, routing, and HTTP lifecycle |
| **Database & ORM** | MySQL 8.0, SQLAlchemy 2.0, PyMySQL | Relational data persistence and schema management |
| **Authentication** | Flask-JWT-Extended, Cryptography | Stateless JWT issuing, token validation, and password security |
| **AI / LLM** | Groq SDK, Compound Mini Models | High-throughput conversational reasoning and spend optimization |
| **Traffic & Security** | Flask-Limiter, Centralized Logging | Rate limiting, brute-force mitigation, and request telemetry |
| **Frontend** | HTML5, Vanilla CSS3, JavaScript (ES6+), Jinja2 | Responsive UI design system without third-party styling bloat |
| **Data Visualization** | Chart.js 4.x | Spending charts, categorical breakdowns, and metric gauges |
| **Production Server** | Gunicorn (Linux/Containers) | Production-ready WSGI HTTP server |
| **Quality Assurance** | Pytest 9.x | Unit, integration, controller, and UI regression test suites |

---

## 📂 Repository Structure

```text
smart-subscription-advisor/
├── controllers/            # HTTP request orchestrators (Web and REST controllers)
│   ├── api_controller.py
│   ├── auth_controller.py
│   ├── chat_controller.py
│   └── subscription_controller.py
├── database/               # Database engine initialization and connection handlers
│   └── db.py
├── docs/                   # Architectural blueprints and engineering specifications
│   └── hybrid_ai_intelligence.md
├── exceptions/             # Domain-specific custom exceptions and HTTP error handlers
│   ├── error_handlers.py
│   └── exceptions.py
├── logging_config/         # Structured application logger with rotating file handlers
│   └── logger.py
├── middleware/             # Request interceptors, JWT resolvers, and rate limiters
│   ├── auth.py
│   └── rate_limiter.py
├── models/                 # SQLAlchemy ORM declarative entity definitions
│   ├── subscription.py
│   └── user.py
├── repositories/           # Isolated data-access layer implementing repository pattern
│   ├── subscription_repository.py
│   └── user_repository.py
├── routes/                 # Blueprint definitions separating Web views and REST endpoints
│   ├── api/                # JSON API route definitions (/api/*)
│   ├── auth.py             # Authentication and user profile endpoints
│   └── subscription.py     # Subscription and analytics web endpoints
├── services/               # Core business logic, deterministic calculators, and AI orchestration
│   ├── ai_reasoning_service.py
│   ├── auth_service.py
│   ├── chat_service.py
│   ├── email_service.py
│   ├── intelligence_service.py
│   └── subscription_service.py
├── static/                 # Static assets (modular CSS, vanilla JS, SVG icons, imagery)
│   ├── css/
│   ├── js/
│   └── images/
├── templates/              # Jinja2 HTML templates adhering to the approved design system
│   ├── partials/           # Reusable components (e.g. global collapsible sidebar)
│   └── ...
├── tests/                  # Automated pytest test suites (109+ tests)
├── utils/                  # Currency helpers, priority estimators, insight generators
├── .env.example            # Canonical environment variable configuration template
├── app.py                  # Application entry point and runtime bootstrap
├── config.py               # Centralized configuration mapping environment variables
├── requirements.txt        # Pinned production and development Python dependencies
└── README.md               # Project documentation
```

---

## 🚀 Getting Started

### Prerequisites
Before running the application, ensure your workstation meets the following requirements:
* **Python:** Version 3.11 or higher
* **Database:** MySQL Server 8.0+ running locally or remotely
* **Package Manager:** `pip` and `virtualenv`
* **Optional:** An API key from [Groq Console](https://console.groq.com) for AI Chatbot capabilities

---

### 1. Clone the Repository

```bash
git clone https://github.com/Sathwik797/smart-subscription-advisor.git
cd smart-subscription-advisor
```

---

### 2. Set Up Virtual Environment

#### Windows (PowerShell / Command Prompt)
```powershell
python -m venv venv
.\venv\Scripts\activate
```

#### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Database Setup

Ensure MySQL is running, then create the application database using your preferred MySQL client:

```sql
CREATE DATABASE smart_subscription_advisor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

### 5. Environment Configuration

Copy the sample environment template and populate your local credentials:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edit `.env` with your preferred editor:

```ini
# Flask Core
SECRET_KEY=generate_a_secure_random_key_for_session_encryption
FLASK_DEBUG=False
PORT=5000

# JWT Authentication
JWT_SECRET_KEY=generate_a_secure_jwt_secret_key
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_COOKIE_SECURE=False  # Set to True in production with HTTPS

# Database Connection (Option A: URI)
DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/smart_subscription_advisor

# Database Connection (Option B: Discrete parameters)
DB_HOST=localhost
DB_PORT=3306
DB_NAME=smart_subscription_advisor
DB_USER=root
DB_PASSWORD=your_password

# AI Advisory Engine (Optional, required for AI Chat)
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=groq/compound-mini
```

---

### 6. Initialize and Run Application

The application automatically checks and executes schema migrations via `db.create_all()` on startup:

```bash
python app.py
```

Access the application in your browser at:
```text
http://127.0.0.1:5000
```

---

## 📡 API Reference

Smart Subscription Advisor provides a modular REST API alongside its server-rendered views.

### Standard Response Structure
All JSON endpoints conform to a standardized response envelope:

```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully"
}
```

### Core API Endpoints

#### Authentication & Account
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register a new user account | No |
| `POST` | `/api/auth/login` | Authenticate credentials and receive JWT | No |
| `GET` | `/api/auth/profile` | Retrieve authenticated user profile | **Yes** (JWT) |
| `PUT` | `/api/auth/profile` | Update profile attributes and preferences | **Yes** (JWT) |

#### Subscriptions
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/subscriptions` | List all subscriptions for current user | **Yes** (JWT) |
| `POST` | `/api/subscriptions` | Create a new tracked subscription | **Yes** (JWT) |
| `GET` | `/api/subscriptions/<id>` | Fetch subscription details by ID | **Yes** (JWT) |
| `PUT` | `/api/subscriptions/<id>` | Update an existing subscription | **Yes** (JWT) |
| `DELETE` | `/api/subscriptions/<id>` | Delete a subscription | **Yes** (JWT) |

#### Intelligence & AI Chat
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/chat` | Query the conversational subscription advisor | **Yes** (JWT) |
| `GET` | `/api/analytics` | Retrieve structured spend aggregates & metrics | **Yes** (JWT) |

---

## 🧪 Quality Assurance & Testing

The repository includes a comprehensive automated test suite implemented with `pytest`. Tests cover unit validation, database repository logic, authentication workflows, navigation behavior, and controller integrity.

### Execute All Tests
```bash
python -m pytest
```

### Run Tests with Verbose Output
```bash
python -m pytest -v
```

### Run Specific Test Modules
```bash
# Verify authentication and session flows
python -m pytest tests/test_login_flow.py

# Verify intelligence and deterministic engine
python -m pytest tests/test_hybrid_intelligence.py

# Verify navigation and layout contracts
python -m pytest tests/test_sidebar_navigation.py
```

---

## 🔒 Security & Data Protection

* **Stateless Token Verification:** Authenticated sessions use signed JSON Web Tokens (JWT) with configurable TTL expiration.
* **SQL Injection Defense:** Zero raw string SQL concatenation; all database interactions are mediated via SQLAlchemy ORM parameterized queries.
* **Brute-Force & Rate Limiting:** Flask-Limiter enforces rate thresholds across sensitive authentication endpoints (`/login`, `/register`, `/api/*`).
* **Password Hashing:** Passwords are cryptographically salted and hashed using PBKDF2 with SHA-256 via Werkzeug.
* **User Isolation:** All repository access queries strictly scope subscription data by `user_id` derived from verified JWT identity claims.

---

## 🚢 Production Deployment

For enterprise or production cloud deployment (e.g., AWS EC2, GCP Compute Engine, DigitalOcean, Docker):

1. **WSGI HTTP Server:** Deploy using Gunicorn with asynchronous or multiple worker processes:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```
2. **Reverse Proxy:** Terminate TLS (HTTPS) via Nginx or Cloudflare, and forward `X-Forwarded-For` and `X-Forwarded-Proto` headers.
3. **Environment Security:**
   * Set `FLASK_DEBUG=False` in `.env`.
   * Set `JWT_COOKIE_SECURE=True` to require HTTPS cookies.
   * Store `SECRET_KEY` and `JWT_SECRET_KEY` in a secure secret manager.

---

## 🤝 Contributing

Contributions are welcome! Please follow this workflow:

1. **Fork the Repository** on GitHub.
2. **Create a Feature Branch:**
   ```bash
   git checkout -b feature/spend-forecasting
   ```
3. **Commit Changes:** Adhere to conventional commit guidelines (`feat:`, `fix:`, `docs:`):
   ```bash
   git commit -m "feat: add spend forecasting projection models"
   ```
4. **Run Test Suite:** Ensure all 109+ tests pass without errors:
   ```bash
   python -m pytest
   ```
5. **Push to GitHub & Open Pull Request:** Push your branch and open a PR with a clear description of changes.

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for complete details.

---

## 👨‍💻 Maintainer

**Sathwik Reddy**  
* GitHub: [@Sathwik797](https://github.com/Sathwik797)  
* Project Repository: [Smart Subscription Advisor](https://github.com/Sathwik797/smart-subscription-advisor)

<div align="center">
<sub>Engineered with precision for transparency, performance, and financial intelligence.</sub>
</div>
