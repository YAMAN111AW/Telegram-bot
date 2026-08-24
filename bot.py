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
        last_daily TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        language TEXT DEFAULT 'ar'
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
ASSET_TYPES_AR = ["عيون", "عشوائية", "كرات وخرائط أعلام"]
ASSET_TYPES_EN = ["Eyes", "Random", "Balls & Flag Maps"]
ASSET_TYPES_FA = ["چشم‌ها", "تصادفی", "توپ‌ها و نقشه‌های پرچم"]
PAINTERS = ["@Arabic_Painter1", "@Palestine_Hilal", "@BrahimAnimation", "@moha1234561100"]

# الألعاب الأساسية
TYPING_SENTENCES_AR = [
    "البطة مش دايماً مؤنثة", "اللي بيته من قزاز لا يرمي الناس بالطوب",
    "الوقت كالسيف إن لم تقطعه قطعك", "العلم في الصغر كالنقش على الحجر",
    "من جد وجد ومن زرع حصد", "رب أخ لك لم تلده أمك",
    "الصديق وقت الضيق", "من راقب الناس مات هماً",
    "العجلة من الشيطان", "الحاجة أم الاختراع",
    "من تكبر على الناس ذل", "ما كل ما يتمنى المرء يدركه",
    "القرش الأبيض ينفع في اليوم الأسود", "يد واحدة لا تصفق", "الحب أعمى"
]

TYPING_SENTENCES_EN = [
    "The quick brown fox jumps over the lazy dog",
    "A journey of a thousand miles begins with a single step",
    "Actions speak louder than words", "All that glitters is not gold",
    "Better late than never", "Don't count your chickens before they hatch",
    "Every cloud has a silver lining", "Fortune favors the bold",
    "Knowledge is power", "Practice makes perfect",
    "Time is money", "Where there's a will there's a way",
    "You can't judge a book by its cover", "Honesty is the best policy",
    "Laughter is the best medicine"
]

TYPING_SENTENCES_FA = [
    "زندگی زیباست", "آب رفته به جوی باز نمی‌گردد",
    "از تو حرکت از خدا برکت", "بادآورده را باد می‌برد",
    "تا نباشد چیزکی مردم نگویند چیزها", "جوجه را آخر پاییز می‌شمارند",
    "خواستن توانستن است", "دوست آن است که گیرد دست دوست",
    "رطب خورده منع رطب چون کند", "سالی که نکوست از بهارش پیداست",
    "شیر بی‌یال و دم و اشکم که دید", "عقل سالم در بدن سالم است",
    "قدر زر زرگر شناسد قدر گوهر گوهری", "کاچی بهتر از هیچی",
    "ماهی را هر وقت از آب بگیری تازه است"
]

SCRAMBLE_WORDS_AR = ["تفاحة", "كمبيوتر", "هرم", "شمس", "قمر", "مدرسة", "كتاب", "بحر", "سماء", "نجمة", "وردة", "أسد", "نمر", "فيل", "زرافة", "بطريق", "تلفاز", "ثلاجة", "سيارة", "طائرة"]
SCRAMBLE_WORDS_EN = ["apple", "computer", "pyramid", "sun", "moon", "school", "book", "sea", "sky", "star", "flower", "lion", "tiger", "elephant", "giraffe", "penguin", "television", "refrigerator", "car", "airplane"]
SCRAMBLE_WORDS_FA = ["سیب", "کامپیوتر", "هرم", "خورشید", "ماه", "مدرسه", "کتاب", "دریا", "آسمان", "ستاره", "گل", "شیر", "ببر", "فیل", "زرافه", "پنگوئن", "تلویزیون", "یخچال", "ماشین", "هواپیما"]

COUNTRIES_AR = {"مصر": "القاهرة", "السعودية": "الرياض", "الإمارات": "أبوظبي", "المغرب": "الرباط", "الجزائر": "الجزائر", "تونس": "تونس", "لبنان": "بيروت", "الأردن": "عمان", "الكويت": "الكويت", "قطر": "الدوحة", "البحرين": "المنامة", "عمان": "مسقط", "اليمن": "صنعاء", "سوريا": "دمشق", "العراق": "بغداد", "فلسطين": "القدس", "ليبيا": "طرابلس", "السودان": "الخرطوم", "موريتانيا": "نواكشوط", "الصومال": "مقديشو"}
COUNTRIES_EN = {"Egypt": "Cairo", "Saudi Arabia": "Riyadh", "UAE": "Abu Dhabi", "Morocco": "Rabat", "Algeria": "Algiers", "Tunisia": "Tunis", "Lebanon": "Beirut", "Jordan": "Amman", "Kuwait": "Kuwait City", "Qatar": "Doha", "Bahrain": "Manama", "Oman": "Muscat", "Yemen": "Sana'a", "Syria": "Damascus", "Iraq": "Baghdad", "Palestine": "Jerusalem", "Libya": "Tripoli", "Sudan": "Khartoum", "Mauritania": "Nouakchott", "Somalia": "Mogadishu"}
COUNTRIES_FA = {"مصر": "قاهره", "عربستان سعودی": "ریاض", "امارات": "ابوظبی", "مراکش": "رباط", "الجزایر": "الجزیره", "تونس": "تونس", "لبنان": "بیروت", "اردن": "امان", "کویت": "کویت", "قطر": "دوحه", "بحرین": "منامه", "عمان": "مسقط", "یمن": "صنعا", "سوریه": "دمشق", "عراق": "بغداد", "فلسطین": "قدس", "لیبی": "طرابلس", "سودان": "خرطوم", "موریتانی": "نواکشوت", "سومالی": "مقدیشو"}

PROVERBS_AR = {"اللي استحوا": "ماتوا", "اللي بيته من قزاز": "لا يرمي الناس بالطوب", "القرد في عين أمه": "غزال", "إدي العيش لخبازه": "ولو أكل نصه", "جاجة حفرت على راسها": "عفرت", "الباب اللي يجيلك منه الريح": "سده واستريح", "اللي ما يعرف الصقر": "يشويه", "إن غاب القط": "العب يا فار", "عصفور في اليد": "خير من عشرة على الشجرة", "من شب على شيء": "شاب عليه", "اللي ما يطول العنب": "يقول حامض", "اتق شر": "من أحسنت إليه", "ما حك جلدك": "مثل ظفرك", "إذا كان حبيبك عسل": "ما تلحسه كله", "الطول طول نخلة": "والعقل عقل صخلة"}

OPPOSITES_AR = {"كبير": "صغير", "طويل": "قصير", "جميل": "قبيح", "سريع": "بطيء", "قوي": "ضعيف", "غني": "فقير", "حار": "بارد", "ناعم": "خشن", "ذكي": "غبي", "شجاع": "جبان", "كريم": "بخيل", "واسع": "ضيق", "مرتفع": "منخفض", "نظيف": "قذر", "هادئ": "مزعج", "ثقيل": "خفيف", "مشرق": "مظلم", "جديد": "قديم", "حي": "ميت", "مبتسم": "عابس"}
OPPOSITES_EN = {"big": "small", "long": "short", "beautiful": "ugly", "fast": "slow", "strong": "weak", "rich": "poor", "hot": "cold", "soft": "rough", "smart": "stupid", "brave": "coward", "generous": "stingy", "wide": "narrow", "high": "low", "clean": "dirty", "quiet": "noisy", "heavy": "light", "bright": "dark", "new": "old", "alive": "dead", "smiling": "frowning"}
OPPOSITES_FA = {"بزرگ": "کوچک", "بلند": "کوتاه", "زیبا": "زشت", "سریع": "کند", "قوی": "ضعیف", "غنی": "فقیر", "گرم": "سرد", "نرم": "زبر", "باهوش": "احمق", "شجاع": "ترسو", "سخاوتمند": "خسیس", "عریض": "باریک", "مرتفع": "پایین", "تمیز": "کثیف", "آرام": "شلوغ", "سنگین": "سبک", "روشن": "تاریک", "نو": "قدیمی", "زنده": "مرده", "خندان": "اخمو"}

FAST_WORDS_AR = ["أسد", "وردة", "سماء", "كرة", "بحر", "قلم", "نجم", "شجرة", "تفاحة", "قمر", "شمس", "جبل", "نهر", "طائر", "سمكة", "زهرة", "مطر", "ريح", "ثلج", "نار"]
FAST_WORDS_EN = ["lion", "flower", "sky", "ball", "sea", "pen", "star", "tree", "apple", "moon", "sun", "mountain", "river", "bird", "fish", "rain", "wind", "snow", "fire", "book"]
FAST_WORDS_FA = ["شیر", "گل", "آسمان", "توپ", "دریا", "قلم", "ستاره", "درخت", "سیب", "ماه", "خورشید", "کوه", "رود", "پرنده", "ماهی", "باران", "باد", "برف", "آتش", "کتاب"]

TRIVIA_AR = {"ما هي أكبر قارة في العالم؟": "آسيا", "ما هو أطول نهر في العالم؟": "النيل", "كم عدد ألوان قوس قزح؟": "7", "ما هو الكوكب الأحمر؟": "المريخ", "من هو مخترع المصباح الكهربائي؟": "إديسون", "ما هي أصغر قارة في العالم؟": "أستراليا", "كم عدد عظام جسم الإنسان؟": "206", "ما هو أسرع حيوان بري؟": "الفهد", "ما هي عاصمة اليابان؟": "طوكيو", "من هو مكتشف الجاذبية؟": "نيوتن", "كم عدد الكواكب في المجموعة الشمسية؟": "8", "ما هو البحر الأكثر ملوحة؟": "البحر الميت", "كم عدد السور في القرآن؟": "114", "من هي أم المؤمنين الأولى؟": "خديجة", "كم عدد الأرجل عند الأخطبوط؟": "8"}
TRIVIA_EN = {"What is the largest continent?": "Asia", "What is the longest river?": "Nile", "How many colors in a rainbow?": "7", "What is the red planet?": "Mars", "Who invented the light bulb?": "Edison", "What is the smallest continent?": "Australia", "How many bones in the human body?": "206", "What is the fastest land animal?": "cheetah", "What is the capital of Japan?": "Tokyo", "Who discovered gravity?": "Newton", "How many planets in the solar system?": "8", "What is the saltiest sea?": "Dead Sea", "How many chapters in the Quran?": "114", "Who was the first wife of the Prophet?": "Khadija", "How many legs does an octopus have?": "8"}
TRIVIA_FA = {"بزرگترین قاره جهان چیست؟": "آسیا", "طولانی‌ترین رود جهان چیست؟": "نیل", "رنگین کمان چند رنگ دارد؟": "7", "سیاره سرخ کدام است؟": "مریخ", "مخترع لامپ کیست؟": "ادیسون", "کوچکترین قاره جهان چیست؟": "استرالیا", "بدن انسان چند استخوان دارد؟": "206", "سریع‌ترین حیوان خشکی چیست؟": "یوزپلنگ", "پایتخت ژاپن چیست؟": "توکیو", "کاشف جاذبه کیست؟": "نیوتن", "منظومه شمسی چند سیاره دارد؟": "8", "شورترین دریا کدام است؟": "دریای مرده", "قرآن چند سوره دارد؟": "114", "اولین همسر پیامبر که بود؟": "خدیجه", "اختاپوس چند پا دارد؟": "8"}

