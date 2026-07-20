from flask import Flask, render_template, redirect, send_from_directory, url_for, request, session
from flask_mysqldb import MySQL
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from flask_cors import CORS
from flask import jsonify
from datetime import datetime, timedelta
# import tensorflow as tf
import numpy as np
from decimal import Decimal
from PIL import Image
import jwt
from config import JWT_SECRET
import io
import re
import secrets
from flask_mail import Mail, Message
from config import (
    SECRET_KEY,
    MAIL_SERVER,
    MAIL_PORT,
    MAIL_USE_TLS,
    MAIL_USERNAME,
    MAIL_PASSWORD,
    MAIL_DEFAULT_SENDER
)
from google.oauth2 import id_token
from google.auth.transport import requests
import json
import MySQLdb.cursors

app = Flask(__name__)
app.secret_key = 'secret-key-aman-123'
CORS(app)

# ================= DATABASE CONFIG =================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''      
app.config['MYSQL_DB'] = 'food_recommendation_db'

mysql = MySQL(app)

# EMAIL
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS

app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER

mail = Mail(app)

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admins WHERE username=%s", (username,))
        admin = cur.fetchone()
        cur.close()

        if admin and check_password_hash(admin[2], password):
            session['admin'] = admin[1]
            return redirect(url_for('dashboard'))

        return render_template("login.html", error="Username / password salah")

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", title="Dashboard")

@app.route("/users")
@login_required
def users():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT 
            u.user_id,
            u.nama,
            u.email,
            p.umur,
            p.jenis_kelamin,
            p.tinggi_badan,
            p.berat_badan,
            p.aktivitas,
            p.tujuan,
            p.kebutuhan_kalori
        FROM users u
        LEFT JOIN user_profiles p ON u.user_id = p.user_id
    """)
    rows = cur.fetchall()
    cur.close()

    users = []
    for row in rows:
        users.append({
            "user_id": row[0],
            "nama": row[1],
            "email": row[2],
            "umur": row[3],
            "jenis_kelamin": row[4],
            "tinggi_badan": row[5],
            "berat_badan": row[6],
            "aktivitas": row[7],
            "tujuan": row[8],
            "kebutuhan_kalori": row[9],
        })
    
    print("================")
    print("Tanggal :", row[0])
    print("Aktivitas :", row[1])
    print("Aktivitas kategori :", row[2])

    print("Diet :", row[4])
    print("Diet kategori :", row[5])

    print("Tidur :", row[6])
    print("Tidur kategori :", row[7])

    print("Stress :", row[8])
    print("Stress kategori :", row[9])

    return render_template("user_data.html", users=users)

# ================== DELETE USER ==================
@app.route("/delete_user/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    try:
        cur = mysql.connection.cursor()
        # Hapus data profil dulu agar tidak melanggar foreign key
        cur.execute("DELETE FROM user_profiles WHERE user_id=%s", (user_id,))
        # Hapus user
        cur.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
        mysql.connection.commit()
        cur.close()
        return jsonify({"success": True, "message": "User berhasil dihapus"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/settings")
def settings():
    return render_template("settings.html", title="Settings")

# ================== API SIGNUP ==================

def is_strong_password(password):
    return re.match(
        r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$',
        password
    )

@app.route("/api/signup", methods=["POST"])
def api_signup():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Request tidak valid"
        }), 400

    nama = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not nama or not email or not password:
        return jsonify({
            "success": False,
            "message": "Semua field wajib diisi"
        }), 400

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({
            "success":False,
            "message":"Format email tidak valid"
        }),400

    if not is_strong_password(password):
        return jsonify({
            "success": False,
            "message": "Password minimal 8 karakter dan harus mengandung huruf besar, huruf kecil, angka dan simbol"
        }), 400

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT user_id FROM users WHERE email=%s",
        (email,)
    )

    if cur.fetchone():
        cur.close()

        return jsonify({
            "success": False,
            "message": "Email sudah digunakan"
        }), 409

    hashed_password = generate_password_hash(password)

    token = secrets.token_urlsafe(32)

    created_at = datetime.now()

    cur.execute("""
        INSERT INTO users(
            nama,
            email,
            password,
            provider,
            email_verified,
            verification_token,
            created_at
        )
        VALUES(%s,%s,%s,%s,%s,%s,%s)
    """,(
        nama,
        email,
        hashed_password,
        "local",
        False,
        token,
        created_at
    ))

    mysql.connection.commit()

    user_id = cur.lastrowid

    cur.close()

    verify_link = f"http://192.168.110.2:5000/api/verify-email/{token}"

    try:
        print("Kirim email ke:", email)

        msg = Message(
            subject="Verifikasi Akun Sehati",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[email]
        )

        msg.body = f"""
        Halo {nama},

        Terima kasih sudah mendaftar di aplikasi Sehati.

        Untuk mengaktifkan akun Anda, silakan klik tombol berikut:

        {verify_link}

        Link ini digunakan untuk verifikasi akun Anda.

        Jika Anda tidak melakukan pendaftaran, abaikan email ini.

        Salam,
        Tim Sehati
        """
        mail.send(msg)

        print("EMAIL BERHASIL TERKIRIM")

    except Exception as e:
        print("EMAIL ERROR:", e)

    return jsonify({
        "success": True,
        "user_id": user_id,
        "message": "Silakan cek email untuk verifikasi akun"
    }), 201

# ================= VERIFIKASI EMAIL ================= 
@app.route("/api/verify-email/<token>")
def verify_email(token):

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT user_id
        FROM users
        WHERE verification_token=%s
    """, (token,))

    user = cur.fetchone()

    if not user:
        cur.close()
        return "Token tidak valid"

    cur.execute("""
        UPDATE users
        SET
            email_verified=TRUE,
            verification_token=NULL
        WHERE user_id=%s
    """, (user[0],))

    mysql.connection.commit()

    cur.close()

    return """
    <h2>Email berhasil diverifikasi</h2>
    <p>Silakan kembali ke aplikasi dan login.</p>
    """

