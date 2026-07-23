import telebot
import random
import time
import threading
import os
from flask import Flask
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

# 🔑 إعدادات البوت
BOT_TOKEN = os.getenv("BOT_TOKEN", "8868110647:AAHjffbopZF-p6E9EP9HqB3a2l99IbG-TeI")
bot = telebot.TeleBot(BOT_TOKEN)

# ------------------- اتصال PostgreSQL -------------------
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/game_db")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def setup_database():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        score INTEGER DEFAULT 100,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        title TEXT DEFAULT '⚔️ مغامر',
        total_wins INTEGER DEFAULT 0,
        last_daily TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    cur.close()
    conn.close()

setup_database()

# ------------------- كود Flask لإبقاء البوت حياً -------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 البوت شغال ومستقر!"

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()

# ------------------- قواميس الألعاب -------------------
active_games = {}
games_lock = threading.Lock()
pending_orders = {}
pending_assets = {}

SHOP_PRICES = {"assets": 500, "draw": 1000, "video": 2000}
ASSET_TYPES = ["عيون", "عشوائية", "كرات وخرائط أعلام"]
PAINTERS = ["@Arabic_Painter1", "@alhilal_bahraini", "@BrahimAnimation", "@moha1234561100"]

# الألعاب الأساسية
TYPING_SENTENCES = [
    "البطة مش دايماً مؤنثة",
    "اللي بيته من قزاز لا يرمي الناس بالطوب",
    "الوقت كالسيف إن لم تقطعه قطعك",
    "العلم في الصغر كالنقش على الحجر",
    "من جد وجد ومن زرع حصد",
    "رب أخ لك لم تلده أمك",
    "الصديق وقت الضيق",
    "من راقب الناس مات هماً",
    "العجلة من الشيطان",
    "الحاجة أم الاختراع",
    "من تكبر على الناس ذل",
    "ما كل ما يتمنى المرء يدركه",
    "القرش الأبيض ينفع في اليوم الأسود",
    "يد واحدة لا تصفق",
    "الحب أعمى"
]

SCRAMBLE_WORDS = [
    "تفاحة", "كمبيوتر", "هرم", "شمس", "قمر", "مدرسة", "كتاب", "بحر",
    "سماء", "نجمة", "وردة", "أسد", "نمر", "فيل", "زرافة", "بطريق",
    "تلفاز", "ثلاجة", "سيارة", "طائرة"
]

COUNTRIES = {
    "مصر": "القاهرة", "السعودية": "الرياض", "الإمارات": "أبوظبي",
    "المغرب": "الرباط", "الجزائر": "الجزائر", "تونس": "تونس",
    "لبنان": "بيروت", "الأردن": "عمان", "الكويت": "الكويت",
    "قطر": "الدوحة", "البحرين": "المنامة", "عمان": "مسقط",
    "اليمن": "صنعاء", "سوريا": "دمشق", "العراق": "بغداد",
    "فلسطين": "القدس", "ليبيا": "طرابلس", "السودان": "الخرطوم",
    "موريتانيا": "نواكشوط", "الصومال": "مقديشو"
}

PROVERBS = {
    "اللي استحوا": "ماتوا",
    "اللي بيته من قزاز": "لا يرمي الناس بالطوب",
    "القرد في عين أمه": "غزال",
    "إدي العيش لخبازه": "ولو أكل نصه",
    "جاجة حفرت على راسها": "عفرت",
    "الباب اللي يجيلك منه الريح": "سده واستريح",
    "اللي ما يعرف الصقر": "يشويه",
    "إن غاب القط": "العب يا فار",
    "عصفور في اليد": "خير من عشرة على الشجرة",
    "من شب على شيء": "شاب عليه",
    "اللي ما يطول العنب": "يقول حامض",
    "اتق شر": "من أحسنت إليه",
    "ما حك جلدك": "مثل ظفرك",
    "إذا كان حبيبك عسل": "ما تلحسه كله",
    "الطول طول نخلة": "والعقل عقل صخلة"
}

OPPOSITES = {
    "كبير": "صغير", "طويل": "قصير", "جميل": "قبيح", "سريع": "بطيء",
    "قوي": "ضعيف", "غني": "فقير", "حار": "بارد", "ناعم": "خشن",
    "ذكي": "غبي", "شجاع": "جبان", "كريم": "بخيل", "واسع": "ضيق",
    "مرتفع": "منخفض", "نظيف": "قذر", "هادئ": "مزعج", "ثقيل": "خفيف",
    "مشرق": "مظلم", "جديد": "قديم", "حي": "ميت", "مبتسم": "عابس"
}

FAST_WORDS = [
    "أسد", "وردة", "سماء", "كرة", "بحر", "قلم", "نجم", "شجرة",
    "تفاحة", "قمر", "شمس", "جبل", "نهر", "طائر", "سمكة", "زهرة",
    "مطر", "ريح", "ثلج", "نار"
]

TRIVIA = {
    "ما هي أكبر قارة في العالم؟": "آسيا",
    "ما هو أطول نهر في العالم؟": "النيل",
    "كم عدد ألوان قوس قزح؟": "7",
    "ما هو الكوكب الأحمر؟": "المريخ",
    "من هو مخترع المصباح الكهربائي؟": "إديسون",
    "ما هي أصغر قارة في العالم؟": "أستراليا",
    "كم عدد عظام جسم الإنسان؟": "206",
    "ما هو أسرع حيوان بري؟": "الفهد",
    "ما هي عاصمة اليابان؟": "طوكيو",
    "من هو مكتشف الجاذبية؟": "نيوتن",
    "كم عدد الكواكب في المجموعة الشمسية؟": "8",
    "ما هو البحر الأكثر ملوحة؟": "البحر الميت",
    "كم عدد السور في القرآن؟": "114",
    "من هي أم المؤمنين الأولى؟": "خديجة",
    "كم عدد الأرجل عند الأخطبوط؟": "8"
}