RIDDLES_AR = {"ما هو الشيء الذي يمشي بلا رجلين ويبكي بلا عينين؟": "السحاب", "ما هو الشيء الذي كلما أخذت منه كبر؟": "الحفرة", "ما هو الشيء الذي له أسنان ولا يعض؟": "المشط", "ما هو الشيء الذي يكتب ولا يقرأ؟": "القلم", "ما هو الشيء الذي يسمع بلا أذن ويتكلم بلا لسان؟": "الهاتف", "ما هو الشيء الذي يرى كل شيء ولا عيون له؟": "المرآة", "ما هو الشيء الذي يحمل أكثر من 1000 طن ولا يحمل مسماراً؟": "البحر", "ما هو الشيء الذي إذا دخل الماء تشتت؟": "الورق", "ما هو الشيء الذي له رأس ولا عيون؟": "الدبوس", "ما هو الشيء الذي يلف حول الغرفة ولا يتحرك؟": "الحائط", "ما هو الشيء الذي ينام بحذائه؟": "الحصان", "ما هو الشيء الذي يقرصك ولا تراه؟": "الجوع", "ما هو الشيء الذي يكسو الناس وهو عارٍ؟": "الإبرة", "ما هو الشيء الذي له رقبة وليس له رأس؟": "القنينة", "ما هو الشيء الذي يأكل ولا يشبع؟": "النار"}
RIDDLES_EN = {"What has legs but doesn't walk?": "table", "What gets wetter the more it dries?": "towel", "What has teeth but can't bite?": "comb", "What has words but never speaks?": "book", "What has an ear but can't hear?": "corn", "What has eyes but can't see?": "needle", "What can carry a thousand tons but not a nail?": "sea", "What disappears when you put it in water?": "paper", "What has a head but no eyes?": "pin", "What goes around the room without moving?": "wall", "What sleeps with its shoes on?": "horse", "What bites without teeth?": "hunger", "What clothes people but is naked itself?": "needle", "What has a neck but no head?": "bottle", "What eats but never gets full?": "fire"}
RIDDLES_FA = {"آن چیست که پا دارد اما راه نمی‌رود؟": "میز", "آن چیست که هر چه خشک‌تر می‌شود خیس‌تر می‌شود؟": "حوله", "آن چیست که دندان دارد اما گاز نمی‌گیرد؟": "شانه", "آن چیست که کلمه دارد اما حرف نمی‌زند؟": "کتاب", "آن چیست که گوش دارد اما نمی‌شنود؟": "ذرت", "آن چیست که چشم دارد اما نمی‌بیند؟": "سوزن", "آن چیست که هزار تن بار می‌برد اما میخ را نمی‌برد؟": "دریا", "آن چیست که در آب ناپدید می‌شود؟": "کاغذ", "آن چیست که سر دارد اما چشم ندارد؟": "سنجاق", "آن چیست که دور اتاق می‌چرخد اما حرکت نمی‌کند؟": "دیوار", "آن چیست که با کفش‌هایش می‌خوابد؟": "اسب", "آن چیست که بدون دندان گاز می‌گیرد؟": "گرسنگی", "آن چیست که مردم را می‌پوشاند اما خودش عریان است؟": "سوزن", "آن چیست که گردن دارد اما سر ندارد؟": "بطری", "آن چیست که می‌خورد اما سیر نمی‌شود؟": "آتش"}

TRANSLATE_WORDS_AR = {"Book": "كتاب", "Sun": "شمس", "Moon": "قمر", "Water": "ماء", "Fire": "نار", "Tree": "شجرة", "Star": "نجم", "Heart": "قلب", "Sky": "سماء", "River": "نهر", "Mountain": "جبل", "Flower": "زهرة", "Rain": "مطر", "Snow": "ثلج", "Wind": "ريح", "Light": "ضوء", "Darkness": "ظلام", "Love": "حب", "Peace": "سلام", "War": "حرب"}
TRANSLATE_WORDS_EN = {"كتاب": "Book", "شمس": "Sun", "قمر": "Moon", "ماء": "Water", "نار": "Fire", "شجرة": "Tree", "نجم": "Star", "قلب": "Heart", "سماء": "Sky", "نهر": "River", "جبل": "Mountain", "زهرة": "Flower", "مطر": "Rain", "ثلج": "Snow", "ريح": "Wind", "ضوء": "Light", "ظلام": "Darkness", "حب": "Love", "سلام": "Peace", "حرب": "War"}
TRANSLATE_WORDS_FA = {"کتاب": "Book", "خورشید": "Sun", "ماه": "Moon", "آب": "Water", "آتش": "Fire", "درخت": "Tree", "ستاره": "Star", "قلب": "Heart", "آسمان": "Sky", "رود": "River", "کوه": "Mountain", "گل": "Flower", "باران": "Rain", "برف": "Snow", "باد": "Wind", "نور": "Light", "تاریکی": "Darkness", "عشق": "Love", "صلح": "Peace", "جنگ": "War"}

EMOJI_GUESS_AR = {"🦁👑": "الأسد الملك", "🚢💥🧊": "تيتانيك", "🧙‍♂️⚡🏰": "هاري بوتر", "🕷️🦸‍♂️": "سبايدر مان", "👻🚫": "صائدو الأشباح", "🦖🏞️": "الحديقة الجوراسية", "🧸🎈": "تيد", "🚀🌙": "أبولو 13", "🐟🔍": "البحث عن نيمو", "🤖🌿": "والي", "🏎️⚡": "سيارات", "👸❄️": "ملكة الثلج", "🐉🥋": "كونغ فو باندا", "🕵️‍♂️🔍": "شارلوك هولمز", "🧞‍♂️🪔": "علاء الدين", "🐒🌴👑": "طرزان", "🐭👨‍🍳": "راتاتوي", "👹👸": "الجميلة والوحش", "🦸‍♂️🛡️": "كابتن أمريكا"}
EMOJI_GUESS_EN = {"🦁👑": "Lion King", "🚢💥🧊": "Titanic", "🧙‍♂️⚡🏰": "Harry Potter", "🕷️🦸‍♂️": "Spiderman", "👻🚫": "Ghostbusters", "🦖🏞️": "Jurassic Park", "🧸🎈": "Ted", "🚀🌙": "Apollo 13", "🐟🔍": "Finding Nemo", "🤖🌿": "WALL-E", "🏎️⚡": "Cars", "👸❄️": "Frozen", "🐉🥋": "Kung Fu Panda", "🕵️‍♂️🔍": "Sherlock Holmes", "🧞‍♂️🪔": "Aladdin", "🐒🌴👑": "Tarzan", "🐭👨‍🍳": "Ratatouille", "👹👸": "Beauty and the Beast", "🦸‍♂️🛡️": "Captain America"}
EMOJI_GUESS_FA = {"🦁👑": "شیر شاه", "🚢💥🧊": "تایتانیک", "🧙‍♂️⚡🏰": "هری پاتر", "🕷️🦸‍♂️": "اسپایدرمن", "👻🚫": "شکارچیان روح", "🦖🏞️": "پارک ژوراسیک", "🧸🎈": "تد", "🚀🌙": "آپولو 13", "🐟🔍": "در جستجوی نمو", "🤖🌿": "وال-ای", "🏎️⚡": "ماشین‌ها", "👸❄️": "یخزده", "🐉🥋": "پاندای کونگ‌فوکار", "🕵️‍♂️🔍": "شرلوک هلمز", "🧞‍♂️🪔": "علاءالدین", "🐒🌴👑": "تارزان", "🐭👨‍🍳": "راتاتویی", "👹👸": "دیو و دلبر", "🦸‍♂️🛡️": "کاپیتان آمریکا"}

DIALECTS_AR = {"شنو معنى كلمة 'دريوي' في اللهجة المغربية؟": "شخص لطيف", "ما معنى 'قوطي' في اللهجة العراقية؟": "علبة", "إيش تعني 'يديني' في اللهجة السعودية؟": "يعطيني", "ما معنى 'كشخة' في اللهجة الكويتية؟": "أنيق", "شنو 'البلوك' في اللهجة التونسية؟": "الحي", "ما معنى 'بزاف' في اللهجة الجزائرية؟": "كثير", "إيش 'صهيوني' في اللهجة اليمنية؟": "جميل", "ما معنى 'طرشي' في اللهجة البحرينية؟": "طرش البحر", "شنو 'البسباس' في اللهجة الليبية؟": "الفلفل", "ما معنى 'دشّر' في اللهجة السودانية؟": "اترك", "إيش 'كزدورة' في اللهجة الأردنية؟": "نزهة", "شنو 'شحال' في اللهجة المغربية؟": "كم", "ما معنى 'خاشوقة' في اللهجة العراقية؟": "ملعقة", "إيش 'مصرقع' في اللهجة السعودية؟": "مجنون", "ما معنى 'قفشة' في اللهجة المصرية؟": "نكتة"}

CROSSWORD_AR = {"ما هو الشيء الذي يمشي بلا رجلين ويطير بلا أجنحة؟": "الوقت", "ما هو الشيء الذي كلما زاد نقص؟": "العمر", "ما هو الشيء الذي له أوراق وليس شجرة؟": "الكتاب", "ما هو الشيء الذي له عين ولا يرى؟": "الإبرة", "ما هو الشيء الذي يخترق الزجاج ولا يكسره؟": "الضوء", "ما هو الشيء الذي يحملك وتحمله في نفس الوقت؟": "الحذاء", "ما هو الشيء الذي تأكل منه وهو لا يؤكل؟": "الطبق", "ما هو الشيء الذي يموت إذا وضع في الماء؟": "النار", "ما هو الشيء الذي يسير بلا رجلين؟": "السفينة", "ما هو الشيء الذي له فروع وليس شجرة؟": "النهر", "ما هو الشيء الذي يذوب في الشمس؟": "الثلج", "ما هو الشيء الذي يكبر بالضرب؟": "المسمار", "ما هو الشيء الذي لا يمشي إلا بالضرب؟": "الكرة", "ما هو الشيء الذي يبكي بلا عينين؟": "السحاب", "ما هو الشيء الذي يزيد بالاستعمال؟": "العقل"}

