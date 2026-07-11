import telebot
import random
import time
import threading
import sqlite3
import os
from flask import Flask
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🔑 إعدادات البوت (يفضل وضع التوكن في متغيرات البيئة في Railway)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8868110647:AAHjffbopZF-p6E9EP9HqB3a2l99IbG-TeI")
bot = telebot.TeleBot(BOT_TOKEN)

# ------------------- حماية التزامن (Thread Locks) -------------------
db_lock = threading.Lock()
games_lock = threading.Lock()

# ------------------- كود Flask لإبقاء البوت حياً (لـ Railway) -------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 البوت شغال ومستقر!"

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()

# ------------------- إعداد قاعدة البيانات -------------------
def get_db_connection():
    # check_same_thread=False ضرورية لتجنب أخطاء SQLite في البوتات
    conn = sqlite3.connect("game.db", timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def setup_database():
    with db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                score INTEGER DEFAULT 100, 
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                title TEXT DEFAULT '⚔️ مغامر',
                total_wins INTEGER DEFAULT 0,
                last_daily TIMESTAMP
            )
            """)
            conn.commit()

setup_database()

# ------------------- قواميس الألعاب -------------------
active_games = {} 
pending_orders = {}

SHOP_PRICES = {"assets": 500, "draw": 1000, "video": 2000}
PAINTERS = ["@Arabic_Painter1", "@alhilal_bahraini", "@BrahimAnimation", "@yamenhazani"]

funny_responses = {
    "win": ["🎉 {name} فاز! ذكاء خارق 😂", "🏆 {name} كسب! التاج لايق عليك 🤣", "🔥 {name} دمر الجميع! أسطورة!", "😎 {name} جابها في الثمانيات! وحش!", "🧠 {name} مخه شغال صح، عاش!"],
    "timeout": ["⏰ الوقت خلص وكلكم نايمين! 😂", "😴 ولا واحد عرف؟ شكلكم محتاجين قهوة!", "🐌 بطيئين جداً! الإجابة طارت."]
}
TITLES = {0: "⚔️ مبتدئ", 200: "🛡️ محارب", 400: "⚜️ فارس", 700: "👑 أمير", 1000: "🤴 ملك", 1500: "🦁 أسد الكروب", 2500: "🔥 أسطورة", 5000: "💎 إمبراطور"}
COUNTRIES = {"السعودية":"الرياض", "مصر":"القاهرة", "العراق":"بغداد", "سوريا":"دمشق", "المغرب":"الرباط", "الجزائر":"الجزائر", "فلسطين":"القدس", "اليمن":"صنعاء", "الكويت":"الكويت", "قطر":"الدوحة", "الإمارات":"أبوظبي", "عمان":"مسقط", "البحرين":"المنامة", "تونس":"تونس", "ليبيا":"طرابلس", "السودان":"الخرطوم", "فرنسا":"باريس", "بريطانيا":"لندن", "إيطاليا":"روما", "إسبانيا":"مدريد", "اليابان":"طوكيو", "روسيا":"موسكو", "الصين":"بكين", "ألمانيا":"برلين", "تركيا":"أنقرة"}
SCRAMBLE_WORDS = ["كمبيوتر", "مبرمج", "أسطورة", "تليجرام", "تحدي", "بطولة", "جائزة", "احتراف", "خوارزمية", "مصفوفة", "تشفير", "سيرفر", "قرصنة", "إمبراطورية", "اقتصاد", "عسكرية", "أسلحة", "تحالف", "استراتيجية", "جيش", "قاعدة", "خريطة"]
PROVERBS = {"عصفور في اليد خير من عشرة على":"الشجرة", "من جد وجد ومن زرع":"حصد", "الوقت كالسيف إن لم تقطعه":"قطعك", "الجار قبل":"الدار", "الصديق وقت":"الضيق", "فاقد الشيء لا":"يعطيه", "الطيور على أشكالها":"تقع", "مصائب قوم عند قوم":"فوائد", "العقل السليم في الجسم":"السليم", "العجلة من":"الشيطان", "خير الكلام ما قل":"ودل", "في التأني السلامة وفي العجلة":"الندامة", "من حفر حفرة لأخيه وقع":"فيها", "السكوت علامة":"الرضا", "درهم وقاية خير من قنطار":"علاج", "البعيد عن العين بعيد عن":"القلب", "حبل الكذب":"قصير", "كل تأخيرة وفيها":"خيرة", "إذا عرف السبب بطل":"العجب", "عذر أقبح من":"ذنب"}
OPPOSITES = {"طويل":"قصير", "سريع":"بطيء", "أبيض":"أسود", "كبير":"صغير", "قوي":"ضعيف", "بارد":"حار", "غني":"فقير", "سعيد":"حزين", "شجاع":"جبان", "قريب":"بعيد", "عالي":"واطي", "جديد":"قديم", "صعب":"سهل", "جميل":"قبيح", "واسع":"ضيق", "خفيف":"ثقيل", "نور":"ظلام", "بداية":"نهاية", "حب":"كره", "نجاح":"فشل"}
TRIVIA = {"ما هو أسرع حيوان بري？":"الفهد", "المعدن الأغلى في العالم (يبدأ بالروديوم)？":"الروديوم", "أكبر قارة في العالم؟":"اسيا", "مكتشف الجاذبية؟":"نيوتن", "عاصمة الولايات المتحدة؟":"واشنطن", "لغة البرازيل؟":"البرتغالية", "أطول نهر في العالم؟":"النيل", "الكوكب الأحمر؟":"المريخ", "كم عدد قارات العالم؟":"7", "أكبر محيط؟":"الهادي", "عملة اليابان؟":"الين", "صاحب لوحة الموناليزا؟":"دافنشي", "كم لون في قوس قزح؟":"7", "غاز التنفس؟":"الاكسجين", "مخترع المصباح؟":"اديسون", "مدينة التلال السبع؟":"روما", "عاصمة اليابان القديمة؟":"كيوتو", "أول دولة استخدمت الورق؟":"الصين", "باني الهرم الأكبر؟":"خوفو", "أصغر دولة في العالم؟":"الفاتيكان"}
RIDDLES = {"كلما أخذت مني كبرت؟":"الحفرة", "يمشي بلا رجلين ويبكي بلا عينين؟":"السحابة", "له أسنان ولا يعض؟":"المشط", "بيته من خيط وضعيف؟":"العنكبوت", "أمامك دائماً ولا تراه؟":"المستقبل", "يسمع بلا أذن ويتكلم بلا لسان؟":"التلفون", "لا يبتل في الماء؟":"الضوء", "له رأس وعين واحدة？":"الإبرة", "يحمل أثقالاً ولا يطيق مسماراً؟":"البحر", "يمشي ويقف بلا أرجل؟":"الوقت", "أخضر في الأرض أسود في السوق أحمر في البيت؟":"الشاي", "عضمه بره ولحمه جوه؟":"السلحفاة", "يقرصك ولا تراه؟":"الجوع", "مدينة بلا بيوت ونهر بلا ماء؟":"الخريطة", "ليس شجرة وله أوراق؟":"الكتاب", "حوله ماء وهو نار؟":"البركان", "يدور ولا يتعب؟":"العقرب", "إذا دخل الماء ضاع؟":"الملح", "يذهب ولا يعود؟":"الدخان", "له رقبة ولا رأس له؟":"الزجاجة"}
EMOJI_GUESS = {"🦇👨🏻":"باتمان", "🚢🧊💔":"تيتانيك", "🕷️👨🏻":"سبايدرمان", "🦁👑":"الاسد الملك", "🐼🥋":"كونغ فو باندا", "🧙‍♂️⚡👓":"هاري بوتر", "🏴‍☠️🚢☠️":"قراصنة الكاريبي", "🚗⚡⏱️":"العودة للمستقبل", "🤡🎈":"ات", "🦖🦕🏞️":"الحديقة الجوراسية", "👽🚲🌕":"اي تي", "💊🔴🔵":"ماتريكس", "🦍🏢":"كينغ كونغ", "🦈🏖️🩸":"الفك المفترس", "👦🏻🍫🏭":"تشارلي ومصنع الشوكولاتة", "👨‍🚀🌌⏱️":"انترستيلار", "🧞‍♂️🐒🕌":"علاء الدين", "🧸🤠🚀":"قصة لعبة", "🦹‍♂️🃏":"الجوكر", "🚗😡🏜️":"ماد ماكس"}
TYPING_SENTENCES = ["البوت الأسطوري يحكم الكروب", "سرعة البديهة أساس الفوز", "الملك يدافع عن عرشه بشراسة", "التحدي القادم سيكون أصعب", "جيشي جاهز للمعركة الفاصلة", "الاقتصاد القوي يبني دول قوية", "بايثون لغة برمجة عظيمة", "الذكاء الاصطناعي مستقبل التكنولوجيا", "تليجرام أفضل تطبيق محادثة", "النقاط تجلب لك المجد والثروة", "لا تستسلم حتى النهاية", "أعلام الدول ترفرف عالياً", "التحالفات ضرورية للفوز", "الهجوم خير وسيلة للدفاع", "قاعدة البيانات تحفظ مجهودك", "الرسام يجسد الخيال للواقع", "الوقت يمضي بسرعة فائقة", "التصميم الجيد يحتاج دقة", "الخريطة تكشف أسرار العالم", "كل نقطة تصنع فارقاً"]
FAST_WORDS = ["هجوم", "دفاع", "صاروخ", "دبابة", "طائرة", "مدفع", "حصن", "جندي", "تحالف", "خيانة", "معاهدة", "سلام", "حرب", "ثروة", "ذهب", "ألماس", "مخزن", "جنرال", "قائد", "خريطة"]
TRANSLATE_WORDS = {"apple":"تفاحة", "book":"كتاب", "car":"سيارة", "sun":"شمس", "moon":"قمر", "star":"نجمة", "water":"ماء", "fire":"نار", "earth":"أرض", "sky":"سماء", "sword":"سيف", "shield":"درع", "king":"ملك", "queen":"ملكة", "army":"جيش", "war":"حرب", "peace":"سلام", "money":"مال", "gold":"ذهب", "flag":"علم"}
DIALECTS = {"ما معنى كلمة 'زقرت' باللهجة السورية واللبنانية؟": "قبضاي", "ما معنى كلمة 'مبحرين' أو 'بحر فيني' باللهجة الحجازية؟": "يطالع", "ما معنى كلمة 'هسه' باللهجة العراقية؟": "الان", "ما معنى كلمة 'باهي' باللهجة التونسية والليبية؟": "جميل", "ما معنى كلمة 'وايد' باللهجة الخليجية؟": "كثير", "ما معنى كلمة 'برشا' باللهجة التونسية؟": "كثير", "ما معنى كلمة 'ديالي' باللهجة المغربية؟": "حقي", "ما معنى كلمة 'جدع' باللهجة المصرية؟": "شجاع", "ما معنى كلمة 'دحين' باللهجة السعودية؟": "الان", "ما معنى كلمة 'كوشة' باللهجة السودانية؟": "مزبلة", "ما معنى كلمة 'شين' باللهجة الخليجية والسودانية؟": "قبيح", "ما معنى كلمة 'غاوية' باللهجة العمانية؟": "جميلة", "ما معنى كلمة 'بزاف' باللهجة الجزائرية والمغربية؟": "كثير", "ما معنى كلمة 'قرت قرة' باللهجة اليمنية؟": "جلست", "ما معنى كلمة 'إرمس' باللهجة الإماراتية؟": "تكلم", "ما معنى كلمة 'تكة' باللهجة الأردنية والفلسطينية؟": "قليل", "ما معنى كلمة 'خاشوقة' باللهجة الإماراتية والعراقية؟": "ملعقة", "ما معنى كلمة 'سيباوي' باللهجة المصرية (سيب الحاجه)؟": "اتركها", "ما معنى كلمة 'سيده' باللهجة الخليجية (امشي سيده)؟": "مستقيم", "ما معنى كلمة 'چندوب' أو 'جنزير' باللهجة العراقية؟": "سلسلة"}

# ------------------- إدارة اللاعبين -------------------
def get_player(user_id):
    with db_lock:
        with get_db_connection() as conn:
            return conn.cursor().execute("SELECT * FROM players WHERE user_id = ?", (user_id,)).fetchone()

def update_player(user_id, username, first_name, score=None, wins=None, losses=None):
    with db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            player = cursor.execute("SELECT score FROM players WHERE user_id = ?", (user_id,)).fetchone()
            
            if not player:
                cursor.execute("""
                    INSERT OR IGNORE INTO players (user_id, username, first_name, title, last_daily, score) 
                    VALUES (?, ?, ?, ?, ?, 100)
                """, (user_id, username, first_name, "⚔️ مبتدئ", (datetime.now() - timedelta(days=1)).isoformat()))
                current_score = 100
            else:
                current_score = player['score']

            if score is not None: current_score = score
            
            cursor.execute("""
                UPDATE players SET 
                score = COALESCE(?, score), wins = COALESCE(?, wins), losses = COALESCE(?, losses), username = ?
                WHERE user_id = ?
            """, (score, wins, losses, username, user_id))
            
            new_title = "⚔️ مبتدئ"
            for limit, title in sorted(TITLES.items(), reverse=True):
                if current_score >= limit:
                    new_title = title
                    break
            cursor.execute("UPDATE players SET title = ? WHERE user_id = ?", (new_title, user_id))
            conn.commit()

# ------------------- نظام المتجر -------------------
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
        
    order_type_map = {"assets": "ملحقات", "draw": "رسم رسمة", "video": "فيديو تعاوني"}
    pending_orders[user_id] = {'type': order_type_map[item_key], 'price': price, 'state': 'waiting_flag'}
    bot.edit_message_text(f"✅ اخترت: **{order_type_map[item_key]}**\n\n🖼️ **الآن:** أرسل صورة علمك/دولتك للطلب.", call.message.chat.id, call.message.message_id)

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in pending_orders and pending_orders[m.from_user.id].get('state') == 'waiting_flag')
def handle_flag_photo(message):
    user_id = message.from_user.id
    pending_orders[user_id]['photo_id'] = message.photo[-1].file_id
    pending_orders[user_id]['state'] = 'waiting_painter'
    
    markup = InlineKeyboardMarkup()
    for painter in PAINTERS: 
        markup.row(InlineKeyboardButton(f"🖌️ {painter}", callback_data=f"painter:{painter}"))
    bot.reply_to(message, "📸 تم استلام العلم!\n👇 **الخطوة الأخيرة:** اختر الرسام لتنفيذ طلبك:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('painter:'))
def handle_painter_selection(call):
    user_id = call.from_user.id
    painter = call.data.split(':')[1] 
    
    if user_id not in pending_orders or pending_orders[user_id].get('state') != 'waiting_painter':
        return bot.answer_callback_query(call.id, "❌ الطلب منتهي.", show_alert=True)
        
    order, player = pending_orders[user_id], get_player(user_id)
    painter_username = painter.replace('@', '') 
    
    with db_lock:
        with get_db_connection() as conn:
            painter_data = conn.cursor().execute("SELECT user_id FROM players WHERE username = ?", (painter_username,)).fetchone()
        
    if not painter_data:
        bot.answer_callback_query(call.id, f"❌ الرسام {painter} غير مسجل!", show_alert=True)
        return bot.edit_message_text(f"⚠️ **عذراً!** الرسام {painter} لم يقم بتسجيل حسابه بالبوت (يجب أن يرسل /start).", call.message.chat.id, call.message.message_id)
        
    painter_chat_id = painter_data['user_id']
    
    if player['score'] < order['price']:
        del pending_orders[user_id]
        return bot.edit_message_text("❌ نقاطك لم تعد تكفي لإتمام الطلب!", call.message.chat.id, call.message.message_id)
        
    update_player(user_id, call.from_user.username, call.from_user.first_name, score=player['score'] - order['price'])
    
    order_text = f"🚨 **طلب مدفوع جديد من المتجر!** 🚨\n\n👤 **اللاعب:** {call.from_user.first_name} (@{call.from_user.username})\n📋 **الطلب:** {order['type']}\n\n⏱️ **ملاحظة:** يجب إنهاء الطلب خلال 24 ساعة!"
    try:
        bot.send_photo(painter_chat_id, order['photo_id'], caption=order_text)
        bot.edit_message_text(f"✅ **تمت العملية بنجاح!**\nخصمنا {order['price']} نقطة، وتم إرسال طلبك لحساب الرسام {painter}.", call.message.chat.id, call.message.message_id)
    except Exception:
        bot.edit_message_text(f"⚠️ فشل إرسال الطلب للرسام {painter} (قد يكون حظر البوت).", call.message.chat.id, call.message.message_id)
        
    del pending_orders[user_id]

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
                "🎲 **قائمة الألعاب (16 لعبة):**\n"
                "/g1 خمن الرقم | /g2 رياضيات | /g3 سرعة كتابة\n/g4 اعكس الكلمة | /g5 عواصم | /g6 رتب الحروف\n"
                "/g7 أكمل المثل | /g8 عد الإيموجي | /g9 عكس الكلمة\n/g10 أسرع كلمة | /g11 أسئلة ثقافية | /g12 ألغاز\n"
                "/g13 متتالية أرقام | /g14 ترجمة | /g15 إيموجي أفلام | /g16 اللهجات العربية 🔥\n\n"
                "🔥 وللاختيار العشوائي: /randomgame")
        bot.reply_to(message, text)
    elif cmd == "top":
        with db_lock:
            with get_db_connection() as conn:
                top = conn.cursor().execute("SELECT first_name, score, title FROM players ORDER BY score DESC LIMIT 10").fetchall()
        text = "🏆 **أفضل 10 لاعبين:**\n\n" + "\n".join([f"{i}. {p['title']} {p['first_name']} - {p['score']} نقطة" for i, p in enumerate(top, 1)])
        bot.reply_to(message, text)
    elif cmd == "daily":
        last = datetime.fromisoformat(player['last_daily'])
        time_since_last = datetime.now() - last
        
        if time_since_last >= timedelta(days=1):
            new_score = player['score'] + 50
            update_player(user.id, user.username, user.first_name, score=new_score)
            with db_lock:
                with get_db_connection() as conn:
                    conn.cursor().execute("UPDATE players SET last_daily = ? WHERE user_id = ?", (datetime.now().isoformat(), user.id))
                    conn.commit()
            bot.reply_to(message, f"🎁 استلمت 50 نقطة مجانية! نقاطك الآن أصبحت: {new_score} نقطة.")
        else:
            remaining_time = timedelta(days=1) - time_since_last
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            bot.reply_to(message, f"⏳ لقد استلمت مكافأتك مسبقاً يا وحش!\nعد بعد: **{hours} ساعة و {minutes} دقيقة** ⏱️")

@bot.message_handler(commands=[f'g{i}' for i in range(1, 17)] + ['randomgame'])
def start_specific_game(message):
    chat_id = message.chat.id
    with games_lock:
        if chat_id in active_games: 
            return bot.reply_to(message, "⏳ يا كابتن، في تحدي شغال أصلاً، خلصوه أول!")
        
    cmd = message.text.split()[0].split('@')[0].replace('/', '')
    game_id = random.randint(1, 16) if cmd == 'randomgame' else int(cmd.replace('g', ''))
    
    if game_id == 1: ans, q = str(random.randint(1, 100)), "🔢 خمن الرقم بين 1 و 100"
    elif game_id == 2:
        n1, n2, op = random.randint(10, 100), random.randint(1, 50), random.choice(['+', '-', '*'])
        ans, q = str(eval(f"{n1}{op}{n2}")), f"🧮 ناتج: {n1} {op} {n2} = ؟"
    elif game_id == 3: ans, q = (s:=random.choice(TYPING_SENTENCES)), f"⌨️ أسرع واحد يكتب الجملة:\n`{s}`"
    elif game_id == 4: ans, q = (w:=random.choice(SCRAMBLE_WORDS))[::-1], f"🔄 اعكس حروف الكلمة: **{w}**"
    elif game_id == 5: c, cap = random.choice(list(COUNTRIES.items())); ans, q = cap, f"🌍 ما هي عاصمة **{c}** ؟"
    elif game_id == 6: ans, q = (w:=random.choice(SCRAMBLE_WORDS)), f"🧩 رتب هذه الحروف لتكوين كلمة: **{''.join(random.sample(w, len(w)))}**"
    elif game_id == 7: h, m = random.choice(list(PROVERBS.items())); ans, q = m, f"📜 أكمل المثل الشعبي:\n{h} ... (كلمة واحدة)"
    elif game_id == 8:
        e, count = random.choice(["🍎", "🔥", "💎", "💣", "⚔️"]), random.randint(4, 9)
        emojis = [e]*count + [random.choice(["🍌", "🍉", "💧"])]*20; random.shuffle(emojis)
        ans, q = str(count), f"👀 كم مرة تكرر الإيموجي {e} هنا؟\n{''.join(emojis)}"
    elif game_id == 9: w, opp = random.choice(list(OPPOSITES.items())); ans, q = opp, f"↔️ ما هو عكس كلمة: **{w}** ؟"
    elif game_id == 10: ans, q = random.choice(FAST_WORDS), f"⚡ أسرع شخص يكتب الكلمة:\n**{ans}**"
    elif game_id == 11: qu, a = random.choice(list(TRIVIA.items())); ans, q = a, f"🧠 سؤال ثقافي:\n{qu}"
    elif game_id == 12: qu, a = random.choice(list(RIDDLES.items())); ans, q = a, f"🕵️‍♂️ لغز:\n{qu}"
    elif game_id == 13: 
        start, step = random.randint(1,10), random.randint(2,5)
        ans, q = str(start+4*step), f"🔢 أكمل المتتالية: {start}, {start+step}, {start+2*step}, {start+3*step}, ... ؟"
    elif game_id == 14: en, ar = random.choice(list(TRANSLATE_WORDS.items())); ans, q = ar, f"🇺🇸 ترجم للعربية: '{en}'"
    elif game_id == 15: em, mov = random.choice(list(EMOJI_GUESS.items())); ans, q = mov, f"🎬 خمن اسم الفيلم من الإيموجي: {em}"
    elif game_id == 16: qu, a = random.choice(list(DIALECTS.items())); ans, q = a, f"🗣️ **تحدي اللهجات العربية:**\n{qu}"

    with games_lock:
        active_games[chat_id] = ans.strip().lower()
        
    bot.send_message(chat_id, f"🎮 **تحدي جديد!**\n\n{q}\n\n⏳ لديكم 45 ثانية يا شباب!")
    threading.Timer(45.0, end_group_game, args=[chat_id, ans]).start()

def end_group_game(chat_id, correct_answer):
    with games_lock:
        if chat_id in active_games and active_games[chat_id] == correct_answer.strip().lower():
            del active_games[chat_id]
            timeout_msg = random.choice(funny_responses['timeout'])
            try: bot.send_message(chat_id, f"{timeout_msg}\n✅ الإجابة كانت: **{correct_answer}**")
            except: pass

@bot.message_handler(func=lambda m: m.chat.type in ["group", "supergroup"] and not m.text.startswith('/'))
def handle_group_answers(message):
    chat_id = message.chat.id
    
    # تحقق سريع بدون قفل ثقيل
    if chat_id not in active_games:
        return
        
    with games_lock:
        if chat_id in active_games and str(message.text).strip().lower() == active_games[chat_id]:
            ans = active_games.pop(chat_id)
            
            # تحديث بيانات الفائز
            update_player(message.from_user.id, message.from_user.username, message.from_user.first_name)
            player = get_player(message.from_user.id)
            update_player(message.from_user.id, message.from_user.username, message.from_user.first_name, score=player['score'] + 15)
            
            win_msg = random.choice(funny_responses['win']).format(name=message.from_user.first_name)
            bot.reply_to(message, f"{win_msg}\nالإجابة: {ans}\n🤑 أضفنا لك 15 نقطة!")

# ------------------- تشغيل البوت بشكل مستقر -------------------
if __name__ == "__main__":
    print("✅ البوت شغال ومحمي ضد التوقف...")
    # استخدام infinity_polling يمنع توقف البوت في حال حدوث خطأ في الاتصال
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

