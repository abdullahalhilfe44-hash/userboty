import os
import sqlite3
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

# بيانات التطبيق والحساب
API_ID = int(os.environ.get("API_ID", 2040))
API_HASH = os.environ.get("API_HASH", "b18441a1ff607e10a989891a5462e627")
STRING_SESSION = os.environ.get("STRING_SESSION", "")

# إضافة رقم الهاتف والـ ID الشخصي
PHONE_NUMBER = "+9647721606233"
USER_ID = 8164462667

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# إعداد قاعدة البيانات المحلية
db = sqlite3.connect("database.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS groups (
    key TEXT,
    chat_id INTEGER,
    msg_id INTEGER
)
""")
db.commit()

@client.on(events.NewMessage(incoming=True))
async def incoming(e):
    if e.is_private and not e.is_group:
        await e.forward_to("me")

@client.on(events.NewMessage(outgoing=True))
async def out(e):
    if e.is_private and e.chat_id == (await client.get_me()).id:
        t = e.raw_text.strip()
        target_chat = e.chat_id
        
        # 1. حفظ مجموعة: /مجموعة 1 1000
        if t.startswith("/مجموعة ") or t.startswith("/savegroup "):
            parts = t.split(" ")
            if len(parts) >= 2 and e.is_reply:
                try:
                    k = parts[1]
                    target_count = int(parts[2]) if len(parts) > 2 else 50
                    reply_msg = await e.get_reply_message()
                    start_id = reply_msg.id
                    
                    await e.edit(f"⏳ جاري فحص وسحب {target_count} مقطع...")
                    
                    cursor.execute("DELETE FROM groups WHERE key = ?", (k,))
                    db.commit()
                    
                    count = 0
                    search_limit = target_count * 15
                    
                    async for msg in client.iter_messages(target_chat, min_id=start_id - 1, limit=search_limit, reverse=True):
                        if msg.media:
                            cursor.execute("INSERT INTO groups (key, chat_id, msg_id) VALUES (?, ?, ?)", (k, target_chat, msg.id))
                            count += 1
                            if count >= target_count:
                                break
                    db.commit()
                    await e.edit(f"✅ تم حفظ {count} مقطع بنجاح تحت المفتاح: /{k}")
                except Exception as ex:
                    await e.edit(f"❌ حدث خطأ: {str(ex)}")
            else:
                await e.edit("❌ الاستخدام الصحيح: /مجموعة <المفتاح> <العدد> بالرد على أول مقطع")
        
        # 2. إضافة مقطع: /إضافة 1
        elif t.startswith("/إضافة ") or t.startswith("/add "):
            parts = t.split(" ")
            if len(parts) >= 2 and e.is_reply:
                try:
                    reply_msg = await e.get_reply_message()
                    if reply_msg and reply_msg.media:
                        k = parts[1]
                        cursor.execute("INSERT INTO groups (key, chat_id, msg_id) VALUES (?, ?, ?)", (k, target_chat, reply_msg.id))
                        db.commit()
                        
                        cursor.execute("SELECT COUNT(*) FROM groups WHERE key = ?", (k,))
                        total = cursor.fetchone()[0]
                        await e.edit(f"✅ تمت الإضافة للمفتاح: /{k}\n📁 الإجمالي: {total}")
                    else:
                        await e.edit("❌ الرسالة المحددة لا تحتوي على ميديا.")
                except Exception as ex:
                    await e.edit(f"❌ حدث خطأ: {str(ex)}")
            else:
                await e.edit("❌ الاستخدام الصحيح: /إضافة <المفتاح> بالرد على المقطع")
        
        # 3. حذف مفتاح: /حذف 1
        elif t.startswith("/حذف ") or t.startswith("/del ") or t.startswith("/delete "):
            try:
                k = t.split(" ")[1]
                cursor.execute("DELETE FROM groups WHERE key = ?", (k,))
                db.commit()
                await e.edit(f"🗑️ تم حذف المفتاح /{k} بنجاح!")
            except Exception:
                await e.edit("❌ الاستخدام الصحيح: /حذف <المفتاح>")
        
        # 4. لوحة المفاتيح التفاعلية الشاملة: /قائمة
        elif t == "/قائمة" or t == "/list" or t == "/keys" or t == "/مفاتيح":
            cursor.execute("SELECT DISTINCT key FROM groups")
            keys = cursor.fetchall()
            if keys:
                buttons = []
                row_buttons = []
                for idx, row in enumerate(keys):
                    k = row[0]
                    cursor.execute("SELECT COUNT(*) FROM groups WHERE key = ?", (k,))
                    count = cursor.fetchone()[0]
                    row_buttons.append(Button.inline(f"📁 /{k} ({count})", data=f"send_{k}".encode()))
                    if len(row_buttons) == 2:
                        buttons.append(row_buttons)
                        row_buttons = []
                if row_buttons:
                    buttons.append(row_buttons)
                
                buttons.append([Button.inline("🔄 تحديث القائمة", data="refresh_menu".encode())])
                
                await e.delete()
                await client.send_message(target_chat, "🎛️ **لوحة مفاتيح الوسائط السريعة:**\nاختر المفتاح للإرسال الفوري:", buttons=buttons)
            else:
                await e.edit("📭 لا توجد مفاتيح محفوظة حالياً.")
        
        # 5. إرسال مباشر بكتابة المفتاح مثل /1
        elif t.startswith("/"):
            k = t[1:]
            cursor.execute("SELECT msg_id FROM groups WHERE key = ?", (k,))
            msg_ids = cursor.fetchall()
            if msg_ids:
                await e.delete()
                for row in msg_ids:
                    try:
                        await client.send_message(target_chat, '', file=row[0])
                    except Exception:
                        pass

# التعامل مع الأزرار الشفافة التفاعلية
@client.on(events.CallbackQuery)
async def callback(event):
    data = event.data.decode()
    sender_id = event.chat_id
    
    if data.startswith("send_"):
        k = data.split("_")[1]
        cursor.execute("SELECT msg_id FROM groups WHERE key = ?", (k,))
        msg_ids = cursor.fetchall()
        if msg_ids:
            await event.answer(f"جاري إرسال مفتاح /{k}...")
            for row in msg_ids:
                try:
                    await client.send_message(sender_id, '', file=row[0])
                except Exception:
                    pass
        else:
            await event.answer("المفتاح غير موجود!", alert=True)
            
    elif data == "refresh_menu":
        cursor.execute("SELECT DISTINCT key FROM groups")
        keys = cursor.fetchall()
        if keys:
            buttons = []
            row_buttons = []
            for row in keys:
                k = row[0]
                cursor.execute("SELECT COUNT(*) FROM groups WHERE key = ?", (k,))
                count = cursor.fetchone()[0]
                row_buttons.append(Button.inline(f"📁 /{k} ({count})", data=f"send_{k}".encode()))
                if len(row_buttons) == 2:
                    buttons.append(row_buttons)
                    row_buttons = []
            if row_buttons:
                buttons.append(row_buttons)
            buttons.append([Button.inline("🔄 تحديث القائمة", data="refresh_menu".encode())])
            
            await event.edit("🎛️ **لوحة مفاتيح الوسائط السريعة (محدثة):**", buttons=buttons)
            await event.answer("تم تحديث القائمة بنجاح!")
        else:
            await event.answer("لا توجد مفاتيح حالياً", alert=True)

print("Bot running securely with StringSession...")
client.start()
client.run_until_disconnected()
        
