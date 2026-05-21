
import os
import secrets
from flask import Blueprint, request, jsonify, session, url_for, redirect, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from core.db import (
    create_platform_user, get_platform_user_by_email, 
    verify_platform_user
)

auth_bp = Blueprint('auth', __name__)


def _dev_auth_shortcuts_enabled() -> bool:
    app_env = os.environ.get("APP_ENV", "development").lower()
    if app_env not in {"development", "dev", "local"}:
        return False
    return os.environ.get("ENGINE_DEV_AUTH_SHORTCUTS", "").lower() in {"1", "true", "yes"}

@auth_bp.route("/login")
def auth_login_page():
    from flask import current_app
    if 'user_id' in session:
        return redirect(url_for('index'))
    return send_from_directory(current_app.template_folder, "auth.html")

@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Lütfen e-posta ve şifrenizi girin."}), 400
        
    hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
    token = secrets.token_hex(16)
    
    res = create_platform_user(email, hashed_pw, token)
    if not res["success"]:
        return jsonify({"error": res["error"]}), 400
        
    # Development shortcut is opt-in; production-like flows keep verification mandatory.
    if _dev_auth_shortcuts_enabled():
        verify_platform_user(token)
    
    return jsonify({"success": True, "message": "Kayıt başarılı! Giriş yapabilirsiniz."})

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")

    user = get_platform_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
         return jsonify({"error": "Geçersiz e-posta veya şifre."}), 401
         
    if not user["is_verified"]:
         return jsonify({"error": "Lütfen e-posta adresinizi doğrulayın."}), 403
         
    session['user_id'] = user['id']
    session['email'] = user['email']
    return jsonify({"success": True})

@auth_bp.route("/api/auth/verify/<token>", methods=["GET"])
def verify_email(token):
    success = verify_platform_user(token)
    if success:
        return "<h2 style='color:green; font-family:sans-serif'>Hesabınız doğrulandı! <a href='/login'>Giriş Yap</a></h2>"
    return "<h2 style='color:red; font-family:sans-serif'>Geçersiz token!</h2>"

@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})