FOOD_CHAIN_AR = {"ماذا يأكل الأسد؟": "اللحم", "ماذا تأكل البقرة؟": "العشب", "ماذا يأكل الدب؟": "السمك", "ماذا يأكل النسر؟": "الأرانب", "ماذا يأكل القرش؟": "الأسماك", "ماذا تأكل الزرافة؟": "أوراق الشجر", "ماذا يأكل الثعبان؟": "الفئران", "ماذا يأكل البطريق؟": "الأسماك", "ماذا يأكل الضفدع؟": "الحشرات", "ماذا تأكل النحلة؟": "الرحيق", "ماذا يأكل الذئب؟": "الغزلان", "ماذا يأكل التمساح؟": "اللحم", "ماذا تأكل القطة؟": "الفئران", "ماذا يأكل البومة؟": "الفئران", "ماذا يأكل الدلفين؟": "الأسماك"}
FOOD_CHAIN_EN = {"What does a lion eat?": "meat", "What does a cow eat?": "grass", "What does a bear eat?": "fish", "What does an eagle eat?": "rabbits", "What does a shark eat?": "fish", "What does a giraffe eat?": "leaves", "What does a snake eat?": "mice", "What does a penguin eat?": "fish", "What does a frog eat?": "insects", "What does a bee eat?": "nectar", "What does a wolf eat?": "deer", "What does a crocodile eat?": "meat", "What does a cat eat?": "mice", "What does an owl eat?": "mice", "What does a dolphin eat?": "fish"}
FOOD_CHAIN_FA = {"شیر چه می‌خورد؟": "گوشت", "گاو چه می‌خورد؟": "علف", "خرس چه می‌خورد؟": "ماهی", "عقاب چه می‌خورد؟": "خرگوش", "کوسه چه می‌خورد؟": "ماهی", "زرافه چه می‌خورد؟": "برگ", "مار چه می‌خورد؟": "موش", "پنگوئن چه می‌خورد؟": "ماهی", "قورباغه چه می‌خورد؟": "حشرات", "زنبور چه می‌خورد؟": "شهد", "گرگ چه می‌خورد؟": "گوزن", "تمساح چه می‌خورد؟": "گوشت", "گربه چه می‌خورد؟": "موش", "جغد چه می‌خورد؟": "موش", "دلفین چه می‌خورد؟": "ماهی"}

MATH_PUZZLES_AR = {"ما هو العدد الذي إذا ضربته في نفسه وأضفت 5 يصبح 30؟": "5", "ما هو العدد الذي إذا قسمته على 2 وأضفت 3 يصبح 10؟": "14", "ما هو العدد الذي إذا ضربته في 3 وطرحت 7 يصبح 20؟": "9", "ما هو العدد الذي إذا أضفت إليه 15 يصبح 40؟": "25", "ما هو العدد الذي نصفه ثلثه؟": "0", "ما هو العدد الذي ربعه يساوي 5؟": "20", "ما هو العدد الذي 20% منه يساوي 10؟": "50", "ما هو العدد الذي إذا ضربته في 4 كان الناتج 48؟": "12", "ما هو العدد الذي إذا طرحته من 100 كان الناتج 65؟": "35", "ما هو العدد الذي 3 أضعافه زائد 8 يساوي 32؟": "8", "ما هو العدد الذي إذا قسمته على 5 كان الناتج 7؟": "35", "ما هو العدد الذي 10% منه يساوي 5؟": "50", "ما هو العدد الذي مربعه 144؟": "12", "ما هو العدد الذي جذره التربيعي 9؟": "81", "ما هو العدد الذي 7 أضعافه تساوي 63؟": "9"}
MATH_PUZZLES_EN = {"What number multiplied by itself plus 5 equals 30?": "5", "What number divided by 2 plus 3 equals 10?": "14", "What number multiplied by 3 minus 7 equals 20?": "9", "What number plus 15 equals 40?": "25", "What number is half of its third?": "0", "What number's quarter equals 5?": "20", "What number is 20% of 50?": "10", "What number times 4 equals 48?": "12", "What number subtracted from 100 equals 65?": "35", "What number times 3 plus 8 equals 32?": "8", "What number divided by 5 equals 7?": "35", "What number's 10% equals 5?": "50", "What number squared equals 144?": "12", "What number's square root is 9?": "81", "What number times 7 equals 63?": "9"}
MATH_PUZZLES_FA = {"کدام عدد ضرب در خودش به اضافه ۵ مساوی ۳۰ می‌شود؟": "5", "کدام عدد تقسیم بر ۲ به اضافه ۳ مساوی ۱۰ می‌شود؟": "14", "کدام عدد ضرب در ۳ منهای ۷ مساوی ۲۰ می‌شود؟": "9", "کدام عدد به اضافه ۱۵ مساوی ۴۰ می‌شود؟": "25", "کدام عدد نصفش ثلثش است؟": "0", "کدام عدد یک چهارمش مساوی ۵ است؟": "20", "کدام عدد ۲۰ درصدش مساوی ۱۰ است؟": "50", "کدام عدد ضرب در ۴ مساوی ۴۸ می‌شود؟": "12", "کدام عدد از ۱۰۰ کم شود ۶۵ می‌ماند؟": "35", "کدام عدد ۳ برابرش به اضافه ۸ مساوی ۳۲ است؟": "8", "کدام عدد تقسیم بر ۵ مساوی ۷ می‌شود؟": "35", "کدام عدد ۱۰ درصدش مساوی ۵ است؟": "50", "کدام عدد مربعش ۱۴۴ است؟": "12", "کدام عدد ریشه دومش ۹ است؟": "81", "کدام عدد ۷ برابرش مساوی ۶۳ است؟": "9"}

LOGIC_PUZZLES_AR = {"ما هو الشيء الذي تراه في الليل ولا تراه في النهار؟": "القمر", "ما هو الشيء الذي يدخل الماء ولا يبتل؟": "الضوء", "ما هو الشيء الذي يزيد كلما أخذنا منه؟": "الحفرة", "ما هو الشيء الذي لا يسير إلا بالضرب؟": "المسمار", "ما هو الشيء الذي كلما كثر لدينا قل سعره؟": "الذهب", "ما هو الشيء الذي يكتب ولا يقرأ؟": "القلم", "ما هو الشيء الذي يحمل قنطاراً ولا يحمل مسماراً؟": "السفينة", "ما هو الشيء الذي يخترق البيوت دون استئذان؟": "الهواء", "ما هو الشيء الذي يضحك بلا فم؟": "المرآة", "ما هو الشيء الذي إذا غليته جمد؟": "البيض", "ما هو الشيء الذي يزرع مرة ويحصد كل سنة؟": "الشجرة", "ما هو الشيء الذي له وجه بلا لسان؟": "الساعة", "ما هو الشيء الذي يحرق نفسه لينير للآخرين؟": "الشمعة", "ما هو الشيء الذي يجري ولا يمشي؟": "الماء", "ما هو الشيء الذي له أجنحة ولا يطير؟": "الطائرة الورقية"}
LOGIC_PUZZLES_EN = {"What do you see at night but not during the day?": "moon", "What goes in water but doesn't get wet?": "light", "What gets bigger the more you take from it?": "hole", "What only works when hit?": "nail", "What becomes cheaper the more you have?": "gold", "What writes but can't read?": "pen", "What carries tons but not a nail?": "ship", "What enters houses without permission?": "air", "What smiles without a mouth?": "mirror", "What hardens when boiled?": "egg", "What is planted once and harvested yearly?": "tree", "What has a face but no tongue?": "clock", "What burns itself to give light?": "candle", "What runs but doesn't walk?": "water", "What has wings but can't fly?": "kite"}
LOGIC_PUZZLES_FA = {"آن چیست که شب می‌بینی اما روز نمی‌بینی؟": "ماه", "آن چیست که داخل آب می‌رود اما خیس نمی‌شود؟": "نور", "آن چیست که هر چه از آن برداری بزرگتر می‌شود؟": "چاله", "آن چیست که فقط با ضربه کار می‌کند؟": "میخ", "آن چیست که هر چه بیشتر داشته باشی ارزانتر می‌شود؟": "طلا", "آن چیست که می‌نویسد اما نمی‌خواند؟": "قلم", "آن چیست که تن‌ها بار می‌برد اما میخ را نمی‌برد؟": "کشتی", "آن چیست که بدون اجازه وارد خانه‌ها می‌شود؟": "هوا", "آن چیست که بدون دهان می‌خندد؟": "آینه", "آن چیست که با جوشاندن سفت می‌شود؟": "تخم مرغ", "آن چیست که یک بار کاشته می‌شود و هر سال برداشت می‌شود؟": "درخت", "آن چیست که صورت دارد اما زبان ندارد؟": "ساعت", "آن چیست که خود را می‌سوزاند تا به دیگران نور دهد؟": "شمع", "آن چیست که می‌دود اما راه نمی‌رود؟": "آب", "آن چیست که بال دارد اما پرواز نمی‌کند؟": "بادبادک"}

MISSING_WORDS_AR = {"أكمل الجملة: الشمس تشرق من ...": "الشرق", "أكمل الجملة: البحر ...": "أزرق", "أكمل الجملة: القطة ...": "تموء", "أكمل الجملة: السماء ...": "صافية", "أكمل الجملة: الطائر ...": "يطير", "أكمل الجملة: الطفل ...": "يلعب", "أكمل الجملة: الجبل ...": "شاهق", "أكمل الجملة: النار ...": "تحرق", "أكمل الجملة: الماء ...": "يجري", "أكمل الجملة: القمر ...": "يضيء", "أكمل الجملة: الورد ...": "جميل", "أكمل الجملة: العسل ...": "حلو", "أكمل الجملة: الكلب ...": "ينبح", "أكمل الجملة: الرياح ...": "تهب", "أكمل الجملة: الثلج ...": "يذوب"}
MISSING_WORDS_EN = {"Complete: The sun rises in the ...": "east", "Complete: The sea is ...": "blue", "Complete: The cat ...": "meows", "Complete: The sky is ...": "clear", "Complete: The bird ...": "flies", "Complete: The child ...": "plays", "Complete: The mountain is ...": "high", "Complete: The fire ...": "burns", "Complete: The water ...": "flows", "Complete: The moon ...": "shines", "Complete: The flower is ...": "beautiful", "Complete: The honey is ...": "sweet", "Complete: The dog ...": "barks", "Complete: The wind ...": "blows", "Complete: The snow ...": "melts"}
MISSING_WORDS_FA = {"کامل کن: خورشید از ... طلوع می‌کند": "شرق", "کامل کن: دریا ... است": "آبی", "کامل کن: گربه ... می‌کند": "میو", "کامل کن: آسمان ... است": "صاف", "کامل کن: پرنده ... می‌کند": "پرواز", "کامل کن: کودک ... می‌کند": "بازی", "کامل کن: کوه ... است": "بلند", "کامل کن: آتش ... می‌زند": "می‌سوزد", "کامل کن: آب ... می‌کند": "جریان", "کامل کن: ماه ... می‌کند": "می‌درخشد", "کامل کن: گل ... است": "زیبا", "کامل کن: عسل ... است": "شیرین", "کامل کن: سگ ... می‌کند": "پارس", "کامل کن: باد ... می‌کند": "می‌وزد", "کامل کن: برف ... می‌شود": "آب"}

