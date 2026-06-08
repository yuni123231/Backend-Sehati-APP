from flask import Flask, render_template, redirect, send_from_directory, url_for, request, session
from flask_mysqldb import MySQL
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from flask_cors import CORS
from flask import jsonify
from datetime import datetime
import tensorflow as tf
import numpy as np
from decimal import Decimal
from PIL import Image
import io
import json
import MySQLdb.cursors

app = Flask(__name__)
app.secret_key = 'secret-key-aman-123'
CORS(app)

# ==============================
# CONFIG
# ==============================
# MODEL_PATH = "model/food_classifier_finetune.keras"
# LABEL_PATH = "model/labels.json"

# ==============================
# LOAD MODEL
# ==============================
# print("Loading model...")
# model = tf.keras.models.load_model(MODEL_PATH)
# print("Model loaded successfully!")

# ==============================
# LOAD LABELS (WAJIB SESUAI TRAINING)
# ==============================
# with open(LABEL_PATH, "r") as f:
#     CLASS_NAMES = json.load(f)

# print("Labels loaded:", CLASS_NAMES)

# ==============================
# KALORI PER 100 GRAM
# ==============================
# FOOD_CALORIES = {
#     "hamburger": 297,
#     "pizza": 266,
#     "donuts": 421,
#     "pancakes": 227,
#     "waffles": 291,
#     "macaroni_and_cheese": 164,
#     "chocolate_cake": 371,
#     "cheesecake": 321,
#     "french_fries": 312,
#     "chicken_wings": 254,
#     "ramen": 440,
#     "ice_cream": 207,
#     "omelette": 154,
#     "spaghetti_bolognese": 121,
#     "steak": 143,
#     "hot_dog": 310,
#     "fried_rice": 174,
#     "sushi": 143,
#     "caesar_salad": 150,
#     "takoyaki": 210,
#     "gado_gado": 137,
#     "rendang": 193,
#     "soto": 312,
#     "sate_ayam": 225,
#     "bakso": 202
# }

# ==============================
# PREPROCESS FUNCTION
# ==============================
# def preprocess_image(image):
#     image = image.resize((224, 224))
#     image = np.array(image, dtype=np.float32) / 255.0
#     image = np.expand_dims(image, axis=0)
#     return image

# ==============================
# HEALTH CHECK
# ==============================
# @app.route("/")
# def home():
#     return jsonify({
#         "status": "Backend Running",
#         "model_output_shape": model.output_shape
#     })

# ================= DATABASE CONFIG =================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''      
app.config['MYSQL_DB'] = 'food_recommendation_db'

mysql = MySQL(app)

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

# @app.route("/food-log")
# @login_required
# def dashboard_food_log():
#     cur = mysql.connection.cursor()
#     cur.execute("""
#         SELECT fd.created_at, u.nama, fd.food_name, fd.total_calories, fd.detection_id
#         FROM food_detections fd
#         LEFT JOIN users u ON fd.user_id = u.user_id
#         ORDER BY fd.created_at DESC
#     """)
#     rows = cur.fetchall()
#     cur.close()

#     food_logs = []
#     for row in rows:
#         food_logs.append({
#             "date": row[0].strftime("%Y-%m-%d %H:%M:%S"),
#             "user": row[1],
#             "food_item": row[2],
#             "calories": int(row[3]),
#             "id": row[4]
#         })

#     return render_template("food_detection.html", food_logs=food_logs)

# @app.route("/api/delete-detection/<int:detection_id>", methods=["POST"])
# @login_required
# def delete_detection(detection_id):
#     try:
#         cur = mysql.connection.cursor()
#         cur.execute("DELETE FROM food_detections WHERE detection_id=%s", (detection_id,))
#         mysql.connection.commit()
#         cur.close()
#         return jsonify({"success": True, "message": "Detection deleted"})
#     except Exception as e:
#         return jsonify({"success": False, "message": str(e)}), 500

