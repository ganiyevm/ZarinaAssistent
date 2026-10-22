import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
# Bosh adminlar (vergul bilan): ular boshqa adminlarni qo'sha oladi
SUPER_ADMINS = {
    int(x) for x in os.getenv("SUPER_ADMINS", "").replace(" ", "").split(",") if x
}
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")
# Birinchi ishga tushganda baza bo'sh bo'lsa shu fayldan xodimlar yuklanadi
SEED_FILE = os.getenv("SEED_FILE", "")

LANGS = {
    "uz_latn": "O‘zbek (lotin)",
    "uz_cyrl": "Ўзбек (кирилл)",
    "ru": "Русский",
}
GENDERS = {"M": "Erkak", "F": "Ayol"}
