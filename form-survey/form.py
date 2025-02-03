from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import requests
import os
import uuid

# ایجاد اپلیکیشن Flask
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# تنظیمات API و چت
TOKEN = 'bot333725:b380f262-c3d2-4433-a16b-28dbc83c10ad'
CHAT_ID = '@post_sender'
TELEGRAM_BOT_TOKEN = '8000764348:AAEytputhjTO8Sp7QA939fUCm8ja6YQI23I'
TELEGRAM_ADMIN_CHAT_ID = '167514573'
API_URL = "https://eitaayar.ir/api"

# تابع ارسال پیام به API
def send_message_to_eita(chat_id, message_text):
    try:
        url = f"{API_URL}/{TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message_text}
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"Failed to send message: {response.text}")
        else:
            print("Message sent successfully.")
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")

# تابع ارسال پیام به ربات تلگرام
def send_telegram_message(chat_id, message_text, keyboard=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message_text}
    if keyboard:
        payload["reply_markup"] = json.dumps({"inline_keyboard": keyboard})
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print(f"Telegram message failed: {response.text}")
    else:
        print("Telegram message sent successfully.")

# تابع بارگذاری فایل JSON
def load_json_file(filepath, default_value):
    if not os.path.exists(filepath):
        with open(filepath, 'w') as file:
            json.dump(default_value, file)
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
            if isinstance(default_value, dict) and not isinstance(data, dict):
                return {}
            elif isinstance(default_value, list) and not isinstance(data, list):
                return []
            return data
    except json.JSONDecodeError:
        return default_value

# صفحه اصلی
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash("لطفاً نام خود را وارد کنید.", "danger")
            return redirect(url_for('index'))
        session['name'] = name
        session['user_id'] = str(uuid.uuid4())
        session['ip'] = request.remote_addr
        return redirect(url_for('select_survey'))
    return render_template('index.html')

# صفحه بعدی فرم و اختیاری بودن وارد کردن نام و نام خانوادگی
@app.route('/select_survey', methods=['POST'])
def next_page():
    return render_template('select_survey.html')  

# صفحه مدیریت
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # اعتبارسنجی ورود مدیر
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'mrhjf' and password == 'smb110':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash("نام کاربری یا رمز عبور اشتباه است.", "danger")
    return render_template('admin_panel.html')

# داشبورد مدیریت
@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))

    # بارگزاری داده‌ها
    completed_surveys = load_json_file('data/completed_surveys.json', {})
    exam_responses = load_json_file('data/exam_responses.json', [])
    haram_responses = load_json_file('data/haram_responses.json', [])
    access_requests = load_json_file('data/access_requests.json', [])

    if request.method == 'POST':
        action = request.form.get('action')
        ip = request.form.get('ip')

        if action == 'approve':
            for survey in ['exam', 'haram']:
                if ip in completed_surveys.get(survey, []):
                    completed_surveys[survey].remove(ip)
            with open('data/completed_surveys.json', 'w') as file:
                json.dump(completed_surveys, file)
            flash(f"درخواست دسترسی کاربر با IP: {ip} قبول شد.", "success")

        elif action == 'reject':
            flash(f"درخواست دسترسی کاربر با IP: {ip} رد شد.", "warning")

        return redirect(url_for('admin_dashboard'))

    return render_template(
        'admin_dashboard.html',
        exam_responses=exam_responses,
        haram_responses=haram_responses,
        access_requests=access_requests
    )

# انتخاب نظرسنجی
@app.route('/select_survey')
def select_survey():
    ip = session.get('ip', '')
    completed_surveys = load_json_file('data/completed_surveys.json', {})
    if ip in completed_surveys.get("exam", []) and ip in completed_surveys.get("haram", []):
        flash("شما قبلاً در همه نظرسنجی‌ها شرکت کرده‌اید.", "info")
        return redirect(url_for('index'))
    available_surveys = []
    if ip not in completed_surveys.get("exam", []):
        available_surveys.append("exam")
    if ip not in completed_surveys.get("haram", []):
        available_surveys.append("haram")
    return render_template('select_survey.html', available_surveys=available_surveys)