# ================= API SIGNIN =================
@app.route("/api/signin", methods=["POST"])
def api_signin():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Request tidak valid"
        }), 400

    email = data.get("email")
    password = data.get("password")


    if not email or not password:
        return jsonify({
            "success":False,
            "message":"Email dan password wajib diisi"
        }),400
    
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            user_id,
            nama,
            password,
            email_verified
        FROM users
        WHERE email=%s
    """,(email,))

    user = cur.fetchone()

    cur.close()

    # cek email ada atau tidak
    if not user:
        return jsonify({
            "success": False,
            "message": "Email tidak ditemukan"
        }),404

    # cek password
    if not check_password_hash(user[2], password):

        return jsonify({
            "success": False,
            "message": "Password salah"
        }),401

    # cek email sudah diverifikasi atau belum
    if not user[3]:

        return jsonify({
            "success": False,
            "message": "Silakan verifikasi email terlebih dahulu"
        }),403

    return jsonify({

        "success": True,
        "user_id": user[0],
        "nama": user[1]

    }),200

# ================= SIGN IN GOOGLE =================

@app.route('/api/signin-google', methods=['POST'])
def signin_google():

    data = request.get_json()

    if not data:
        return jsonify({
            "success":False,
            "message":"Request tidak valid"
        }),400

    email = data.get("email")

    if not email:
        return jsonify({
            "success":False,
            "message":"Email wajib ada"
        }),400

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            user_id,
            nama,
            email_verified
        FROM users
        WHERE email=%s
    """,(email,))
    user = cur.fetchone()
    cur.close()

    # email tidak ada
    if not user:
        return jsonify({
            "success":False,
            "message":"Email belum terdaftar"
        }),404

    # email belum diverifikasi
    if not user[2]:
        return jsonify({
            "success":False,
            "message":
            "Silakan verifikasi email terlebih dahulu"
        }),403

    return jsonify({
        "success":True,
        "user_id":user[0],
        "nama":user[1]
    }),200

# ================= FORGOT PASSWORD =================

@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({
            "success":False,
            "message":"Email wajib diisi"
        }),400
    cur = mysql.connection.cursor()
    cur.execute(
        """
        SELECT user_id,nama
        FROM users
        WHERE email=%s
        """,
        (email,)
    )
    user = cur.fetchone()
    if not user:
        cur.close()
        return jsonify({
            "success":False,
            "message":"Email tidak ditemukan"
        }),404
    # buat OTP 6 digit
    otp = str(
        secrets.randbelow(900000)+100000
    )
    expired = datetime.now() + timedelta(
        minutes=10
    )
    # simpan OTP ke users
    cur.execute(
        """
        UPDATE users
        SET 
        otp_code=%s,
        otp_expired=%s
        WHERE user_id=%s
        """,
        (otp, expired, user[0])
    )
    mysql.connection.commit()
    cur.close()
    try:
        msg = Message(
            subject=
            "Reset Password Sehati",
            sender=
            app.config['MAIL_DEFAULT_SENDER'],
            recipients=[
                email
            ]
        )
        msg.body=f"""
        Halo {user[1]}


        Kode OTP reset password kamu:


        {otp}


        Kode berlaku 5 menit.


        Tim Sehati

        """
        mail.send(msg)
    except Exception as e:
        print(
            "EMAIL ERROR:",
            e
        )
    return jsonify({
        "success":True,
        "message":
        "OTP berhasil dikirim"
    })

# ================= RESET PASSWORD =================
@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    data=request.get_json()
    email=data.get("email")
    otp=data.get("otp")
    password=data.get("password")
    if not email or not otp or not password:
        return jsonify({
            "success":False,
            "message":"Data belum lengkap"
        }),400
    cur=mysql.connection.cursor()
    cur.execute(
        """
        SELECT 
        user_id,
        otp_expired
        FROM users
        WHERE email=%s
        AND otp_code=%s
        """,
        (
        email,
        otp
        )
    )
    user=cur.fetchone()
    if not user:
        cur.close()
        return jsonify({
            "success":False,
            "message":
            "OTP salah"
        })
    if datetime.now() > user[1]:
        cur.close()
        return jsonify({
            "success":False,
            "message":
            "OTP sudah kadaluarsa"
        })
    password_hash = generate_password_hash(
        password
    )
    cur.execute(
        """
        UPDATE users
        SET
        password=%s,
        otp_code=NULL,
        otp_expired=NULL
        WHERE user_id=%s
        """,
        (
        password_hash,
        user[0]
        )
    )
    mysql.connection.commit()
    cur.close()
    return jsonify({
        "success":True,
        "message":
        "Password berhasil diperbarui"
    })

