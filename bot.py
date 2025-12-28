import logging
import asyncio
import threading
import os
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import engine

# --- Web Server for Rendering ---
web_app = Flask(__name__)
@web_app.route('/')
def health(): return "Bot Active", 200

def run_web_server():
    port = int(os.environ.get("PORT", 5000))
    web_app.run(host='0.0.0.0', port=port)

# --- Bot Config ---
TOKEN = '8220448877:AAF8mDyfUgnUWKX5B3VBozRz6Yjac5a34SQ'
logging.basicConfig(level=logging.INFO)
(MAIN, MB_SUB, FAM_SUB, GET_NUM, GET_PWD, GET_M_NUM, GET_M_PWD, GET_QUOTA, SELECT_FINAL) = range(9)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("💰 Money Back", callback_data='MB')],
          [InlineKeyboardButton("👥 Flex Family", callback_data='FAM')],
          [InlineKeyboardButton("🎁 Flex Discount", callback_data='FLX')]]
    text = "✨ **مرحباً بك في بوت خدمات فودافون الذكي** ✨\nيرجى اختيار القسم:"
    markup = InlineKeyboardMarkup(kb)
    if update.callback_query: await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
    else: await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')
    return MAIN

async def menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'MB':
        kb = [[InlineKeyboardButton("🔍 فحص الرصيد", callback_data='MB_SCAN'), InlineKeyboardButton("🔄 استرداد", callback_data='MB_REF')], [InlineKeyboardButton("🔙 رجوع", callback_data='BACK')]]
        await query.edit_message_text("💰 **قسم Money Back**", reply_markup=InlineKeyboardMarkup(kb))
        return MB_SUB
    elif query.data == 'FAM':
        kb = [[InlineKeyboardButton("➕ إضافة", callback_data='F_ADD'), InlineKeyboardButton("✅ قبول", callback_data='F_ACC')], [InlineKeyboardButton("❌ حذف", callback_data='F_REM'), InlineKeyboardButton("🤖 تلقائي", callback_data='F_AUTO')], [InlineKeyboardButton("🔙 رجوع", callback_data='BACK')]]
        await query.edit_message_text("👥 **قسم Flex Family**", reply_markup=InlineKeyboardMarkup(kb))
        return FAM_SUB
    elif query.data == 'FLX':
        context.user_data['op'] = 'F_OFFER'
        kb = [[InlineKeyboardButton(f"⭐ {n}", callback_data=f"X_FLX_{f}")] for f, n in engine.FLEX_PACKAGES.items()]
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data='BACK')])
        await query.edit_message_text("🎁 **اختر باقة Flex Discount المستهدفة:**", reply_markup=InlineKeyboardMarkup(kb))
        return SELECT_FINAL

async def sub_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'BACK': return await start(update, context)
    context.user_data['op'] = query.data
    await query.edit_message_text("📱 أرسل **رقم الهاتف الأساسي**:")
    return GET_NUM

async def get_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['num'] = update.message.text
    await update.message.reply_text("🔑 أرسل **كلمة المرور**:")
    return GET_PWD

async def get_pwd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pwd'] = update.message.text
    op = context.user_data['op']
    if op.startswith('F_') and op != 'F_OFFER':
        await update.message.reply_text("👤 أرسل **رقم هاتف العضو**:")
        return GET_M_NUM
    return await run_process(update, context)

async def get_m_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['m_num'] = update.message.text
    op = context.user_data['op']
    if op in ['F_ADD', 'F_AUTO']:
        kb = [[InlineKeyboardButton("10%", callback_data='10'), InlineKeyboardButton("20%", callback_data='20'), InlineKeyboardButton("40%", callback_data='40')]]
        await update.message.reply_text("📊 **اختر نسبة توزيع الفليكسات:**", reply_markup=InlineKeyboardMarkup(kb))
        return GET_QUOTA
    elif op == 'F_ACC':
        await update.message.reply_text("🔑 أرسل **باسورد العضو** للقبول:")
        return GET_M_PWD
    return await run_process(update, context)

