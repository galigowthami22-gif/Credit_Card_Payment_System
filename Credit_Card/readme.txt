Day 1 — Project Setup + Authentication + Card Management (Beginner MVT Version)

=========================================================
1. PROJECT STRUCTURE
=========================================================
project_root/
  |- core/                   # Main Django project settings folder
  |- users/                  # Authentication & User Management app
  |- cards/                  # Card Management app
  |- templates/              # HTML Templates (for the "T" in MVT)
      |- base.html           # Main layout file
      |- users/              # Login/Register templates
      |- cards/              # Card listing/adding templates
  |- requirements.txt        # Python dependencies
  |- .env                    # Environment variables (Database setup)
  |- manage.py               # Django execution script

=========================================================
2. STEP-BY-STEP IMPLEMENTATION GUIDE
=========================================================

---------------------------------------------------------
Step 1: Django Project Setup & Configuration
---------------------------------------------------------
1.1 Create Virtual Environment & Install Dependencies
  Open your terminal and run:
  > python -m venv venv
  > venv\Scripts\activate  (On Windows)
  > pip install django mysqlclient python-dotenv

1.2 Create Django Project and Apps
  > django-admin startproject core .
  > python manage.py startapp users
  > python manage.py startapp cards
  Run these commands from the project directory that contains `manage.py`.
  In this repository, `manage.py` adds the `Credit_Card` directory to Python's
  import path so the existing `core`, `users`, and `cards` packages can be found.

1.3 Configure .env File
  Create a `.env` file in your project folder:
  SECRET_KEY=your_django_secret_key
  DB_NAME=credit_cards_db
  DB_USER=root
  DB_PASSWORD=your_mysql_password
  DB_HOST=localhost
  DB_PORT=3306
  DB_PASSWORD must be the exact MySQL password; write special characters literally
  (for example, use `@`, not its URL-encoded form `%40`).

  Install project dependencies from the repository root with:
  > venv\Scripts\python.exe -m pip install -r requirements.txt

1.4 Configure Settings (core/settings.py)
  - Load environment variables using `python-dotenv`.
  - Add to INSTALLED_APPS: 'users', 'cards'.
  - Configure DATABASES to use MySQL with the `.env` variables.
  - Set TEMPLATES 'DIRS' to `[BASE_DIR / 'templates']`.
  - Set `LOGIN_REDIRECT_URL = 'card_list'` and `LOGOUT_REDIRECT_URL = 'login'`.

1.5 Connect Django and FastAPI
  Both services use the same MySQL database and JWT signing key. Put the values
  in the same `.env` file (the project root or `Credit_Card` directory):
  DB_NAME=credit_cards_db
  DB_USER=root
  DB_PASSWORD=your_mysql_password
  DB_HOST=localhost
  DB_PORT=3306
  SECRET_KEY=your_django_secret
  JWT_SECRET_KEY=your_shared_jwt_secret

  Use a randomly generated JWT_SECRET_KEY of at least 32 characters and keep
  it private. Both services must use exactly the same key.
  If `DATABASE_URL` is set, both services use it instead of the DB_* settings.
  Run both services from the repository root in separate terminals:
  > venv\Scripts\python.exe manage.py migrate
  > venv\Scripts\python.exe manage.py runserver 8000
  > venv\Scripts\python.exe -m uvicorn main:app --reload --port 8001

  The Django website is at http://localhost:8000 and FastAPI Swagger is at
  http://127.0.0.1:8001/docs. Do not open `/docs` on the Django port. Use the
  same hostname when opening Django and its token endpoint, since `localhost`
  and `127.0.0.1` do not share a browser login session. A signed-in API Token
  link is also available in the Django navigation.
  signed in to Django, open http://127.0.0.1:8000/auth/token/ and copy the
  returned access_token into Swagger's Authorize dialog as a Bearer token.
  Payments submitted from the Django card list are sent to FastAPI, which
  verifies that the card belongs to the authenticated Django user and writes
  the transaction into the same MySQL `payments` table shown in transaction
  history.

---------------------------------------------------------
Step 2: User Authentication (MVT Pattern)
---------------------------------------------------------
2.1 Create Views (users/views.py)
  - Manual Registration: Create a `register_view` that handles `if request.method == 'POST'`. Extract `username`, `email`, and `password` from `request.POST` and use `User.objects.create_user()` to save the user.
  - Manual Login: Create a `login_view` that extracts credentials from `request.POST`, checks them using `authenticate()`, and logs the user in using `login()`.
  - Manual Logout: Create a `logout_view` that uses `logout(request)`.