RIDDLES = {
    "ما هو الشيء الذي يمشي بلا رجلين ويبكي بلا عينين؟": "السحاب",
    "ما هو الشيء الذي كلما أخذت منه كبر؟": "الحفرة",
    "ما هو الشيء الذي له أسنان ولا يعض؟": "المشط",
    "ما هو الشيء الذي يكتب ولا يقرأ؟": "القلم",
    "ما هو الشيء الذي يسمع بلا أذن ويتكلم بلا لسان؟": "الهاتف",
    "ما هو الشيء الذي يرى كل شيء ولا عيون له؟": "المرآة",
    "ما هو الشيء الذي يحمل أكثر من 1000 طن ولا يحمل مسماراً؟": "البحر",
    "ما هو الشيء الذي إذا دخل الماء تشتت؟": "الورق",
    "ما هو الشيء الذي له رأس ولا عيون؟": "الدبوس",
    "ما هو الشيء الذي يلف حول الغرفة ولا يتحرك؟": "الحائط",
    "ما هو الشيء الذي ينام بحذائه؟": "الحصان",
    "ما هو الشيء الذي يقرصك ولا تراه؟": "الجوع",
    "ما هو الشيء الذي يكسو الناس وهو عارٍ؟": "الإبرة",
    "ما هو الشيء الذي له رقبة وليس له رأس؟": "القنينة",
    "ما هو الشيء الذي يأكل ولا يشبع؟": "النار"
}

TRANSLATE_WORDS = {
    "Book": "كتاب", "Sun": "شمس", "Moon": "قمر", "Water": "ماء",
    "Fire": "نار", "Tree": "شجرة", "Star": "نجم", "Heart": "قلب",
    "Sky": "سماء", "River": "نهر", "Mountain": "جبل", "Flower": "زهرة",
    "Rain": "مطر", "Snow": "ثلج", "Wind": "ريح", "Light": "ضوء",
    "Darkness": "ظلام", "Love": "حب", "Peace": "سلام", "War": "حرب"
}

EMOJI_GUESS = {
    "🦁👑": "الأسد الملك",
    "🚢💥🧊": "تيتانيك",
    "🧙‍♂️⚡🏰": "هاري بوتر",
    "🕷️🦸‍♂️": "سبايدر مان",
    "👻🚫": "صائدو الأشباح",
    "🦖🏞️": "الحديقة الجوراسية",
    "🧸🎈": "تيد",
    "🚀🌙": "أبولو 13",
    "🐟🔍": "البحث عن نيمو",
    "🦁👦🏿🌴": "الملك الأسد 2",
    "🤖🌿": "والي",
    "🏎️⚡": "سيارات",
    "👸❄️": "ملكة الثلج",
    "🐉🥋": "كونغ فو باندا",
    "🕵️‍♂️🔍": "شارلوك هولمز",
    "🧞‍♂️🪔": "علاء الدين",
    "🐒🌴👑": "طرزان",
    "🐭👨‍🍳": "راتاتوي",
    "👹👸": "الجميلة والوحش",
    "🦸‍♂️🛡️": "كابتن أمريكا"
}

DIALECTS = {
    "شنو معنى كلمة 'دريوي' في اللهجة المغربية؟": "شخص لطيف",
    "ما معنى 'قوطي' في اللهجة العراقية؟": "علبة",
    "إيش تعني 'يديني' في اللهجة السعودية؟": "يعطيني",
    "ما معنى 'كشخة' في اللهجة الكويتية؟": "أنيق",
    "شنو 'البلوك' في اللهجة التونسية؟": "الحي",
    "ما معنى 'بزاف' في اللهجة الجزائرية؟": "كثير",
    "إيش 'صهيوني' في اللهجة اليمنية؟": "جميل",
    "ما معنى 'طرشي' في اللهجة البحرينية؟": "طرش البحر",
    "شنو 'البسباس' في اللهجة الليبية؟": "الفلفل",
    "ما معنى 'دشّر' في اللهجة السودانية؟": "اترك",
    "إيش 'كزدورة' في اللهجة الأردنية؟": "نزهة",
    "شنو 'شحال' في اللهجة المغربية؟": "كم",
    "ما معنى 'خاشوقة' في اللهجة العراقية؟": "ملعقة",
    "إيش 'مصرقع' في اللهجة السعودية؟": "مجنون",
    "ما معنى 'قفشة' في اللهجة المصرية؟": "نكتة"
}

# الألعاب الجديدة (كل واحدة 15-20 عنصر)
CROSSWORD = {
    "ما هو الشيء الذي يمشي بلا رجلين ويطير بلا أجنحة؟": "الوقت",
    "ما هو الشيء الذي كلما زاد نقص؟": "العمر",
    "ما هو الشيء الذي له أوراق وليس شجرة؟": "الكتاب",
    "ما هو الشيء الذي له عين ولا يرى؟": "الإبرة",
    "ما هو الشيء الذي يخترق الزجاج ولا يكسره؟": "الضوء",
    "ما هو الشيء الذي يحملك وتحمله في نفس الوقت؟": "الحذاء",
    "ما هو الشيء الذي تأكل منه وهو لا يؤكل؟": "الطبق",
    "ما هو الشيء الذي يموت إذا وضع في الماء؟": "النار",
    "ما هو الشيء الذي يسير بلا رجلين؟": "السفينة",
    "ما هو الشيء الذي له فروع وليس شجرة؟": "النهر",
    "ما هو الشيء الذي يذوب في الشمس؟": "الثلج",
    "ما هو الشيء الذي يكبر بالضرب؟": "المسمار",
    "ما هو الشيء الذي لا يمشي إلا بالضرب؟": "الكرة",
    "ما هو الشيء الذي يبكي بلا عينين؟": "السحاب",
    "ما هو الشيء الذي يزيد بالاستعمال؟": "العقل"
}