# نظرسنجی امتحانات
@app.route('/exam_survey', methods=['GET', 'POST'])
def exam_survey():
    ip = session.get('ip', '')
    completed_surveys = load_json_file('data/completed_surveys.json', {})
    if not isinstance(completed_surveys.get("exam"), list):
        completed_surveys["exam"] = []
    if ip in completed_surveys.get("exam", []):
        flash("شما قبلاً به سوالات امتحانی پاسخ داده‌اید.", "warning")
        return redirect(url_for('select_survey'))
    if request.method == 'POST':
        name = session.get('name', 'نام وارد نشده')
        user_id = session.get('user_id', 'بدون شناسه')
        questions = {
            'q1': "فاصله بین امتحانات:",
            'q2': "امتحانات جنبی، قبل از شروع ترم برگزار شود؟",
            'q3': "پاسخ گویی ناظرین به سوالات در جلسه:",
            'q4': "سوالات امتحانی در چه سطحی بود؟ بهمراه عنوان درس:",
            'q5': "مطالعه مدرسه در زمان امتحانات الزامی باشد:",
            'q6': "میزان عملکرد شما در امتحان ترم:",
            'q7': "علت ضعیف عمل کردن شما در امتحان ترم:",
            'q8': "راهکار شما در ارتقای معدل:"
        }
        responses = {}
        for q in questions:
            responses[q] = request.form.get(q)
            responses[f"{q}_desc"] = request.form.get(f"{q}_desc")  # تشریحی
        all_responses = load_json_file('data/exam_responses.json', [])
        all_responses.append({"user_id": user_id, "name": name, "ip": ip, "responses": responses})
        with open('data/exam_responses.json', 'w') as file:
            json.dump(all_responses, file)
        completed_surveys.setdefault("exam", []).append(ip)
        with open('data/completed_surveys.json', 'w') as file:
            json.dump(completed_surveys, file)
        summary_text = "📊 **خلاصه نتایج نظرسنجی امتحانات**:\n\n"
        detailed_text = "📝 **پاسخ‌های تشریحی نظرسنجی امتحانات**:\n\n"
        for q, question_text in questions.items():
            if q.startswith('q') and q not in ['q7', 'q8']:
                options = ["ضعیف", "متوسط", "خوب"]
                total = len([r for r in all_responses if r['responses'].get(q)])
                counts = {option: sum(1 for r in all_responses if r['responses'].get(q) == option) for option in options}
                percentages = {option: f"{count / total * 100:.1f}%" if total > 0 else "0%" for option, count in counts.items()}
                summary_text += f"📌 {question_text}\n"
                for option, percent in percentages.items():
                    summary_text += f"  - {option}: {percent}\n"
            if q in ['q1', 'q2', 'q3', 'q4', 'q5', 'q6']:
                desc = responses.get(f"{q}_desc")
                if desc:
                    detailed_text += f"👤 {name} | 🌐 {ip}\n"
                    detailed_text += f"  - {questions[q]} (توضیحات): {desc}\n"
        send_message_to_eita(CHAT_ID, summary_text)
        send_telegram_message(TELEGRAM_ADMIN_CHAT_ID, summary_text)
        if detailed_text != "📝 **پاسخ‌های تشریحی نظرسنجی امتحانات**:\n\n":
            send_message_to_eita(CHAT_ID, detailed_text)
            send_telegram_message(TELEGRAM_ADMIN_CHAT_ID, detailed_text)
        flash('نظر شما ثبت شد!', 'success')
        return redirect(url_for('select_survey'))
    return render_template('exam_survey.html')