2.2 Create HTML Templates (templates/users/)
  - `register.html`: Display the registration form with a submit button.
  - `login.html`: Display the login form.

2.3 Setup URLs (users/urls.py)
  - Map routes to your register view and Django's LoginView/LogoutView.

---------------------------------------------------------
Step 3: Card Management (MVT Pattern)
---------------------------------------------------------
3.1 Define Card Model (cards/models.py)
  - Fields:
      - user (ForeignKey to Django's built-in User model)
      - card_holder_name (CharField)
      - masked_card_number (CharField)
      - last_four_digits (CharField)
      - expiry_date (CharField)
  - CRITICAL SECURITY RULE: Do NOT add fields for Full Card Number, CVV, or PIN to the database model!

3.2 Form Handling via HTML (templates/cards/add_card.html)
  - Instead of Django Forms, write standard HTML `<form method="POST">` tags in your template with standard `<input name="card_number">` fields.

3.3 Create Views (cards/views.py)
  - Use the `@login_required` decorator to protect these pages so only logged-in users can see them.
  - `card_list` view: Fetch cards where `user=request.user` and send them to the template.
  - `add_card` view: Handle the POST request manually (`if request.method == 'POST'`). Extract `request.POST.get('card_number')`, mask it (e.g., turning "1234567812345678" into "**** **** **** 5678"), save the card using `Card.objects.create()`, and ignore the CVV/PIN.
  - `delete_card` view: Find a card by ID and delete it.

3.4 Create HTML Templates (templates/cards/)
  - `card_list.html`: Loop through the saved cards and show them nicely on the page.
  - `add_card.html`: Show the form to type in new credit card details.

---------------------------------------------------------
Step 4: Database Migrations
---------------------------------------------------------
  Make sure your MySQL database (`credit_card_db`) is created first using a tool like MySQL Workbench.
  > python manage.py makemigrations
  > python manage.py migrate

---------------------------------------------------------
Step 5: Testing in your Browser
---------------------------------------------------------
  > python manage.py runserver
  - Open http://127.0.0.1:8000/ in Google Chrome.
  - Register a new account and log in.
  - Go to the Add Card page, fill in some fake details, and click save.
  - Check your database directly (using MySQL Workbench) to make sure ONLY the masked data is saved, not the full card number!

---------------------------------------------------------
Step 6: Git Commit
---------------------------------------------------------
  > git init
  > git add .
  > git commit -m "Day 1 Submission: Beginner MVT Setup, HTML templates, Authentication, Secure Card Management"

=========================================================
3. EXPLANATIONS & CONCEPTS
=========================================================

3.1 How views.py Works
In the Django MVT (Model-View-Template) pattern, `views.py` acts as the "brain" or the "controller" of your application. When a user visits a URL (like `/cards/add/`), Django routes that request to a specific function in `views.py`. This function:
1. Receives the HTTP `request` object (which contains data sent from your HTML forms).
2. Interacts with the Database (Models) to save or fetch data.
3. Renders and returns an HTML template back to the user's browser, passing the database data along so it can be displayed.

3.2 How Users connect with Cards
In our `cards/models.py`, the `Card` model has a `user = models.ForeignKey(User, ...)` field. This establishes a "One-to-Many" relationship in the database. It means:
- One User can own many Cards.
- Each Card belongs to exactly one User.
When saving a card in `views.py`, we explicitly assign it to the currently logged-in user with: `user=request.user`. Then, when displaying the list of cards, we fetch ONLY the cards belonging to that specific user using: `Card.objects.filter(user=request.user)`. This ensures that a user can never see or edit someone else's credit cards.

3.3 What is @login_required?
`@login_required` is a Django decorator placed directly above a view function. It acts as a security checkpoint. It tells Django: "Before executing this function, check if the person is logged in."
- If they ARE logged in: The function runs normally.
- If they ARE NOT logged in: Django instantly intercepts the request and redirects them to the Login page. 
Without this annotation, an anonymous visitor could navigate to the restricted `/cards/` pages and try to view or add cards, which would crash the system or create security flaws because `request.user` wouldn't be a valid logged-in user!
