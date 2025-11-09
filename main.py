import os
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client, Client
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Завантажуємо змінні з .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not FLASK_SECRET_KEY:
    raise Exception("Перевірте, чи змінні SUPABASE_URL, SUPABASE_KEY, FLASK_SECRET_KEY є у .env")

# Підключаємося до Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# -------------------- Головна сторінка --------------------
@app.route("/")
def index():
   username = session.get("username")
   return render_template("index.html", username=username)
# -------------------- Реєстрація --------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if 'username' in session:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return "Введіть ім’я та пароль", 400

        # Перевірка, чи ім’я вже існує
        existing = supabase.table("users").select("*").eq("username", username).execute()
        if existing.data and len(existing.data) > 0:
            return "Користувач з таким іменем вже існує", 400

        password_hash = generate_password_hash(password)

        # Вставляємо в Supabase
        resp = supabase.table("users").insert({
            "username": username,
            "password_hash": password_hash
        }).execute()


        session["username"] = username
        return redirect(url_for("chats"))

    return render_template("register.html")

# -------------------- Логін --------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if 'username' in session:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return "Введіть ім’я та пароль", 400

        resp = supabase.table("users").select("*").eq("username", username).execute()
        users = resp.data

        if not users or len(users) == 0:
            return "Користувача не знайдено", 404

        user = users[0]
        if not check_password_hash(user["password_hash"], password):
            return "Неправильний пароль", 403

        session["username"] = username
        return redirect(url_for("chats"))

    return render_template("login.html")

# -------------------- Вихід --------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# -------------------- Список чатів --------------------

@app.route("/chats", methods=["GET", "POST"])
def chats():
    if 'username' not in session:
        return redirect(url_for("login"))

    username = session.get("username")

    # ----------------- Отримуємо список всіх користувачів ------------------
    resp_users = supabase.table("users").select("user_id, username").execute()
    users_list = resp_users.data if resp_users.data else []

    # ----------------- Список користувачів для відображення збоку ------------------
    users = [u["username"] for u in users_list if u["username"] != username]

    # ----------------- Надсилання нового повідомлення ------------------
    if request.method == "POST":
        content = request.form.get("content")
        if content:
            # знаходимо user_id поточного користувача
            sender_id = next((u["user_id"] for u in users_list if u["username"] == username), None)
            if sender_id:
                # Перевірка, чи існує чат 0 (загальний чат)
                resp_chat = supabase.table("chats").select("*").eq("chat_id", 0).execute()
                if not resp_chat.data:
                    # якщо немає, створюємо загальний чат
                    supabase.table("chats").insert({
                        "chat_id": 0,
                        "name": "Загальний чат"
                    }).execute()

                # Вставляємо повідомлення
                supabase.table("meseges").insert({
                    "sender": sender_id,
                    "chat_id": 0,   # 0 = загальний чат
                    "meseg": content
                }).execute()
            return redirect(url_for("chats"))

    # ----------------- Отримуємо всі повідомлення для загального чату --------------
    resp_messages = supabase.table("meseges").select("*").eq("chat_id", 0).order("meseg_id").execute()
    messages = resp_messages.data if resp_messages.data else []

    return render_template("chats.html", username=username, users=users, messages=messages)

# -------------------- Тест Supabase --------------------
@app.route("/test_supabase")
def test_supabase():
    resp = supabase.table("users").select("*").execute()
    if resp.error:
        return f"Помилка Supabase: {resp.error.message}"
    return f"Користувачі в базі: {resp.data}"

# -------------------- Запуск --------------------
if __name__ == "__main__":
    app.run(debug=True)