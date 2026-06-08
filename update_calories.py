# update_calories.py
from app import app, mysql, hitung_kebutuhan_kalori

def update_all_profiles():
    """
    Hitung dan update kebutuhan_kalori untuk semua user.
    Baik yang lama (NULL) maupun yang baru.
    """
    with app.app_context():  # Pastikan Flask context aktif
        cur = mysql.connection.cursor()

        # Ambil semua profil yang masih belum dihitung atau ingin diupdate
        cur.execute("""
            SELECT user_id, umur, berat_badan, tinggi_badan, jenis_kelamin, aktivitas, tujuan
            FROM user_profiles
        """)
        rows = cur.fetchall()

        if not rows:
            print("Tidak ada profil user di database.")
            return

        count = 0
        for row in rows:
            user_id, umur, berat_badan, tinggi_badan, jenis_kelamin, aktivitas, tujuan = row

            # Lewati profil yang datanya tidak lengkap
            if None in (umur, berat_badan, tinggi_badan, jenis_kelamin, aktivitas, tujuan):
                continue

            # Hitung kalori
            kalori = hitung_kebutuhan_kalori(
                jk=jenis_kelamin,
                umur=umur,
                bb=berat_badan,
                tb=tinggi_badan,
                aktivitas=aktivitas,
                tujuan=tujuan
            )

            # Update ke database
            cur.execute(
                "UPDATE user_profiles SET kebutuhan_kalori=%s WHERE user_id=%s",
                (kalori, user_id)
            )
            count += 1

        mysql.connection.commit()
        cur.close()
        print(f"Berhasil update kebutuhan_kalori untuk {count} profil user!")

@app.route("/api/user_profile/<int:user_id>", methods=["GET"])
def api_get_user_profile(user_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT u.nama, p.kebutuhan_kalori
        FROM users u
        LEFT JOIN user_profiles p ON u.user_id = p.user_id
        WHERE u.user_id=%s
    """, (user_id,))
    row = cur.fetchone()
    cur.close()

    if row:
        return jsonify({"success": True, "profile": {"nama": row[0], "kebutuhan_kalori": row[1]}}), 200
    else:
        return jsonify({"success": False, "message": "User tidak ditemukan"}), 404


if __name__ == "__main__":
    update_all_profiles()
