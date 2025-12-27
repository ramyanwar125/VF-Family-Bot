import logging
import asyncio
import threading
import os
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import engine

# --- إعداد سيرفر Flask لفتح بورت ريندر ---
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "Bot is running and healthy!", 200

def run_web_server():
    port = int(os.environ.get("PORT", 5000))
    web_app.run(host='0.0.0.0', port=port)

# --- إعدادات البوت الأساسية ---
TOKEN = '8220448877:AAF8mDyfUgnUWKX5B3VBozRz6Yjac5a34SQ'
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

(MAIN, MB_SUB, FAM_SUB, GET_NUM, GET_PWD, GET_M_NUM, GET_M_PWD, GET_QUOTA, SELECT_FINAL) = range(9)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("💰 Money Back", callback_data='MB')],
          [InlineKeyboardButton("👨‍👩‍👧‍👦 Flex Family", callback_data='FAM')],
          [InlineKeyboardButton("🎁 Flex Discount", callback_data='FLX')]]
    text = "💎 **بوت فودافون الشامل**\nيرجى اختيار القسم المطلوبة من الأزرار:"
    markup = InlineKeyboardMarkup(kb)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')
    return MAIN

async def menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'MB':
        kb = [[InlineKeyboardButton("🔍 فحص رصيد", callback_data='MB_SCAN'), InlineKeyboardButton("🔄 استرداد باقة", callback_data='MB_REF')], 
              [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data='BACK')]]
        await query.edit_message_text("💰 **قسم Money Back**", reply_markup=InlineKeyboardMarkup(kb))
        return MB_SUB
    elif query.data == 'FAM':
        kb = [[InlineKeyboardButton("➕ إضافة عضو", callback_data='F_ADD'), InlineKeyboardButton("✅ قبول دعوة", callback_data='F_ACC')], 
              [InlineKeyboardButton("❌ حذف عضو", callback_data='F_REM'), InlineKeyboardButton("🤖 إضافة تلقائية", callback_data='F_AUTO')], 
              [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data='BACK')]]
        await query.edit_message_text("👨‍👩‍👧‍👦 **إدارة العائلة**", reply_markup=InlineKeyboardMarkup(kb))
        return FAM_SUB
    elif query.data == 'FLX':
        context.user_data['op'] = 'F_OFFER'
        kb = [[InlineKeyboardButton(f"⭐ {v['desc']}", callback_data=f"X_FLX_{k}")] for k, v in engine.PACKAGES.items()]
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data='BACK')])
        await query.edit_message_text("🎁 **اختر الباقة لتفعيل الخصم:**", reply_markup=InlineKeyboardMarkup(kb))
        return SELECT_FINAL

async def final_exe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'BACK': return await start(update, context)
    
    if "X_FLX_" in query.data:
        context.user_data['selected_pkg'] = query.data.replace("X_FLX_", "")
        await query.edit_message_text("📱 **أرسل رقم الهاتف الآن:**")
        return GET_NUM
    return MAIN

async def sub_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'BACK': return await start(update, context)
    context.user_data['op'] = query.data
    await query.edit_message_text("📱 **أرسل رقم الهاتف الأساسي:**")
    return GET_NUM

async def get_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['num'] = update.message.text
    await update.message.reply_text("🔑 **أرسل كلمة المرور:**")
    return GET_PWD

async def get_pwd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pwd'] = update.message.text
    op = context.user_data['op']
    if op.startswith('F_') and op != 'F_OFFER':
        await update.message.reply_text("👤 **أرسل رقم هاتف العضو:**")
        return GET_M_NUM
    return await run_process(update, context)

async def get_m_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['m_num'] = update.message.text
    op = context.user_data['op']
    if op in ['F_ADD', 'F_AUTO']:
        kb = [[InlineKeyboardButton("10% (1300 فليكس)", callback_data='1300')], 
              [InlineKeyboardButton("20% (2600 فليكس)", callback_data='2600')], 
              [InlineKeyboardButton("40% (5200 فليكس)", callback_data='5200')]]
        await update.message.reply_text("📊 **اختر النسبة:**", reply_markup=InlineKeyboardMarkup(kb))
        return GET_QUOTA
    elif op == 'F_ACC':
        await update.message.reply_text("🔑 **أرسل كلمة مرور العضو:**")
        return GET_M_PWD
    return await run_process(update, context)

async def handle_extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        context.user_data['quota'] = update.callback_query.data
        if context.user_data['op'] == 'F_AUTO':
            await update.callback_query.edit_message_text("🔑 **أرسل كلمة مرور العضو:**")
            return GET_M_PWD
    else: 
        context.user_data['m_pwd'] = update.message.text
    return await run_process(update, context)

async def run_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    msg = update.message if update.message else update.callback_query.message
    status = await msg.reply_text("⏳ **جاري التنفيذ...**")
    try:
        # استخدام asyncio.to_thread لتشغيل دوال engine المتزامنة دون تعطيل البوت
        token = await asyncio.to_thread(engine.get_token, ud['num'], ud['pwd'])
        op = ud['op']
        
        if op == 'MB_SCAN':
            res = await asyncio.to_thread(engine.run_money_back_scan, ud['num'], token)
            await status.edit_text(f"💰 **رصيد الماني باك:** `{res}` جنيه")
        elif op == 'F_OFFER':
            res = await asyncio.to_thread(engine.execute_flex_discount, ud['num'], token, ud['selected_pkg'])
            await status.edit_text("✅ تم تفعيل الخصم!" if res else "❌ الخط غير مؤهل")
        elif op == 'F_ADD':
            res = await asyncio.to_thread(engine.add_member_async, None, token, ud['num'], ud['m_num'], ud['quota'])
            await status.edit_text("✅ تم الإرسال" if res else "❌ فشل")
        elif op == 'F_ACC':
            mt = await asyncio.to_thread(engine.get_token, ud['m_num'], ud['m_pwd'])
            res = await asyncio.to_thread(engine.accept_invitation_async, None, ud['num'], ud['m_num'], mt)
            await status.edit_text("✅ تم القبول" if res else "❌ فشل")
        # يمكنك إضافة بقية الحالات هنا بنفس الطريقة
    except Exception as e: 
        await status.edit_text(f"⚠️ **خطأ:** `{str(e)}`")
    
    await asyncio.sleep(2)
    return ConversationHandler.END

def main():
    # تشغيل سيرفر Flask في خيط منفصل
    threading.Thread(target=run_web_server, daemon=True).start()
    
    # تشغيل البوت
    app = Application.builder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN: [CallbackQueryHandler(menu_click)],
            MB_SUB: [CallbackQueryHandler(sub_click)],
            FAM_SUB: [CallbackQueryHandler(sub_click)],
            GET_NUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_num)],
            GET_PWD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_pwd)],
            GET_M_NUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_m_num)],
            GET_M_PWD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_extra)],
            GET_QUOTA: [CallbackQueryHandler(handle_extra)],
            SELECT_FINAL: [CallbackQueryHandler(final_exe)]
        }, 
        fallbacks=[CommandHandler("start", start)]
    )
    
    app.add_handler(conv)
    print("🚀 Bot started with Flask server...")
    app.run_polling()

if __name__ == '__main__':
    main()
