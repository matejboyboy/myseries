# from fileinput import filename
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import os
import psycopg2
import psycopg2.extras


app = Flask(__name__)
app.secret_key = "some-long-random-string"

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'PROFILE_PIC')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

# -------------------------------------------------
# HOME
# -------------------------------------------------
@app.route("/")
def home():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT id, name, episodes, genre, duration, image
        FROM series
        ORDER BY RANDOM()
        LIMIT 6
    """)
    hot_series = cur.fetchall()

    cur.execute("""
        SELECT id, name, image
        FROM series
        ORDER BY aired DESC
        LIMIT 20
    """)
    newest_series = cur.fetchall()

    cur.execute("""
        SELECT id, name, image
        FROM series
        WHERE genre ILIKE '%Romance%'
        ORDER BY RANDOM()
        LIMIT 20
    """)
    romance_series = cur.fetchall()

    cur.execute("""
        SELECT id, name, image
        FROM series
        WHERE genre ILIKE '%Action%'
        ORDER BY RANDOM()
        LIMIT 20
    """)
    action_series = cur.fetchall()

    cur.execute("""
        SELECT id, name, image
        FROM series
        WHERE genre ILIKE '%Drama%'
        ORDER BY RANDOM()
        LIMIT 20
    """)
    drama_series = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("HomePage.html", hot_series=hot_series, newest_series=newest_series,
                           romance_series=romance_series, action_series=action_series, drama_series=drama_series)
# -------------------------------------------------
# ALL SERIES
# -------------------------------------------------
@app.route("/series")
def series():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT id, name, episodes, genre, aired, endedairing,
               source, duration, rating, image
        FROM series
        ORDER BY name
    """)
    all_series = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("Series.html", series=all_series)


# -------------------------------------------------
# ABOUT
# -------------------------------------------------
@app.route("/about_us")
def about_us():
    return render_template("About_Us.html")