# ================== API USER PROFILE ==================
@app.route("/api/user_profile", methods=["POST"])
def api_user_profile():
    data = request.get_json()
    
    user_id = data.get("user_id")
    nama = data.get("name")
    email = data.get("email")
    password = data.get("password")  # optional

    umur = data.get("umur")
    berat_badan = data.get("berat_badan")
    tinggi_badan = data.get("tinggi_badan")
    jenis_kelamin = data.get("jenis_kelamin")
    aktivitas = data.get("aktivitas")
    tujuan = data.get("tujuan")
    alamat = data.get("alamat")

    if not user_id:
        return jsonify({"success": False, "message": "User ID tidak ditemukan"}), 400
    # if not all([umur, berat_badan, tinggi_badan, jenis_kelamin, aktivitas, tujuan]):
    #     return jsonify({"success": False, "message": "Data tidak lengkap"}), 400

    # ================= HITUNG KALORI =================
    result = hitung_kebutuhan_kalori(
        jk=jenis_kelamin,
        umur=int (umur),
        bb=float(berat_badan),
        tb=float(tinggi_badan),
        aktivitas=aktivitas,
        tujuan=tujuan
    )

    kebutuhan_kalori = result ["kebutuhan_kalori"]

    cur = mysql.connection.cursor()

    # ================= UPDATE TABEL USERS =================
    if nama or email or password:
        update_fields = []
        params = []
        if nama:
            update_fields.append("nama=%s")
            params.append(nama)
        if email:
            update_fields.append("email=%s")
            params.append(email)
        if password:
            hashed_password = generate_password_hash(password)
            update_fields.append("password=%s")
            params.append(hashed_password)
        params.append(user_id)
        cur.execute(f"UPDATE users SET {', '.join(update_fields)} WHERE user_id=%s", params)

    # ================= UPDATE/INSERT PROFIL =================
    cur.execute("SELECT profile_id FROM user_profiles WHERE user_id=%s", (user_id,))
    if cur.fetchone():
        cur.execute("""
            UPDATE user_profiles
            SET umur=%s,
                berat_badan=%s,
                tinggi_badan=%s,
                jenis_kelamin=%s,
                aktivitas=%s,
                tujuan=%s,
                kebutuhan_kalori=%s,
                alamat=%s
            WHERE user_id=%s
        """, (umur, berat_badan, tinggi_badan, jenis_kelamin, aktivitas, tujuan, kebutuhan_kalori, alamat, user_id))
    else:
        cur.execute("""
            INSERT INTO user_profiles
            (user_id, umur, berat_badan, tinggi_badan,
             jenis_kelamin, aktivitas, tujuan, kebutuhan_kalori, alamat)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, umur, berat_badan, tinggi_badan, jenis_kelamin, aktivitas, tujuan, kebutuhan_kalori, alamat))
    
    mysql.connection.commit()
    cur.close()

    return jsonify({
        "success": True,
        "message": "Profil berhasil diupdate",
        # "kebutuhan_kalori": kebutuhan_kalori
        "data" : result
    }), 200

# ==============================
# HITUNG KALORI + BMI
# ==============================

def hitung_kebutuhan_kalori(jk, umur, bb, tb, aktivitas, tujuan):
    
    # ================== BMR (HARRIS-BENEDICT) ==================
    if jk == 'Male':
        bmr = 66 + (13.7 * bb) + (5 * tb) - (6.8 * umur)
    else:
        bmr = 655 + (9.6 * bb) + (5 * tb) - (1.8 * umur)

    # ================== AKTIVITAS (PAL - 3 LEVEL SESUAI FLUTTER) ==================
    faktor = {
        'Light': 1.375,      # jarang olahraga
        'Moderate': 1.55,    # 1-3x/minggu
        'Active': 1.725      # 4x+/minggu
    }.get(aktivitas, 1.55)

    # ================== TDEE ==================
    tdee = bmr * faktor

    # ================== PENYESUAIAN TUJUAN ==================
    if tujuan == 'Lose Weight':
        tdee -= 300   # aman untuk remaja
    elif tujuan == 'Gain Weight':
        tdee += 300
    # Maintain → tidak diubah

    # ================== BATAS REALISTIS ==================
    tdee = max(1400, min(tdee, 2800))

    # ================== BMI ==================
    tb_meter = tb / 100
    bmi = bb / (tb_meter ** 2)

    # ================== KATEGORI BMI ==================
    if bmi < 18.5:
        kategori = "Kurus"
    elif bmi < 25:
        kategori = "Normal"
    elif bmi < 30:
        kategori = "Kegemukan"
    else:
        kategori = "Obesitas"

    # ================== REKOMENDASI ==================
    rekomendasi = []

    # berdasarkan BMI
    if kategori == "Kurus":
        rekomendasi.append("Perbanyak asupan kalori dan protein")
    elif kategori == "Normal":
        rekomendasi.append("Pertahankan pola makan seimbang")
    elif kategori == "Overweight":
        rekomendasi.append("Kurangi makanan tinggi gula dan lemak")
    else:
        rekomendasi.append("Atur pola makan dan lakukan olahraga rutin")

    # berdasarkan aktivitas (3 level)
    if aktivitas == "Light":
        rekomendasi.append("Coba mulai aktivitas ringan seperti jalan kaki 30 menit/hari")
    elif aktivitas == "Moderate":
        rekomendasi.append("Pertahankan aktivitas fisik secara rutin")
    elif aktivitas == "Active":
        rekomendasi.append("Aktivitas sudah baik, tetap konsisten")

    # ================== OUTPUT ==================
    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "bmi": round(bmi, 1),
        "kategori": kategori,
        "kebutuhan_kalori": round(tdee)
    }

@app.route("/api/user_profile/<int:user_id>", methods=["GET"])
def api_get_user_profile(user_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT u.nama, u.email, u.profile_photo, p.umur, p.berat_badan, p.tinggi_badan, 
               p.jenis_kelamin, p.aktivitas, p.tujuan, p.kebutuhan_kalori, p.alamat
        FROM users u
        LEFT JOIN user_profiles p ON u.user_id = p.user_id
        WHERE u.user_id=%s
    """, (user_id,))
    row = cur.fetchone()
    cur.close()

    if not row:
        return jsonify({"success": False, "message": "User tidak ditemukan"}), 404
    
    nama = row[0]
    email = row[1]
    profile_photo = row [2]
    umur = row[3]
    bb = row[4]
    tb = row[5]
    jk = row[6]
    aktivitas = row[7]
    tujuan = row[8]
    kebutuhan_kalori = int(row[9]) if row[9] else 0
    alamat = row[10]

    # 🔥 HITUNG ULANG BMI & TDEE
    hasil = hitung_kebutuhan_kalori(
        jk=jk,
        umur=int(umur),
        bb=float(bb),
        tb=float(tb),
        aktivitas=aktivitas,
        tujuan=tujuan
    )

    return jsonify({
        "success": True,
        "profile": {
            "nama": nama,
            "email": email,
            "profile_photo": profile_photo,
            "umur": umur,
            "berat_badan": bb,
            "tinggi_badan": tb,
            "jenis_kelamin": jk,
            "aktivitas": aktivitas,
            "tujuan": tujuan,

            "alamat": alamat,
            # "kebutuhan_kalori": kebutuhan_kalori,
            "kebutuhan_kalori": hasil["tdee"],

            # 🔥 INI YANG KURANG SEBELUMNYA
            "bmi": hasil["bmi"],
            "kategori": hasil["kategori"],
            "tdee": hasil["tdee"]
        }
    }), 200

# ================== API UPDATE USER ACCOUNT ==================
@app.route("/api/user_account/<int:user_id>", methods=["PUT"])
def api_update_user_account(user_id):
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Request tidak valid"}), 400

    nama = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not nama or not email:
        return jsonify({"success": False, "message": "Nama dan email wajib diisi"}), 400

    cur = mysql.connection.cursor()

    # cek user
    cur.execute("SELECT user_id FROM users WHERE user_id=%s", (user_id,))
    if not cur.fetchone():
        cur.close()
        return jsonify({"success": False, "message": "User tidak ditemukan"}), 404

    # update akun
    if password:
        hashed_password = generate_password_hash(password)
        cur.execute("""
            UPDATE users
            SET nama=%s, email=%s, password=%s
            WHERE user_id=%s
        """, (nama, email, hashed_password, user_id))
    else:
        cur.execute("""
            UPDATE users
            SET nama=%s, email=%s
            WHERE user_id=%s
        """, (nama, email, user_id))

    mysql.connection.commit()
    cur.close()

    return jsonify({
        "success": True,
        "message": "Akun berhasil diperbarui"
    }), 200