SHAPES_AR = {"ما هو الشكل الذي له 3 أضلاع؟": "مثلث", "ما هو الشكل الذي له 4 أضلاع متساوية؟": "مربع", "ما هو الشكل الذي له 5 أضلاع؟": "مخمس", "ما هو الشكل الذي ليس له أضلاع؟": "دائرة", "ما هو الشكل الذي له 6 أضلاع؟": "مسدس", "ما هو الشكل الذي له 8 أضلاع؟": "مثمن", "ما هو الشكل الذي له 4 أضلاع متوازية؟": "متوازي أضلاع", "ما هو الشكل الذي له زاوية قائمة واحدة؟": "مثلث قائم", "ما هو الشكل الذي له قطران متساويان؟": "مربع", "ما هو الشكل الذي مساحته الطول × العرض؟": "مستطيل", "ما هو الشكل الذي له 7 أضلاع؟": "مسبع", "ما هو الشكل الذي زواياه 360 درجة؟": "دائرة", "ما هو الشكل الذي له 10 أضلاع؟": "معشر", "ما هو الشكل الذي أضلاعه غير متساوية؟": "مثلث مختلف الأضلاع", "ما هو الشكل المكون من 4 مثلثات؟": "هرم"}
SHAPES_EN = {"What shape has 3 sides?": "triangle", "What shape has 4 equal sides?": "square", "What shape has 5 sides?": "pentagon", "What shape has no sides?": "circle", "What shape has 6 sides?": "hexagon", "What shape has 8 sides?": "octagon", "What shape has 4 parallel sides?": "parallelogram", "What shape has one right angle?": "right triangle", "What shape has equal diagonals?": "square", "What shape's area is length × width?": "rectangle", "What shape has 7 sides?": "heptagon", "What shape has 360 degrees?": "circle", "What shape has 10 sides?": "decagon", "What shape has unequal sides?": "scalene triangle", "What shape is made of 4 triangles?": "pyramid"}
SHAPES_FA = {"کدام شکل ۳ ضلع دارد؟": "مثلث", "کدام شکل ۴ ضلع مساوی دارد؟": "مربع", "کدام شکل ۵ ضلع دارد؟": "پنج‌ضلعی", "کدام شکل ضلع ندارد؟": "دایره", "کدام شکل ۶ ضلع دارد؟": "شش‌ضلعی", "کدام شکل ۸ ضلع دارد؟": "هشت‌ضلعی", "کدام شکل ۴ ضلع موازی دارد؟": "متوازی‌الاضلاع", "کدام شکل یک زاویه قائمه دارد؟": "مثلث قائم‌الزاویه", "کدام شکل قطرهای مساوی دارد؟": "مربع", "مساحت کدام شکل طول × عرض است؟": "مستطیل", "کدام شکل ۷ ضلع دارد؟": "هفت‌ضلعی", "کدام شکل ۳۶۰ درجه دارد؟": "دایره", "کدام شکل ۱۰ ضلع دارد؟": "ده‌ضلعی", "کدام شکل اضلاع نامساوی دارد؟": "مثلث مختلف‌الاضلاع", "کدام شکل از ۴ مثلث ساخته شده؟": "هرم"}

HISTORY_DATES_AR = {"في أي عام سقطت الخلافة العثمانية؟": "1924", "في أي عام كانت الثورة الفرنسية؟": "1789", "في أي عام انتهت الحرب العالمية الأولى؟": "1918", "في أي عام انتهت الحرب العالمية الثانية؟": "1945", "في أي عام سقطت الأندلس؟": "1492", "في أي عام اكتشفت أمريكا؟": "1492", "في أي عام قامت الثورة الجزائرية؟": "1954", "في أي عام استقلت مصر؟": "1952", "في أي عام تأسست الأمم المتحدة؟": "1945", "في أي عام هبط الإنسان على القمر؟": "1969", "في أي عام بدأت الثورة السورية؟": "2011", "في أي عام وقعت معركة حطين؟": "1187", "في أي عام فتحت القسطنطينية؟": "1453", "في أي عام استقلت تونس؟": "1956", "في أي عام تأسست المملكة العربية السعودية؟": "1932"}
HISTORY_DATES_EN = {"When did the Ottoman Empire fall?": "1924", "When was the French Revolution?": "1789", "When did WWI end?": "1918", "When did WWII end?": "1945", "When did Andalusia fall?": "1492", "When was America discovered?": "1492", "When was the Algerian Revolution?": "1954", "When did Egypt gain independence?": "1952", "When was the UN founded?": "1945", "When did man land on the moon?": "1969", "When did the Syrian revolution start?": "2011", "When was the Battle of Hattin?": "1187", "When was Constantinople conquered?": "1453", "When did Tunisia gain independence?": "1956", "When was Saudi Arabia founded?": "1932"}
HISTORY_DATES_FA = {"امپراتوری عثمانی در چه سالی سقوط کرد؟": "1924", "انقلاب فرانسه در چه سالی بود؟": "1789", "جنگ جهانی اول در چه سالی تمام شد؟": "1918", "جنگ جهانی دوم در چه سالی تمام شد؟": "1945", "اندلس در چه سالی سقوط کرد؟": "1492", "آمریکا در چه سالی کشف شد؟": "1492", "انقلاب الجزایر در چه سالی بود؟": "1954", "مصر در چه سالی مستقل شد؟": "1952", "سازمان ملل در چه سالی تاسیس شد؟": "1945", "انسان در چه سالی به ماه رفت؟": "1969", "انقلاب سوریه در چه سالی شروع شد؟": "2011", "نبرد حطین در چه سالی بود؟": "1187", "قسطنطنیه در چه سالی فتح شد؟": "1453", "تونس در چه سالی مستقل شد؟": "1956", "عربستان سعودی در چه سالی تاسیس شد؟": "1932"}

NEW_CAPITALS_AR = {"عاصمة أستراليا؟": "كانبرا", "عاصمة البرازيل؟": "برازيليا", "عاصمة كندا؟": "أوتاوا", "عاصمة الهند؟": "نيودلهي", "عاصمة الصين؟": "بكين", "عاصمة روسيا؟": "موسكو", "عاصمة جنوب أفريقيا؟": "بريتوريا", "عاصمة الأرجنتين؟": "بوينس آيرس", "عاصمة تركيا؟": "أنقرة", "عاصمة إيران؟": "طهران", "عاصمة باكستان؟": "إسلام أباد", "عاصمة نيجيريا؟": "أبوجا", "عاصمة كينيا؟": "نيروبي", "عاصمة ماليزيا؟": "كوالالمبور", "عاصمة الفلبين؟": "مانيلا", "عاصمة تشيلي؟": "سانتياغو", "عاصمة اليونان؟": "أثينا", "عاصمة النرويج؟": "أوسلو", "عاصمة السويد؟": "ستوكهولم", "عاصمة فنلندا؟": "هلسنكي"}
NEW_CAPITALS_EN = {"Capital of Australia?": "Canberra", "Capital of Brazil?": "Brasilia", "Capital of Canada?": "Ottawa", "Capital of India?": "New Delhi", "Capital of China?": "Beijing", "Capital of Russia?": "Moscow", "Capital of South Africa?": "Pretoria", "Capital of Argentina?": "Buenos Aires", "Capital of Turkey?": "Ankara", "Capital of Iran?": "Tehran", "Capital of Pakistan?": "Islamabad", "Capital of Nigeria?": "Abuja", "Capital of Kenya?": "Nairobi", "Capital of Malaysia?": "Kuala Lumpur", "Capital of Philippines?": "Manila", "Capital of Chile?": "Santiago", "Capital of Greece?": "Athens", "Capital of Norway?": "Oslo", "Capital of Sweden?": "Stockholm", "Capital of Finland?": "Helsinki"}
NEW_CAPITALS_FA = {"پایتخت استرالیا؟": "کانبرا", "پایتخت برزیل؟": "برازیلیا", "پایتخت کانادا؟": "اتاوا", "پایتخت هند؟": "دهلی نو", "پایتخت چین؟": "پکن", "پایتخت روسیه؟": "مسکو", "پایتخت آفریقای جنوبی؟": "پرتوریا", "پایتخت آرژانتین؟": "بوینس آیرس", "پایتخت ترکیه؟": "آنکارا", "پایتخت ایران؟": "تهران", "پایتخت پاکستان؟": "اسلام‌آباد", "پایتخت نیجریه؟": "آبوجا", "پایتخت کنیا؟": "نایروبی", "پایتخت مالزی؟": "کوالالامپور", "پایتخت فیلیپین؟": "مانیل", "پایتخت شیلی؟": "سانتیاگو", "پایتخت یونان؟": "آتن", "پایتخت نروژ؟": "اسلو", "پایتخت سوئد؟": "استکهلم", "پایتخت فنلاند؟": "هلسینکی"}