# نظرسنجی حرم
@app.route('/haram_survey', methods=['GET', 'POST'])
def haram_survey():
    ip = session.get('ip', '')
    completed_surveys = load_json_file('data/completed_surveys.json', {})
    if not isinstance(completed_surveys.get("haram"), list):
        completed_surveys["haram"] = []
    if ip in completed_surveys.get("haram", []):
        flash("شما قبلاً به سوالات حرم پاسخ داده‌اید.", "warning")
        return redirect(url_for('select_survey'))
    if request.method == 'POST':
        name = session.get('name', 'نام وارد نشده')
        user_id = session.get('user_id', 'بدون شناسه')
        questions = {
            'hq1': "ارزیابی شما از کلیت برنامه حرم:",
            'hq2': "برنامه سخنرانی:",
            'hq3': "برنامه مناجات خوانی:",
            'hq4': "برنامه حلقه معرفت:",
            'hq5': "برنامه حرم شناسی:",
            'hq6': "پذیرایی:",
            'hq7': "درصورت توفیق مجدد، چند درصد علاقه به شرکت دارید؟",
            'hq8': "نظر شما در مورد بهتر اجرا شدن این برنامه:"
        }
        responses = {}
        for q in questions:
            responses[q] = request.form.get(q)  # جواب گزینه‌ای
            responses[f"{q}_desc"] = request.form.get(f"{q}_desc")  # جواب تشریحی
        all_responses = load_json_file('data/haram_responses.json', [])
        all_responses.append({"user_id": user_id, "name": name, "ip": ip, "responses": responses})
        with open('data/haram_responses.json', 'w') as file:
            json.dump(all_responses, file)
        completed_surveys.setdefault("haram", []).append(ip)
        with open('data/completed_surveys.json', 'w') as file:
            json.dump(completed_surveys, file)
        def calculate_percentage(question_key, options):
            total = len([r for r in all_responses if r['responses'].get(question_key)])
            counts = {option: sum(1 for r in all_responses if r['responses'].get(question_key) == option) for option in options}
            percentages = {option: f"{count / total * 100:.1f}%" if total > 0 else "0%" for option, count in counts.items()}
            return percentages
        summary_text = "📊 **خلاصه نتایج نظرسنجی حرم**:\n\n"
        detailed_text = "📝 **پاسخ‌های تشریحی نظرسنجی حرم**:\n\n"
        for q, question_text in questions.items():
            if q.startswith('hq') and q not in ['hq7', 'hq8']:
                options = ["ضعیف", "متوسط", "خوب"]
                percentages = calculate_percentage(q, options)
                summary_text += f"📌 {question_text}\n"
                for option, percent in percentages.items():
                    summary_text += f"  - {option}: {percent}\n"
            if q in ['hq1', 'hq2', 'hq3', 'hq4', 'hq5', 'hq6']:
                desc = responses.get(f"{q}_desc")
                if desc:
                    detailed_text += f"👤 {name} | 🌐 {ip}\n"
                    detailed_text += f"  - {questions[q]} (توضیحات): {desc}\n"
        send_message_to_eita(CHAT_ID, summary_text)
        send_telegram_message(TELEGRAM_ADMIN_CHAT_ID, summary_text)
        if detailed_text != "📝 **پاسخ‌های تشریحی نظرسنجی حرم**:\n\n":
            send_message_to_eita(CHAT_ID, detailed_text)
            send_telegram_message(TELEGRAM_ADMIN_CHAT_ID, detailed_text)
        flash('نظر شما ثبت شد!', 'success')
        return redirect(url_for('select_survey'))
    return render_template('haram_survey.html')

# درخواست دسترسی مجدد
@app.route('/request_access', methods=['GET', 'POST'])
def request_access():
    if request.method == 'POST':
        name = request.form.get('name', 'نامشخص')
        reason = request.form.get('reason', 'بدون توضیحات')
        ip = session.get('ip', '')
        message = f"کاربر {name} با IP: {ip} درخواست دسترسی دوباره کرده است.\nدلیل: {reason}"
        send_message_to_eita(CHAT_ID, message)
        keyboard = [[{"text": "قبول", "callback_data": f"approve:{ip}"}, {"text": "رد", "callback_data": f"reject:{ip}"}]]
        send_telegram_message(TELEGRAM_ADMIN_CHAT_ID, message, keyboard=keyboard)
        access_requests = load_json_file('data/access_requests.json', [])
        access_requests.append({"name": name, "ip": ip, "reason": reason})
        with open('data/access_requests.json', 'w') as file:
            json.dump(access_requests, file)
        flash("درخواست شما ارسال شد و به زودی بررسی خواهد شد.", "info")
        return redirect(url_for('index'))
    return render_template('request_access.html')

# Endpoint برای مدیریت درخواست‌ها در ربات تلگرام
@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    data = request.json
    if 'callback_query' in data:
        query = data['callback_query']
        chat_id = query['message']['chat']['id']
        callback_data = query['data']
        if callback_data.startswith('approve:'):
            ip = callback_data.split(':')[1]
            completed_surveys = load_json_file('data/completed_surveys.json', {})
            for survey in ['exam', 'haram']:
                if ip in completed_surveys.get(survey, []):
                    completed_surveys[survey].remove(ip)
            with open('data/completed_surveys.json', 'w') as file:
                json.dump(completed_surveys, file)
            send_telegram_message(chat_id, f"درخواست دسترسی کاربر با IP: {ip} قبول شد.")
        elif callback_data.startswith('reject:'):
            ip = callback_data.split(':')[1]
            send_telegram_message(chat_id, f"درخواست دسترسی کاربر با IP: {ip} رد شد.")
    return '', 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=9000)