@app.route("/api/logout", methods=["POST"])
def api_logout():
    return jsonify({
        "success": True,
        "message": "Logout berhasil"
    }), 200

############ PARAMETER GAYA HISUP SEHAT ############
@app.route('/api/save-activity', methods=['POST'])
def save_activity():
    try:
        data = request.get_json()

        user_id = int(data.get('user_id', 0))
        durasi_aktivitas = int(data.get('durasi_aktivitas', 0))
        intensitas_aktivitas = int(data.get('intensitas_aktivitas', 0))
        sedentary = int(data.get('sedentary', 0))

        print("DURASI :", durasi_aktivitas)
        print("INTENSITAS :", intensitas_aktivitas)
        print("SEDENTARY :", sedentary)

        if user_id == 0:
            return jsonify({
                "success": False,
                "message": "User tidak valid"
            }), 400

        cur = mysql.connection.cursor()

        # ================= 1. SIMPAN DATA HARI INI =================
        insert_query = """
        INSERT INTO user_activities (
            user_id,
            durasi_aktivitas,
            intensitas_aktivitas,
            sedentary,
            created_at
        )
        VALUES (%s,%s,%s,%s,NOW())
        """

        cur.execute(insert_query, (
            user_id,
            durasi_aktivitas,
            intensitas_aktivitas,
            sedentary
        ))

        mysql.connection.commit()

        # ================= 2. HITUNG FREKUENSI WHO (7 HARI) =================
        cur.execute("""
            SELECT COUNT(DISTINCT DATE(created_at))
            FROM user_activities
            WHERE user_id = %s
            AND created_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        """, (user_id,))

        frekuensi_mingguan = cur.fetchone()[0]

        print("===================")
        print("USER :", user_id)
        print("FREKUENSI :", frekuensi_mingguan)
        print("===================")

        # ================= 3. SKOR FREKUENSI =================
        if frekuensi_mingguan >= 5:
            skor_frekuensi = 3
        elif frekuensi_mingguan >= 3:
            skor_frekuensi = 2
        else:
            skor_frekuensi = 1

        # ================= 4. SKOR LAIN =================
        skor_durasi = durasi_aktivitas
        skor_intensitas = intensitas_aktivitas
        skor_sedentary = sedentary

        skor_total = (
            skor_durasi +
            skor_intensitas +
            skor_sedentary +
            skor_frekuensi
        )

        # ================= 5. KATEGORI =================
        if skor_total >= 9:
            kategori = "Aktif (Baik)"
        elif skor_total >= 6:
            kategori = "Cukup Aktif"
        else:
            kategori = "Kurang Aktif"

        # ================= 6. UPDATE DATA TERAKHIR =================
        update_query = """
        UPDATE user_activities
        SET
            frekuensi_mingguan = %s,
            skor_total = %s,
            kategori = %s
        WHERE id = LAST_INSERT_ID()
        """

        cur.execute(update_query, (
            frekuensi_mingguan,
            skor_total,
            kategori
        ))

        mysql.connection.commit()
        cur.close()

        return jsonify({
            "success": True,
            "message": "Data aktivitas berhasil disimpan",
            "frekuensi_mingguan": frekuensi_mingguan,
            "skor_total": skor_total,
            "kategori": kategori
        }), 201

    except Exception as e:
        print("ERROR SAVE ACTIVITY:", str(e))
        return jsonify({
            "success": False,
            "message": "Gagal menyimpan data aktivitas",
            "error": str(e)
        }), 500

@app.route('/api/get-activity/<int:user_id>', methods=['GET'])
def get_activity(user_id):
    try:
        cur = mysql.connection.cursor()

        query = """
        SELECT

            durasi_aktivitas,
            intensitas_aktivitas,
            sedentary,
            frekuensi_mingguan,
            skor_total,
            kategori,
            created_at

        FROM user_activities

        WHERE user_id = %s
        AND DATE(created_at) = CURDATE()

        ORDER BY created_at DESC
        LIMIT 1
        """

        cur.execute(query, (user_id,))

        data = cur.fetchone()

        cur.close()

        if not data:
            return jsonify({
                "success": False,
                "message": "Data aktivitas tidak ditemukan"
            }), 404

        return jsonify({
            "success": True,
            "data": {

                "durasi_aktivitas": data[0],
                "intensitas_aktivitas": data[1],
                "sedentary": data[2],
                "frekuensi_mingguan": data[3],
                "skor_total": data[4],
                "kategori": data[5],
                "created_at": str(data[6])

            }
        })

    except Exception as e:
        print("ERROR GET ACTIVITY:", str(e))

        return jsonify({
            "success": False,
            "message": "Gagal mengambil data aktivitas",
            "error": str(e)
        }), 500
    
################### POLA MAKAN ########################