async def handle_extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        context.user_data['quota'] = update.callback_query.data
        if context.user_data['op'] == 'F_AUTO':
            await update.callback_query.edit_message_text("🔑 أرسل **باسورد العضو** للقبول التلقائي:")
            return GET_M_PWD
    else: context.user_data['m_pwd'] = update.message.text
    return await run_process(update, context)

async def run_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    msg = update.message if update.message else update.callback_query.message
    status = await msg.reply_text("⏳ **جاري التنفيذ...**")
    try:
        token = await asyncio.to_thread(engine.get_token, ud['num'], ud['pwd'])
        op = ud['op']
        
        if op == 'MB_SCAN':
            res = await asyncio.to_thread(engine.run_money_back, ud['num'], token, 'SCAN')
            await status.edit_text(f"💰 رصيد الماني باك الحالي: `{res}` ج.م", parse_mode='Markdown')
        elif op == 'F_OFFER':
            res = await asyncio.to_thread(engine.execute_order, ud['num'], token, ud['selected_pkg'], 'FLEX')
            await status.edit_text("✅ تم تفعيل Flex Discount بنجاح!" if res else "❌ فشل التفعيل.")
        elif op == 'F_ADD':
            res = await asyncio.to_thread(engine.family_op, ud['num'], token, ud['m_num'], 'SEND', ud['quota'])
            await status.edit_text("✅ تم إرسال الدعوة" if res else "❌ فشل الإرسال")
        elif op == 'F_ACC':
            mt = await asyncio.to_thread(engine.get_token, ud['m_num'], ud['m_pwd'])
            res = await asyncio.to_thread(engine.family_op, ud['num'], None, ud['m_num'], 'ACCEPT', m_token=mt)
            await status.edit_text("✅ تم قبول الدعوة بنجاح" if res else "❌ فشل القبول")
        elif op == 'F_AUTO':
            if await asyncio.to_thread(engine.family_op, ud['num'], token, ud['m_num'], 'SEND', ud['quota']):
                await asyncio.sleep(1)
                mt = await asyncio.to_thread(engine.get_token, ud['m_num'], ud['m_pwd'])
                res = await asyncio.to_thread(engine.family_op, ud['num'], None, ud['m_num'], 'ACCEPT', m_token=mt)
                await status.edit_text("🚀 تم الإضافة والقبول التلقائي بنجاح!" if res else "⚠️ تم الإرسال وفشل القبول.")
        elif op == 'F_REM':
            res = await asyncio.to_thread(engine.family_op, ud['num'], token, ud['m_num'], 'REMOVE')
            await status.edit_text("✅ تم حذف العضو بنجاح" if res else "❌ فشل الحذف")
            
    except Exception as e: await status.edit_text(f"❌ خطأ: `{str(e)}`", parse_mode='Markdown')
    await asyncio.sleep(2)
    return await start(update, context)

async def final_exe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'BACK': return await start(update, context)
    if "X_FLX_" in query.data:
        context.user_data['selected_pkg'] = query.data.replace("X_FLX_", "")
        await query.edit_message_text("📱 ممتاز! أرسل الآن **رقم الهاتف الأساسي**:")
        return GET_NUM
    elif "X_REF_" in query.data:
        tid, tk, n = query.data.replace("X_REF_", ""), context.user_data['tk'], context.user_data['num']
        res = await asyncio.to_thread(engine.execute_order, n, tk, tid, "REFUND")
        await query.edit_message_text("✅ تم الاسترداد بنجاح" if res else "❌ فشل الاسترداد")
        return await start(update, context)

def main():
    threading.Thread(target=run_web_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN: [CallbackQueryHandler(menu_click)], MB_SUB: [CallbackQueryHandler(sub_click)],
            FAM_SUB: [CallbackQueryHandler(sub_click)], GET_NUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_num)],
            GET_PWD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_pwd)],
            GET_M_NUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_m_num)],
            GET_M_PWD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_extra)],
            GET_QUOTA: [CallbackQueryHandler(handle_extra)], SELECT_FINAL: [CallbackQueryHandler(final_exe)]
        }, fallbacks=[CommandHandler("start", start)])
    app.add_handler(conv)
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
