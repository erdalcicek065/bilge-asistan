import os
import sqlite3
import json
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import google.generativeai as genai

# 1. ORTAM DEĞİŞKENLERİ
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', 'gizli_anahtar_123')
CORS(app)

# 2. API ANAHTARI KONTROLÜ
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    print("❌ HATA: .env dosyasında GEMINI_API_KEY bulunamadı!")
else:
    try:
        genai.configure(api_key=API_KEY.strip())
        print(f"✅ API Anahtarı Algılandı.")
    except Exception as e:
        print(f"❌ API Ayar Hatası: {e}")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'ozel_egitim_v2.db')

if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, school_name TEXT, role TEXT DEFAULT 'teacher', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, tc_no TEXT, name TEXT, dob DATE, gender TEXT, diagnosis TEXT, report_end_date DATE, parent_name TEXT, parent_phone TEXT, level TEXT, medication_info TEXT, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS assessments (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, lesson TEXT, performance TEXT, needs TEXT, expectation TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(student_id) REFERENCES students(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS bep_reports (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, report_content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(student_id) REFERENCES students(id))''')
    conn.commit(); conn.close()
init_db()

class User(UserMixin):
    def __init__(self, id, email, school_name): self.id, self.email, self.school_name = id, email, school_name

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,)); u = c.fetchone()
    conn.close()
    return User(u[0], u[1], u[3]) if u else None

# ROTALAR
@app.route('/')
def index(): return render_template('index.html')

@app.route('/get_curriculum')
def get_curriculum():
    try: return jsonify(json.load(open(os.path.join(DATA_DIR, 'mufredat.json'), 'r', encoding='utf-8')))
    except: return jsonify({"Hata": ["Müfredat verisi yok."]})

@app.route('/register', methods=['POST'])
def register():
    d = request.json
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT INTO users (email, password, school_name) VALUES (?, ?, ?)", (d['email'], generate_password_hash(d['password']), d['school']))
        conn.commit(); conn.close()
        return jsonify({"status": "success"})
    except: return jsonify({"error": "Mail zaten kayitli"}), 400

@app.route('/login', methods=['POST'])
def login():
    d = request.json
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (d['email'],)); u = c.fetchone()
    conn.close()
    if u and check_password_hash(u[2], d['password']): 
        login_user(User(u[0], u[1], u[3])); return jsonify({"status": "success"})
    return jsonify({"error": "Hatali giris"}), 401

@app.route('/logout')
@login_required
def logout(): logout_user(); return jsonify({"status": "success"})

@app.route('/check_login')
def check_login(): return jsonify({"logged_in": current_user.is_authenticated})

@app.route('/add_student', methods=['POST'])
@login_required
def add_student():
    d = request.json
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    try:
        c.execute("""INSERT INTO students (user_id, tc_no, name, dob, gender, diagnosis, report_end_date, parent_name, parent_phone, level, medication_info, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                  (current_user.id, d.get('tc_no'), d['name'], d.get('dob'), d.get('gender'), d.get('diagnosis'), d.get('report_end_date'), d.get('parent_name'), d.get('parent_phone'), d.get('level'), d.get('medication_info'), d.get('notes')))
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)}), 500
    finally: conn.close()

@app.route('/get_students', methods=['GET'])
@login_required
def get_students():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; c = conn.cursor()
    c.execute("SELECT * FROM students WHERE user_id = ? ORDER BY id DESC", (current_user.id,))
    rows = [dict(r) for r in c.fetchall()]; conn.close()
    return jsonify(rows)

@app.route('/save_assessment', methods=['POST'])
@login_required
def save_assessment():
    d = request.json
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("DELETE FROM assessments WHERE student_id = ? AND lesson = ?", (d['student_id'], d['lesson']))
    c.execute("INSERT INTO assessments (student_id, lesson, performance, needs, expectation) VALUES (?, ?, ?, ?, ?)", (d['student_id'], d['lesson'], d['performance'], d['needs'], d['expectation']))
    conn.commit(); conn.close()
    return jsonify({"status": "success"})

@app.route('/generate_full_bep', methods=['POST'])
@login_required
def generate_full_bep():
    d = request.json
    student_id = d['student_id']
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; c = conn.cursor()
    c.execute("SELECT * FROM students WHERE id = ?", (student_id,)); s = dict(c.fetchone())
    c.execute("SELECT * FROM assessments WHERE student_id = ?", (student_id,)); asses = [dict(r) for r in c.fetchall()]
    
    if not asses:
        conn.close(); return jsonify({"error": "Önce Kaba Değerlendirme Formlarını doldurun!"})

    knowledge = ""
    try: knowledge = open(os.path.join(DATA_DIR, 'uzman_bilgi.txt'), 'r', encoding='utf-8').read()
    except: pass

    # HATA VEREN KISIM BURASIYDI, DÜZELTİLDİ:
    prompt = f"GÖREV: MEB Formatında BEP Hazırla.\n"
    prompt += f"ÖĞRENCİ: {s['name']}, {s['diagnosis']}, {s['level']}\n"
    prompt += "VERİLER:\n"
    
    for a in asses: 
        prompt += f"- {a['lesson']}: {a['performance']} -> Hedef: {a['expectation']}\n"
    
    prompt += "\nYÖNERGE: Sadece HTML Tablosu ver.\n"
    prompt += "SÜTUNLAR: 1.Ders 2.Performans 3.Uzun Dönemli Amaç 4.Kısa Dönemli Amaçlar 5.Yöntem 6.Materyal 7.Değerlendirme 8.Tarih\n"
    prompt += f"KAYNAK: {knowledge[:3000]}"
    
    ai_res = ask_ai_internal(prompt)
    if "error" in ai_res: conn.close(); return jsonify(ai_res)
    
    c.execute("INSERT INTO bep_reports (student_id, report_content) VALUES (?, ?)", (student_id, ai_res["ai_response"]))
    conn.commit(); conn.close()
    return jsonify(ai_res)

@app.route('/get_bep_list', methods=['POST'])
@login_required
def get_bep_list():
    d = request.json
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; c = conn.cursor()
    c.execute("SELECT id, created_at FROM bep_reports WHERE student_id = ? ORDER BY created_at DESC", (d['student_id'],))
    rows = [dict(r) for r in c.fetchall()]; conn.close()
    return jsonify(rows)

@app.route('/get_bep_content', methods=['POST'])
@login_required
def get_bep_content():
    d = request.json
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; c = conn.cursor()
    c.execute("SELECT report_content FROM bep_reports WHERE id = ?", (d['report_id'],))
    row = c.fetchone(); conn.close()
    return jsonify({"content": row['report_content']}) if row else jsonify({"error":"Yok"})

@app.route('/ask_bilge_chat', methods=['POST'])
@login_required
def ask_bilge_chat():
    d = request.json
    msg = d.get('message', '')
    prompt = f"SENİN ROLÜN: Bilge Asistan. Özel eğitim öğretmenlerinin dostusun. SORU: {msg}. Kısa, samimi ve çözüm odaklı cevap ver."
    return jsonify(ask_ai_internal(prompt))

# --- AKILLI MODEL SEÇİCİ ---
def ask_ai_internal(prompt):
    try:
        # 1. Modelleri Bul
        available_models = []
        print("\n🔍 Uygun Modeller Aranıyor...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        print(f"📋 Bulunan Modeller: {available_models}")

        if not available_models:
            return {"error": "API Anahtarınız hiçbir modele erişemiyor."}

        # 2. Seçim Yap
        selected_model_name = available_models[0]
        for m_name in available_models:
            if 'flash' in m_name:
                selected_model_name = m_name
                break
            elif 'pro' in m_name and 'vision' not in m_name:
                selected_model_name = m_name

        print(f"🚀 Seçilen Model: {selected_model_name}")

        # 3. İsteği Gönder
        model = genai.GenerativeModel(selected_model_name)
        response = model.generate_content(prompt)
        
        return {"status": "success", "ai_response": response.text.replace("```html","").replace("```","").strip()}

    except Exception as e:
        print(f"❌ Kritik Hata: {e}")
        return {"error": f"Yapay zeka hatası: {str(e)}"}

if __name__ == '__main__':
    app.run(debug=True)