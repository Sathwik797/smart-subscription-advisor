# 🚀 Smart Subscription Advisor

A Flask-based web application that helps users efficiently manage their subscriptions, track monthly and yearly expenses, and receive smart recommendations based on their usage patterns.

---

## 📌 Project Overview

Managing multiple subscriptions can be difficult. Smart Subscription Advisor allows users to organize all their subscriptions in one place, monitor spending, and receive intelligent insights to help reduce unnecessary expenses.

---

## ✨ Features

### 🔐 Authentication
- User Registration
- Secure Login & Logout
- Duplicate Email Validation
- Duplicate Username Validation
- Smart Username Suggestions
- Profile Management

### 👤 User Profile
- View Profile
- Edit Username
- Edit Occupation
- Edit Financial Preference

### 📋 Subscription Management
- Add Subscription
- Edit Subscription
- Delete Subscription
- Search Subscriptions

### 🤖 Smart Recommendation System
- Subscription Priority (High / Medium / Low)
- Personalized Recommendations
- Smart Subscription Insights

### 📊 Dashboard & Analytics
- Total Subscriptions
- Monthly Spending
- Yearly Spending
- Subscription Health Score
- Interactive Charts

### 📤 Export
- Export Subscription Data to CSV

### 📱 Responsive Design
- Mobile Friendly
- Desktop Friendly

---

## 🛠️ Tech Stack

### Frontend
- HTML5
- CSS3
- Bootstrap 5
- JavaScript
- Jinja2

### Backend
- Python
- Flask
- Flask-Login
- Flask-SQLAlchemy

### Database
- MySQL

### Libraries
- SQLAlchemy
- PyMySQL
- python-dotenv
- Pandas
- Chart.js

---

## 📂 Project Structure

```
smart-subscription-advisor/
│
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── database/
├── models/
├── routes/
├── templates/
├── static/
├── exports/
└── recommendation/
```

---

## ⚙️ Installation

### Clone the repository

```bash
git clone https://github.com/Sathwik797/smart-subscription-advisor.git
```

### Move into the project

```bash
cd smart-subscription-advisor
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Virtual Environment

Windows

```bash
venv\Scripts\activate
```

Linux/Mac

```bash
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Create a `.env` file

```env
SECRET_KEY=your_secret_key

DB_HOST=localhost
DB_PORT=3306
DB_NAME=subscription_assisstant
DB_USER=root
DB_PASSWORD=your_password
```

### Run the application

```bash
python app.py
```

Open your browser and visit

```
http://127.0.0.1:5000
```

---

## 📸 Screenshots

### 🏠 Home Page

(Add Screenshot)

### 🔐 Login Page

(Add Screenshot)

### 📝 Registration Page

(Add Screenshot)

### 📊 Dashboard

(Add Screenshot)

### 📋 Subscription Management

(Add Screenshot)

### 🤖 Smart Recommendation

(Add Screenshot)

### 📈 Analytics

(Add Screenshot)

### 👤 User Profile

(Add Screenshot)

---

## 🧪 Testing

The application has been tested for:

- ✅ User Registration
- ✅ Login & Logout
- ✅ Duplicate Email Validation
- ✅ Duplicate Username Validation
- ✅ Username Suggestions
- ✅ Profile Management
- ✅ Add/Edit/Delete Subscription
- ✅ Search Functionality
- ✅ Recommendation Updates
- ✅ Smart Insights
- ✅ Dashboard Analytics
- ✅ CSV Export
- ✅ Mobile Responsiveness

---

## 🔮 Future Enhancements

- Email Notifications for Renewals
- Monthly Budget Tracking
- Payment Gateway Integration
- Password Reset via Email
- Notification Preferences
- Dark Mode
- AI-based Subscription Cost Optimization

---

## 👨‍💻 Author

**Sathwik Reddy**

GitHub:
https://github.com/Sathwik797

---

## 📄 License

This project is licensed under the MIT License.

---

⭐ If you found this project useful, consider giving it a star on GitHub.