# -------------------------------------------------
# SERIES INFO PAGE BY ID
# -------------------------------------------------
# -------------------------------------------------
# SERIES INFO PAGE BY ID (with user rating)
# -------------------------------------------------
@app.route("/series/<int:series_id>")
def series_info(series_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM series WHERE id=%s", (series_id,))
    series = cur.fetchone()

    if not series:
        cur.close()
        conn.close()
        return "Series not found", 404

    safe_name = series['name'].replace(" ", "").lower()
    summary_file = os.path.join(app.root_path, 'static', 'SUMMARIES', f"{safe_name}.txt")

    series['Summary'] = "Summary not available."
    if os.path.exists(summary_file):
        with open(summary_file, 'r', encoding='utf-8') as f:
            series['Summary'] = f.read()

    user_data = None
    if session.get('username'):
        cur.execute("""
            SELECT rating, status
            FROM user_series
            WHERE series_id = %s
            AND user_id = (
                SELECT id FROM user_info WHERE username=%s
            )
            """, (series_id, session['username']))

        user_data = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("info.html", series=series, user_data=user_data)




# -------------------------------------------------
# SERIES INFO PAGE BY NAME (WITH SUMMARY)
# -------------------------------------------------
@app.route('/series_info/<series_name>')
def series_info_by_name(series_name):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM series WHERE name ILIKE %s", (series_name,))
    series = cur.fetchone()

    cur.close()
    conn.close()

    if not series:
        return "Series not found.", 404

    safe_name = series['name'].replace(" ", "").lower()
    summary_file = os.path.join(app.root_path, 'static', 'SUMMARIES', f"{safe_name}.txt")

    summary = "Summary not available."

    if os.path.exists(summary_file):
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = f.read()
        except Exception as e:
            summary = f"Error reading summary: {str(e)}"

    series['Summary'] = summary

    return render_template('info.html', series=series)

# USER AUTH
# -------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM user_info WHERE username=%s", (username,))
        if cur.fetchone():
            cur.close()
            conn.close()
            flash("Username already exists", "error")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        cur.execute("""
            INSERT INTO user_info (username, password, created_at)
            VALUES (%s, %s, %s)
        """, (username, hashed_password, date.today()))

        conn.commit()
        cur.close()
        conn.close()

        flash("Account created successfully!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT password, color_theme, profile_pic
            FROM user_info 
            WHERE username = %s
        """, (username,))

        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user or not check_password_hash(user["password"], password):
            flash("Invalid username or password", "error")
            return redirect(url_for("login"))

        # Ensure safe defaults
        session["username"] = username
        session["theme"] = user.get("color_theme") or "light"
        session["profile_pic"] = user.get("profile_pic") or ""  # <-- set empty string if None

        flash("Logged in successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("login.html")

@app.route("/set_theme", methods=["POST"])
def set_theme():
    if "username" not in session:
        return jsonify({"success": False})

    data = request.get_json()
    new_theme = data.get("theme")

    if new_theme not in ["light", "dark"]:
        return jsonify({"success": False})

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE user_info 
        SET color_theme = %s
        WHERE username = %s
    """, (new_theme, session["username"]))

    conn.commit()
    cur.close()
    conn.close()

    session["theme"] = new_theme

    return jsonify({"success": True})

@app.context_processor
def inject_theme():
    return dict(current_theme=session.get("theme", "light"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "success")
    return redirect(url_for("login"))


import os # Make sure this is at the top

# ... (other routes) ...

@app.route("/profile")
def profile():
    if "username" not in session:
        return redirect(url_for("login"))

    pic_folder = os.path.join(app.root_path, 'static', 'PROFILE_PIC')
    if not os.path.exists(pic_folder):
        os.makedirs(pic_folder)

    images = [f for f in os.listdir(pic_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT created_at, profile_pic
        FROM user_info
        WHERE username = %s
    """, (session["username"],))

    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:  # fallback in case the user is missing
        join_date = "Unknown"
        profile_pic = None
    else:
        join_date = user.get("created_at", "Unknown")
        profile_pic = user.get("profile_pic")

    return render_template(
        "profile.html",
        username=session["username"],
        join_date=join_date,
        profile_pic=profile_pic,
        images=images
    )

@app.route('/set_profile_picture', methods=['POST'])
def set_profile_picture():
    if "username" not in session:
        return jsonify({'success': False})

    data = request.get_json()
    new_pic = data.get('new_picture')

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE user_info
        SET profile_pic = %s
        WHERE username = %s
    """, (new_pic, session["username"]))

    conn.commit()
    cur.close()
    conn.close()

    session['profile_pic'] = new_pic

    return jsonify({'success': True, 'new_picture': new_pic})


@app.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    if "username" not in session:
        return jsonify({'success': False})

    if 'profile_picture' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})

    file = request.files['profile_picture']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})

    if file and allowed_file(file.filename):
        import uuid
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"

        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            UPDATE user_info
            SET profile_pic = %s
            WHERE username = %s
        """, (filename, session["username"]))

        conn.commit()
        cur.close()
        conn.close()

        session['profile_pic'] = filename

        return jsonify({'success': True, 'filename': filename})

    return jsonify({'success': False, 'error': 'Invalid file type'})

# -------------------------------------------------
# ADD TO LIST
# -------------------------------------------------
@app.route("/add_to_list", methods=["POST"])
def add_to_list():
    if "username" not in session:
        return redirect(url_for("login"))

    series_id = request.form["series_id"]
    rating = request.form.get("rating") or None
    status = request.form.get("status") or "plan_to_watch"
    next_page = request.form.get("next")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO user_series (user_id, series_id, rating, status)
        VALUES (
            (SELECT id FROM user_info WHERE username=%s),
            %s,
            %s,
            %s
        )
        ON CONFLICT (user_id, series_id)
        DO UPDATE SET
            rating = EXCLUDED.rating,
            status = EXCLUDED.status
    """, (session["username"], series_id, rating, status))

    conn.commit()
    cur.close()
    conn.close()

    flash("Saved to your list!", "success")
    print("SERIES ID:", series_id)
    print("RATING:", rating)
    print("STATUS:", status)
    print("USERNAME:", session["username"])

    return redirect(url_for("series_info", series_id=series_id))
# -------------------------------------------------
# MY SERIES
# -------------------------------------------------
@app.route("/my_series")
def my_series():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT s.id, s.name, s.episodes, s.genre, s.aired,
               s.endedairing, s.source, s.duration,
               s.rating, s.image,
               us.rating AS user_score,
               us.status
        FROM user_series us
        JOIN series s ON s.id = us.series_id
        WHERE us.user_id = (
            SELECT id FROM user_info WHERE username=%s
        )
    """, (session["username"],))

    user_series = cur.fetchall()

    cur.close()
    conn.close()

    for s in user_series:
        if s["user_score"] is not None:
            s["user_score"] = int(s["user_score"])

    return render_template("my_series.html", user_series=user_series)



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