FOOD_CHAIN = {
    "ماذا يأكل الأسد؟": "اللحم",
    "ماذا تأكل البقرة؟": "العشب",
    "ماذا يأكل الدب؟": "السمك",
    "ماذا يأكل النسر؟": "الأرانب",
    "ماذا يأكل القرش؟": "الأسماك",
    "ماذا تأكل الزرافة؟": "أوراق الشجر",
    "ماذا يأكل الثعبان؟": "الفئران",
    "ماذا يأكل البطريق؟": "الأسماك",
    "ماذا يأكل الضفدع؟": "الحشرات",
    "ماذا تأكل النحلة؟": "الرحيق",
    "ماذا يأكل الذئب؟": "الغزلان",
    "ماذا يأكل التمساح؟": "اللحم",
    "ماذا تأكل القطة؟": "الفئران",
    "ماذا يأكل البومة؟": "الفئران",
    "ماذا يأكل الدلفين؟": "الأسماك"
}

MATH_PUZZLES = {
    "ما هو العدد الذي إذا ضربته في نفسه وأضفت 5 يصبح 30؟": "5",
    "ما هو العدد الذي إذا قسمته على 2 وأضفت 3 يصبح 10؟": "14",
    "ما هو العدد الذي إذا ضربته في 3 وطرحت 7 يصبح 20؟": "9",
    "ما هو العدد الذي إذا أضفت إليه 15 يصبح 40؟": "25",
    "ما هو العدد الذي نصفه ثلثه؟": "0",
    "ما هو العدد الذي ربعه يساوي 5؟": "20",
    "ما هو العدد الذي 20% منه يساوي 10؟": "50",
    "ما هو العدد الذي إذا ضربته في 4 كان الناتج 48؟": "12",
    "ما هو العدد الذي إذا طرحته من 100 كان الناتج 65؟": "35",
    "ما هو العدد الذي 3 أضعافه زائد 8 يساوي 32؟": "8",
    "ما هو العدد الذي إذا قسمته على 5 كان الناتج 7؟": "35",
    "ما هو العدد الذي 10% منه يساوي 5؟": "50",
    "ما هو العدد الذي مربعه 144؟": "12",
    "ما هو العدد الذي جذره التربيعي 9؟": "81",
    "ما هو العدد الذي 7 أضعافه تساوي 63؟": "9"
}

LOGIC_PUZZLES = {
    "ما هو الشيء الذي تراه في الليل ولا تراه في النهار؟": "القمر",
    "ما هو الشيء الذي يدخل الماء ولا يبتل؟": "الضوء",
    "ما هو الشيء الذي يزيد كلما أخذنا منه؟": "الحفرة",
    "ما هو الشيء الذي لا يسير إلا بالضرب؟": "المسمار",
    "ما هو الشيء الذي كلما كثر لدينا قل سعره؟": "الذهب",
    "ما هو الشيء الذي يكتب ولا يقرأ؟": "القلم",
    "ما هو الشيء الذي يحمل قنطاراً ولا يحمل مسماراً؟": "السفينة",
    "ما هو الشيء الذي يخترق البيوت دون استئذان؟": "الهواء",
    "ما هو الشيء الذي يضحك بلا فم؟": "المرآة",
    "ما هو الشيء الذي إذا غليته جمد؟": "البيض",
    "ما هو الشيء الذي يزرع مرة ويحصد كل سنة؟": "الشجرة",
    "ما هو الشيء الذي له وجه بلا لسان؟": "الساعة",
    "ما هو الشيء الذي يحرق نفسه لينير للآخرين؟": "الشمعة",
    "ما هو الشيء الذي يجري ولا يمشي؟": "الماء",
    "ما هو الشيء الذي له أجنحة ولا يطير؟": "الطائرة الورقية"
}

MISSING_WORDS = {
    "أكمل الجملة: الشمس تشرق من ...": "الشرق",
    "أكمل الجملة: البحر ...": "أزرق",
    "أكمل الجملة: القطة ...": "تموء",
    "أكمل الجملة: السماء ...": "صافية",
    "أكمل الجملة: الطائر ...": "يطير",
    "أكمل الجملة: الطفل ...": "يلعب",
    "أكمل الجملة: الجبل ...": "شاهق",
    "أكمل الجملة: النار ...": "تحرق",
    "أكمل الجملة: الماء ...": "يجري",
    "أكمل الجملة: القمر ...": "يضيء",
    "أكمل الجملة: الورد ...": "جميل",
    "أكمل الجملة: العسل ...": "حلو",
    "أكمل الجملة: الكلب ...": "ينبح",
    "أكمل الجملة: الرياح ...": "تهب",
    "أكمل الجملة: الثلج ...": "يذوب"
}