@app.route('/api/save-dietary', methods=['POST'])
def save_dietary():
    try:
        data = request.get_json()
        print("DATA DIETARY MASUK:", data)  # 🔥 DEBUG WAJIB

        user_id = int(data.get('user_id', 0))
        frekuensi_makan = int(data.get('frekuensi_makan', 0))
        sarapan = int(data.get('sarapan', 0))
        sayur_buah = int(data.get('sayur_buah', 0))
        junk_food = int(data.get('junk_food', 0))
        minuman_manis = int(data.get('minuman_manis', 0))
        air_putih = int(data.get('air_putih', 0))
        makanan_lengkap = int(data.get('makanan_lengkap', 0))
        skor_total = int(data.get('skor_total', 0))
        kategori = data.get('kategori', "")

        cur = mysql.connection.cursor()

        query = """
        INSERT INTO user_dietary (
            user_id,
            frekuensi_makan,
            sarapan,
            sayur_buah,
            junk_food,
            minuman_manis,
            air_putih,
            makanan_lengkap,
            skor_total,
            kategori
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            user_id,
            frekuensi_makan,
            sarapan,
            sayur_buah,
            junk_food,
            minuman_manis,
            air_putih,
            makanan_lengkap,
            skor_total,
            kategori
        )

        cur.execute(query, values)
        mysql.connection.commit()
        cur.close()

        return jsonify({
            "success": True,
            "message": "Data pola makan berhasil disimpan"
        }), 201

    except Exception as e:
        print("ERROR SAVE DIETARY:", str(e))
        return jsonify({
            "success": False,
            "message": "Gagal menyimpan data",
            "error": str(e)
        }), 500

@app.route('/api/get-dietary/<int:user_id>', methods=['GET'])
def get_dietary(user_id):
    try:
        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT 
                frekuensi_makan,
                sarapan,
                sayur_buah,
                junk_food,
                minuman_manis,
                air_putih,
                makanan_lengkap,
                skor_total,
                kategori
            FROM user_dietary
            WHERE user_id = %s
            AND DATE(created_at) = CURDATE()
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))

        data = cur.fetchone()
        cur.close()

        if data:
            return jsonify({
                "success": True,
                "data": {
                    "frekuensi_makan": data[0],
                    "sarapan": data[1],
                    "sayur_buah": data[2],
                    "junk_food": data[3],
                    "minuman_manis": data[4],
                    "air_putih": data[5],
                    "makanan_lengkap": data[6],
                    "skor_total": data[7],
                    "kategori": data[8],
                }
            })
        else:
            return jsonify({"success": False})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    
################### STRESS ########################

@app.route('/api/save-stress', methods=['POST'])
def save_stress():
    try:
        data = request.get_json()

        print("DATA STRESS MASUK:", data)

        user_id = int(data.get('user_id', 0))

        kontrol_diri = int(data.get('kontrol_diri', 0))
        beban_pikiran = int(data.get('beban_pikiran', 0))
        stres_harian = int(data.get('stres_harian', 0))
        percaya_diri = int(data.get('percaya_diri', 0))
        kepuasan_hidup = int(data.get('kepuasan_hidup', 0))
        emosi = int(data.get('emosi', 0))
        coping = int(data.get('coping', 0))
        overthinking = int(data.get('overthinking', 0))
        kewalahan = int(data.get('kewalahan', 0))
        kendali_situasi = int(data.get('kendali_situasi', 0))

        skor_total = int(data.get('skor_total', 0))
        kategori = data.get('kategori', "")

        cur = mysql.connection.cursor()

        query = """
        INSERT INTO user_stress (
            user_id,
            kontrol_diri,
            beban_pikiran,
            stres_harian,
            percaya_diri,
            kepuasan_hidup,
            emosi,
            coping,
            overthinking,
            kewalahan,
            kendali_situasi,
            skor_total,
            kategori
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            user_id,
            kontrol_diri,
            beban_pikiran,
            stres_harian,
            percaya_diri,
            kepuasan_hidup,
            emosi,
            coping,
            overthinking,
            kewalahan,
            kendali_situasi,
            skor_total,
            kategori
        )

        cur.execute(query, values)

        mysql.connection.commit()
        cur.close()

        return jsonify({
            "success": True,
            "message": "Data stres berhasil disimpan"
        }), 201

    except Exception as e:
        print("ERROR SAVE STRESS:", str(e))

        return jsonify({
            "success": False,
            "message": "Gagal menyimpan data stres",
            "error": str(e)
        }), 500


################### GET STRESS ########################

@app.route('/api/get-stress/<int:user_id>', methods=['GET'])
def get_stress(user_id):
    try:

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT
                kontrol_diri,
                beban_pikiran,
                stres_harian,
                percaya_diri,
                kepuasan_hidup,
                emosi,
                coping,
                overthinking,
                kewalahan,
                kendali_situasi,
                skor_total,
                kategori
            FROM user_stress
            WHERE user_id = %s
            AND DATE(created_at) = CURDATE()
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))

        data = cur.fetchone()

        cur.close()

        if data:
            return jsonify({
                "success": True,
                "data": {

                    "kontrol_diri": data[0],
                    "beban_pikiran": data[1],
                    "stres_harian": data[2],
                    "percaya_diri": data[3],
                    "kepuasan_hidup": data[4],
                    "emosi": data[5],
                    "coping": data[6],
                    "overthinking": data[7],
                    "kewalahan": data[8],
                    "kendali_situasi": data[9],

                    "skor_total": data[10],
                    "kategori": data[11],
                }
            })

        else:
            return jsonify({
                "success": False,
                "message": "Data tidak ditemukan"
            })

    except Exception as e:
        print("ERROR GET STRESS:", str(e))

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

################### SLEEP ########################

