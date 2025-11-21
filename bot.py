import json
import requests
from datetime import datetime
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# === المتغيرات الأساسية ===
TOKEN = "8512434703:AAG5y80qQVuez_mNUncmRmh-ovJW3Z27XGk"
GITHUB_TOKEN = "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"
REPO_OWNER = "aaro3498-boop"
REPO_NAME = "mko"
FILE_PATH = "accounts.json"
BRANCH = "main"

# === خطوات المحادثة ===
PHOTO, PRICE, DESCRIPTION = range(3)
user_data_store = {}

# --- أدوات مساعدة للتعامل مع GitHub ---
def get_github_file():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}?ref={BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        return None

def update_github_file(new_content, sha):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    data = {
        "message": f"Add new account via bot",
        "content": new_content,
        "sha": sha,
        "branch": BRANCH
    }
    r = requests.put(url, headers=headers, data=json.dumps(data))
    return r.status_code == 200 or r.status_code == 201

# --- بدء المحادثة ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً! أرسل صورة الحساب أولاً:")
    return PHOTO

# --- استقبال الصورة ---
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    photo_url = photo_file.file_path  # رابط مؤقت
    user_data_store["image"] = photo_url
    await update.message.reply_text("جيد، الآن أرسل السعر (مثلاً: 100 6) بالجنيه والدولار مفصول بمسافة:")
    return PRICE

# --- استقبال السعر ---
async def price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().split()
    if len(text) != 2 or not all(t.replace('.','',1).isdigit() for t in text):
        await update.message.reply_text("الرجاء إرسال السعر بالشكل الصحيح: EGP USD (مثلاً 100 6)")
        return PRICE
    user_data_store["price_egp"] = float(text[0])
    user_data_store["price_usd"] = float(text[1])
    await update.message.reply_text("أخيرًا، أرسل وصف الحساب:")
    return DESCRIPTION

# --- استقبال الوصف ---
async def description_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    if not desc:
        await update.message.reply_text("الوصف لا يمكن أن يكون فارغًا، أرسله من فضلك.")
        return DESCRIPTION
    user_data_store["description"] = desc

    # الآن نضيف الحساب إلى GitHub
    gh_file = get_github_file()
    if not gh_file:
        await update.message.reply_text("فشل في جلب الملف من GitHub.")
        return ConversationHandler.END

    content = requests.get(gh_file['download_url']).text
    data = json.loads(content)
    accounts = data.get("accounts", [])

    new_id = str(len(accounts)+1)
    new_account = {
        "id": new_id,
        "uid": "",  # يمكنك لاحقًا توليده أو تركه فارغ
        "image": user_data_store["image"],
        "price_egp": user_data_store["price_egp"],
        "price_usd": user_data_store["price_usd"],
        "description": user_data_store["description"],
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

    accounts.append(new_account)
    data["accounts"] = accounts
    new_content_b64 = json.dumps(data, indent=2).encode("utf-8")
    import base64
    new_content_b64 = base64.b64encode(new_content_b64).decode()

    success = update_github_file(new_content_b64, gh_file["sha"])
    if success:
        await update.message.reply_text("✅ تم إضافة الحساب بنجاح على الموقع!")
    else:
        await update.message.reply_text("❌ حدث خطأ أثناء رفع الحساب إلى GitHub.")

    user_data_store.clear()
    return ConversationHandler.END

# --- إلغاء العملية ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.")
    user_data_store.clear()
    return ConversationHandler.END

# --- إعداد المحادثة ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, photo_handler)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price_handler)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_handler)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