SHAPES = {
    "ما هو الشكل الذي له 3 أضلاع؟": "مثلث",
    "ما هو الشكل الذي له 4 أضلاع متساوية؟": "مربع",
    "ما هو الشكل الذي له 5 أضلاع؟": "مخمس",
    "ما هو الشكل الذي ليس له أضلاع؟": "دائرة",
    "ما هو الشكل الذي له 6 أضلاع؟": "مسدس",
    "ما هو الشكل الذي له 8 أضلاع؟": "مثمن",
    "ما هو الشكل الذي له 4 أضلاع متوازية؟": "متوازي أضلاع",
    "ما هو الشكل الذي له زاوية قائمة واحدة؟": "مثلث قائم",
    "ما هو الشكل الذي له قطران متساويان؟": "مربع",
    "ما هو الشكل الذي مساحته الطول × العرض؟": "مستطيل",
    "ما هو الشكل الذي له 7 أضلاع؟": "مسبع",
    "ما هو الشكل الذي زواياه 360 درجة؟": "دائرة",
    "ما هو الشكل الذي له 10 أضلاع؟": "معشر",
    "ما هو الشكل الذي أضلاعه غير متساوية؟": "مثلث مختلف الأضلاع",
    "ما هو الشكل المكون من 4 مثلثات؟": "هرم"
}

HISTORY_DATES = {
    "في أي عام سقطت الخلافة العثمانية؟": "1924",
    "في أي عام كانت الثورة الفرنسية؟": "1789",
    "في أي عام انتهت الحرب العالمية الأولى؟": "1918",
    "في أي عام انتهت الحرب العالمية الثانية؟": "1945",
    "في أي عام سقطت الأندلس؟": "1492",
    "في أي عام اكتشفت أمريكا؟": "1492",
    "في أي عام قامت الثورة الجزائرية؟": "1954",
    "في أي عام استقلت مصر؟": "1952",
    "في أي عام تأسست الأمم المتحدة؟": "1945",
    "في أي عام هبط الإنسان على القمر؟": "1969",
    "في أي عام بدأت الثورة السورية؟": "2011",
    "في أي عام وقعت معركة حطين؟": "1187",
    "في أي عام فتحت القسطنطينية؟": "1453",
    "في أي عام استقلت تونس؟": "1956",
    "في أي عام تأسست المملكة العربية السعودية؟": "1932"
}

NEW_CAPITALS = {
    "عاصمة أستراليا؟": "كانبرا",
    "عاصمة البرازيل؟": "برازيليا",
    "عاصمة كندا؟": "أوتاوا",
    "عاصمة الهند؟": "نيودلهي",
    "عاصمة الصين؟": "بكين",
    "عاصمة روسيا؟": "موسكو",
    "عاصمة جنوب أفريقيا؟": "بريتوريا",
    "عاصمة الأرجنتين؟": "بوينس آيرس",
    "عاصمة تركيا؟": "أنقرة",
    "عاصمة إيران؟": "طهران",
    "عاصمة باكستان؟": "إسلام أباد",
    "عاصمة نيجيريا؟": "أبوجا",
    "عاصمة كينيا؟": "نيروبي",
    "عاصمة ماليزيا؟": "كوالالمبور",
    "عاصمة الفلبين؟": "مانيلا",
    "عاصمة تشيلي؟": "سانتياغو",
    "عاصمة اليونان؟": "أثينا",
    "عاصمة النرويج؟": "أوسلو",
    "عاصمة السويد؟": "ستوكهولم",
    "عاصمة فنلندا؟": "هلسنكي"
}

CHEMISTRY = {
    "ما هو الرمز الكيميائي للماء؟": "H2O",
    "ما هو الرمز الكيميائي للأكسجين؟": "O2",
    "ما هو الرمز الكيميائي للذهب؟": "Au",
    "ما هو الرمز الكيميائي للفضة؟": "Ag",
    "ما هو الرمز الكيميائي للحديد؟": "Fe",
    "ما هو الرمز الكيميائي للصوديوم؟": "Na",
    "ما هو الرمز الكيميائي للبوتاسيوم؟": "K",
    "ما هو الرمز الكيميائي للكالسيوم؟": "Ca",
    "ما هو الرمز الكيميائي للنحاس؟": "Cu",
    "ما هو الرمز الكيميائي للزنك؟": "Zn",
    "ما هو الرمز الكيميائي للرصاص؟": "Pb",
    "ما هو الرمز الكيميائي للزئبق؟": "Hg",
    "ما هو الرمز الكيميائي لليورانيوم؟": "U",
    "ما هو الرمز الكيميائي للنيتروجين؟": "N2",
    "ما هو الرمز الكيميائي لثاني أكسيد الكربون؟": "CO2",
    "ما هو الرمز الكيميائي للملح؟": "NaCl",
    "ما هو الرمز الكيميائي للكربون؟": "C",
    "ما هو الرمز الكيميائي للكلور؟": "Cl",
    "ما هو الرمز الكيميائي للهيدروجين؟": "H2",
    "ما هو الرمز الكيميائي للمغنيسيوم؟": "Mg"
}