CHEMISTRY_AR = {"ما هو الرمز الكيميائي للماء؟": "H2O", "ما هو الرمز الكيميائي للأكسجين؟": "O2", "ما هو الرمز الكيميائي للذهب؟": "Au", "ما هو الرمز الكيميائي للفضة؟": "Ag", "ما هو الرمز الكيميائي للحديد؟": "Fe", "ما هو الرمز الكيميائي للصوديوم؟": "Na", "ما هو الرمز الكيميائي للبوتاسيوم؟": "K", "ما هو الرمز الكيميائي للكالسيوم؟": "Ca", "ما هو الرمز الكيميائي للنحاس؟": "Cu", "ما هو الرمز الكيميائي للزنك؟": "Zn", "ما هو الرمز الكيميائي للرصاص؟": "Pb", "ما هو الرمز الكيميائي للزئبق؟": "Hg", "ما هو الرمز الكيميائي لليورانيوم؟": "U", "ما هو الرمز الكيميائي للنيتروجين؟": "N2", "ما هو الرمز الكيميائي لثاني أكسيد الكربون؟": "CO2", "ما هو الرمز الكيميائي للملح؟": "NaCl", "ما هو الرمز الكيميائي للكربون؟": "C", "ما هو الرمز الكيميائي للكلور؟": "Cl", "ما هو الرمز الكيميائي للهيدروجين؟": "H2", "ما هو الرمز الكيميائي للمغنيسيوم؟": "Mg"}
CHEMISTRY_EN = {"Chemical symbol for water?": "H2O", "Chemical symbol for oxygen?": "O2", "Chemical symbol for gold?": "Au", "Chemical symbol for silver?": "Ag", "Chemical symbol for iron?": "Fe", "Chemical symbol for sodium?": "Na", "Chemical symbol for potassium?": "K", "Chemical symbol for calcium?": "Ca", "Chemical symbol for copper?": "Cu", "Chemical symbol for zinc?": "Zn", "Chemical symbol for lead?": "Pb", "Chemical symbol for mercury?": "Hg", "Chemical symbol for uranium?": "U", "Chemical symbol for nitrogen?": "N2", "Chemical symbol for carbon dioxide?": "CO2", "Chemical symbol for salt?": "NaCl", "Chemical symbol for carbon?": "C", "Chemical symbol for chlorine?": "Cl", "Chemical symbol for hydrogen?": "H2", "Chemical symbol for magnesium?": "Mg"}
CHEMISTRY_FA = {"نماد شیمیایی آب؟": "H2O", "نماد شیمیایی اکسیژن؟": "O2", "نماد شیمیایی طلا؟": "Au", "نماد شیمیایی نقره؟": "Ag", "نماد شیمیایی آهن؟": "Fe", "نماد شیمیایی سدیم؟": "Na", "نماد شیمیایی پتاسیم؟": "K", "نماد شیمیایی کلسیم؟": "Ca", "نماد شیمیایی مس؟": "Cu", "نماد شیمیایی روی؟": "Zn", "نماد شیمیایی سرب؟": "Pb", "نماد شیمیایی جیوه؟": "Hg", "نماد شیمیایی اورانیوم؟": "U", "نماد شیمیایی نیتروژن؟": "N2", "نماد شیمیایی دی‌اکسید کربن؟": "CO2", "نماد شیمیایی نمک؟": "NaCl", "نماد شیمیایی کربن؟": "C", "نماد شیمیایی کلر؟": "Cl", "نماد شیمیایی هیدروژن؟": "H2", "نماد شیمیایی منیزیم؟": "Mg"}

ANIMALS_AR = {"ما هو أسرع حيوان في العالم؟": "الفهد", "ما هو أكبر حيوان في العالم؟": "الحوت الأزرق", "ما هو أطول حيوان في العالم؟": "الزرافة", "ما هو أذكى حيوان في العالم؟": "الدلفين", "ما هو أقوى حيوان في العالم؟": "الفيل", "ما هو أصغر طائر في العالم؟": "الطنان", "ما هو الحيوان الذي لا يشرب الماء؟": "الكنغر", "ما هو الحيوان الذي ينام واقفاً؟": "الحصان", "ما هو الحيوان الذي يغير لونه؟": "الحرباء", "ما هو الحيوان الذي له 3 قلوب؟": "الأخطبوط", "ما هو الحيوان الذي يعيش أطول عمر؟": "السلحفاة", "ما هو الحيوان الذي يلد ولا يبيض؟": "الخفاش", "ما هو الحيوان الذي يرى بالأذن؟": "الوطواط", "ما هو الحيوان الملقب بسفينة الصحراء؟": "الجمل", "ما هو الحيوان الذي له ذاكرة قوية؟": "الفيل", "ما هو الحيوان الذي يأكل الحجارة؟": "التمساح", "ما هو الحيوان الذي لا ينام؟": "القرش", "ما هو الحيوان الذي يعيش في الماء والبر؟": "الضفدع", "ما هو الحيوان الذي له بصمة مثل الإنسان؟": "الكوالا", "ما هو الحيوان الذي يضحك؟": "الضبع"}
ANIMALS_EN = {"What is the fastest animal?": "cheetah", "What is the largest animal?": "blue whale", "What is the tallest animal?": "giraffe", "What is the smartest animal?": "dolphin", "What is the strongest animal?": "elephant", "What is the smallest bird?": "hummingbird", "What animal never drinks water?": "kangaroo rat", "What animal sleeps standing up?": "horse", "What animal changes color?": "chameleon", "What animal has 3 hearts?": "octopus", "What animal lives the longest?": "tortoise", "What animal gives birth and doesn't lay eggs?": "bat", "What animal sees with its ears?": "bat", "What animal is called the ship of the desert?": "camel", "What animal has a strong memory?": "elephant", "What animal eats stones?": "crocodile", "What animal never sleeps?": "shark", "What animal lives in water and land?": "frog", "What animal has fingerprints like humans?": "koala", "What animal laughs?": "hyena"}
ANIMALS_FA = {"سریع‌ترین حیوان جهان؟": "یوزپلنگ", "بزرگ‌ترین حیوان جهان؟": "نهنگ آبی", "بلندترین حیوان جهان؟": "زرافه", "باهوش‌ترین حیوان جهان؟": "دلفین", "قوی‌ترین حیوان جهان؟": "فیل", "کوچک‌ترین پرنده جهان؟": "مرغ مگس‌خوار", "کدام حیوان آب نمی‌نوشد؟": "کانگورو", "کدام حیوان ایستاده می‌خوابد؟": "اسب", "کدام حیوان رنگ عوض می‌کند؟": "آفتاب‌پرست", "کدام حیوان ۳ قلب دارد؟": "اختاپوس", "کدام حیوان بیشترین عمر را دارد؟": "لاک‌پشت", "کدام حیوان زایمان می‌کند و تخم نمی‌گذارد؟": "خفاش", "کدام حیوان با گوش می‌بیند؟": "خفاش", "به کدام حیوان کشتی صحرا می‌گویند؟": "شتر", "کدام حیوان حافظه قوی دارد؟": "فیل", "کدام حیوان سنگ می‌خورد؟": "تمساح", "کدام حیوان هرگز نمی‌خوابد؟": "کوسه", "کدام حیوان در آب و خشکی زندگی می‌کند؟": "قورباغه", "کدام حیوان اثر انگشت مثل انسان دارد؟": "کوآلا", "کدام حیوان می‌خندد؟": "کفتار"}

# رسائل مضحكة
funny_responses = {
    "win": {
        "ar": ["🎉 {name} فاز! ذكاء خارق 😂", "🏆 {name} كسب! التاج لايق عليك 🤣", "🔥 {name} دمر الجميع! أسطورة!", "😎 {name} جابها في الثمانيات! وحش!", "🧠 {name} مخه شغال صح، عاش!"],
        "en": ["🎉 {name} wins! What a genius 😂", "🏆 {name} got it! Crown fits you 🤣", "🔥 {name} destroyed everyone! Legend!", "😎 {name} nailed it! Beast mode!", "🧠 {name}'s brain works perfectly!"],
        "fa": ["🎉 {name} برد! چه نابغه‌ای 😂", "🏆 {name} گرفت! تاج بهت میاد 🤣", "🔥 {name} همه رو نابود کرد! افسانه!", "😎 {name} عالی بود! هیولا!", "🧠 {name} مغزش عالی کار می‌کنه!"]
    },
    "timeout": {
        "ar": ["⏰ الوقت خلص وكلكم نايمين! 😂", "😴 ولا واحد عرف؟ شكلكم محتاجين قهوة!", "🐌 بطيئين جداً! الإجابة طارت."],
        "en": ["⏰ Time's up! You all fell asleep 😂", "😴 No one knew? You need coffee!", "🐌 Too slow! The answer is gone."],
        "fa": ["⏰ وقت تموم شد! همه خوابیدین 😂", "😴 هیچکی ندونست؟ قهوه لازم دارین!", "🐌 خیلی کندین! جواب پرید."]
    }
}

TITLES = {
    "ar": {0: "⚔️ مبتدئ", 200: "🛡️ محارب", 400: "⚜️ فارس", 700: "👑 أمير", 1000: "🤴 ملك", 1500: "🦁 أسد الكروب", 2500: "🔥 أسطورة", 5000: "💎 إمبراطور"},
    "en": {0: "⚔️ Beginner", 200: "🛡️ Warrior", 400: "⚜️ Knight", 700: "👑 Prince", 1000: "🤴 King", 1500: "🦁 Lionheart", 2500: "🔥 Legend", 5000: "💎 Emperor"},
    "fa": {0: "⚔️ مبتدی", 200: "🛡️ جنگجو", 400: "⚜️ شوالیه", 700: "👑 شاهزاده", 1000: "🤴 پادشاه", 1500: "🦁 شیردل", 2500: "🔥 افسانه", 5000: "💎 امپراتور"}
}

