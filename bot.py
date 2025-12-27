import telebot
from telebot import types
import engine
import asyncio
import aiohttp
import os

# ضع توكن بوت التليجرام الخاص بك هنا أو استخدم متغيرات البيئة
TOKEN = '8320774023:AAFiFH3DMFZVI-njS3i-h50q4WmNwGpdpeg'
bot = telebot.TeleBot(TOKEN)

user_data = {}

def main_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 ماني باك", callback_data='MB'),
        types.InlineKeyboardButton("🎁 خصم فليكس", callback_data='FLX'),
        types.InlineKeyboardButton("🚀 تطيير أفراد", callback_data='F_FLY'),
        types.InlineKeyboardButton("🔄 إعادة تشغيل", callback_data='START')
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "💎 **مرحباً بك في بوت خدمات فودافون**\nاختر الخدمة المطلوبة:", 
                     reply_markup=main_markup(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    if call.data == 'START':
        bot.edit_message_text("تمت إعادة التشغيل. اختر خدمة:", chat_id, call.message.message_id, reply_markup=main_markup())
    
    elif call.data == 'MB':
        user_data[chat_id] = {'op': 'MB'}
        msg = bot.send_message(chat_id, "📱 أرسل رقم الهاتف المراد فحصه:")
        bot.register_next_step_handler(msg, get_num)
        
    elif call.data == 'FLX':
        user_data[chat_id] = {'op': 'FLX'}
        markup = types.InlineKeyboardMarkup()
        for k, v in engine.PACKAGES.items():
            markup.add(types.InlineKeyboardButton(v['desc'], callback_data=f"PKG_{k}"))
        bot.edit_message_text("🎁 اختر الباقة المستهدفة للخصم:", chat_id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith('PKG_'):
        user_data[chat_id]['pkg'] = call.data.split('_')[1]
        msg = bot.send_message(chat_id, "📱 أرسل رقم الهاتف:")
        bot.register_next_step_handler(msg, get_num)

    elif call.data == 'F_FLY':
        user_data[chat_id] = {'op': 'FLY'}
        msg = bot.send_message(chat_id, "👤 أرسل رقم المالك (Owner):")
        bot.register_next_step_handler(msg, get_num)

# --- تسلسل إدخال البيانات ---
def get_num(message):
    chat_id = message.chat.id
    user_data[chat_id]['num'] = message.text
    msg = bot.send_message(chat_id, "🔑 أرسل كلمة المرور:")
    bot.register_next_step_handler(msg, get_pwd)

def get_pwd(message):
    chat_id = message.chat.id
    user_data[chat_id]['pwd'] = message.text
    ud = user_data[chat_id]
    
    if ud['op'] == 'FLY':
        msg = bot.send_message(chat_id, "👥 أرسل رقم العضو:")
        bot.register_next_step_handler(msg, get_m_num)
    else:
        execute_process(message)

def get_m_num(message):
    chat_id = message.chat.id
    user_data[chat_id]['m_num'] = message.text
    msg = bot.send_message(chat_id, "🔑 أرسل كلمة مرور العضو:")
    bot.register_next_step_handler(msg, get_m_pwd)

def get_m_pwd(message):
    chat_id = message.chat.id
    user_data[chat_id]['m_pwd'] = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("10%", callback_data='Q_10'), 
               types.InlineKeyboardButton("20%", callback_data='Q_20'),
               types.InlineKeyboardButton("40%", callback_data='Q_40'))
    bot.send_message(chat_id, "📊 اختر نسبة الحصة:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('Q_'))
def set_quota_and_fly(call):
    chat_id = call.message.chat.id
    user_data[chat_id]['quota'] = call.data.split('_')[1]
    bot.answer_callback_query(call.id, "جاري بدء عملية التطيير...")
    asyncio.run(run_flying_async(chat_id))

# --- التنفيذ ---
def execute_process(message):
    chat_id = message.chat.id
    ud = user_data[chat_id]
    prog = bot.send_message(chat_id, "⏳ جاري المعالجة...")
    try:
        token = engine.get_token(ud['num'], ud['pwd'])
        if ud['op'] == 'MB':
            res = engine.run_money_back_scan(ud['num'], token)
            bot.edit_message_text(f"💰 رصيد الماني باك المتاح: {res} جنيه", chat_id, prog.message_id)
        elif ud['op'] == 'FLX':
            res = engine.execute_flex_discount(ud['num'], token, ud['pkg'])
            bot.edit_message_text("✅ تم تفعيل الخصم بنجاح!" if res else "❌ فشل التفعيل أو الخط غير مؤهل", chat_id, prog.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ خطأ: {str(e)}", chat_id, prog.message_id)

async def run_flying_async(chat_id):
    ud = user_data[chat_id]
    status = bot.send_message(chat_id, "🚀 جاري الإرسال المتزامن (A/B)...")
    async with aiohttp.ClientSession() as session:
        o_token = await engine.get_token_async(session, ud['num'], ud['pwd'])
        m_token = await engine.get_token_async(session, ud['m_num'], ud['m_pwd'])
        if not o_token or not m_token:
            bot.edit_message_text("❌ فشل جلب التوكنات.", chat_id, status.message_id)
            return
        tasks = [engine.add_member_async(session, o_token, ud['num'], ud['m_num'], ud['quota']) for _ in range(2)]
        results = await asyncio.gather(*tasks)
        if any(results):
            bot.edit_message_text("⚡ تم الإرسال! جاري محاولة القبول...", chat_id, status.message_id)
            await asyncio.sleep(5)
            if await engine.accept_invitation_async(session, ud['num'], ud['m_num'], m_token):
                bot.edit_message_text("🎉 تم التطيير بنجاح!", chat_id, status.message_id)
            else: bot.edit_message_text("❌ فشل القبول التلقائي.", chat_id, status.message_id)
        else: bot.edit_message_text("❌ فشل الإرسال المتزامن.", chat_id, status.message_id)

bot.infinity_polling()