@app.route('/api/save-sleep', methods=['POST'])
def save_sleep():
    try:
        data = request.get_json()
        # print("DATA SLEEP MASUK:", data)  # 🔥 DEBUG

        user_id = int(data.get('user_id', 0))
        durasi = int(data.get('durasi_tidur', 0))
        gangguan = int(data.get('gangguan', 0))
        kualitas = int(data.get('kualitas_tidur', 0))
        lama_terbangun = int(data.get('lama_terbangun', 0))
        mengantuk = int(data.get('mengantuk_siang', 0))
        latensi = int(data.get('latensi_tidur', 0))
        jadwal = int(data.get('jadwal_tidur', 0))
        skor_total = int(data.get('skor_total', 0))
        kategori = data.get('kategori', "")

        cur = mysql.connection.cursor()

        query = """
        INSERT INTO user_sleeps(
            user_id,
            durasi_tidur,
            gangguan,
            kualitas_tidur,
            lama_terbangun,
            mengantuk_siang,
            latensi_tidur,
            jadwal_tidur,
            skor_total,
            kategori
        )
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            user_id,
            durasi,
            gangguan,
            kualitas,
            lama_terbangun,
            mengantuk,
            latensi,
            jadwal,
            skor_total,
            kategori
        )

        cur.execute(query, values)
        mysql.connection.commit()
        cur.close()

        return jsonify({
            "success": True,
            "message": "Data pola tidur berhasil disimpan"
        }), 201

    except Exception as e:
        print("ERROR SAVE SLEEP:", str(e))
        return jsonify({
            "success": False,
            "message": "Gagal menyimpan data pola tidur",
            "error": str(e)
        }), 500
    
@app.route('/api/get-sleep/<int:user_id>', methods=['GET'])
def get_sleep(user_id):
    try:
        print("USER ID SLEEP:", user_id)

        cur = mysql.connection.cursor()

        cur.execute("""
        SELECT
            durasi_tidur,
            gangguan,
            kualitas_tidur,
            lama_terbangun,
            mengantuk_siang,
            latensi_tidur,
            jadwal_tidur,
            skor_total,
            kategori
        FROM user_sleeps
        WHERE user_id=%s
        AND DATE(created_at)=CURDATE()
        ORDER BY created_at DESC
        LIMIT 1
        """, (user_id,))

        data = cur.fetchone()

        print("HASIL SLEEP:", data)

        cur.close()

        if data:
            return jsonify({
                "success": True,
                "data": {
                    "durasi_tidur": data[0],
                    "gangguan": data[1],
                    "kualitas_tidur": data[2],
                    "lama_terbangun": data[3],
                    "mengantuk_siang": data[4],
                    "latensi_tidur": data[5],
                    "jadwal_tidur": data[6],
                    "skor_total": data[7],
                    "kategori": data[8]
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": "Data tidak ditemukan"
            })

    except Exception as e:
        print("ERROR GET SLEEP:", str(e))
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
    
# ================= KESIMPULAN GAYA HIUP ==================
def get_health_status(score):

    if score >= 7.0:
        return (
            "Seimbang",
            "Gaya hidup kamu sudah seimbang dan konsisten ✨"
        )

    elif score >= 5.5:
        return (
            "Cukup Seimbang",
            "Gaya hidup kamu cukup baik, tetapi masih ada ruang untuk perbaikan 🌱"
        )

    else:
        return (
            "Perlu Perbaikan",
            "Perlu perhatian lebih pada gaya hidup sehari-hari 😴"
        )
    
@app.route('/api/today/<int:user_id>', methods=['GET'])
def get_today(user_id):
    try:
        cur = mysql.connection.cursor()

        query = """
        SELECT 
            COALESCE(
                (
                    SELECT skor_total
                    FROM user_activities
                    WHERE user_id=%s
                    AND DATE(created_at)=CURDATE()
                    ORDER BY created_at DESC
                    LIMIT 1
                ), 0
            ) AS aktivitas,

            COALESCE(
                (
                    SELECT skor_total
                    FROM user_dietary
                    WHERE user_id=%s
                    AND DATE(created_at)=CURDATE()
                    ORDER BY created_at DESC
                    LIMIT 1
                ), 0
            ) AS diet,
            COALESCE(
                (
                    SELECT skor_total
                    FROM user_sleeps
                    WHERE user_id=%s
                    AND DATE(created_at)=CURDATE()
                    ORDER BY created_at DESC
                    LIMIT 1
                ), 0
            ) AS tidur,

            COALESCE(
                (
                    SELECT skor_total
                    FROM user_stress
                    WHERE user_id=%s
                    AND DATE(created_at)=CURDATE()
                    ORDER BY created_at DESC
                    LIMIT 1
                ), 0
            ) AS stres
        """

        cur.execute(query, (
            user_id,
            user_id,
            user_id,
            user_id
        ))

        data = cur.fetchone()

        cur.close()

        aktivitas_raw = data[0]
        diet_raw = data[1]
        tidur_raw = data[2]
        stres_raw = data[3]

        # ================= NORMALISASI =================
        aktivitas = (aktivitas_raw / 12) * 10
        diet = (diet_raw / 21) * 10
        if tidur_raw == 0:
            tidur = 0
        else:
            tidur = 10 - ((tidur_raw / 21) * 10)

        tidur = max(0, min(10, tidur))

        if stres_raw == 0:
            stres = 0
        else:
            stres = 10 - ((stres_raw / 40) * 10)

        aktivitas = max(0, min(10, aktivitas))
        diet = max(0, min(10, diet))
        tidur = max(0, min(10, tidur))
        stres = max(0, min(10, stres))

        # ================= BOBOT =================
        score = round(
            (diet * 0.25) +
            (aktivitas * 0.143) +
            (tidur * 0.25) +
            (stres * 0.357),
            1
        )
        status, conclusion = get_health_status(score)

        return jsonify({
            "success": True,

            # nilai asli untuk tampilan user
            "aktivitas": aktivitas_raw,
            "diet": diet_raw,
            "tidur": tidur_raw,
            "stres": stres_raw,


            # nilai normalisasi SAW
            "aktivitas_normal": round(aktivitas,1),
            "diet_normal": round(diet,1),
            "tidur_normal": round(tidur,1),
            "stres_normal": round(stres,1),

            "score": score,
            "status": status,
            "conclusion": conclusion
        })

    except Exception as e:
        print("ERROR TODAY:", str(e))

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
       
@app.route('/api/history/<int:user_id>', methods=['GET'])
def get_history(user_id):
    try:
        cur = mysql.connection.cursor()

        query = """
        SELECT 
            dates.tanggal,

            COALESCE(a.skor_total, 0) as aktivitas,
            COALESCE(a.kategori, '-') as aktivitas_kategori,
            COALESCE(a.frekuensi_mingguan, 0) as frekuensi_mingguan,

            COALESCE(d.skor_total, 0) as diet,
            COALESCE(d.kategori, '-') as diet_kategori,

            COALESCE(s.skor_total, 0) as tidur,
            COALESCE(s.kategori, '-') as tidur_kategori,

            COALESCE(st.skor_total, 0) as stres,
            COALESCE(st.kategori, '-') as stres_kategori

        FROM (
            SELECT CURDATE() as tanggal
            UNION SELECT CURDATE() - INTERVAL 1 DAY
            UNION SELECT CURDATE() - INTERVAL 2 DAY
            UNION SELECT CURDATE() - INTERVAL 3 DAY
            UNION SELECT CURDATE() - INTERVAL 4 DAY
            UNION SELECT CURDATE() - INTERVAL 5 DAY
            UNION SELECT CURDATE() - INTERVAL 6 DAY
        ) dates

        LEFT JOIN (
            SELECT DATE(created_at) as tanggal, skor_total, kategori, frekuensi_mingguan
            FROM user_activities
            WHERE id IN (
                SELECT MAX(id) 
                FROM user_activities 
                WHERE user_id = %s 
                GROUP BY DATE(created_at)
            )
        ) a ON dates.tanggal = a.tanggal

        LEFT JOIN (
            SELECT DATE(created_at) as tanggal, skor_total, kategori
            FROM user_dietary
            WHERE id IN (
                SELECT MAX(id) 
                FROM user_dietary 
                WHERE user_id = %s 
                GROUP BY DATE(created_at)
            )
        ) d ON dates.tanggal = d.tanggal

        LEFT JOIN (
            SELECT DATE(created_at) as tanggal, skor_total, kategori
            FROM user_sleeps
            WHERE id IN (
                SELECT MAX(id) 
                FROM user_sleeps 
                WHERE user_id = %s 
                GROUP BY DATE(created_at)
            )
        ) s ON dates.tanggal = s.tanggal

        LEFT JOIN (
            SELECT DATE(created_at) as tanggal, skor_total, kategori
            FROM user_stress
            WHERE id IN (
                SELECT MAX(id) 
                FROM user_stress 
                WHERE user_id = %s 
                GROUP BY DATE(created_at)
            )
        ) st ON dates.tanggal = st.tanggal

        ORDER BY dates.tanggal ASC
        """

        cur.execute(query, (
            user_id,
            user_id,
            user_id,
            user_id
        ))

        print("USER ID :", user_id)

        rows = cur.fetchall()

        cur.close()

        result = []

        bulan = [
            "Jan", "Feb", "Mar", "Apr",
            "Mei", "Jun", "Jul", "Agu",
            "Sep", "Okt", "Nov", "Des"
        ]

        hari = [
            "Senin",
            "Selasa",
            "Rabu",
            "Kamis",
            "Jumat",
            "Sabtu",
            "Minggu"
        ]

        from datetime import datetime

        for row in rows:

            aktivitas_raw = row[1]
            frekuensi_mingguan = row[3]

            diet_raw = row[4]
            tidur_raw = row[6]
            stres_raw = row[8]

            # ================= FORMAT TANGGAL =================

            parsed = datetime.strptime(
                str(row[0]),
                "%Y-%m-%d"
            )

            full_date = (
                f"{parsed.day} "
                f"{bulan[parsed.month - 1]} "
                f"{parsed.year}"
            )

            full_label = (
                f"{hari[parsed.weekday()]}, "
                f"{full_date}"
            )

            # ================= BELUM ADA DATA =================

            if (
                aktivitas_raw == 0 and
                diet_raw == 0 and
                tidur_raw == 0 and
                stres_raw == 0
            ):

                result.append({

                    "tanggal": str(row[0]),

                    "full_label": full_label,

                    "score": 0,
                    
                    # ================= TAMBAH =================

                    "frekuensi_mingguan":
                        frekuensi_mingguan if frekuensi_mingguan else 0,

                    "status": "Belum Ada Data",

                    "aktivitas": 0,
                    "diet": 0,
                    "tidur": 0,
                    "stres": 0,

                    "aktivitas_kategori": "-",
                    "diet_kategori": "-",
                    "tidur_kategori": "-",
                    "stres_kategori": "-",

                    "conclusion":
                    "Belum ada laporan gaya hidup.",

                    "recommendation":
                    "Lengkapi data aktivitas, pola makan, tidur, dan stres."
                })

                continue

            # ================= NORMALISASI =================

            aktivitas = (aktivitas_raw / 12) * 10
            diet = (diet_raw / 21) * 10

            if tidur_raw == 0:
                tidur = 0
            else:
                tidur = 10 - ((tidur_raw / 21) * 10)

            if stres_raw == 0:
                stres = 0
            else:
                stres = 10 - ((stres_raw / 40) * 10)

            aktivitas = max(0, min(10, aktivitas))
            diet = max(0, min(10, diet))
            tidur = max(0, min(10, tidur))
            stres = max(0, min(10, stres))

            print("===== SCORE PARAMETER =====")
            print("Aktivitas Raw :", aktivitas_raw)
            print("Aktivitas Normal :", round(aktivitas, 2))

            print("Diet Raw :", diet_raw)
            print("Diet Normal :", round(diet, 2))

            print("Tidur Raw :", tidur_raw)
            print("Tidur Normal :", round(tidur, 2))

            print("Stress Raw :", stres_raw)
            print("Stress Normal :", round(stres, 2))
            print("===========================")

            total = round(
                (diet * 0.25) +
                (aktivitas * 0.143) +
                (tidur * 0.25) +
                (stres * 0.357),
                1
            )
            print("===== PERHITUNGAN SAW =====")
            print("Diet :", round(diet * 0.25, 2))
            print("Aktivitas :", round(aktivitas * 0.143, 2))
            print("Tidur :", round(tidur * 0.25, 2))
            print("Stress :", round(stres * 0.357, 2))
            print("Total Score :", total)
            print("===========================")
            status, conclusion = get_health_status(total)

            # ================= DEBUG =================

            print("======================")
            print("Tanggal :", row[0])
            print("Aktivitas :", aktivitas_raw)
            print("Diet :", diet_raw)
            print("Tidur :", tidur_raw)
            print("Stress :", stres_raw)
            print("Frekuensi :", frekuensi_mingguan)
            print("Total :", total)
            print("Status :", status)

            # ================= REKOMENDASI BERDASARKAN PERSENTASE =================
            rekomendasi = []

            # Aktivitas
            aktivitas_persen = aktivitas_raw / 12
            if aktivitas_persen < 0.5:
                rekomendasi.append({
                    "nilai": aktivitas_persen,
                    "pesan":
                    "Tingkatkan aktivitas fisik minimal 60 menit setiap hari sesuai anjuran WHO."
                })

            # Diet
            diet_persen = diet_raw / 21
            if diet_persen < 0.5:
                rekomendasi.append({
                    "nilai": diet_persen,
                    "pesan":
                    "Perbaiki pola makan dengan makan teratur, memperbanyak buah dan sayur, serta mengurangi makanan cepat saji."
                })

            # Tidur
            tidur_baik = 21 - tidur_raw
            tidur_persen = tidur_baik / 21
            if tidur_persen < 0.5:
                rekomendasi.append({
                    "nilai": tidur_persen,
                    "pesan":
                    "Perbaiki kualitas tidur dengan tidur 7–9 jam dan menjaga jadwal tidur."
                })

            # Stress
            stress_baik = 40 - stres_raw
            stress_persen = stress_baik / 40
            if stress_persen < 0.5:
                rekomendasi.append({
                    "nilai": stress_persen,
                    "pesan":
                    "Kelola stres dengan relaksasi, aktivitas positif, dan istirahat cukup."
                })

            print("===== SCORE REKOMENDASI =====")
            print("Aktivitas :", round(aktivitas_raw / 12, 2))
            print("Diet :", round(diet_raw / 21, 2))
            print("Tidur :", round((21 - tidur_raw) / 21, 2))
            print("Stress :", round((40 - stres_raw) / 40, 2))
            print("=============================")

            if rekomendasi:
                recommendation_text = "\n".join(
                    [item["pesan"] for item in rekomendasi]
                )
            else:
                recommendation_text = (
                    "Semua aspek gaya hidup sudah baik. Pertahankan kebiasaan sehatmu."
                )

             # ================= FORMAT TANGGAL =================

            parsed = datetime.strptime(
                str(row[0]),
                "%Y-%m-%d"
            )

            full_date = (
                f"{parsed.day} "
                f"{bulan[parsed.month - 1]} "
                f"{parsed.year}"
            )

            full_label = (
                f"{hari[parsed.weekday()]}, "
                f"{full_date}"
            )

            # ================= JSON =================

            result.append({
                "tanggal": str(row[0]),
                "full_label": full_label,
                "score": total,
                "status": status,

                "aktivitas": aktivitas_raw,
                "diet": diet_raw,
                "tidur": tidur_raw,
                "stres": stres_raw,

                "aktivitas_normal": round(aktivitas,1),
                "diet_normal": round(diet,1),
                "tidur_normal": round(tidur,1),
                "stres_normal": round(stres,1),

                # ================= TAMBAH =================
                "frekuensi_mingguan": frekuensi_mingguan if frekuensi_mingguan else 0,

                "aktivitas_kategori": row[2],
                "diet_kategori": row[5],
                "tidur_kategori": row[7],
                "stres_kategori": row[9],
                "conclusion": conclusion,
                "recommendation": recommendation_text
            })

        print(result)
        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        print("ERROR HISTORY:", str(e))

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
    
@app.route('/api/today-report/<int:user_id>', methods=['GET'])
def today_report(user_id):

    try:
        cur = mysql.connection.cursor()

        query = """
        SELECT

        COALESCE(
        (SELECT skor_total
        FROM user_activities
        WHERE user_id=%s
        AND DATE(created_at)=CURDATE()
        ORDER BY id DESC LIMIT 1),0),

        COALESCE(
        (SELECT skor_total
        FROM user_dietary
        WHERE user_id=%s
        AND DATE(created_at)=CURDATE()
        ORDER BY id DESC LIMIT 1),0),

        COALESCE(
        (SELECT skor_total
        FROM user_sleeps
        WHERE user_id=%s
        AND DATE(created_at)=CURDATE()
        ORDER BY id DESC LIMIT 1),0),

        COALESCE(
        (SELECT skor_total
        FROM user_stress
        WHERE user_id=%s
        AND DATE(created_at)=CURDATE()
        ORDER BY id DESC LIMIT 1),0)

        """

        cur.execute(query,(
            user_id,
            user_id,
            user_id,
            user_id
        ))

        data = cur.fetchone()

        cur.close()

        aktivitas = (data[0]/12)*10
        diet = (data[1]/21)*10

        tidur = 0
        if data[2] > 0:
            tidur = 10 - ((data[2]/21)*10)

        stres = 0
        if data[3] > 0:
            stres = 10 - ((data[3]/40)*10)

        aktivitas = max(0,min(10,aktivitas))
        diet = max(0,min(10,diet))
        tidur = max(0,min(10,tidur))
        stres = max(0,min(10,stres))

        score = round(
            (diet*0.25)+
            (aktivitas*0.143)+
            (tidur*0.25)+
            (stres*0.357),
            1
        )
    
        status, conclusion = get_health_status(score)

        print("RAW")
        print(data)
        print("===== SAW BACKEND =====")
        print("Aktivitas :", aktivitas)
        print("Diet :", diet)
        print("Tidur :", tidur)
        print("Stress :", stres)
        print("Total :", score)
        print("Status :", status)
        print("=======================")

        return jsonify({
            "success":True,
            "score":score,
            "status":status,
            "conclusion":conclusion
        })

    except Exception as e:

        return jsonify({
            "success":False,
            "message":str(e)
        })
      
# ================= REKOMENDASI SARAN PSIKOLOG =================
@app.route('/api/psikolog', methods=['GET'])
def get_psikolog():
    try:
        kota = request.args.get('kota', '').lower()

        cur = mysql.connection.cursor()

        # ambil data berdasarkan kota
        cur.execute("""
            SELECT nama, tempat, url
            FROM psikolog
            WHERE LOWER(kota) LIKE %s
        """, ('%' + kota + '%',))

        rows = cur.fetchall()
        cur.close()

        result = []

        for r in rows:
            result.append({
                "dokter": r[0],
                "tempat": r[1],
                "url": r[2]
            })

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

# ================= UPLOAD FOTO PROFIL =================
import os

UPLOAD_FOLDER = "uploads/profile"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload_profile_photo', methods=['POST'])
def upload_profile_photo():

    user_id = request.form.get('user_id')

    if 'photo' not in request.files:
        return jsonify({
            "success": False,
            "message": "Foto tidak ditemukan"
        }), 400

    photo = request.files['photo']

    if photo.filename == '':
            return jsonify({
                "success": False,
                "message": "File kosong"
            }), 400

    filename = f"user_{user_id}.jpg"

    photo_path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    photo.save(photo_path)

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE users
        SET profile_photo=%s
        WHERE user_id=%s
    """, (
        filename,
        user_id
    ))

    mysql.connection.commit()

    cursor.close()

    return jsonify({
        "success": True,
        "photo": filename
    })

# =====================================================
# AMBIL FOTO PROFIL
# =====================================================

@app.route('/uploads/profile/<filename>')
def profile_photo(filename):

    print("FILE DIMINTA:", filename)

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )

@app.route('/api/user_profile/<int:user_id>')
def get_user_profile(user_id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        WHERE user_id=%s
    """, (user_id,))

    user = cursor.fetchone()

    print("USER:", user)

    cursor.close()

    return jsonify({
        "success": True,
        "profile": user
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

