from flask import Flask, render_template, request, session, redirect
import os
import random
import smtplib
from email.mime.text import MIMEText

import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "secret123")

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# 🔥 AI API
MODEL_NAME = os.environ.get("HUGGINGFACE_MODEL", "google/flan-t5-base")
API_URL = f"https://router.huggingface.co/hf-inference/models/{MODEL_NAME}"
api_token = os.environ.get("HUGGINGFACE_API_TOKEN")
headers = {"Authorization": f"Bearer {api_token}"} if api_token else {}


def build_default_profile(name="", skills="", experience="", extra=""):
    name_text = name or "The candidate"
    skills_text = skills or "adaptability, communication, and a willingness to learn"
    experience_text = experience or "hands-on project work and practical problem-solving"
    extra_text = extra or "a strong focus on professional growth"
    return (
        f"{name_text} is a motivated professional with experience in "
        f"{experience_text}. Their strengths include {skills_text}. They bring "
        f"{extra_text} and are well prepared to contribute effectively in a "
        f"dynamic work environment."
    )


def generate_ai(prompt, fallback_text):
    if not api_token:
        return fallback_text

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json={"inputs": prompt},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            generated_text = data[0].get("generated_text", "").strip()
            return generated_text or fallback_text
        if isinstance(data, dict) and data.get("error"):
            return fallback_text
        return fallback_text
    except requests.RequestException:
        return fallback_text
    except ValueError:
        return fallback_text


def get_form_value(field_name, default=""):
    return request.form.get(field_name, default).strip()

# OTP
def send_otp(email):
    otp = str(random.randint(1000, 9999))

    sender_email = os.environ.get("OTP_SENDER_EMAIL")
    app_password = os.environ.get("OTP_APP_PASSWORD")

    if sender_email and app_password:
        msg = MIMEText(f"Your CVGenie OTP is {otp}")
        msg["Subject"] = "CVGenie OTP"
        msg["From"] = sender_email
        msg["To"] = email

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)
            server.quit()
        except Exception:
            pass

    return otp

# ROUTES
@app.route("/")
def home():
    return render_template("home.html", user=session.get("user"))

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/free")
def free():
    return render_template("free.html")

@app.route("/premium")
def premium():
    return render_template("premium.html")

# 🔥 GENERATE FREE
@app.route("/generate", methods=["POST"])
def generate():
    name = get_form_value("name")
    email = get_form_value("email")
    mobile = get_form_value("mobile")
    other = get_form_value("other")

    skills = get_form_value("skills")
    exp = get_form_value("experience")
    extra = get_form_value("extra")

    prompt = f"""
    Create a professional resume:

    Name: {name}
    Email: {email}
    Mobile: {mobile}
    Other: {other}

    Skills: {skills}
    Experience: {exp}
    Extra: {extra}
    """

    fallback_profile = build_default_profile(
        name=name,
        skills=skills,
        experience=exp,
        extra=extra or other,
    )
    result = generate_ai(prompt, fallback_profile)

    return render_template(
        "result.html",
        name=name,
        email=email,
        mobile=mobile,
        skills=skills,
        experience=exp,
        extra=extra,
        result=result,
        photo=None,
    )
# 🔥 GENERATE PREMIUM
@app.route("/generate-premium", methods=["POST"])
def generate_premium():
    name = get_form_value("name")
    email = get_form_value("email")
    mobile = get_form_value("mobile")
    skills = get_form_value("skills")
    experience = get_form_value("experience")
    extra = get_form_value("extra")

    photo = request.files.get("photo")
    filename = None

    if photo and photo.filename:
        filename = secure_filename(photo.filename)
        photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    prompt = f"""
    Write a professional profile summary for:

    Name: {name}
    Skills: {skills}
    Experience: {experience}
    """

    fallback_profile = build_default_profile(
        name=name,
        skills=skills,
        experience=experience,
        extra=extra,
    )
    result = generate_ai(prompt, fallback_profile)

    return render_template(
        "result.html",
        name=name,
        email=email,
        mobile=mobile,
        skills=skills,
        experience=experience,
        extra=extra,
        result=result,
        photo=filename,
    )
# OTP
@app.route("/send-otp", methods=["POST"])
def send_otp_route():
    email = get_form_value("email")
    if not email:
        return redirect("/login")
    otp = send_otp(email)
    session["otp"] = otp
    session["temp_user"] = email
    return render_template("otp.html")

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    if get_form_value("otp") == session.get("otp"):
        session["user"] = session.get("temp_user")
        return redirect("/?login=success")
    return "Wrong OTP"

if __name__ == "__main__":
    app.run(debug=True)
