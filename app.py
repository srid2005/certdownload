from flask import Flask, render_template, request, send_file, flash, redirect, url_for,session
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os

import datetime
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


app = Flask(__name__)
app.secret_key = "luxury_hackathon_secret_2026" 
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "secretpassword123"



# Get the absolute path of the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Config using absolute paths
PARTICIPANTS_FILE = os.path.join(BASE_DIR, "participants.csv")
WINNERS_FILE = os.path.join(BASE_DIR, "winners.csv") 
TPL_WINNER = os.path.join(BASE_DIR, "winners_template.png")
TPL_PARTICIPANT = os.path.join(BASE_DIR, "participant_template.png")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "static/generated")
FONT_PATH = os.path.join(BASE_DIR, "SpaceMono-Bold.ttf")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def generate_certificate(name, template_path, output_dir):
    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype(FONT_PATH , 50)
    draw.text((900, 700), name, fill="black", font=font, anchor="lt")

    file_path = os.path.join(output_dir, f"{name.replace(' ', '_')}.pdf")
    img.save(file_path, "PDF")
    return file_path



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash("Invalid credentials", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route("/admin", methods=["GET", "POST"])
def admin():
    # 1. Protection Check
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # 2. CREATE Logic (Handling both possible form field names)
    if request.method == "POST":
        new_id = request.form.get("team_id", "").strip()
        if new_id:
            df_w = pd.read_csv(WINNERS_FILE)
            if new_id not in df_w["team_id"].astype(str).values:
                new_row = pd.DataFrame([{"team_id": new_id}])
                df_w = pd.concat([df_w, new_row], ignore_index=True)
                df_w.to_csv(WINNERS_FILE, index=False)
                flash(f"Team {new_id} added to winners!", "success")
            else:
                flash(f"Team {new_id} already exists.", "warning")
            return redirect(url_for('admin'))

    # 3. DELETE Logic
    if request.args.get("delete"):
        target_id = request.args.get("delete")
        df_w = pd.read_csv(WINNERS_FILE)
        df_w = df_w[df_w["team_id"].astype(str) != str(target_id)]
        df_w.to_csv(WINNERS_FILE, index=False)
        flash(f"Team {target_id} removed.", "success")
        return redirect(url_for('admin'))

    # 4. READ Logic
    try:
        winners_list = pd.read_csv(WINNERS_FILE).to_dict(orient="records")
    except FileNotFoundError:
        winners_list = []
    
    return render_template("admin.html", winners=winners_list)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Match these names with your HTML <input name="...">
        user_input_name = request.form.get("participant_name", "").strip()
        team_id = request.form.get("team_id", "").strip()

        if not user_input_name or not team_id:
            return render_template("index.html", error="Please fill in all fields.")

        try:
            df = pd.read_csv(PARTICIPANTS_FILE)
            winners_df = pd.read_csv(WINNERS_FILE)
        except FileNotFoundError:
            return render_template("index.html", error="Database files missing. Contact Admin.")

        # Match Name AND Team ID (Case insensitive for name)
        match = df[(df["member_name"].str.lower() == user_input_name.lower()) & 
                   (df["team_id"].astype(str) == team_id)]

        if match.empty:
            return render_template("index.html", error="Record not found. Ensure Name and Team ID are correct.")



        # Get the official name from CSV (for correct capitalization)
        official_name = match.iloc[0]["member_name"].title()

        # Check for Winner Status
        is_winner = team_id in winners_df["team_id"].astype(str).values
        template = TPL_WINNER if is_winner else TPL_PARTICIPANT

        # Generate and send
        try:
            log_entry = f"{timestamp},{team_id},{official_name},Downloaded\n"
            pdf_path = generate_certificate(official_name, template, OUTPUT_FOLDER)
            with open(os.path.join(BASE_DIR, "downloads.log"), "a") as log_file:
                log_file.write(log_entry)
            return send_file(pdf_path, as_attachment=True)
        except Exception as e:
            return render_template("index.html", error=f"Generation Error: {str(e)}")

    return render_template("index.html")




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 