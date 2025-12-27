import asyncio
import os
import threading
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import aiohttp
import engine

# --- سيرفر Flask لإبقاء البوت مستيقظاً على ريندر ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Alive"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- إعدادات Aiogram ---
TOKEN = '8220448877:AAF8mDyfUgnUWKX5B3VBozRz6Yjac5a34SQ'
bot = Bot(token=TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
    waiting_for_num = State()
    waiting_for_pwd = State()
    waiting_for_m_num = State()
    waiting_for_m_pwd = State()

def main_kb():
    buttons = [
        [InlineKeyboardButton(text="💰 ماني باك", callback_data="op_MB"),
         InlineKeyboardButton(text="🎁 خصم فليكس", callback_data="op_FLX")],
        [InlineKeyboardButton(text="👥 إضافة فليكس فاميلي", callback_data="op_ADD_FAM")],
        [InlineKeyboardButton(text="🚀 تطيير أفراد (ثغرة)", callback_data="op_FLY")],
        [InlineKeyboardButton(text="🔄 إعادة تشغيل", callback_data="start_over")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("💎 **مرحباً بك في بوت خدمات فودافون الشامل**\n\nاختر الخدمة المطلوبة من الأزرار أدناه:", 
                         reply_markup=main_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "start_over")
async def restart(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🔄 تم البدء من جديد. اختر الخدمة:", reply_markup=main_kb())

@dp.callback_query(F.data.startswith("op_"))
async def process_op(callback: types.CallbackQuery, state: FSMContext):
    op = callback.data.split("_")[1] if "ADD" not in callback.data else "ADD_FAM"
    await state.update_data(op=op)
    
    if op == "FLX":
        buttons = [[InlineKeyboardButton(text=v['desc'], callback_data=f"pkg_{k}")] for k, v in engine.PACKAGES.items()]
        await callback.message.edit_text("🎁 اختر باقة الخصم المستهدفة:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        text = "👤 أرسل رقم المالك (Owner):"
        await callback.message.answer(text)
        await state.set_state(Form.waiting_for_num)

@dp.callback_query(F.data.startswith("pkg_"))
async def process_pkg(callback: types.CallbackQuery, state: FSMContext):
    pkg = callback.data.split("_")[1]
    await state.update_data(pkg=pkg)
    await callback.message.answer("📱 أرسل رقم الهاتف المراد تفعيل الخصم عليه:")
    await state.set_state(Form.waiting_for_num)

@dp.message(Form.waiting_for_num)
async def get_num(message: types.Message, state: FSMContext):
    await state.update_data(num=message.text)
    await message.answer("🔑 أرسل كلمة مرور الحساب:")
    await state.set_state(Form.waiting_for_pwd)

@dp.message(Form.waiting_for_pwd)
async def get_pwd(message: types.Message, state: FSMContext):
    await state.update_data(pwd=message.text)
    data = await state.get_data()
    
    if data['op'] in ['FLY', 'ADD_FAM']:
        await message.answer("👥 أرسل رقم العضو (Member):")
        await state.set_state(Form.waiting_for_m_num)
    else:
        await execute_simple_op(message, state)

@dp.message(Form.waiting_for_m_num)
async def get_m_num(message: types.Message, state: FSMContext):
    await state.update_data(m_num=message.text)
    await message.answer("🔑 أرسل كلمة مرور العضو:")
    await state.set_state(Form.waiting_for_m_pwd)

@dp.message(Form.waiting_for_m_pwd)
async def get_m_pwd(message: types.Message, state: FSMContext):
    await state.update_data(m_pwd=message.text)
    buttons = [
        [InlineKeyboardButton(text="10%", callback_data="q_10"),
         InlineKeyboardButton(text="20%", callback_data="q_20"),
         InlineKeyboardButton(text="40%", callback_data="q_40")]
    ]
    await message.answer("📊 اختر نسبة توزيع الحصة:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("q_"))
async def final_family_process(callback: types.CallbackQuery, state: FSMContext):
    quota = callback.data.split("_")[1]
    data = await state.get_data()
    op = data.get('op')
    
    msg = await callback.message.edit_text("⏳ جاري بدء العملية...")
    
    async with aiohttp.ClientSession() as session:
        o_t = await engine.get_token_async(session, data['num'], data['pwd'])
        m_t = await engine.get_token_async(session, data['m_num'], data['m_pwd'])
        
        if not o_t or not m_t:
            await msg.edit_text("❌ فشل في جلب التوكنات. تأكد من الأرقام والباسورد.")
            return

        if op == "FLY":
            await msg.edit_text("🚀 جاري تنفيذ ثغرة التطيير المزدوج...")
            t1 = await engine.add_member_async(session, o_t, data['num'], data['m_num'], quota)
            await asyncio.sleep(0.1)
            t2 = await engine.add_member_async(session, o_t, data['num'], data['m_num'], quota)
            success = t1 or t2
        else:
            await msg.edit_text("⏳ جاري إضافة الفرد بشكل رسمي...")
            success = await engine.add_member_async(session, o_t, data['num'], data['m_num'], quota)

        if success:
            await msg.edit_text("⚡ نجح الطلب! جاري محاولة القبول تلقائياً...")
            await asyncio.sleep(6)
            if await engine.accept_invitation_async(session, data['num'], data['m_num'], m_t):
                await msg.answer("✅ تم بنجاح! الفرد الآن مضاف في المجموعة.")
            else:
                await msg.answer("⚠️ تم الإرسال لكن القبول التلقائي فشل. جرب القبول يدوياً.")
        else:
            await msg.edit_text("❌ فشلت العملية. قد يكون الخط غير مؤهل.")
    
    await state.clear()

async def execute_simple_op(message, state):
    data = await state.get_data()
    msg = await message.answer("⏳ جاري المعالجة...")
    try:
        token = engine.get_token(data['num'], data['pwd'])
        if data['op'] == 'MB':
            res = engine.run_money_back_scan(data['num'], token)
            await msg.edit_text(f"💰 رصيد الماني باك المتاح: {res} جنيه")
        elif data['op'] == 'FLX':
            res = engine.execute_flex_discount(data['num'], token, data['pkg'])
            await msg.edit_text("✅ تم تفعيل خصم الباقة بنجاح!" if res else "❌ الخط غير مؤهل لهذا الخصم")
    except Exception as e: await msg.edit_text(f"⚠️ خطأ: {e}")
    await state.clear()

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
