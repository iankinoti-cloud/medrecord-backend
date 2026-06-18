  #Medrecord-backend 
 This is the backend REST API for the Hospital Management System, built using **FastAPI**, **PostgreSQL**, and **Docker**. It handles patient data, administrative operations, and secure user authentication.

---

##  Features

* **JWT Authentication:** Secure login and registration with role-based access control (Admin, Staff, Doctor).
* **Patient Records Management:** Full CRUD operations for managing patient profiles and medical histories.
* **Database Migrations:** Structured PostgreSQL schema management.
* **Containerized Environment:** Fully dockerized setup for easy local development and deployment.

---

## Tech Stack

* **Framework:** FastAPI (Python)
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy / SQLModel
* **Containerization:** Docker & Docker Compose
* **Authentication:** PyJWT / Passlib (Bcrypt)

---

##  Getting Started (Local Development)

### Prerequisites
Make sure you have the following installed on your system:
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine (if using WSL/Ubuntu)
* Python 3.11+ (optional, for running without containers)

### 1. Clone the Repository
```bash
git clone [https://github.com/](https://github.com/)iankinoti-cloud/medrecord-backend.git
cd medrecord-backend