# ------------------- إدارة اللاعبين -------------------
def get_player(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE user_id = %s", (user_id,))
    player = cur.fetchone()
    cur.close()
    conn.close()
    return player

def update_player(user_id, username, first_name, score=None, wins=None, losses=None, language=None):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT score, language FROM players WHERE user_id = %s", (user_id,))
    player = cur.fetchone()
    
    if not player:
        lang = language if language else 'ar'
        cur.execute("""
            INSERT INTO players (user_id, username, first_name, title, score, language) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, username, first_name, TITLES[lang][0], 100, lang))
        current_score = 100
        current_lang = lang
    else:
        current_score = player['score']
        current_lang = language if language else player.get('language', 'ar')
    
    if score is not None:
        current_score = score
    
    cur.execute("""
        UPDATE players SET 
        score = COALESCE(%s, score), 
        wins = COALESCE(%s, wins), 
        losses = COALESCE(%s, losses), 
        username = %s,
        language = COALESCE(%s, language)
        WHERE user_id = %s
    """, (score, wins, losses, username, language, user_id))
    
    new_title = TITLES[current_lang][0]
    for limit, title in sorted(TITLES[current_lang].items(), reverse=True):
        if current_score >= limit:
            new_title = title
            break
    cur.execute("UPDATE players SET title = %s WHERE user_id = %s", (new_title, user_id))
    
    conn.commit()
    cur.close()
    conn.close()
    return current_lang

# ------------------- أمر الإعدادات -------------------
@bot.message_handler(commands=['settings'])
def settings_cmd(message):
    user = message.from_user
    player = get_player(user.id)
    lang = player['language'] if player else 'ar'
    
    texts = {
        "ar": "⚙️ **اختر لغتك المفضلة:**",
        "en": "⚙️ **Choose your preferred language:**",
        "fa": "⚙️ **زبان مورد نظر خود را انتخاب کنید:**"
    }
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🇸🇦 العربية", callback_data="setlang_ar"),
        InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa")
    )
    markup.row(InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"))
    
    bot.reply_to(message, texts[lang], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def set_language(call):
    user = call.from_user
    lang = call.data.split('_')[1]
    update_player(user.id, user.username, user.first_name, language=lang)
    
    success_msg = {
        "ar": "✅ تم تغيير اللغة إلى العربية بنجاح!",
        "en": "✅ Language changed to English successfully!",
        "fa": "✅ زبان با موفقیت به فارسی تغییر کرد!"
    }
    
    bot.answer_callback_query(call.id, success_msg[lang][:50])
    try:
        bot.edit_message_text(success_msg[lang], call.message.chat.id, call.message.message_id)
    except:
        bot.send_message(call.message.chat.id, success_msg[lang])

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
        cur.execute("SELECT user_id, score, language FROM players WHERE username = %s", (username,))
        player = cur.fetchone()
        
        if not player:
            bot.reply_to(message, f"❌ لا يوجد لاعب بهذا الاسم: @{username}")
            cur.close()
            conn.close()
            return
        
        new_score = player['score'] + points
        cur.execute("UPDATE players SET score = %s WHERE user_id = %s", (new_score, player['user_id']))
        conn.commit()
        
        lang = player.get('language', 'ar')
        msgs = {
            "ar": f"🎁 تم إضافة {points} نقطة إلى رصيدك بواسطة الأدمن!\nنقاطك الآن: {new_score}",
            "en": f"🎁 {points} points added by admin!\nYour score: {new_score}",
            "fa": f"🎁 {points} امتیاز توسط ادمین اضافه شد!\nامتیاز شما: {new_score}"
        }
        
        bot.reply_to(message, f"✅ تم إضافة {points} نقطة للاعب @{username}\nنقاطه الآن: {new_score}")
        
        try:
            bot.send_message(player['user_id'], msgs[lang])
        except:
            pass
        
        cur.close()
        conn.close()
        
    except ValueError:
        bot.reply_to(message, "❌ يجب إدخال عدد صحيح للنقاط")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")

# ------------------- نظام المتجر -------------------
@bot.message_handler(commands=['shop'])
def shop_cmd(message):
    update_player(message.from_user.id, message.from_user.username, message.from_user.first_name)
    player = get_player(message.from_user.id)
    lang = player['language']
    
    asset_types = {"ar": ASSET_TYPES_AR, "en": ASSET_TYPES_EN, "fa": ASSET_TYPES_FA}[lang]
    shop_text = {
        "ar": f"🛒 **متجر اللعبة الأسطوري!**\n💰 نقاطك: **{player['score']}**\n\nاختر ما تود شراءه:",
        "en": f"🛒 **Legendary Game Shop!**\n💰 Your points: **{player['score']}**\n\nChoose what to buy:",
        "fa": f"🛒 **فروشگاه افسانه‌ای بازی!**\n💰 امتیاز شما: **{player['score']}**\n\nانتخاب کنید چه می‌خواهید بخرید:"
    }
    
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(f"🛍️ {asset_types[0]} ({SHOP_PRICES['assets']})", callback_data="buy_assets"))
    markup.row(InlineKeyboardButton(f"🎨 رسم ({SHOP_PRICES['draw']})", callback_data="buy_draw"))
    markup.row(InlineKeyboardButton(f"🎬 فيديو ({SHOP_PRICES['video']})", callback_data="buy_video"))
    
    bot.reply_to(message, shop_text[lang], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy_click(call):
    user_id = call.from_user.id
    item_key = call.data.split('_')[1]
    price = SHOP_PRICES[item_key]
    player = get_player(user_id)
    lang = player['language']
    
    if player['score'] < price:
        msg = {"ar": f"❌ نقاطك غير كافية! تحتاج {price} نقطة.", "en": f"❌ Not enough points! You need {price}.", "fa": f"❌ امتیاز کافی نیست! {price} امتیاز لازم داری."}
        return bot.answer_callback_query(call.id, msg[lang], show_alert=True)
    
    if item_key == "assets":
        asset_types = {"ar": ASSET_TYPES_AR, "en": ASSET_TYPES_EN, "fa": ASSET_TYPES_FA}[lang]
        markup = InlineKeyboardMarkup()
        for asset_type in asset_types:
            markup.row(InlineKeyboardButton(f"🎨 {asset_type}", callback_data=f"asset_type:{asset_type}"))
        markup.row(InlineKeyboardButton("🔙 رجوع" if lang == "ar" else ("🔙 Back" if lang == "en" else "🔙 بازگشت"), callback_data="back_to_shop"))
        
        texts = {
            "ar": "🛍️ **اختر نوع الملحقات:**\n\n1️⃣ ملحقات عيون\n2️⃣ ملحقات عشوائية\n3️⃣ ملحقات كرات وخرائط أعلام",
            "en": "🛍️ **Choose asset type:**\n\n1️⃣ Eyes Assets\n2️⃣ Random Assets\n3️⃣ Balls & Flag Maps",
            "fa": "🛍️ **نوع ملحقات را انتخاب کنید:**\n\n1️⃣ ملحقات چشم\n2️⃣ ملحقات تصادفی\n3️⃣ توپ‌ها و نقشه‌های پرچم"
        }
        
        bot.edit_message_text(texts[lang], call.message.chat.id, call.message.message_id, reply_markup=markup)
    else:
        order_type_map = {
            "ar": {"draw": "رسم رسمة", "video": "فيديو تعاوني"},
            "en": {"draw": "Drawing", "video": "Collaborative Video"},
            "fa": {"draw": "نقاشی", "video": "ویدیوی مشارکتی"}
        }
        pending_orders[user_id] = {'type': order_type_map[lang][item_key], 'price': price, 'state': 'waiting_flag'}
        
        msg = {
            "ar": f"✅ اخترت: **{order_type_map['ar'][item_key]}**\n\n🖼️ **الآن:** أرسل صورة علمك/دولتك للطلب.",
            "en": f"✅ You chose: **{order_type_map['en'][item_key]}**\n\n🖼️ **Now:** Send a picture of your flag for the order.",
            "fa": f"✅ انتخاب کردی: **{order_type_map['fa'][item_key]}**\n\n🖼️ **حالا:** عکس پرچمت رو بفرست."
        }
        bot.edit_message_text(msg[lang], call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('asset_type:'))
def handle_asset_type(call):
    user_id = call.from_user.id
    asset_type = call.data.split(':')[1]
    lang = get_player(user_id)['language']
    
    pending_assets[user_id] = {'type': asset_type, 'state': 'waiting_flag'}
    
    msg = {
        "ar": f"✅ اخترت: **ملحقات {asset_type}**\n\n📸 **الخطوة 1:** أرسل صورة علمك/دولتك.",
        "en": f"✅ You chose: **{asset_type} Assets**\n\n📸 **Step 1:** Send your flag picture.",
        "fa": f"✅ انتخاب کردی: **ملحقات {asset_type}**\n\n📸 **مرحله ۱:** عکس پرچمت رو بفرست."
    }
    
    bot.edit_message_text(msg[lang], call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_shop')
def back_to_shop(call):
    shop_cmd(call.message)

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in pending_assets and pending_assets[m.from_user.id].get('state') == 'waiting_flag')
def handle_asset_flag_photo(message):
    user_id = message.from_user.id
    lang = get_player(user_id)['language']
    pending_assets[user_id]['photo_id'] = message.photo[-1].file_id
    pending_assets[user_id]['state'] = 'waiting_name'
    
    msg = {
        "ar": "📸 تم استلام العلم!\n\n📝 **الخطوة 2:** أرسل اسمك (الاسم الذي تريد كتابته على الملحقات).",
        "en": "📸 Flag received!\n\n📝 **Step 2:** Send your name to write on assets.",
        "fa": "📸 پرچم دریافت شد!\n\n📝 **مرحله ۲:** اسمت رو برای نوشتن روی ملحقات بفرست."
    }
    bot.reply_to(message, msg[lang])

@bot.message_handler(func=lambda m: m.from_user.id in pending_assets and pending_assets[m.from_user.id].get('state') == 'waiting_name')
def handle_asset_name(message):
    user_id = message.from_user.id
    lang = get_player(user_id)['language']
    pending_assets[user_id]['name'] = message.text
    pending_assets[user_id]['state'] = 'waiting_count'
    
    msg = {
        "ar": f"✅ تم استلام الاسم: **{message.text}**\n\n🔢 **الخطوة 3:** كم ملحق تريد؟ (الحد الأقصى 25)",
        "en": f"✅ Name received: **{message.text}**\n\n🔢 **Step 3:** How many assets? (max 25)",
        "fa": f"✅ اسم دریافت شد: **{message.text}**\n\n🔢 **مرحله ۳:** چند ملحق می‌خوای؟ (حداکثر ۲۵)"
    }
    bot.reply_to(message, msg[lang])

@bot.message_handler(func=lambda m: m.from_user.id in pending_assets and pending_assets[m.from_user.id].get('state') == 'waiting_count')
def handle_asset_count(message):
    user_id = message.from_user.id
    lang = get_player(user_id)['language']
    
    try:
        count = int(message.text)
        if count < 1 or count > 25:
            msg = {"ar": "❌ العدد يجب أن يكون بين 1 و 25!", "en": "❌ Number must be between 1 and 25!", "fa": "❌ تعداد باید بین ۱ تا ۲۵ باشد!"}
            bot.reply_to(message, msg[lang])
            return
        
        pending_assets[user_id]['count'] = count
        pending_assets[user_id]['state'] = 'waiting_painter'
        
        markup = InlineKeyboardMarkup()
        for painter in PAINTERS:
            markup.row(InlineKeyboardButton(f"🖌️ {painter}", callback_data=f"asset_painter:{painter}"))
        
        msg = {
            "ar": f"✅ تم تحديد العدد: {count}\n\n🎨 **الخطوة الأخيرة:** اختر الرسام لتنفيذ طلبك:",
            "en": f"✅ Count set: {count}\n\n🎨 **Final step:** Choose the painter:",
            "fa": f"✅ تعداد تعیین شد: {count}\n\n🎨 **مرحله آخر:** نقاش رو انتخاب کن:"
        }
        bot.reply_to(message, msg[lang], reply_markup=markup)
        
    except ValueError:
        msg = {"ar": "❌ يجب إدخال رقم صحيح!", "en": "❌ Please enter a valid number!", "fa": "❌ لطفاً یک عدد صحیح وارد کنید!"}
        bot.reply_to(message, msg[lang])

@bot.callback_query_handler(func=lambda call: call.data.startswith('asset_painter:'))
def handle_asset_painter(call):
    user_id = call.from_user.id
    painter = call.data.split(':')[1]
    lang = get_player(user_id)['language']
    
    if user_id not in pending_assets or pending_assets[user_id].get('state') != 'waiting_painter':
        return bot.answer_callback_query(call.id, "❌ الطلب منتهي." if lang == "ar" else ("❌ Order expired." if lang == "en" else "❌ سفارش منقضی شده."), show_alert=True)
    
    asset_data = pending_assets[user_id]
    painter_username = painter.replace('@', '')
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM players WHERE username = %s", (painter_username,))
    painter_data = cur.fetchone()
    cur.close()
    conn.close()
    
    if not painter_data:
        msg = {"ar": f"❌ الرسام {painter} غير مسجل!", "en": f"❌ Painter {painter} not registered!", "fa": f"❌ نقاش {painter} ثبت نام نکرده!"}
        bot.answer_callback_query(call.id, msg[lang], show_alert=True)
        return
    
    painter_chat_id = painter_data['user_id']
    price = SHOP_PRICES['assets']
    player = get_player(user_id)
    
    if player['score'] < price:
        del pending_assets[user_id]
        msg = {"ar": "❌ نقاطك لم تعد تكفي!", "en": "❌ Not enough points!", "fa": "❌ امتیاز کافی نیست!"}
        return bot.edit_message_text(msg[lang], call.message.chat.id, call.message.message_id)
    
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
        success_msg = {
            "ar": f"✅ **تمت العملية بنجاح!**\nخصمنا {price} نقطة، وتم إرسال طلبك لحساب الرسام {painter}.",
            "en": f"✅ **Success!**\nDeducted {price} points, order sent to {painter}.",
            "fa": f"✅ **با موفقیت انجام شد!**\n{price} امتیاز کم شد، سفارش به {painter} ارسال شد."
        }
        bot.edit_message_text(success_msg[lang], call.message.chat.id, call.message.message_id)
    except Exception as e:
        error_msg = {
            "ar": f"⚠️ فشل إرسال الطلب للرسام {painter}.\nالخطأ: {str(e)}",
            "en": f"⚠️ Failed to send to {painter}.\nError: {str(e)}",
            "fa": f"⚠️ ارسال به {painter} ناموفق.\nخطا: {str(e)}"
        }
        bot.edit_message_text(error_msg[lang], call.message.chat.id, call.message.message_id)
    
    del pending_assets[user_id]

# ------------------- الأوامر الأساسية والألعاب -------------------
@bot.message_handler(commands=['start', 'top', 'daily'])
def basic_commands(message):
    cmd = message.text.split()[0].split('@')[0].replace('/', '')
    user = message.from_user
    update_player(user.id, user.username, user.first_name)
    player = get_player(user.id)
    lang = player['language']
    
    if cmd == "start":
        texts = {
            "ar": ("🎮 أهلاً بك في بوت التحديات الأسطوري!\n🎁 كل لاعب جديد يحصل على 100 نقطة\n\n"
                   "**الأوامر:**\n/shop - المتجر\n/top - المتصدرين\n/daily - الهدية اليومية\n/settings - الإعدادات\n\n"
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
                   "🔥 /randomgame - لعبة عشوائية"),
            "en": ("🎮 Welcome to Ultimate Challenges Bot!\n🎁 Every new player gets 100 points\n\n"
                   "**Commands:**\n/shop - Shop\n/top - Leaderboard\n/daily - Daily Gift\n/settings - Settings\n\n"
                   "🎲 **Games (26 games):**\n"
                   "/g1 Guess Number | /g2 Math | /g3 Speed Typing\n"
                   "/g4 Reverse Word | /g5 Capitals | /g6 Arrange Letters\n"
                   "/g7 Proverb | /g8 Count Emoji | /g9 Opposites\n"
                   "/g10 Fastest Word | /g11 Trivia | /g12 Riddles\n"
                   "/g13 Number Sequence | /g14 Translate | /g15 Emoji Movies\n"
                   "/g16 Arabic Dialects | /g17 Crossword | /g18 Food Chain\n"
                   "/g19 Math Puzzle | /g20 Logic Puzzle | /g21 Missing Words\n"
                   "/g22 Shapes | /g23 History Dates | /g24 New Capitals\n"
                   "/g25 Chemistry | /g26 Animals\n\n"
                   "🔥 /randomgame - Random Game"),
            "fa": ("🎮 به ربات چالش‌های افسانه‌ای خوش آمدی!\n🎁 هر بازیکن جدید ۱۰۰ امتیاز می‌گیرد\n\n"
                   "**دستورات:**\n/shop - فروشگاه\n/top - برترین‌ها\n/daily - هدیه روزانه\n/settings - تنظیمات\n\n"
                   "🎲 **بازی‌ها (۲۶ بازی):**\n"
                   "/g1 حدس عدد | /g2 ریاضی | /g3 تایپ سریع\n"
                   "/g4 کلمه برعکس | /g5 پایتخت‌ها | /g6 مرتب کردن حروف\n"
                   "/g7 ضرب‌المثل | /g8 شمارش ایموجی | /g9 متضادها\n"
                   "/g10 سریع‌ترین کلمه | /g11 اطلاعات عمومی | /g12 معما\n"
                   "/g13 دنباله اعداد | /g14 ترجمه | /g15 فیلم با ایموجی\n"
                   "/g16 لهجه‌های عربی | /g17 جدول کلمات | /g18 زنجیره غذایی\n"
                   "/g19 معمای ریاضی | /g20 معمای منطقی | /g21 کلمات ناقص\n"
                   "/g22 اشکال هندسی | /g23 تاریخ‌های تاریخی | /g24 پایتخت‌های جدید\n"
                   "/g25 شیمی | /g26 حیوانات\n\n"
                   "🔥 /randomgame - بازی تصادفی")
        }
        bot.reply_to(message, texts[lang])
    
    elif cmd == "top":
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT first_name, score, title FROM players ORDER BY score DESC LIMIT 10")
        top = cur.fetchall()
        cur.close()
        conn.close()
        
        headers = {"ar": "🏆 **أفضل 10 لاعبين:**\n\n", "en": "🏆 **Top 10 Players:**\n\n", "fa": "🏆 **۱۰ بازیکن برتر:**\n\n"}
        point_word = {"ar": "نقطة", "en": "points", "fa": "امتیاز"}
        
        text = headers[lang] + "\n".join([f"{i+1}. {p['title']} {p['first_name']} - {p['score']} {point_word[lang]}" for i, p in enumerate(top)])
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
            
            msgs = {
                "ar": f"🎁 استلمت 50 نقطة مجانية! نقاطك الآن: {new_score} نقطة.",
                "en": f"🎁 You got 50 free points! Your score: {new_score} points.",
                "fa": f"🎁 ۵۰ امتیاز رایگان گرفتی! امتیازت: {new_score} امتیاز."
            }
            bot.reply_to(message, msgs[lang])
        else:
            remaining_time = timedelta(days=1) - time_since_last
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            msgs = {
                "ar": f"⏳ استلمت مكافأتك مسبقاً!\nعد بعد: **{hours} ساعة و {minutes} دقيقة**",
                "en": f"⏳ Already claimed!\nCome back in: **{hours}h {minutes}m**",
                "fa": f"⏳ قبلاً گرفتی!\nبعد از **{hours} ساعت و {minutes} دقیقه** برگرد"
            }
            bot.reply_to(message, msgs[lang])

@bot.message_handler(commands=[f'g{i}' for i in range(1, 27)] + ['randomgame'])
def start_specific_game(message):
    chat_id = message.chat.id
    player = get_player(message.from_user.id)
    lang = player['language'] if player else 'ar'
    
    with games_lock:
        if chat_id in active_games:
            msgs = {"ar": "⏳ يا كابتن، في تحدي شغال أصلاً، خلصوه أول!", "en": "⏳ A challenge is already running!", "fa": "⏳ یه چالش در حال اجراست!"}
            return bot.reply_to(message, msgs[lang])
    
    cmd = message.text.split()[0].split('@')[0].replace('/', '')
    game_id = random.randint(1, 26) if cmd == 'randomgame' else int(cmd.replace('g', ''))
    
    # اختيار اللعبة حسب اللغة
    if game_id == 1:
        ans = str(random.randint(1, 100))
        q = {"ar": "🔢 خمن الرقم بين 1 و 100", "en": "🔢 Guess the number between 1 and 100", "fa": "🔢 عدد بین ۱ تا ۱۰۰ را حدس بزن"}[lang]
    elif game_id == 2:
        n1, n2, op = random.randint(10, 100), random.randint(1, 50), random.choice(['+', '-', '*'])
        ans = str(eval(f"{n1}{op}{n2}"))
        q = {"ar": f"🧮 ناتج: {n1} {op} {n2} = ؟", "en": f"🧮 Calculate: {n1} {op} {n2} = ?", "fa": f"🧮 حاصل: {n1} {op} {n2} = ؟"}[lang]
    elif game_id == 3:
        s = random.choice({"ar": TYPING_SENTENCES_AR, "en": TYPING_SENTENCES_EN, "fa": TYPING_SENTENCES_FA}[lang])
        ans = s
        q = {"ar": f"⌨️ أسرع واحد يكتب:\n`{s}`", "en": f"⌨️ Fastest to type:\n`{s}`", "fa": f"⌨️ سریع‌ترین تایپ:\n`{s}`"}[lang]
    elif game_id == 4:
        w = random.choice({"ar": SCRAMBLE_WORDS_AR, "en": SCRAMBLE_WORDS_EN, "fa": SCRAMBLE_WORDS_FA}[lang])
        ans = w[::-1]
        q = {"ar": f"🔄 اعكس حروف: **{w}**", "en": f"🔄 Reverse: **{w}**", "fa": f"🔄 برعکس کن: **{w}**"}[lang]
    elif game_id == 5:
        c, cap = random.choice(list({"ar": COUNTRIES_AR, "en": COUNTRIES_EN, "fa": COUNTRIES_FA}[lang].items()))
        ans = cap
        q = {"ar": f"🌍 عاصمة **{c}**؟", "en": f"🌍 Capital of **{c}**?", "fa": f"🌍 پایتخت **{c}**؟"}[lang]
    elif game_id == 6:
        w = random.choice({"ar": SCRAMBLE_WORDS_AR, "en": SCRAMBLE_WORDS_EN, "fa": SCRAMBLE_WORDS_FA}[lang])
        shuffled = ''.join(random.sample(w, len(w)))
        ans = w
        q = {"ar": f"🧩 رتب الحروف: **{shuffled}**", "en": f"🧩 Arrange: **{shuffled}**", "fa": f"🧩 مرتب کن: **{shuffled}**"}[lang]
    elif game_id == 7:
        if lang == "ar":
            h, m = random.choice(list(PROVERBS_AR.items()))
            ans, q = m, f"📜 أكمل المثل:\n{h} ..."
        else:
            return start_specific_game_by_id(message, chat_id, random.randint(11, 12))
    elif game_id == 8:
        e, count = random.choice(["🍎", "🔥", "💎", "💣", "⚔️"]), random.randint(4, 9)
        emojis = [e]*count + [random.choice(["🍌", "🍉", "💧"])]*20
        random.shuffle(emojis)
        ans = str(count)
        q = {"ar": f"👀 كم {e}؟\n{''.join(emojis)}", "en": f"👀 How many {e}?\n{''.join(emojis)}", "fa": f"👀 چندتا {e}؟\n{''.join(emojis)}"}[lang]
    elif game_id == 9:
        w, opp = random.choice(list({"ar": OPPOSITES_AR, "en": OPPOSITES_EN, "fa": OPPOSITES_FA}[lang].items()))
        ans = opp
        q = {"ar": f"↔️ عكس **{w}**؟", "en": f"↔️ Opposite of **{w}**?", "fa": f"↔️ متضاد **{w}**؟"}[lang]
    elif game_id == 10:
        ans = random.choice({"ar": FAST_WORDS_AR, "en": FAST_WORDS_EN, "fa": FAST_WORDS_FA}[lang])
        q = {"ar": f"⚡ اكتب:\n**{ans}**", "en": f"⚡ Type:\n**{ans}**", "fa": f"⚡ تایپ کن:\n**{ans}**"}[lang]
    elif game_id == 11:
        qu, a = random.choice(list({"ar": TRIVIA_AR, "en": TRIVIA_EN, "fa": TRIVIA_FA}[lang].items()))
        ans = a
        q = {"ar": f"🧠 {qu}", "en": f"🧠 {qu}", "fa": f"🧠 {qu}"}[lang]
    elif game_id == 12:
        qu, a = random.choice(list({"ar": RIDDLES_AR, "en": RIDDLES_EN, "fa": RIDDLES_FA}[lang].items()))
        ans = a
        q = {"ar": f"🕵️‍♂️ {qu}", "en": f"🕵️‍♂️ {qu}", "fa": f"🕵️‍♂️ {qu}"}[lang]
    elif game_id == 13:
        start, step = random.randint(1,10), random.randint(2,5)
        ans = str(start+4*step)
        seq = f"{start}, {start+step}, {start+2*step}, {start+3*step}"
        q = {"ar": f"🔢 أكمل: {seq}, ...", "en": f"🔢 Complete: {seq}, ...", "fa": f"🔢 کامل کن: {seq}, ..."}[lang]
    elif game_id == 14:
        word_list = {"ar": TRANSLATE_WORDS_AR, "en": TRANSLATE_WORDS_EN, "fa": TRANSLATE_WORDS_FA}[lang]
        src, target = random.choice(list(word_list.items()))
        ans = target
        q = {"ar": f"🇺🇸 ترجم: '{src}'", "en": f"🇸🇦 Translate: '{src}'", "fa": f"🇸🇦 ترجمه: '{src}'"}[lang]
    elif game_id == 15:
        em, mov = random.choice(list({"ar": EMOJI_GUESS_AR, "en": EMOJI_GUESS_EN, "fa": EMOJI_GUESS_FA}[lang].items()))
        ans = mov
        q = {"ar": f"🎬 الفيلم: {em}", "en": f"🎬 Movie: {em}", "fa": f"🎬 فیلم: {em}"}[lang]
    elif game_id == 16:
        if lang == "ar":
            qu, a = random.choice(list(DIALECTS_AR.items()))
            ans, q = a, f"🗣️ {qu}"
        else:
            return start_specific_game_by_id(message, chat_id, 11)
    elif game_id == 17:
        if lang == "ar":
            qu, a = random.choice(list(CROSSWORD_AR.items()))
            ans, q = a, f"🧩 {qu}"
        else:
            return start_specific_game_by_id(message, chat_id, 12)
    elif game_id == 18:
        qu, a = random.choice(list({"ar": FOOD_CHAIN_AR, "en": FOOD_CHAIN_EN, "fa": FOOD_CHAIN_FA}[lang].items()))
        ans = a
        q = {"ar": f"🍽️ {qu}", "en": f"🍽️ {qu}", "fa": f"🍽️ {qu}"}[lang]
    elif game_id == 19:
        qu, a = random.choice(list({"ar": MATH_PUZZLES_AR, "en": MATH_PUZZLES_EN, "fa": MATH_PUZZLES_FA}[lang].items()))
        ans = a
        q = {"ar": f"🧮 {qu}", "en": f"🧮 {qu}", "fa": f"🧮 {qu}"}[lang]
    elif game_id == 20:
        qu, a = random.choice(list({"ar": LOGIC_PUZZLES_AR, "en": LOGIC_PUZZLES_EN, "fa": LOGIC_PUZZLES_FA}[lang].items()))
        ans = a
        q = {"ar": f"🧠 {qu}", "en": f"🧠 {qu}", "fa": f"🧠 {qu}"}[lang]
    elif game_id == 21:
        qu, a = random.choice(list({"ar": MISSING_WORDS_AR, "en": MISSING_WORDS_EN, "fa": MISSING_WORDS_FA}[lang].items()))
        ans = a
        q = {"ar": f"📝 {qu}", "en": f"📝 {qu}", "fa": f"📝 {qu}"}[lang]
    elif game_id == 22:
        qu, a = random.choice(list({"ar": SHAPES_AR, "en": SHAPES_EN, "fa": SHAPES_FA}[lang].items()))
        ans = a
        q = {"ar": f"📐 {qu}", "en": f"📐 {qu}", "fa": f"📐 {qu}"}[lang]
    elif game_id == 23:
        qu, a = random.choice(list({"ar": HISTORY_DATES_AR, "en": HISTORY_DATES_EN, "fa": HISTORY_DATES_FA}[lang].items()))
        ans = a
        q = {"ar": f"📅 {qu}", "en": f"📅 {qu}", "fa": f"📅 {qu}"}[lang]
    elif game_id == 24:
        qu, a = random.choice(list({"ar": NEW_CAPITALS_AR, "en": NEW_CAPITALS_EN, "fa": NEW_CAPITALS_FA}[lang].items()))
        ans = a
        q = {"ar": f"🌍 {qu}", "en": f"🌍 {qu}", "fa": f"🌍 {qu}"}[lang]
    elif game_id == 25:
        qu, a = random.choice(list({"ar": CHEMISTRY_AR, "en": CHEMISTRY_EN, "fa": CHEMISTRY_FA}[lang].items()))
        ans = a
        q = {"ar": f"🧪 {qu}", "en": f"🧪 {qu}", "fa": f"🧪 {qu}"}[lang]
    elif game_id == 26:
        qu, a = random.choice(list({"ar": ANIMALS_AR, "en": ANIMALS_EN, "fa": ANIMALS_FA}[lang].items()))
        ans = a
        q = {"ar": f"🐾 {qu}", "en": f"🐾 {qu}", "fa": f"🐾 {qu}"}[lang]
    else:
        return bot.reply_to(message, "❌ رقم اللعبة غير صالح")
    
    with games_lock:
        active_games[chat_id] = ans.strip().lower()
    
    game_start_msg = {"ar": f"🎮 **تحدي جديد!**\n\n{q}\n\n⏳ 45 ثانية!", "en": f"🎮 **New Challenge!**\n\n{q}\n\n⏳ 45 seconds!", "fa": f"🎮 **چالش جدید!**\n\n{q}\n\n⏳ ۴۵ ثانیه!"}[lang]
    bot.send_message(chat_id, game_start_msg)
    threading.Timer(45.0, end_group_game, args=[chat_id, ans]).start()

def start_specific_game_by_id(message, chat_id, game_id):
    """دالة مساعدة لتشغيل لعبة برقم محدد"""
    player = get_player(message.from_user.id)
    lang = player['language'] if player else 'ar'
    
    if game_id == 11:
        qu, a = random.choice(list({"ar": TRIVIA_AR, "en": TRIVIA_EN, "fa": TRIVIA_FA}[lang].items()))
        ans, q = a, f"🧠 {qu}"
    elif game_id == 12:
        qu, a = random.choice(list({"ar": RIDDLES_AR, "en": RIDDLES_EN, "fa": RIDDLES_FA}[lang].items()))
        ans, q = a, f"🕵️‍♂️ {qu}"
    else:
        return
    
    with games_lock:
        active_games[chat_id] = ans.strip().lower()
    
    game_start_msg = {"ar": f"🎮 **تحدي جديد!**\n\n{q}\n\n⏳ 45 ثانية!", "en": f"🎮 **New Challenge!**\n\n{q}\n\n⏳ 45 seconds!", "fa": f"🎮 **چالش جدید!**\n\n{q}\n\n⏳ ۴۵ ثانیه!"}[lang]
    bot.send_message(chat_id, game_start_msg)
    threading.Timer(45.0, end_group_game, args=[chat_id, ans]).start()

def end_group_game(chat_id, correct_answer):
    with games_lock:
        if chat_id in active_games and active_games[chat_id] == correct_answer.strip().lower():
            del active_games[chat_id]
            timeout_msg = random.choice(funny_responses['timeout']['ar'])
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
            lang = player['language'] if player else 'ar'
            
            update_player(message.from_user.id, message.from_user.username, message.from_user.first_name, score=player['score'] + 15)
            
            win_msg = random.choice(funny_responses['win'][lang]).format(name=message.from_user.first_name)
            point_msg = {"ar": "نقطة", "en": "points", "fa": "امتیاز"}[lang]
            bot.reply_to(message, f"{win_msg}\nالإجابة: {ans}\n🤑 أضفنا لك 15 {point_msg}!")

# ------------------- تشغيل البوت -------------------
if __name__ == "__main__":
    print("✅ البوت متعدد اللغات شغال ومستقر...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