ANIMALS = {
    "ما هو أسرع حيوان في العالم؟": "الفهد",
    "ما هو أكبر حيوان في العالم؟": "الحوت الأزرق",
    "ما هو أطول حيوان في العالم؟": "الزرافة",
    "ما هو أذكى حيوان في العالم؟": "الدلفين",
    "ما هو أقوى حيوان في العالم؟": "الفيل",
    "ما هو أصغر طائر في العالم؟": "الطنان",
    "ما هو الحيوان الذي لا يشرب الماء؟": "الكنغر",
    "ما هو الحيوان الذي ينام واقفاً؟": "الحصان",
    "ما هو الحيوان الذي يغير لونه؟": "الحرباء",
    "ما هو الحيوان الذي له 3 قلوب؟": "الأخطبوط",
    "ما هو الحيوان الذي يعيش أطول عمر؟": "السلحفاة",
    "ما هو الحيوان الذي يلد ولا يبيض؟": "الخفاش",
    "ما هو الحيوان الذي يرى بالأذن؟": "الوطواط",
    "ما هو الحيوان الملقب بسفينة الصحراء؟": "الجمل",
    "ما هو الحيوان الذي له ذاكرة قوية؟": "الفيل",
    "ما هو الحيوان الذي يأكل الحجارة؟": "التمساح",
    "ما هو الحيوان الذي لا ينام؟": "القرش",
    "ما هو الحيوان الذي يعيش في الماء والبر؟": "الضفدع",
    "ما هو الحيوان الذي له بصمة مثل الإنسان؟": "الكوالا",
    "ما هو الحيوان الذي يضحك؟": "الضبع"
}

funny_responses = {
    "win": ["🎉 {name} فاز! ذكاء خارق 😂", "🏆 {name} كسب! التاج لايق عليك 🤣", "🔥 {name} دمر الجميع! أسطورة!", "😎 {name} جابها في الثمانيات! وحش!", "🧠 {name} مخه شغال صح، عاش!"],
    "timeout": ["⏰ الوقت خلص وكلكم نايمين! 😂", "😴 ولا واحد عرف؟ شكلكم محتاجين قهوة!", "🐌 بطيئين جداً! الإجابة طارت."]
}

TITLES = {0: "⚔️ مبتدئ", 200: "🛡️ محارب", 400: "⚜️ فارس", 700: "👑 أمير", 1000: "🤴 ملك", 1500: "🦁 أسد الكروب", 2500: "🔥 أسطورة", 5000: "💎 إمبراطور"}

