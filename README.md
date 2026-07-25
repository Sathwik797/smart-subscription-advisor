# 🚀 Smart Subscription Advisor

A production-inspired full-stack web application that helps users manage their subscriptions, monitor expenses, and receive personalized recommendations while demonstrating modern backend architecture using Flask.

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Flask](https://img.shields.io/badge/Flask-Backend-black)
![MySQL](https://img.shields.io/badge/Database-MySQL-orange)
![JWT](https://img.shields.io/badge/Auth-JWT-success)
![License](https://img.shields.io/badge/License-MIT-green)

---

# 📌 Project Overview

Managing multiple subscriptions across different platforms can become expensive and difficult to track.

Smart Subscription Advisor allows users to:

- Track all subscriptions in one place
- Monitor monthly and yearly expenses
- Receive personalized subscription recommendations
- Visualize spending through analytics
- Export subscription data
- Securely manage accounts using authentication

Apart from solving the business problem, this project also demonstrates production-style backend architecture including layered architecture, repository pattern, request validation, JWT authentication, centralized logging, and global exception handling.

---

# ✨ Features

## 🔐 Authentication

- User Registration
- Secure Login & Logout
- JWT Protected REST APIs
- Duplicate Username Validation
- Duplicate Email Validation
- Smart Username Suggestions

---

## 👤 User Management

- View Profile
- Update Username
- Update Occupation
- Update Financial Preference

---

## 📋 Subscription Management

- Add Subscription
- Update Subscription
- Delete Subscription
- Search Subscription
- Subscription Categorization

---

## 🤖 Smart Recommendation System

- Subscription Priority
- Personalized Recommendations
- Smart Insights
- Spending Optimization Suggestions

---

## 📊 Dashboard & Analytics

- Total Active Subscriptions
- Monthly Spending
- Yearly Spending
- Health Score
- Interactive Charts
- Spending Overview

---

## 📤 Export

- Export Subscription Details to CSV

---

## 📱 Responsive UI

- Desktop Friendly
- Mobile Responsive
- Bootstrap 5 Interface

---

# 🏛️ Backend Architecture

This project follows a layered architecture to improve maintainability, scalability, and separation of concerns.

```
Browser / REST Client
          │
          ▼
+-----------------------+
|       Routes          |
+-----------------------+
          │
          ▼
+-----------------------+
|     Controllers       |
+-----------------------+
          │
          ▼
+-----------------------+
|     Validators        |
+-----------------------+
          │
          ▼
+-----------------------+
|      Services         |
|  Business Logic       |
+-----------------------+
          │
          ▼
+-----------------------+
|    Repositories       |
| Database Operations   |
+-----------------------+
          │
          ▼
+-----------------------+
|    MySQL Database     |
+-----------------------+

      ▲
      │
 JWT Authentication

      ▲
      │
Global Exception Handler

      ▲
      │
Centralized Logging
```

---

# 🏗️ Design Patterns Used

- Layered Architecture
- Repository Pattern
- Service Layer Pattern
- MVC Architecture
- Dependency Separation
- REST API Design

---

# 🛠️ Tech Stack

## Frontend

- HTML5
- CSS3
- Bootstrap 5
- JavaScript
- Jinja2
- Chart.js

---

## Backend

- Python
- Flask
- Flask-JWT-Extended
- Flask-Login
- Flask-SQLAlchemy

---

## Database

- MySQL
- SQLAlchemy ORM

---

## Validation & Security

- JWT Authentication
- Password Hashing
- Request Validation
- Input Sanitization

---

## Logging

- Python Logging
- Request Logging
- Authentication Logs
- Validation Logs
- Error Logs

---

## Testing

- Pytest

---

# 📂 Project Structure

```
smart-subscription-advisor/
│
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── controllers/
│
├── services/
│
├── repositories/
│
├── routes/
│   └── api/
│
├── validators/
│
├── exceptions/
│
├── middleware/
│
├── logging_config/
│
├── database/
│
├── models/
│
├── templates/
│
├── static/
│
├── tests/
│
├── logs/
│
└── exports/
```

---

# 🔄 Request Flow

```
Client Request
      │
      ▼
Routes
      │
      ▼
Controllers
      │
      ▼
Validators
      │
      ▼
Services
      │
      ▼
Repositories
      │
      ▼
Database

Response follows the reverse path.
```

---

# ⚙️ Installation

## Clone Repository

```bash
git clone https://github.com/Sathwik797/smart-subscription-advisor.git
```

## Navigate

```bash
cd smart-subscription-advisor
```

## Create Virtual Environment

```bash
python -m venv venv
```

## Activate

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Create .env

```env
SECRET_KEY=your_secret_key

JWT_SECRET_KEY=your_jwt_secret

DB_HOST=localhost
DB_PORT=3306
DB_NAME=subscription_assisstant
DB_USER=root
DB_PASSWORD=your_password
```

---

## Run Application

```bash
python app.py
```

Open:

```
http://127.0.0.1:5000
```

---

# 🔐 Authentication

## Web Authentication

- Flask Login
- Session Authentication

## REST APIs

- JWT Authentication
- Protected API Endpoints

---

# 🧪 Testing

The application includes testing for:

- User Registration
- User Login
- JWT Authentication
- Validation Layer
- Exception Handling
- Subscription CRUD
- Search
- Dashboard
- CSV Export

---

# 📊 Logging

Centralized logging records:

- Application Startup
- Request Lifecycle
- Authentication Events
- Validation Errors
- Exceptions
- API Access
- Unauthorized Requests

---

# 📸 Screenshots

## Home

(Add Screenshot)

---

## Login

(Add Screenshot)

---

## Dashboard

(Add Screenshot)

---

## Subscription Management

(Add Screenshot)

---

## Analytics

(Add Screenshot)

---

## User Profile

(Add Screenshot)

---

## API Testing (Postman)

(Add Screenshot)

---

# 🚀 Future Enhancements

- Email Verification
- Password Reset
- Pagination
- Sorting
- Filtering
- Rate Limiting
- Swagger/OpenAPI Documentation
- Docker Support
- CI/CD Pipeline
- Redis Caching
- AI-based Cost Optimization
- Subscription Renewal Notifications

---

# 👨‍💻 Author

**Sathwik Reddy**

GitHub

https://github.com/Sathwik797

LinkedIn

(Add LinkedIn Profile)

---

# 📄 License

This project is licensed under the MIT License.

---

# ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.

Contributions, suggestions, and feedback are always welcome!
