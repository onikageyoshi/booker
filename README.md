# 🏠 Airbnb Clone API

A production-style RESTful backend inspired by Airbnb, built with **Python**, **Django**, and **Django REST Framework**. The API provides secure authentication, property listings, bookings, payments, user management, and media uploads while following modern backend development practices.

---

## 📖 Overview

This project was built to simulate the backend architecture of a vacation rental platform similar to Airbnb. It focuses on scalable API development, secure authentication, and clean database design.

The application allows users to register, list properties, browse available accommodations, make bookings, process payments, and manage their accounts through RESTful endpoints.

---

# 🚀 Features

## Authentication

- Custom User Model
- Email Authentication
- JWT Authentication
- Login & Logout
- Refresh Tokens
- Password Reset
- OTP Verification
- Role-Based Access Control

---

## User Management

- User Registration
- User Profiles
- Profile Image Upload
- Update Profile
- Change Password

---

## Property Management

- Create Listings
- Update Listings
- Delete Listings
- View Listings
- Property Categories
- Pricing Information
- Availability Status
- Property Images

---

## Booking System

- Book Properties
- Booking Validation
- Booking History
- Booking Status
- Prevent Double Bookings
- Booking Cancellation

---

## Payment System

- Paystack Integration
- Payment Initialization
- Payment Verification
- Webhook Support
- Payment Records
- Transaction Tracking

---

## Notifications

- Booking Notifications
- Payment Notifications
- Property Updates

---

## Media Handling

- Cloudinary Image Uploads
- Property Images
- User Profile Images

---

## API Features

- RESTful Architecture
- JSON Responses
- Pagination
- Filtering
- Search
- Validation
- Error Handling
- Swagger Documentation

---

# 🛠 Tech Stack

## Backend

- Python
- Django
- Django REST Framework

## Database

- PostgreSQL
- SQLite (Development)

## Authentication

- JWT (Simple JWT)

## Cloud Storage

- Cloudinary

## Documentation

- Swagger (drf_yasg)

## Deployment

- Gunicorn
- Nginx
- WhiteNoise
- Docker

## Version Control

- Git
- GitHub

---

# 📂 Project Structure

```
airbnb/
│
├── apps/
│   ├── users/
│   ├── properties/
│   ├── bookings/
│   ├── payments/
│   ├── notifications/
│   └── reviews/
│
├── config/
├── media/
├── static/
├── requirements.txt
├── manage.py
└── README.md
```

---

# 🔒 Authentication Flow

1. User registers an account.
2. JWT Access and Refresh tokens are generated.
3. Protected endpoints require an Access Token.
4. Refresh Tokens are used to obtain new Access Tokens.
5. Permissions restrict access to authorized users.

---

# 📦 API Modules

### Users

- Register
- Login
- Logout
- Profile
- Password Management

### Properties

- Create Listing
- Update Listing
- Delete Listing
- Browse Listings
- Property Details

### Bookings

- Create Booking
- View Bookings
- Cancel Booking

### Payments

- Initialize Payment
- Verify Payment
- Payment History

### Reviews

- Add Review
- Update Review
- Delete Review

---

# 🧱 Database Design

The project uses relational database modeling with Django ORM.

Key relationships include:

- One User → Many Properties
- One User → Many Bookings
- One Property → Many Bookings
- One Property → Many Reviews
- One Booking → One Payment

---

# 🔐 Security Features

- JWT Authentication
- Password Hashing
- Input Validation
- Role-Based Permissions
- Protected API Endpoints
- Secure Media Uploads

---

# 📑 API Documentation

Interactive API documentation is available through Swagger.

```
/swagger/
/redoc/
```

---

# ⚙️ Installation

Clone the repository

```bash
git clone https://github.com/servercraft-stack/airbnb-clone.git
```

Navigate into the project

```bash
cd airbnb-clone
```

Create a virtual environment

```bash
python -m venv venv
```

Activate it

Linux/macOS

```bash
source venv/bin/activate
```

Windows

```bash
venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run migrations

```bash
python manage.py migrate
```

Create a superuser

```bash
python manage.py createsuperuser
```

Start the development server

```bash
python manage.py runserver
```

---

# 📌 Future Improvements

- Wishlist functionality
- Messaging between guests and hosts
- Property availability calendar
- Stripe integration
- Email notifications
- Ratings analytics
- Admin dashboard
- Multi-image uploads
- Search optimization
- Recommendation system

---

# 📚 What This Project Demonstrates

This project showcases practical backend development skills including:

- REST API Development
- Database Design
- Authentication & Authorization
- File Upload Management
- Payment Gateway Integration
- Secure API Development
- API Documentation
- PostgreSQL Integration
- Docker-Based Deployment
- Scalable Django Project Structure

---

# 👨‍💻 Author

**David Ibemere Onyekachi**

Backend Developer

GitHub: https://github.com/servercraft-stack

---

## 📄 License

This project is open source and available under the MIT License.