# ------------------- إدارة اللاعبين -------------------
def get_player(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE user_id = %s", (user_id,))
    player = cur.fetchone()
    cur.close()
    conn.close()
    return player

def update_player(user_id, username, first_name, score=None, wins=None, losses=None):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT score FROM players WHERE user_id = %s", (user_id,))
    player = cur.fetchone()
    
    if not player:
        cur.execute("""
            INSERT INTO players (user_id, username, first_name, title, score) 
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, username, first_name, "⚔️ مبتدئ", 100))
        current_score = 100
    else:
        current_score = player['score']
    
    if score is not None:
        current_score = score
    
    cur.execute("""
        UPDATE players SET 
        score = COALESCE(%s, score), 
        wins = COALESCE(%s, wins), 
        losses = COALESCE(%s, losses), 
        username = %s
        WHERE user_id = %s
    """, (score, wins, losses, username, user_id))
    
    new_title = "⚔️ مبتدئ"
    for limit, title in sorted(TITLES.items(), reverse=True):
        if current_score >= limit:
            new_title = title
            break
    cur.execute("UPDATE players SET title = %s WHERE user_id = %s", (new_title, user_id))
    
    conn.commit()
    cur.close()
    conn.close()

# ------------------- أمر الأدمن -------------------
ADMIN_ID = 7073442874

@bot.message_handler(commands=['sendboint'])
def send_points_to_player(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ هذا الأمر للأدمن فقط!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ الاستخدام الصحيح: /sendboint @username [عدد النقاط]")
            return
        
        username = parts[1].replace('@', '')
        points = int(parts[2])
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id, score FROM players WHERE username = %s", (username,))
        player = cur.fetchone()
        
        if not player:
            bot.reply_to(message, f"❌ لا يوجد لاعب بهذا الاسم: @{username}")
            cur.close()
            conn.close()
            return
        
        new_score = player['score'] + points
        cur.execute("UPDATE players SET score = %s WHERE user_id = %s", (new_score, player['user_id']))
        conn.commit()
        
        bot.reply_to(message, f"✅ تم إضافة {points} نقطة للاعب @{username}\nنقاطه الآن: {new_score}")
        
        try:
            bot.send_message(player['user_id'], f"🎁 تم إضافة {points} نقطة إلى رصيدك بواسطة الأدمن!\nنقاطك الآن: {new_score}")
        except:
            pass
        
        cur.close()
        conn.close()
        
    except ValueError:
        bot.reply_to(message, "❌ يجب إدخال عدد صحيح للنقاط")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")

# ------------------- نظام المتجر المطور -------------------
@bot.message_handler(commands=['shop'])
def shop_cmd(message):
    update_player(message.from_user.id, message.from_user.username, message.from_user.first_name)
    player = get_player(message.from_user.id)
    
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(f"🛍️ شراء ملحقات ({SHOP_PRICES['assets']})", callback_data="buy_assets"))
    markup.row(InlineKeyboardButton(f"🎨 رسم رسمة ({SHOP_PRICES['draw']})", callback_data="buy_draw"))
    markup.row(InlineKeyboardButton(f"🎬 فيديو تعاوني ({SHOP_PRICES['video']})", callback_data="buy_video"))
    
    bot.reply_to(message, f"🛒 **متجر اللعبة الأسطوري!**\n💰 نقاطك: **{player['score']}**\n\nاختر ما تود شراءه:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy_click(call):
    user_id = call.from_user.id
    item_key = call.data.split('_')[1]
    price = SHOP_PRICES[item_key]
    player = get_player(user_id)
    
    if player['score'] < price:
        return bot.answer_callback_query(call.id, f"❌ نقاطك غير كافية! تحتاج {price} نقطة.", show_alert=True)
    
    if item_key == "assets":
        markup = InlineKeyboardMarkup()
        for asset_type in ASSET_TYPES:
            markup.row(InlineKeyboardButton(f"🎨 {asset_type}", callback_data=f"asset_type:{asset_type}"))
        markup.row(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_shop"))
        
        bot.edit_message_text(
            "🛍️ **اختر نوع الملحقات:**\n\n"
            "1️⃣ ملحقات عيون\n"
            "2️⃣ ملحقات عشوائية\n"
            "3️⃣ ملحقات كرات وخرائط أعلام",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    else:
        order_type_map = {"draw": "رسم رسمة", "video": "فيديو تعاوني"}
        pending_orders[user_id] = {'type': order_type_map[item_key], 'price': price, 'state': 'waiting_flag'}
        bot.edit_message_text(
            f"✅ اخترت: **{order_type_map[item_key]}**\n\n🖼️ **الآن:** أرسل صورة علمك/دولتك للطلب.",
            call.message.chat.id,
            call.message.message_id
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('asset_type:'))
def handle_asset_type(call):
    user_id = call.from_user.id
    asset_type = call.data.split(':')[1]
    
    pending_assets[user_id] = {'type': asset_type, 'state': 'waiting_flag'}
    
    bot.edit_message_text(
        f"✅ اخترت: **ملحقات {asset_type}**\n\n"
        "📸 **الخطوة 1:** أرسل صورة علمك/دولتك.",
        call.message.chat.id,
        call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_shop')
def back_to_shop(call):
    shop_cmd(call.message)

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in pending_assets and pending_assets[m.from_user.id].get('state') == 'waiting_flag')
def handle_asset_flag_photo(message):
    user_id = message.from_user.id
    pending_assets[user_id]['photo_id'] = message.photo[-1].file_id
    pending_assets[user_id]['state'] = 'waiting_name'
    
    bot.reply_to(message, "📸 تم استلام العلم!\n\n📝 **الخطوة 2:** أرسل اسمك (الاسم الذي تريد كتابته على الملحقات).")

@bot.message_handler(func=lambda m: m.from_user.id in pending_assets and pending_assets[m.from_user.id].get('state') == 'waiting_name')
def handle_asset_name(message):
    user_id = message.from_user.id
    pending_assets[user_id]['name'] = message.text
    pending_assets[user_id]['state'] = 'waiting_count'
    
    bot.reply_to(message, f"✅ تم استلام الاسم: **{message.text}**\n\n🔢 **الخطوة 3:** كم ملحق تريد؟ (الحد الأقصى 25)")

@bot.message_handler(func=lambda m: m.from_user.id in pending_assets and pending_assets[m.from_user.id].get('state') == 'waiting_count')
def handle_asset_count(message):
    user_id = message.from_user.id
    
    try:
        count = int(message.text)
        if count < 1 or count > 25:
            bot.reply_to(message, "❌ العدد يجب أن يكون بين 1 و 25!")
            return
        
        pending_assets[user_id]['count'] = count
        pending_assets[user_id]['state'] = 'waiting_painter'
        
        markup = InlineKeyboardMarkup()
        for painter in PAINTERS:
            markup.row(InlineKeyboardButton(f"🖌️ {painter}", callback_data=f"asset_painter:{painter}"))
        
        bot.reply_to(message, f"✅ تم تحديد العدد: {count}\n\n🎨 **الخطوة الأخيرة:** اختر الرسام لتنفيذ طلبك:", reply_markup=markup)
        
    except ValueError:
        bot.reply_to(message, "❌ يجب إدخال رقم صحيح!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('asset_painter:'))
def handle_asset_painter(call):
    user_id = call.from_user.id
    painter = call.data.split(':')[1]
    
    if user_id not in pending_assets or pending_assets[user_id].get('state') != 'waiting_painter':
        return bot.answer_callback_query(call.id, "❌ الطلب منتهي.", show_alert=True)
    
    asset_data = pending_assets[user_id]
    painter_username = painter.replace('@', '')
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM players WHERE username = %s", (painter_username,))
    painter_data = cur.fetchone()
    cur.close()
    conn.close()
    
    if not painter_data:
        bot.answer_callback_query(call.id, f"❌ الرسام {painter} غير مسجل!", show_alert=True)
        return
    
    painter_chat_id = painter_data['user_id']
    price = SHOP_PRICES['assets']
    player = get_player(user_id)
    
    if player['score'] < price:
        del pending_assets[user_id]
        return bot.edit_message_text("❌ نقاطك لم تعد تكفي لإتمام الطلب!", call.message.chat.id, call.message.message_id)
    
    update_player(user_id, call.from_user.username, call.from_user.first_name, score=player['score'] - price)
    
    order_text = (
        f"🚨 **طلب ملحقات جديد!** 🚨\n\n"
        f"👤 **اللاعب:** {call.from_user.first_name} (@{call.from_user.username})\n"
        f"📋 **نوع الملحقات:** {asset_data['type']}\n"
        f"📝 **الاسم:** {asset_data['name']}\n"
        f"🔢 **العدد:** {asset_data['count']}\n"
        f"⏱️ **ملاحظة:** يجب إنهاء الطلب خلال 24 ساعة!"
    )
    
    try:
        bot.send_photo(painter_chat_id, asset_data['photo_id'], caption=order_text)
        bot.edit_message_text(
            f"✅ **تمت العملية بنجاح!**\n"
            f"خصمنا {price} نقطة، وتم إرسال طلبك لحساب الرسام {painter}.\n\n"
            f"📝 تفاصيل الطلب:\n"
            f"- نوع الملحقات: {asset_data['type']}\n"
            f"- الاسم: {asset_data['name']}\n"
            f"- العدد: {asset_data['count']}",
            call.message.chat.id,
            call.message.message_id
        )
    except Exception as e:
        bot.edit_message_text(
            f"⚠️ فشل إرسال الطلب للرسام {painter} (قد يكون حظر البوت).\n"
            f"الخطأ: {str(e)}",
            call.message.chat.id,
            call.message.message_id
        )
    
    del pending_assets[user_id]

# ------------------- الأوامر الأساسية والألعاب -------------------
@bot.message_handler(commands=['start', 'top', 'daily'])
def basic_commands(message):
    cmd = message.text.split()[0].split('@')[0].replace('/', '')
    user = message.from_user
    update_player(user.id, user.username, user.first_name)
    player = get_player(user.id)
    
    if cmd == "start":
        text = ("🎮 أهلاً بك في بوت التحديات الأسطوري!\nكل لاعب جديد يحصل على 100 نقطة 🎁\n\n"
                "**الأوامر:**\n/shop - المتجر\n/top - المتصدرين\n/daily - الهدية اليومية\n\n"
                "🎲 **قائمة الألعاب (26 لعبة):**\n"
                "/g1 خمن الرقم | /g2 رياضيات | /g3 سرعة كتابة\n"
                "/g4 اعكس الكلمة | /g5 عواصم | /g6 رتب الحروف\n"
                "/g7 أكمل المثل | /g8 عد الإيموجي | /g9 عكس الكلمة\n"
                "/g10 أسرع كلمة | /g11 أسئلة ثقافية | /g12 ألغاز\n"
                "/g13 متتالية أرقام | /g14 ترجمة | /g15 إيموجي أفلام\n"
                "/g16 اللهجات العربية | /g17 كلمات متقاطعة | /g18 سلسلة غذائية\n"
                "/g19 أحجية رياضية | /g20 ألغاز منطقية | /g21 كلمات مفقودة\n"
                "/g22 أشكال هندسية | /g23 تواريخ تاريخية | /g24 دول وعواصم جديدة\n"
                "/g25 كيمياء | /g26 حيوانات\n\n"
                "🔥 وللاختيار العشوائي: /randomgame")
        bot.reply_to(message, text)
    elif cmd == "top":
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT first_name, score, title FROM players ORDER BY score DESC LIMIT 10")
        top = cur.fetchall()
        cur.close()
        conn.close()
        
        text = "🏆 **أفضل 10 لاعبين:**\n\n" + "\n".join([f"{i+1}. {p['title']} {p['first_name']} - {p['score']} نقطة" for i, p in enumerate(top)])
        bot.reply_to(message, text)
    elif cmd == "daily":
        last = player['last_daily']
        time_since_last = datetime.now() - last
        
        if time_since_last >= timedelta(days=1):
            new_score = player['score'] + 50
            update_player(user.id, user.username, user.first_name, score=new_score)
            
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("UPDATE players SET last_daily = %s WHERE user_id = %s", (datetime.now(), user.id))
            conn.commit()
            cur.close()
            conn.close()
            
            bot.reply_to(message, f"🎁 استلمت 50 نقطة مجانية! نقاطك الآن أصبحت: {new_score} نقطة.")
        else:
            remaining_time = timedelta(days=1) - time_since_last
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            bot.reply_to(message, f"⏳ لقد استلمت مكافأتك مسبقاً يا وحش!\nعد بعد: **{hours} ساعة و {minutes} دقيقة** ⏱️")

@bot.message_handler(commands=[f'g{i}' for i in range(1, 27)] + ['randomgame'])
def start_specific_game(message):
    chat_id = message.chat.id
    with games_lock:
        if chat_id in active_games:
            return bot.reply_to(message, "⏳ يا كابتن، في تحدي شغال أصلاً، خلصوه أول!")
    
    cmd = message.text.split()[0].split('@')[0].replace('/', '')
    game_id = random.randint(1, 26) if cmd == 'randomgame' else int(cmd.replace('g', ''))
    
    if game_id == 1:
        ans, q = str(random.randint(1, 100)), "🔢 خمن الرقم بين 1 و 100"
    elif game_id == 2:
        n1, n2, op = random.randint(10, 100), random.randint(1, 50), random.choice(['+', '-', '*'])
        ans, q = str(eval(f"{n1}{op}{n2}")), f"🧮 ناتج: {n1} {op} {n2} = ؟"
    elif game_id == 3:
        s = random.choice(TYPING_SENTENCES)
        ans, q = s, f"⌨️ أسرع واحد يكتب الجملة:\n`{s}`"
    elif game_id == 4:
        w = random.choice(SCRAMBLE_WORDS)
        ans, q = w[::-1], f"🔄 اعكس حروف الكلمة: **{w}**"
    elif game_id == 5:
        c, cap = random.choice(list(COUNTRIES.items()))
        ans, q = cap, f"🌍 ما هي عاصمة **{c}** ؟"
    elif game_id == 6:
        w = random.choice(SCRAMBLE_WORDS)
        shuffled = ''.join(random.sample(w, len(w)))
        ans, q = w, f"🧩 رتب هذه الحروف لتكوين كلمة: **{shuffled}**"
    elif game_id == 7:
        h, m = random.choice(list(PROVERBS.items()))
        ans, q = m, f"📜 أكمل المثل الشعبي:\n{h} ... (كلمة واحدة)"
    elif game_id == 8:
        e, count = random.choice(["🍎", "🔥", "💎", "💣", "⚔️"]), random.randint(4, 9)
        emojis = [e]*count + [random.choice(["🍌", "🍉", "💧"])]*20
        random.shuffle(emojis)
        ans, q = str(count), f"👀 كم مرة تكرر الإيموجي {e} هنا؟\n{''.join(emojis)}"
    elif game_id == 9:
        w, opp = random.choice(list(OPPOSITES.items()))
        ans, q = opp, f"↔️ ما هو عكس كلمة: **{w}** ؟"
    elif game_id == 10:
        ans = random.choice(FAST_WORDS)
        q = f"⚡ أسرع شخص يكتب الكلمة:\n**{ans}**"
    elif game_id == 11:
        qu, a = random.choice(list(TRIVIA.items()))
        ans, q = a, f"🧠 سؤال ثقافي:\n{qu}"
    elif game_id == 12:
        qu, a = random.choice(list(RIDDLES.items()))
        ans, q = a, f"🕵️‍♂️ لغز:\n{qu}"
    elif game_id == 13:
        start, step = random.randint(1,10), random.randint(2,5)
        ans, q = str(start+4*step), f"🔢 أكمل المتتالية: {start}, {start+step}, {start+2*step}, {start+3*step}, ... ؟"
    elif game_id == 14:
        en, ar = random.choice(list(TRANSLATE_WORDS.items()))
        ans, q = ar, f"🇺🇸 ترجم للعربية: '{en}'"
    elif game_id == 15:
        em, mov = random.choice(list(EMOJI_GUESS.items()))
        ans, q = mov, f"🎬 خمن اسم الفيلم من الإيموجي: {em}"
    elif game_id == 16:
        qu, a = random.choice(list(DIALECTS.items()))
        ans, q = a, f"🗣️ **تحدي اللهجات العربية:**\n{qu}"
    elif game_id == 17:
        qu, a = random.choice(list(CROSSWORD.items()))
        ans, q = a, f"🧩 **كلمات متقاطعة:**\n{qu}"
    elif game_id == 18:
        qu, a = random.choice(list(FOOD_CHAIN.items()))
        ans, q = a, f"🍽️ **السلسلة الغذائية:**\n{qu}"
    elif game_id == 19:
        qu, a = random.choice(list(MATH_PUZZLES.items()))
        ans, q = a, f"🧮 **أحجية رياضية:**\n{qu}"
    elif game_id == 20:
        qu, a = random.choice(list(LOGIC_PUZZLES.items()))
        ans, q = a, f"🧠 **لغز منطقي:**\n{qu}"
    elif game_id == 21:
        qu, a = random.choice(list(MISSING_WORDS.items()))
        ans, q = a, f"📝 **كلمات مفقودة:**\n{qu}"
    elif game_id == 22:
        qu, a = random.choice(list(SHAPES.items()))
        ans, q = a, f"📐 **أشكال هندسية:**\n{qu}"
    elif game_id == 23:
        qu, a = random.choice(list(HISTORY_DATES.items()))
        ans, q = a, f"📅 **تواريخ تاريخية:**\n{qu}"
    elif game_id == 24:
        qu, a = random.choice(list(NEW_CAPITALS.items()))
        ans, q = a, f"🌍 **دول وعواصم جديدة:**\n{qu}"
    elif game_id == 25:
        qu, a = random.choice(list(CHEMISTRY.items()))
        ans, q = a, f"🧪 **كيمياء:**\n{qu}"
    elif game_id == 26:
        qu, a = random.choice(list(ANIMALS.items()))
        ans, q = a, f"🐾 **حيوانات:**\n{qu}"
    else:
        return bot.reply_to(message, "❌ رقم اللعبة غير صالح")
    
    with games_lock:
        active_games[chat_id] = ans.strip().lower()
    
    bot.send_message(chat_id, f"🎮 **تحدي جديد!**\n\n{q}\n\n⏳ لديكم 45 ثانية يا شباب!")
    threading.Timer(45.0, end_group_game, args=[chat_id, ans]).start()

def end_group_game(chat_id, correct_answer):
    with games_lock:
        if chat_id in active_games and active_games[chat_id] == correct_answer.strip().lower():
            del active_games[chat_id]
            timeout_msg = random.choice(funny_responses['timeout'])
            try:
                bot.send_message(chat_id, f"{timeout_msg}\n✅ الإجابة كانت: **{correct_answer}**")
            except:
                pass

@bot.message_handler(func=lambda m: m.chat.type in ["group", "supergroup"] and not m.text.startswith('/'))
def handle_group_answers(message):
    chat_id = message.chat.id
    
    if chat_id not in active_games:
        return
    
    with games_lock:
        if chat_id in active_games and str(message.text).strip().lower() == active_games[chat_id]:
            ans = active_games.pop(chat_id)
            
            update_player(message.from_user.id, message.from_user.username, message.from_user.first_name)
            player = get_player(message.from_user.id)
            update_player(message.from_user.id, message.from_user.username, message.from_user.first_name, score=player['score'] + 15)
            
            win_msg = random.choice(funny_responses['win']).format(name=message.from_user.first_name)
            bot.reply_to(message, f"{win_msg}\nالإجابة: {ans}\n🤑 أضفنا لك 15 نقطة!")

# ------------------- تشغيل البوت -------------------
if __name__ == "__main__":
    print("✅ البوت شغال ومحمي ضد التوقف...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
