import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import json
import time
import os

OWNER_ID = 5918992671  # آيدي مالك البوت
DATA_FILE = "users.json"

# تحميل بيانات المستخدمين
def load_users():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

# حفظ بيانات المستخدمين
def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

users_data = load_users()

# إرسال البريد
def send_email(sender_email, sender_password, recipient_emails, subject, message):
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = ", ".join(recipient_emails)
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_emails, msg.as_string())

        return True, f"✅ تم إرسال من {sender_email}"
    except Exception as e:
        if "550" in str(e):
            return False, f"❌ الايميل هذا محظور {sender_email}"
        return False, f"❌ فشل الإرسال من {sender_email}: {e}"

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid not in users_data:
        keyboard = [[InlineKeyboardButton("راسل أواب لتفعيل حسابك", url="https://t.me/ppuxq")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("تواصل مع مالك البوت اواب اެلـ تَِـوَِجَِـو @ppuxq", reply_markup=reply_markup)
        return

    await update.message.reply_text("🎉 مرحبًا بك، أرسل الأمر /send للبدء في إرسال البريد.")

# أمر /add فقط للمالك
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("اكتب الأمر هكذا: /add <user_id>")
        return
    uid = context.args[0]
    users_data[uid] = {"emails": [], "subject": "", "message": "", "recipients": []}
    save_users(users_data)
    await update.message.reply_text(f"✅ تم تفعيل {uid}")

# أمر /del فقط للمالك
async def del_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("اكتب الأمر هكذا: /del <user_id>")
        return
    uid = context.args[0]
    if uid in users_data:
        users_data.pop(uid)
        save_users(users_data)
        await update.message.reply_text(f"❌ تم إلغاء تفعيل {uid}")
    else:
        await update.message.reply_text("المستخدم غير موجود.")

# أمر /config لإضافة الإعدادات للمستخدم
async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid not in users_data:
        return await update.message.reply_text("❌ غير مفعل.")
    
    await update.message.reply_text("أرسل الكليشة:")
    msg = await context.bot.wait_for_message(chat_id=uid)
    users_data[uid]["message"] = msg.text

    await update.message.reply_text("أرسل الموضوع:")
    msg = await context.bot.wait_for_message(chat_id=uid)
    users_data[uid]["subject"] = msg.text

    await update.message.reply_text("أرسل المستلمين مفصولين بفاصلة:")
    msg = await context.bot.wait_for_message(chat_id=uid)
    users_data[uid]["recipients"] = msg.text.split(",")

    await update.message.reply_text("أرسل الإيميلات بصيغة: email:pass في كل سطر:")
    msg = await context.bot.wait_for_message(chat_id=uid)
    lines = msg.text.splitlines()
    users_data[uid]["emails"] = [{"email": l.split(":")[0], "password": l.split(":")[1]} for l in lines if ":" in l]
    save_users(users_data)

    await update.message.reply_text("✅ تم الحفظ.")

# أمر /send للإرسال
async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid not in users_data:
        return await update.message.reply_text("❌ غير مفعل.")

    args = context.args
    if not args or not args[0].isdigit():
        return await update.message.reply_text("❗ أرسل عدد الرسائل هكذا: /send 1000")

    total = int(args[0])
    user_data = users_data[uid]
    sent = 0

    await update.message.reply_text("⏳ جاري الإرسال...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in range(total):
            account = user_data["emails"][i % len(user_data["emails"])]
            recipient_chunk = [user_data["recipients"][i % len(user_data["recipients"])]]
            success, msg = send_email(account["email"], account["password"], recipient_chunk, user_data["subject"], user_data["message"])
            sent += 1
            print(msg)
            if i % 50 == 0:
                await update.message.reply_text(f"📤 تم إرسال {sent}/{total}")
            time.sleep(1)

    await update.message.reply_text("✅ تم إرسال جميع الرسائل.")

# تشغيل البوت
app = ApplicationBuilder().token("‏7753420109:AAHQduj6xC8gEs6oblg6dAqZciPFjtV1fmU").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add_user))
app.add_handler(CommandHandler("del", del_user))
app.add_handler(CommandHandler("config", config))
app.add_handler(CommandHandler("send", send))

app.run_polling()