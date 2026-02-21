from fileinput import filename
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import os
import psycopg2


app = Flask(__name__)
app.secret_key = "some-long-random-string"

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'profile_pic')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATABASE_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)

# -------------------------------------------------
# HOME
# -------------------------------------------------
@app.route("/")
def home():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Hot series (unchanged)
    cursor.execute("""
        SELECT id, Name, Episodes, Genre, Duration, image
        FROM series
        ORDER BY RAND()
        LIMIT 6
    """)
    hot_series = cursor.fetchall()

    # Newest series
    cursor.execute("""
        SELECT id, Name, image
        FROM series
        ORDER BY Aired DESC
        LIMIT 20
    """)
    newest_series = cursor.fetchall()

    # Romance
    cursor.execute("""
        SELECT id, Name, image
        FROM series
        WHERE Genre LIKE '%Romance%'
        ORDER BY RAND()
        LIMIT 20
    """)
    romance_series = cursor.fetchall()

    # Action
    cursor.execute("""
        SELECT id, Name, image
        FROM series
        WHERE Genre LIKE '%Action%'
        ORDER BY RAND()
        LIMIT 20
    """)
    action_series = cursor.fetchall()

    # Drama
    cursor.execute("""
        SELECT id, Name, image
        FROM series
        WHERE Genre LIKE '%Drama%'
        ORDER BY RAND()
        LIMIT 20
    """)
    drama_series = cursor.fetchall()

    cursor.close()

    return render_template(
        "HomePage.html",
        hot_series=hot_series,
        newest_series=newest_series,
        romance_series=romance_series,
        action_series=action_series,
        drama_series=drama_series
    )



# -------------------------------------------------
# ALL SERIES
# -------------------------------------------------
@app.route("/series")
def series():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT id, Name, Episodes, Genre, Aired, EndedAiring,
               Source, Duration, Rating, image
        FROM series
        ORDER BY Name
    """)
    all_series = cursor.fetchall()
    cursor.close()

    return render_template("series.html", series=all_series)


# -------------------------------------------------
# ABOUT
# -------------------------------------------------
@app.route("/about_us")
def about_us():
    return render_template("About_US.html")


# -------------------------------------------------
# SERIES INFO PAGE BY ID
# -------------------------------------------------
# -------------------------------------------------
# SERIES INFO PAGE BY ID (with user rating)
# -------------------------------------------------
@app.route("/series/<int:series_id>")
def series_info(series_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch series info
    cursor.execute("SELECT * FROM series WHERE id=%s", (series_id,))
    series = cursor.fetchone()
    if not series:
        cursor.close()
        return "Series not found", 404

    # Add summary
    safe_name = series['Name'].replace(" ", "").lower()
    summary_file = os.path.join(app.root_path, 'static', 'SUMMARIES', f"{safe_name}.txt")
    series['Summary'] = "Summary not available."
    if os.path.exists(summary_file):
        with open(summary_file, 'r', encoding='utf-8') as f:
            series['Summary'] = f.read()

    user_data = None
    if session.get('username'):
        # Fetch user's rating for this series if it exists
        cursor.execute("""
            SELECT rating 
            FROM user_series
            WHERE series_id = %s
            AND user_id = (SELECT id FROM user_info WHERE username=%s)
        """, (series_id, session['username']))
        user_data = cursor.fetchone()  # Will be None if no rating exists

    cursor.close()

    return render_template("info.html", series=series, user_data=user_data)




# -------------------------------------------------
# SERIES INFO PAGE BY NAME (WITH SUMMARY)
# -------------------------------------------------
@app.route('/series_info/<series_name>')
def series_info_by_name(series_name):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM series WHERE Name LIKE %s", (series_name,))
    series = cursor.fetchone()
    cursor.close()

    if not series:
        return "Series not found.", 404

    # Normalize file name: remove spaces and make lowercase
    safe_name = series['Name'].replace(" ", "").lower()
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

        cur = mysql.connection.cursor()

        # Check if user exists
        cur.execute("SELECT id FROM user_info WHERE username=%s", (username,))
        if cur.fetchone():
            flash("Username already exists", "error")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        cur.execute("""
            INSERT INTO user_info (username, password, created_at)
            VALUES (%s, %s, %s)
        """, (username, hashed_password, date.today()))

        mysql.connection.commit()
        cur.close()

        flash("Account created successfully!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("""
            SELECT password, color_theme, profile_pic
            FROM user_info 
            WHERE username = %s
        """, (username,))
        user = cur.fetchone()
        cur.close()

        if not user or not check_password_hash(user["password"], password):
            flash("Invalid username or password", "error")
            return redirect(url_for("login"))

        session["username"] = username
        session["theme"] = user["color_theme"] or "light"
        session["profile_pic"] = user["profile_pic"]  # ← ADD THIS

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

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE user_info 
        SET color_theme = %s
        WHERE username = %s
    """, (new_theme, session["username"]))

    mysql.connection.commit()
    cur.close()

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

    # 1. Get all files from the profile_pic folder
    # Assuming your path is static/profile_pic
    pic_folder = os.path.join(app.root_path, 'static', 'profile_pic')
    
    # Create folder if it doesn't exist so it doesn't crash
    if not os.path.exists(pic_folder):
        os.makedirs(pic_folder)
        
    images = [f for f in os.listdir(pic_folder) if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))]

    # 2. Get the current join date (using your existing logic)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
    SELECT created_at, profile_pic
    FROM user_info
    WHERE username = %s
    """, (session["username"],))

    user = cursor.fetchone()
    cursor.close()

    return render_template(
    "profile.html",
    username=session["username"],
    join_date=user["created_at"],
    profile_pic=user["profile_pic"],  # ✅ PASS THIS
    images=images
)

@app.route('/set_profile_picture', methods=['POST'])
def set_profile_picture():
    if "username" not in session:
        return jsonify({'success': False})

    data = request.get_json()
    new_pic = data.get('new_picture')

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE user_info
        SET profile_pic = %s
        WHERE username = %s
    """, (new_pic, session["username"]))

    mysql.connection.commit()
    cur.close()

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

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE user_info
            SET profile_pic = %s
            WHERE username = %s
        """, (filename, session["username"]))

        mysql.connection.commit()
        cur.close()

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
    next_page = request.form.get("next")

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO user_series (user_id, series_id, rating)
        VALUES (
            (SELECT id FROM user_info WHERE username=%s),
            %s,
            %s
        )
        ON DUPLICATE KEY UPDATE rating=%s
    """, (session["username"], series_id, rating, rating))

    mysql.connection.commit()
    cur.close()

    flash("Saved to your list!", "success")

    return redirect(next_page or url_for("series_info", series_id=series_id))




# -------------------------------------------------
# MY SERIES
# -------------------------------------------------
@app.route("/my_series")
def my_series():
    if "username" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT s.id, s.Name, s.Episodes, s.Genre, s.Aired,
               s.EndedAiring, s.Source, s.Duration,
               s.Rating, s.image,
               us.rating AS user_score
        FROM user_series us
        JOIN series s ON s.id = us.series_id
        WHERE us.user_id = (
            SELECT id FROM user_info WHERE username=%s
        )
    """, (session["username"],))
    user_series = cursor.fetchall()
    cursor.close()

    # Convert ratings to integers
    for s in user_series:
        if s["user_score"] is not None:
            s["user_score"] = int(s["user_score"])

    return render_template("my_series.html", user_series=user_series)



if __name__ == "__main__":
    app.run()
