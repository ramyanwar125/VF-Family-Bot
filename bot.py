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

# --- سيرفر Flask للبقاء مستيقظاً ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Alive"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- إعدادات البوت (Aiogram 3) ---
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
        [InlineKeyboardButton(text="🚀 تطيير أفراد", callback_data="op_FLY")],
        [InlineKeyboardButton(text="🔄 إعادة تشغيل", callback_data="start_over")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("💎 **بوت فودافون المتطور (نسخة Aiogram)**\nاختر الخدمة:", reply_markup=main_kb(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("op_"))
async def process_op(callback: types.CallbackQuery, state: FSMContext):
    op = callback.data.split("_")[1]
    await state.update_data(op=op)
    
    if op == "FLX":
        buttons = [[InlineKeyboardButton(text=v['desc'], callback_data=f"pkg_{k}")] for k, v in engine.PACKAGES.items()]
        await callback.message.edit_text("🎁 اختر باقة الخصم:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await callback.message.answer("📱 أرسل رقم المالك (Owner):")
        await state.set_state(Form.waiting_for_num)

@dp.callback_query(F.data.startswith("pkg_"))
async def process_pkg(callback: types.CallbackQuery, state: FSMContext):
    pkg = callback.data.split("_")[1]
    await state.update_data(pkg=pkg)
    await callback.message.answer("📱 أرسل رقم الهاتف:")
    await state.set_state(Form.waiting_for_num)

@dp.message(Form.waiting_for_num)
async def get_num(message: types.Message, state: FSMContext):
    await state.update_data(num=message.text)
    await message.answer("🔑 أرسل كلمة المرور:")
    await state.set_state(Form.waiting_for_pwd)

@dp.message(Form.waiting_for_pwd)
async def get_pwd(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(pwd=message.text)
    
    if data['op'] == 'FLY':
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
    await message.answer("📊 اختر نسبة الحصة:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("q_"))
async def final_fly(callback: types.CallbackQuery, state: FSMContext):
    quota = callback.data.split("_")[1]
    data = await state.get_data()
    await callback.message.edit_text("🚀 جاري التطيير المتزامن... انتظر لحظة.")
    
    async with aiohttp.ClientSession() as session:
        o_t = await engine.get_token_async(session, data['num'], data['pwd'])
        m_t = await engine.get_token_async(session, data['m_num'], data['m_pwd'])
        
        if o_t and m_t:
            tasks = [engine.add_member_async(session, o_t, data['num'], data['m_num'], quota) for _ in range(2)]
            results = await asyncio.gather(*tasks)
            if any(results):
                await asyncio.sleep(5)
                if await engine.accept_invitation_async(session, data['num'], data['m_num'], m_t):
                    await callback.message.answer("🎉 تم التطيير بنجاح عبر Aiogram!")
                else: await callback.message.answer("❌ فشل القبول التلقائي.")
            else: await callback.message.answer("❌ فشل الإرسال المزدوج.")
        else: await callback.message.answer("❌ خطأ في التوكنات.")
    await state.clear()

async def execute_simple_op(message, state):
    data = await state.get_data()
    msg = await message.answer("⏳ جاري المعالجة...")
    try:
        token = engine.get_token(data['num'], data['pwd'])
        if data['op'] == 'MB':
            res = engine.run_money_back_scan(data['num'], token)
            await msg.edit_text(f"💰 رصيد الماني باك: {res}")
        elif data['op'] == 'FLX':
            res = engine.execute_flex_discount(data['num'], token, data['pkg'])
            await msg.edit_text("✅ تم التفعيل!" if res else "❌ غير مؤهل")
    except Exception as e: await msg.edit_text(f"⚠️ خطأ: {e}")
    await state.clear()

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