# # ===============================
# # RECOMMENDATIONS DASHBOARD
# # ===============================
# @app.route("/recommendations", methods=["GET", "POST"])
# @login_required
# def recommendations():
#     cur = mysql.connection.cursor()

#     # ================= INSERT DATA =================
#     if request.method == "POST":
#         jenis = request.form.get("jenis")
#         nama = request.form.get("nama")
#         deskripsi = request.form.get("deskripsi")
#         target_kalori = request.form.get("target_kalori")
#         satuan = request.form.get("satuan")
#         sumber = request.form.get("sumber")
#         kategori_kalori = request.form.get("kategori_kalori")

#         cur.execute("""
#             INSERT INTO recommendations
#             (jenis, nama, deskripsi, target_kalori, satuan, sumber, kategori_kalori)
#             VALUES (%s, %s, %s, %s, %s, %s, %s)
#         """, (jenis, nama, deskripsi, target_kalori, satuan, sumber, kategori_kalori))

#         mysql.connection.commit()
#         return redirect(url_for("recommendations"))

#     # ================= AMBIL DATA =================
#     cur.execute("""
#         SELECT recommendation_id, jenis, nama, target_kalori, satuan, sumber, kategori_kalori
#         FROM recommendations
#         ORDER BY recommendation_id DESC
#     """)
#     rows = cur.fetchall()
#     cur.close()

#     recommendations = []
#     for row in rows:
#         recommendations.append({
#             "id": row[0],
#             "jenis": row[1],
#             "nama": row[2],
#             "kalori": row[3],
#             "satuan": row[4],
#             "sumber": row[5],
#             "kategori_kalori": row[6]
#         })

#     return render_template("recommendations.html", recommendations=recommendations)

# @app.route("/delete-recommendation/<int:id>", methods=["POST"])
# @login_required
# def delete_recommendation(id):
#     cur = mysql.connection.cursor()
#     cur.execute("DELETE FROM recommendations WHERE recommendation_id=%s", (id,))
#     mysql.connection.commit()
#     cur.close()
#     return redirect(url_for("recommendations"))

@app.route("/settings")
def settings():
    return render_template("settings.html", title="Settings")

# ================== API SIGNUP ==================

@app.route("/api/signup", methods=["POST"])
def api_signup():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request tidak valid"}), 400

    nama = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not nama or not email or not password:
        return jsonify({"success": False, "message": "Nama, email, dan password wajib diisi"}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT user_id FROM users WHERE email=%s", (email,))
    if cur.fetchone():
        cur.close()
        return jsonify({"success": False, "message": "Email sudah terdaftar"}), 409

    hashed_password = generate_password_hash(password)
    created_at = datetime.now()
    cur.execute("""
        INSERT INTO users (nama, email, password, created_at)
        VALUES (%s, %s, %s, %s)
    """, (nama, email, hashed_password, created_at))
    mysql.connection.commit()
    user_id = cur.lastrowid
    cur.close()

    return jsonify({"success": True, "message": "Registrasi berhasil", "user_id": user_id}), 201

# ================= API SIGNIN =================
@app.route("/api/signin", methods=["POST"])
def api_signin():
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Request tidak valid"}), 400

    email = data.get("email")
    password = data.get("password")

    cur = mysql.connection.cursor()
    cur.execute("SELECT user_id, nama, password FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    cur.close()

    if not user or not check_password_hash(user[2], password):
        return jsonify({"success": False, "message": "Email atau password salah"}), 401

    return jsonify({
        "success": True,
        "user_id": user[0],
        "nama": user[1]
    }), 200

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

    # profile = {
    #     "nama": row[0],
    #     "email": row[1],  # <-- tambahkan ini
    #     "umur": row[2],
    #     "berat_badan": row[3],
    #     "tinggi_badan": row[4],
    #     "jenis_kelamin": row[5],
    #     "aktivitas": row[6],
    #     "tujuan": row[7],
    #     # "kebutuhan_kalori": row[8] if row[8] is not None else 0
    #     "kebutuhan_kalori": int(row[8]) if row[8] else 0

    # }
    
    # return jsonify({"success": True, "data" : profile}), 200

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

# ==============================
# FOOD DETECTION API
# ==============================
# @app.route("/api/food-detection", methods=["POST"])
# def api_food_detection():

#     if "image" not in request.files:
#         return jsonify({
#             "success": False,
#             "message": "Image file not found"
#         }), 400

#     try:
#         file = request.files["image"]

#         # ===== READ IMAGE =====
#         image = Image.open(io.BytesIO(file.read())).convert("RGB")

#         # ===== PREPROCESS =====
#         img_array = preprocess_image(image)

#         # ===== PREDICT =====
#         predictions = model.predict(img_array)
#         predicted_index = int(np.argmax(predictions))
#         confidence = float(np.max(predictions))

#         predicted_label = CLASS_NAMES[predicted_index]

#         # ===== CONFIDENCE THRESHOLD =====
#         if confidence < 0.6:
#             predicted_label = "Tidak yakin"

#         calories = FOOD_CALORIES.get(predicted_label, 0)

#         return jsonify({
#             "success": True,
#             "food_name": predicted_label,
#             "confidence_percent": round(confidence * 100, 2),
#             "calories_per_100g": calories
#         }), 200

#     except Exception as e:
#         return jsonify({
#             "success": False,
#             "error": str(e)
#         }), 500

# # ==============================
# # SAVE DETECTION TO DATABASE
# # ==============================
# @app.route("/api/save-detection", methods=["POST"])
# def api_save_detection():
#     data = request.get_json()
#     try:
#         user_id = data.get("user_id")
#         food_name = data.get("food_name") or "Unknown"
#         calories_per_100g = float(data.get("calories_per_100g", 0))
#         weight_gram = float(data.get("weight_gram", 0))
#         total_calories = float(data.get("total_calories", 0))
#         confidence = float(data.get("confidence", 0))
#         image_path = data.get("image_path") or ""

#         if not user_id:
#             return jsonify({"success": False, "message": "User ID wajib diisi"}), 400

#         cur = mysql.connection.cursor()
#         # ================= CEK USER =================
#         cur.execute("SELECT user_id FROM users WHERE user_id=%s", (user_id,))
#         if not cur.fetchone():
#             cur.close()
#             return jsonify({"success": False, "message": "User tidak ditemukan"}), 400

#         # ================= INSERT DETECTION =================
#         cur.execute("""
#             INSERT INTO food_detections
#             (user_id, food_name, calories_per_100g, weight_gram, total_calories, confidence, image_path, created_at)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
#         """, (user_id, food_name, calories_per_100g, weight_gram, total_calories, confidence, image_path))

#         mysql.connection.commit()
#         cur.close()
#         return jsonify({"success": True, "message": "Hasil deteksi berhasil disimpan"}), 201
#     except Exception as e:
#         print("ERROR SAVE DETECTION:", e)
#         return jsonify({"success": False, "message": str(e)}), 500

# # ============================== 
# # GET TODAY'S DETECTIONS
# # ==============================
# @app.route("/api/todays-detections/<int:user_id>", methods=["GET"])
# def api_todays_detections(user_id):
#     try:
#         cur = mysql.connection.cursor()
        
#         # Ambil semua deteksi hari ini untuk user_id
#         cur.execute("""
#             SELECT food_name, total_calories, created_at
#             FROM food_detections
#             WHERE user_id = %s
#               AND DATE(created_at) = CURDATE()
#             ORDER BY created_at DESC
#         """, (user_id,))
        
#         rows = cur.fetchall()
#         cur.close()
        
#         detections = []
#         for row in rows:
#             detections.append({
#                 "food_name": row[0],
#                 "total_calories": int(row[1]),
#                 "time": row[2].strftime("%H:%M:%S")  # optional: tampil jam deteksi
#             })
        
#         return jsonify({
#             "success": True,
#             "data": detections
#         }), 200
    
#     except Exception as e:
#         print("ERROR GET TODAYS DETECTIONS:", e)
#         return jsonify({
#             "success": False,
#             "message": str(e)
#         }), 500

# # ==============================
# # GET RECOMMENDATIONS FOR USER
# # ==============================
# @app.route("/api/recommendations/<int:user_id>", methods=["GET"])
# def get_recommendations(user_id):
#     try:
#         cur = mysql.connection.cursor()

#         # ================= GET KEBUTUHAN KALORI =================
#         cur.execute("SELECT kebutuhan_kalori FROM user_profiles WHERE user_id=%s", (user_id,))
#         profile = cur.fetchone()
#         if not profile:
#             return jsonify({"success": False, "message": "Profil tidak ditemukan"}), 404

#         kebutuhan_kalori = float(profile[0])  # pastikan float

#         # ================= GET TOTAL KALORI HARI INI =================
#         cur.execute("""
#             SELECT COALESCE(SUM(total_calories),0)
#             FROM food_detections
#             WHERE user_id=%s AND DATE(created_at)=CURDATE()
#         """, (user_id,))
#         total_today = cur.fetchone()[0] or 0

#         # konversi decimal -> float
#         if isinstance(total_today, Decimal):
#             total_today = float(total_today)

#         sisa_kalori = kebutuhan_kalori - total_today

#         # ================= FILTER REKOMENDASI =================
#         if sisa_kalori > 0:
#             # Jika masih ada kalori tersisa → tampilkan makanan <= sisa kalori
#             cur.execute("""
#                 SELECT nama AS description,
#                        target_kalori AS kalori,
#                        kategori_kalori AS kategori
#                 FROM recommendations
#                 WHERE jenis='Food' 
#                   AND target_kalori IS NOT NULL 
#                   AND target_kalori <= %s
#                 ORDER BY target_kalori DESC
#                 LIMIT 50
#             """, (sisa_kalori,))
#         else:
#             # Jika kelebihan kalori → tampilkan aktivitas untuk membakar kalori
#             cur.execute("""
#                 SELECT nama AS description,
#                        target_kalori AS kalori,
#                        kategori_kalori AS kategori
#                 FROM recommendations
#                 WHERE jenis='Activity' 
#                   AND target_kalori IS NOT NULL 
#                   AND target_kalori >= %s
#                 ORDER BY target_kalori ASC
#                 LIMIT 50
#             """, (abs(sisa_kalori),))

#         rows = cur.fetchall()
#         cur.close()

#         results = []
#         for row in rows:
#             results.append({
#                 "description": row[0],
#                 "kalori": float(row[1]) if row[1] is not None else 0,
#                 "kategori": row[2] or "-"
#             })

#         return jsonify({
#             "success": True,
#             "sisa_kalori": round(sisa_kalori, 2),
#             "data": results
#         }), 200

#     except Exception as e:
#         print("ERROR /api/recommendations:", e)
#         return jsonify({"success": False, "message": str(e)}), 500

############ PARAMETER GAYA HISUP SEHAT ############

@app.route('/api/save-activity', methods=['POST'])
def save_activity():
    try:
        data = request.get_json()

        print("DATA MASUK:", data)

        # ================= AMBIL DATA =================

        user_id = int(data.get('user_id', 0))

        durasi_aktivitas = int(
            data.get('durasi_aktivitas', 0)
        )

        frekuensi_olahraga = int(
            data.get('frekuensi_olahraga', 0)
        )

        intensitas_aktivitas = int(
            data.get('intensitas_aktivitas', 0)
        )

        aktivitas_harian = int(
            data.get('aktivitas_harian', 0)
        )

        sedentary = int(
            data.get('sedentary', 0)
        )

        skor_total = int(
            data.get('skor_total', 0)
        )

        kategori = data.get('kategori', '')

        # ================= VALIDASI =================

        if user_id == 0:
            return jsonify({
                "success": False,
                "message": "User tidak valid"
            }), 400

        # ================= SAVE DATABASE =================

        cur = mysql.connection.cursor()

        query = """
        INSERT INTO user_activities (
            user_id,
            durasi_aktivitas,
            frekuensi_olahraga,
            intensitas_aktivitas,
            aktivitas_harian,
            sedentary,
            skor_total,
            kategori
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            user_id,
            durasi_aktivitas,
            frekuensi_olahraga,
            intensitas_aktivitas,
            aktivitas_harian,
            sedentary,
            skor_total,
            kategori
        )

        cur.execute(query, values)

        mysql.connection.commit()
        cur.close()

        return jsonify({
            "success": True,
            "message": "Data aktivitas berhasil disimpan"
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
            frekuensi_olahraga,
            intensitas_aktivitas,
            aktivitas_harian,
            sedentary,
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
                "frekuensi_olahraga": data[1],
                "intensitas_aktivitas": data[2],
                "aktivitas_harian": data[3],
                "sedentary": data[4],
                "skor_total": data[5],
                "kategori": data[6],
                "created_at": str(data[7])
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
        print("DATA SLEEP MASUK:", data)  # 🔥 DEBUG

        user_id = int(data.get('user_id', 0))
        durasi = int(data.get('durasi_tidur', 0))
        gangguan = int(data.get('gangguan', 0))
        lama_terbangun = int(data.get('lama_terbangun', 0))
        kualitas = int(data.get('kualitas_tidur', 0))
        keteraturan = int(data.get('keteraturan', 0))
        skor_total = int(data.get('skor_total', 0))
        kategori = data.get('kategori', "")

        cur = mysql.connection.cursor()

        query = """
        INSERT INTO user_sleeps (
            user_id,
            durasi_tidur,
            gangguan,
            lama_terbangun,
            kualitas_tidur,
            keteraturan,
            skor_total,
            kategori
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            user_id,
            durasi,
            gangguan,
            lama_terbangun,
            kualitas,
            keteraturan,
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
                lama_terbangun,
                kualitas_tidur,
                keteraturan,
                skor_total,
                kategori
            FROM user_sleeps
            WHERE user_id = %s
            AND DATE(created_at) = CURDATE()
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
                    "lama_terbangun": data[2],
                    "kualitas_tidur": data[3],
                    "keteraturan": data[4],
                    "skor_total": data[5],
                    "kategori": data[6],
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

        cur.close()

        aktivitas_raw = data[0]
        diet_raw = data[1]
        tidur_raw = data[2]
        stres_raw = data[3]

        # ================= NORMALISASI =================

        aktivitas = (aktivitas_raw / 15) * 10
        diet = (diet_raw / 21) * 10
        tidur = (tidur_raw / 18) * 10

        if stres_raw == 0:
            stres = 0
        else:
            stres = ((40 - stres_raw) / 40) * 10

        aktivitas = max(0, min(10, aktivitas))
        diet = max(0, min(10, diet))
        tidur = max(0, min(10, tidur))
        stres = max(0, min(10, stres))

        # ================= BOBOT =================

        score = round(
            (diet * 0.15) +
            (aktivitas * 0.20) +
            (tidur * 0.30) +
            (stres * 0.35),
            1
        )

        # ================= STATUS =================

        if score >= 8:
            status = "Sangat Seimbang"
        elif score >= 6:
            status = "Seimbang"
        elif score >= 4:
            status = "Kurang Seimbang"
        else:
            status = "Tidak Seimbang"

        return jsonify({
            "success": True,

            "aktivitas": round(aktivitas, 1),
            "diet": round(diet, 1),
            "tidur": round(tidur, 1),
            "stres": round(stres, 1),

            "score": score,
            "status": status
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
            SELECT 
                DATE(created_at) tanggal,
                MAX(skor_total) skor_total,
                MAX(kategori) kategori
            FROM user_activities
            WHERE user_id = %s
            GROUP BY DATE(created_at)
        ) a ON dates.tanggal = a.tanggal

        LEFT JOIN (
            SELECT 
                DATE(created_at) tanggal,
                MAX(skor_total) skor_total,
                MAX(kategori) kategori
            FROM user_dietary
            WHERE user_id = %s
            GROUP BY DATE(created_at)
        ) d ON dates.tanggal = d.tanggal

        LEFT JOIN (
            SELECT 
                DATE(created_at) tanggal,
                MAX(skor_total) skor_total,
                MAX(kategori) kategori
            FROM user_sleeps
            WHERE user_id = %s
            GROUP BY DATE(created_at)
        ) s ON dates.tanggal = s.tanggal

        LEFT JOIN (
            SELECT 
                DATE(created_at) tanggal,
                MAX(skor_total) skor_total,
                MAX(kategori) kategori
            FROM user_stress
            WHERE user_id = %s
            GROUP BY DATE(created_at)
        ) st ON dates.tanggal = st.tanggal

        ORDER BY dates.tanggal ASC
        """

        cur.execute(query, (
            user_id,
            user_id,
            user_id,
            user_id
        ))

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
            diet_raw = row[3]
            tidur_raw = row[5]
            stres_raw = row[7]

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

            aktivitas = (aktivitas_raw / 15) * 10
            diet = (diet_raw / 21) * 10
            tidur = (tidur_raw / 18) * 10

            # stress dibalik
            # stress dibalik

            if stres_raw == 0:
                stres = 0
            else:
                stres = ((40 - stres_raw) / 40) * 10

            aktivitas = max(0, min(10, aktivitas))
            diet = max(0, min(10, diet))
            tidur = max(0, min(10, tidur))
            stres = max(0, min(10, stres))

            total = round(
                (diet * 0.15) +
                (aktivitas * 0.20) +
                (tidur * 0.30) +
                (stres * 0.35),
                1
            )

            # ================= STATUS =================

            if total >= 8:

                status = "Sangat Seimbang"

                conclusion = (
                    "Gaya hidup kamu sangat seimbang dan konsisten ✨"
                )

            elif total >= 6:

                status = "Seimbang"

                conclusion = (
                    "Gaya hidup kamu sudah cukup baik 🌱"
                )

            elif total >= 4:

                status = "Kurang Seimbang"

                conclusion = (
                    "Masih ada beberapa aspek yang perlu diperbaiki ⚠️"
                )

            else:

                status = "Tidak Seimbang"

                conclusion = (
                    "Perlu perhatian lebih pada gaya hidup sehari-hari 😴"
                )

            # ================= REKOMENDASI =================

            rekomendasi = []

            if aktivitas < 6:
                rekomendasi.append(
                    "tingkatkan aktivitas fisik"
                )

            if diet < 6:
                rekomendasi.append(
                    "perbaiki pola makan"
                )

            if tidur < 6:
                rekomendasi.append(
                    "perbaiki pola tidur"
                )

            if stres < 6:
                rekomendasi.append(
                    "kelola stres lebih baik"
                )

            if len(rekomendasi) == 0:
                recommendation_text = (
                    "Pertahankan kebiasaan sehatmu dan tetap konsisten 💚"
                )
            else:
                recommendation_text = (
                    "Fokus perbaikan minggu ini: "
                    + ", ".join(rekomendasi)
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

                "aktivitas": round(aktivitas, 1),
                "diet": round(diet, 1),
                "tidur": round(tidur, 1),
                "stres": round(stres, 1),

                "aktivitas_kategori": row[2],
                "diet_kategori": row[4],
                "tidur_kategori": row[6],
                "stres_kategori": row[8],

                "conclusion": conclusion,

                "recommendation": recommendation_text

            })

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

