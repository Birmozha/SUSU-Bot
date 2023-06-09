import sqlite3
import os
import smtplib 
from email.mime.multipart import MIMEMultipart                 
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import asyncio


from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text




dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

TOKEN = os.environ.get('TOKEN')
MAIL_BOX = os.environ.get('MAIL_BOX')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')


choose_cat_text = 'Выбери категорию!'

cat_button_text = '<< К категориям'
cat_button = KeyboardButton(text=cat_button_text)

back_button_text = '<< Назад'
back_button = KeyboardButton(text=back_button_text)

bot = Bot(TOKEN, parse_mode='HTML')
dp = Dispatcher(bot, storage=MemoryStorage())

class InfoStates(StatesGroup):
    dialog = State()

class ComplainStates(StatesGroup):
    complain = State()
    wait_text = State()
    wait_photo = State()
    wait_choose = State()    
    additionals = State()

def findAllIkbs(ikbs: list, id):
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        ikb = cur.execute(
                """SELECT qid FROM tree WHERE pid IS (?) AND properties LIKE '%<additionals>' """, (id, )
                ).fetchone()
        if ikb:
            ikbs.append(ikb[0])
            return findAllIkbs(ikbs, ikb[0])
        else:
            return ikbs

# ОБРАБОТЧИК КОМАНДЫ /start
@dp.message_handler(commands=['start'], state=['*'])
async def start(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action='typing')
    await state.finish()
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        # ОТБОР ID ПЕРВОГО ЭЛЕМЕНТА ИЗ БАЗЫ ДАННЫХ
        qid, prop = cur.execute(
            """SELECT qid, properties FROM tree WHERE pid IS NULL AND properties LIKE '<text>%' """
            ).fetchall()[0]
        prop = prop.split(', ')[1]
        # КОНВЕРТАЦИЯ ID В ТЕКСТ ДЛЯ ОТПРАВКИ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ
        text = cur.execute(
            """SELECT text FROM data WHERE id IS (?) """, (qid, )
            ).fetchone()[0]
        # ОТБОР ДОЧЕРНИХ ЭЛЕМЕНТОВ (КНОПОК)
        bid = cur.execute(
            """SELECT qid FROM tree WHERE pid IS (?) AND properties is '<button>' """, (qid, )
            ).fetchall() 
        ikbs = []
        kbs = []
        for id in bid:
            # СОЗДАНИЕ СПИСКА ИНЛАЙН-КНОПОК
            if prop == '<ikb>':
                ikbs.append(cur.execute(
                    """SELECT text, id FROM data WHERE id IS (?) """, (id)
                    ).fetchone())
            # СОЗДАНИЕ СПИСКА ОБЫЧНЫХ КНОПОК
            elif prop == '<kb>':
                kbs.append(cur.execute(
                    """SELECT text FROM data WHERE id IS (?) """, (id)
                    ).fetchone())
    
    # СОЗДАНИЕ КЛАВИАТУРЫ
    if ikbs:
        buttonsText = [button for button in ikbs] # СОЗДАНИЕ СПИСКА ТИПА [('Text', ID), ('Text', ID), ...]
        # СОЗДАНИЕ КЛАВИАТУРЫ КЛАССА Inline
        kb = InlineKeyboardMarkup(row_width=1
                                  ).add(*[InlineKeyboardButton(text=text, callback_data=qid) for text, qid in buttonsText]) # ДОБАВЛЕНИЕ КНОПОК
        await message.answer(text=text, reply_markup=kb)
    elif kbs:
        buttonsText = [button[0] for button in kbs] # СОЗДАНИЕ СПИСКА ТИПА ['Text', 'Text', ...]
        # СОЗДАНИЕ КЛАВИАТУРЫ КЛАССА Reply
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True
                                 ).add(*[KeyboardButton(text=text) for text in buttonsText]) #ДОБАВЛЕНИЕ КНОПОК
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ
        await message.answer(text=text,
                             reply_markup=kb) # ПЕРЕДАЧА КЛАВИТАУРЫ В TELEGRAM
    else:
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ, ЕСЛИ КНОПОК НЕТ
        await message.answer(text=text)


@dp.message_handler(Text(equals=cat_button_text), state=['*'])
async def goCat(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action='typing')
    await state.finish()
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        # ОТБОР ID ПЕРВОГО ЭЛЕМЕНТА ИЗ БАЗЫ ДАННЫХ
        qid, prop = cur.execute(
            """SELECT qid, properties FROM tree WHERE pid IS NULL AND properties LIKE '<text>%' """
            ).fetchall()[0]
        prop = prop.split(', ')[1]
        # КОНВЕРТАЦИЯ ID В ТЕКСТ ДЛЯ ОТПРАВКИ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ
        # ОТБОР ДОЧЕРНИХ ЭЛЕМЕНТОВ (КНОПОК)
        bid = cur.execute(
            """SELECT qid FROM tree WHERE pid IS (?) AND properties is '<button>' """, (qid, )
            ).fetchall() 
        ikbs = []
        kbs = []
        for id in bid:
            # СОЗДАНИЕ СПИСКА ИНЛАЙН-КНОПОК
            if prop == '<ikb>':
                ikbs.append(cur.execute(
                    """SELECT text, id FROM data WHERE id IS (?) """, (id)
                    ).fetchone())
            # СОЗДАНИЕ СПИСКА ОБЫЧНЫХ КНОПОК
            elif prop == '<kb>':
                kbs.append(cur.execute(
                    """SELECT text FROM data WHERE id IS (?) """, (id)
                    ).fetchone())
    
    # СОЗДАНИЕ КЛАВИАТУРЫ
    if ikbs:
        buttonsText = [button for button in ikbs] # СОЗДАНИЕ СПИСКА ТИПА [('Text', ID), ('Text', ID), ...]
        # СОЗДАНИЕ КЛАВИАТУРЫ КЛАССА Inline
        kb = InlineKeyboardMarkup(row_width=1
                                  ).add(*[InlineKeyboardButton(text=text, callback_data=qid) for text, qid in buttonsText]) # ДОБАВЛЕНИЕ КНОПОК
        await message.answer(text=choose_cat_text, reply_markup=kb)
    elif kbs:
        buttonsText = [button[0] for button in kbs] # СОЗДАНИЕ СПИСКА ТИПА ['Text', 'Text', ...]
        # СОЗДАНИЕ КЛАВИАТУРЫ КЛАССА Reply
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True
                                 ).add(*[KeyboardButton(text=text) for text in buttonsText]) #ДОБАВЛЕНИЕ КНОПОК
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ
        await message.answer(text=choose_cat_text,
                             reply_markup=kb) # ПЕРЕДАЧА КЛАВИТАУРЫ В TELEGRAM
    else:
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ, ЕСЛИ КНОПОК НЕТ
        await message.answer(text=choose_cat_text)




@dp.message_handler(state=ComplainStates.additionals)
async def additionals(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action='typing')
    async with state.proxy() as st:
        pid = st['prev']
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        pids = cur.execute(
            """SELECT qid FROM tree WHERE pid is (?) """, (pid, )
        ).fetchall()
        if not pids:
            return await state.finish()
        for el in pids:
            temp = cur.execute(
                """SELECT data.id FROM data, tree WHERE data.text is (?) AND data.id IS (?) """, (message.text, el[0])
            ).fetchone()
            if temp:
                temp = temp[0]
                break
        qid, prop = cur.execute(
            """SELECT qid, properties FROM tree WHERE pid IS (?) and properties LIKE '<text>%' """, (temp, )
            ).fetchall()[0]
        prop = prop.split(', ')[1]
        if prop == '<choosecat>':
            await ComplainStates.wait_choose.set()
        elif prop == '<waitphoto>':
            await ComplainStates.wait_photo.set()
            cure = await state.get_state()
        elif prop == '<waittext>':
            await ComplainStates.wait_text.set()
        elif prop == '<additionals>':
            await ComplainStates.additionals.set()
            
        text = cur.execute(
            """SELECT data.text FROM data, tree WHERE data.id IS (?) AND tree.pid IN (SELECT qid FROM tree WHERE pid is (?)) """, (qid, pid)
            ).fetchone()[0]
        # ОТБОР ДОЧЕРНИХ ЭЛЕМЕНТОВ (КНОПОК)
        bid = cur.execute(
            """SELECT qid FROM tree WHERE pid IS (?) AND properties LIKE '<button%' """, (qid, )
            ).fetchall()
        kbs = []
        for id in bid:
            kbs.append(cur.execute(
                """SELECT text FROM data WHERE id IS (?) """, (id)
                ).fetchone())
    if not text:
        await state.finish()
    if kbs:
        buttonsText = [button[0] for button in kbs] # СОЗДАНИЕ СПИСКА ТИПА ['Text', 'Text', ...]
        # СОЗДАНИЕ КЛАВИАТУРЫ
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True
                                 ).add(*[KeyboardButton(text=text) for text in buttonsText]) # ДОБАВЛЕНИЕ КНОПОК
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ
        await message.answer(text=text,
                             reply_markup=kb) # ПЕРЕДАЧА КЛАВИТАУРЫ В TELEGRAM
    else:
        if prop == '<additionals>':
            await state.finish()
            await message.answer(text=text, reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(cat_button))
        else:
            await message.answer(text=text)
        
    async with state.proxy() as st:
        st['prev'] = qid

@dp.message_handler(state=ComplainStates.wait_choose)
async def waitText(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action='typing')
    async with state.proxy() as st:
        pid = st['prev']
    async with state.proxy() as st:
        st['complain'].append(message.text)
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        # НАХОЖДЕНИЕ ID ПОЛУЧЕННОГО ТЕКСТОВОГО СООБЩЕНИЯ (ВОПРОСА)
        pids = cur.execute(
            """SELECT qid FROM tree WHERE pid is (?) """, (pid, )
        ).fetchall()
        for el in pids:
            temp = cur.execute(
                """SELECT data.id FROM data, tree WHERE data.text is (?) AND data.id IS (?) """, (message.text, el[0])
            ).fetchone()
            if temp:
                temp = temp[0]
                break
        # ОТБОР ИЗ БАЗЫ ДАННЫХ ДОЧЕРНЕГО ID ЭЛЕМЕНТА К ID ТЕКСТОВОГО СООБЩЕНИЯ
        qid, prop = cur.execute(
            """SELECT qid, properties FROM tree WHERE pid IS (?) and properties LIKE '<text>%' """, (temp, )
            ).fetchall()[0]
        prop = prop.split(', ')[1]
        # КОНВЕРТАЦИЯ ID В ТЕКСТ ДЛЯ ОТПРАВКИ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ
        text = cur.execute(
            """SELECT data.text FROM data, tree WHERE data.id IS (?) AND tree.pid IN (SELECT qid FROM tree WHERE pid is (?)) """, (qid, pid)
            ).fetchone()[0]
        # ОТБОР ДОЧЕРНИХ ЭЛЕМЕНТОВ (КНОПОК)
        bid = cur.execute(
            """SELECT qid FROM tree WHERE pid IS (?) AND properties LIKE '<button%' """, (qid, )
            ).fetchall()
        kbs = []
        if not bid:
            texts = []
            findAllIkbs(texts, qid)
        else:  
            for id in bid:
                kbs.append(cur.execute(
                    """SELECT text FROM data WHERE id IS (?) """, (id)
                    ).fetchone())
    if prop == '<choosecat>':
        await ComplainStates.wait_choose.set()
    elif prop == '<waitphoto>':
        await ComplainStates.wait_photo.set()
    elif prop == '<waittext>':
        await ComplainStates.wait_text.set()
    elif prop == '<additionals>':
        await ComplainStates.additionals.set()
    
    if kbs:
        buttonsText = [button[0] for button in kbs] 
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True
                                 ).add(*[KeyboardButton(text=text) for text in buttonsText])
        await message.answer(text=text,
                             reply_markup=kb)
        async with state.proxy() as st:
                st['prev'] = qid
    else:
        if texts:
            last_id = texts[-1]
            with sqlite3.connect('data.db') as db:
                cur = db.cursor()
                bid = cur.execute("""SELECT qid FROM tree WHERE pid is (?) AND properties LIKE '<button%' """, (last_id, )).fetchall()
            for n, text in enumerate(texts):
                with sqlite3.connect('data.db') as db:
                    cur = db.cursor()
                    text = cur.execute("""SELECT text FROM data WHERE id is (?) """, (text, )).fetchone()[0]
                texts[n] = text
            for text in texts[:-1]:
                await bot.send_message(chat_id=message.from_user.id, text=text)
            kbs = []
            if bid:
                for id in bid:
                    kbs.append(cur.execute(
                        """SELECT text FROM data WHERE id IS (?) """, (id)
                        ).fetchone())
                buttonsText = [button[0] for button in kbs]
                kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True
                                 ).add(*[KeyboardButton(text=text) for text in buttonsText])
                await message.answer(text=texts[-1], reply_markup=kb)
                async with state.proxy() as st:
                    st['prev'] = last_id
            else:
                await message.answer(text=texts[-1], reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(cat_button))
        else:
            if prop == '<additionals>':
                await message.answer(text=text, reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(cat_button))
            else:
                await message.answer(text=text)
            async with state.proxy() as st:
                st['prev'] = qid
     

@dp.message_handler(content_types=['any'], state=ComplainStates.wait_photo)
async def waitPhoto(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action='typing')
    async with state.proxy() as st:
        pid = st['prev']
        cat = st['complain'][0]
        
    if message.photo:
        await message.photo[-1].download(destination_file=f'photos/{cat}-{message.message_id}.jpg')
        async with state.proxy() as st:
            st['photo_path'] = f'photos/{cat}-{message.message_id}.jpg'
            st['photo_name'] = f'{cat}-{message.message_id}.jpg'
        with sqlite3.connect('data.db') as db:
            cur = db.cursor()
            next = cur.execute("""
                        SELECT qid FROM tree WHERE pid is (?)
                        """, (pid, )).fetchall()
            if not next:
                async with state.proxy() as st:
                    t = st['complain'][1:]
                    photo_path = st['photo_path']
                    photo_name = st['photo_name']
                addr_from = MAIL_BOX
                addr_to = MAIL_BOX
                msg = MIMEMultipart()
                msg['From'] = addr_from
                msg['To'] = addr_to
                msg['Subject'] = f'Новая жалоба: {cat}'
                body = ''
                for el in t:
                    body += f'{el}\n'
                msg.attach(MIMEText(body, 'plain'))
                with open(f'{photo_path}', 'rb') as fp:
                    img = MIMEImage(fp.read())
                    img.add_header('Content-Disposition', 'attachment', filename=f"{photo_name}")
                    msg.attach(img)
                smtpObj = smtplib.SMTP('smtp.mail.ru')
                smtpObj.starttls()
                smtpObj.login(addr_from, MAIL_PASSWORD)
                smtpObj.send_message(msg)
                smtpObj.quit()
                await state.finish()
                return await message.answer(text='Спасибо, ваша жалоба сохранена')
        with sqlite3.connect('data.db') as db:
            cur = db.cursor()
            qid, prop = cur.execute(
                """SELECT qid, properties FROM tree WHERE pid IS (?) and properties LIKE '<text>%' """, (pid, )
                ).fetchall()[0]
            prop = prop.split(', ')[1]
            # КОНВЕРТАЦИЯ ID В ТЕКСТ ДЛЯ ОТПРАВКИ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ
            text = cur.execute("""
                            SELECT text FROM data WHERE id IS (?)
                            """, (qid, )).fetchone()[0]
            kbs = []
            if prop == '<choosecat>':
                bid = cur.execute(
                    """SELECT qid FROM tree WHERE pid IS (?) AND properties LIKE '<button%' """, (qid, )
                    ).fetchall()
                for id in bid:
                    kbs.append(cur.execute(
                        """SELECT text FROM data WHERE id IS (?) """, (id)
                        ).fetchone())
        if prop == '<choosecat>':
            await ComplainStates.wait_choose.set()
        elif prop == '<waitphoto>':
            await ComplainStates.wait_photo.set()
        elif prop == '<waittext>':
            await ComplainStates.wait_text.set()
        
        if kbs:
            buttonsText = [button[0] for button in kbs] # СОЗДАНИЕ СПИСКА ТИПА ['Text', 'Text', ...]
            # СОЗДАНИЕ КЛАВИАТУРЫ
            kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True
                                    ).add(*[KeyboardButton(text=text) for text in buttonsText]) # ДОБАВЛЕНИЕ КНОПОК
            # ОТПРАВКА СООБЩЕНИЯ БОТОМ
            await message.answer(text=text,
                                reply_markup=kb) # ПЕРЕДАЧА КЛАВИТАУРЫ В TELEGRAM
        else:
            # ОТПРАВКА СООБЩЕНИЯ БОТОМ, ЕСЛИ КНОПОК НЕТ
            await message.answer(text=text)
        
        async with state.proxy() as st:
            st['prev'] = qid
        
    else:
        await message.reply(text='Пожалуйста, пришлите фото')
    
    

@dp.message_handler(state=ComplainStates.wait_text)
async def waitText(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action='typing')
    async with state.proxy() as st:
        pid = st['prev']
        st['complain'].append(message.text)
        cat = st['complain'][0]
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        next = cur.execute("""
                        SELECT qid FROM tree WHERE pid is (?)
                        """, (pid, )).fetchall()
        if not next:
            async with state.proxy() as st:
                t = st['complain']
                photo_path = st['photo_path']
                photo_name = st['photo_name']
            addr_from = MAIL_BOX
            addr_to = MAIL_BOX
            msg = MIMEMultipart()
            msg['From'] = addr_from
            msg['To'] = addr_to
            msg['Subject'] = f'Новая жалоба: {cat}'
            body = ''
            for el in t:
                body += f'{el}\n'
            msg.attach(MIMEText(body, 'plain'))
            # await asyncio.sleep(1)
            if photo_path:
                with open(f'{photo_path}', 'rb') as fp:
                    img = MIMEImage(fp.read())
                    img.add_header('Content-Disposition', 'attachment', filename=f"{photo_name}")
                    msg.attach(img)
            smtpObj = smtplib.SMTP('smtp.mail.ru')
            smtpObj.starttls()
            smtpObj.login(addr_from, MAIL_PASSWORD)
            smtpObj.send_message(msg)
            smtpObj.quit()
            await state.finish()
            return await message.answer(text='Спасибо, ваша жалоба сохранена')
        qid, prop = cur.execute(
            """SELECT qid, properties FROM tree WHERE pid IS (?) and properties LIKE '<text>%' """, (pid, )
            ).fetchall()[0]
        prop = prop.split(', ')[1]
        # КОНВЕРТАЦИЯ ID В ТЕКСТ ДЛЯ ОТПРАВКИ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ
        text = cur.execute("""
                           SELECT text FROM data WHERE id IS (?)
                           """, (qid, )).fetchone()[0]
        kbs = []
        if prop == '<choosecat>':
            bid = cur.execute(
                """SELECT qid FROM tree WHERE pid IS (?) AND properties LIKE '<button%' """, (qid, )
                ).fetchall()
            for id in bid:
                kbs.append(cur.execute(
                    """SELECT text FROM data WHERE id IS (?) """, (id)
                    ).fetchone())
    if prop == '<choosecat>':
        await ComplainStates.wait_choose.set()
    elif prop == '<waitphoto>':
        await ComplainStates.wait_photo.set()
    elif prop == '<waittext>':
        await ComplainStates.wait_text.set()
    
    if kbs:
        buttonsText = [button[0] for button in kbs] # СОЗДАНИЕ СПИСКА ТИПА ['Text', 'Text', ...]
        # СОЗДАНИЕ КЛАВИАТУРЫ
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True
                                 ).add(*[KeyboardButton(text=text) for text in buttonsText]) # ДОБАВЛЕНИЕ КНОПОК
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ
        await message.answer(text=text,
                             reply_markup=kb) # ПЕРЕДАЧА КЛАВИТАУРЫ В TELEGRAM
    else:
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ, ЕСЛИ КНОПОК НЕТ
        await message.answer(text=text)
    
    async with state.proxy() as st:
        st['prev'] = qid
     


@dp.callback_query_handler(state=ComplainStates.complain)
async def complainStart(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.data == 'continue':
        async with state.proxy() as st:
            search_id = st['start']
            st['photo_path'] = None
            st['photo_name'] = None
    else:
        search_id = callback.data
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        # ОТБОР  ИЗ БАЗЫ ДАННЫХ ДОЧЕРНЕГО ID ЭЛЕМЕНТА К ПОЛУЧЕННОМУ ID ОТ CALLBACK-ЗАПРОСА
        qid, prop = cur.execute(
            """SELECT qid, properties FROM tree WHERE pid IS (?) and properties LIKE '<text>%' """, (search_id, )
            ).fetchall()[0]
        prop = prop.split(', ')[1]
        # КОНВЕРТАЦИЯ ID В ТЕКСТ ДЛЯ ОТПРАВКИ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ
        text = cur.execute(
            """SELECT text FROM data WHERE id IS (?) """, (qid, )
            ).fetchone()[0]
        # ОТБОР ДОЧЕРНИХ ЭЛЕМЕНТОВ (КНОПОК)
        bid = cur.execute(
            """SELECT qid FROM tree WHERE pid IS (?) AND properties LIKE '<button%' """, (qid, )
            ).fetchall()
        kbs = []
        for id in bid:
            # СОЗДАНИЕ СПИСКА ИНЛАЙН-КНОПОК
            kbs.append(cur.execute(
                """SELECT text FROM data WHERE id IS (?) """, (id)
                ).fetchone())
    if prop == '<choosecat>':
        await ComplainStates.wait_choose.set()
    elif prop == '<waitphoto>':
        await ComplainStates.wait_photo.set()
    elif prop == '<waittext>':
        await ComplainStates.wait_text.set()
    elif prop == '<additionals>':
        await ComplainStates.additionals.set()
    if kbs:
        buttonsText = [button[0] for button in kbs] # СОЗДАНИЕ СПИСКА ТИПА ['Text', 'Text', ...]
        # СОЗДАНИЕ КЛАВИАТУРЫ
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True
                                 ).add(*[KeyboardButton(text=text) for text in buttonsText]) # ДОБАВЛЕНИЕ КНОПОК
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ
        await callback.message.answer(text=text,
                                      reply_markup=kb) # ПЕРЕДАЧА КЛАВИТАУРЫ В TELEGRAM
    else:
        await state.finish()
        if prop == '<additionals>':
            await callback.message.answer(text=text, reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(cat_button))
        else:
            await callback.message.answer(text=text)
    async with state.proxy() as st:
        st['prev'] = qid

# ОБРАБОТЧИК INLINE-КНОПОК 
@dp.callback_query_handler(state=InfoStates.dialog)
async def dialog(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.data == 'continue':
        async with state.proxy() as db:
                search_id = db['start']
    else:
        search_id = callback.data
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        # ОТБОР  ИЗ БАЗЫ ДАННЫХ ДОЧЕРНЕГО ID ЭЛЕМЕНТА К ПОЛУЧЕННОМУ ID ОТ CALLBACK-ЗАПРОСА
        qid, prop = cur.execute(
            """SELECT qid, properties FROM tree WHERE pid IS (?) and properties LIKE '<text>%' """, (search_id, )
            ).fetchall()[0]
        prop = prop.split(', ')[1]
        # КОНВЕРТАЦИЯ ID В ТЕКСТ ДЛЯ ОТПРАВКИ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ
        text = cur.execute(
            """SELECT text FROM data WHERE id IS (?) """, (qid, )
            ).fetchone()[0]
        # ОТБОР ДОЧЕРНИХ ЭЛЕМЕНТОВ (КНОПОК)
        bid = cur.execute(
            """SELECT qid FROM tree WHERE pid IS (?) AND properties LIKE '<button%' """, (qid, )
            ).fetchall()
        ikbs = []
        kbs = []
        for id in bid:
            # СОЗДАНИЕ СПИСКА ИНЛАЙН-КНОПОК
            if prop == '<ikb>':
                ikbs.append(cur.execute(
                    """SELECT text, id FROM data WHERE id IS (?) """, (id)
                    ).fetchone())
            # СОЗДАНИЕ СПИСКА ОБЫЧНЫХ КНОПОК
            elif prop == '<kb>':
                kbs.append(cur.execute(
                    """SELECT text FROM data WHERE id IS (?) """, (id)
                    ).fetchone())
    
        
    if ikbs:
        buttonsText = [button for button in ikbs] # СОЗДАНИЕ СПИСКА ТИПА [('Text', ID), ('Text', ID), ...]
        # СОЗДАНИЕ КЛАВИАТУРЫ
        kb = InlineKeyboardMarkup(row_width=1
                                  ).add(*[InlineKeyboardButton(text=text, callback_data=qid) for text, qid in buttonsText]) # ДОБАВЛЕНИЕ КНОПОК
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ
        await callback.message.answer(text=text,
                                      reply_markup=kb) # ПЕРЕДАЧА КЛАВИТАУРЫ В TELEGRAM

    elif kbs:
        buttonsText = [button[0] for button in kbs] # СОЗДАНИЕ СПИСКА ТИПА ['Text', 'Text', ...]
        # СОЗДАНИЕ КЛАВИАТУРЫ
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True
                                 ).add(*[KeyboardButton(text=text) for text in buttonsText]) # ДОБАВЛЕНИЕ КНОПОК
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ
        await callback.message.answer(text=text,
                                      reply_markup=kb) # ПЕРЕДАЧА КЛАВИТАУРЫ В TELEGRAM
    else:
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ, ЕСЛИ КНОПОК НЕТ
        await callback.message.answer(text=text)
    async with state.proxy() as st:
        st['prev'] = qid


@dp.message_handler(Text(equals=back_button_text), state=InfoStates.dialog)
async def goBack(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action='typing')
    async with state.proxy() as st:
        pid = st['prev']
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        prev = cur.execute(
            """SELECT pid FROM tree WHERE qid is (?) """, (pid, )
        ).fetchone()[0]
        prev = cur.execute(
            """SELECT pid FROM tree WHERE qid is (?) """, (prev, )
        ).fetchone()[0]
        pids = cur.execute(
            """SELECT qid FROM tree WHERE pid is (?) """, (prev, )
        ).fetchall()
        if cur.execute("""SELECT pid FROM tree WHERE qid is (?) """, (prev, )).fetchone()[0] == 2:
            return await message.answer(text='Вы получили ответы на все вопросы')
    kbs = []
    for id in pids:
        kbs.append(cur.execute(
                        """SELECT text FROM data WHERE id IS (?) """, (id)
                        ).fetchone())
    buttonsText = [button[0] for button in kbs]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True
                                 ).add(*[KeyboardButton(text=text) for text in buttonsText]).add(back_button)
    async with state.proxy() as st:
        st['prev'] = prev
    await message.answer(text='Вернул назад', reply_markup=kb)

# ОБРАБОТЧИК ТЕКСТОВОГО СООБЩЕНИЯ
@dp.message_handler(state=InfoStates.dialog)
async def dialog(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action='typing')
    async with state.proxy() as st:
        pid = st['prev']
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        # НАХОЖДЕНИЕ ID ПОЛУЧЕННОГО ТЕКСТОВОГО СООБЩЕНИЯ (ВОПРОСА)
        pids = cur.execute(
            """SELECT qid FROM tree WHERE pid is (?) """, (pid, )
        ).fetchall()
        for el in pids:
            temp = cur.execute(
                """SELECT id FROM data WHERE text is (?) AND id IS (?) """, (message.text, el[0])
            ).fetchone()
            if temp:
                temp = temp[0]
                break
        
        # ОТБОР ИЗ БАЗЫ ДАННЫХ ДОЧЕРНЕГО ID ЭЛЕМЕНТА К ID ТЕКСТОВОГО СООБЩЕНИЯ
        qid, prop = cur.execute(
            """SELECT qid, properties FROM tree WHERE pid IS (?) and properties LIKE '<text>%' """, (temp, )
            ).fetchall()[0]
        prop = prop.split(', ')[1]
        # КОНВЕРТАЦИЯ ID В ТЕКСТ ДЛЯ ОТПРАВКИ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ
        text = cur.execute(
            """SELECT data.text FROM data, tree WHERE data.id IS (?) AND tree.pid IN (SELECT qid FROM tree WHERE pid is (?)) """, (qid, pid)
            ).fetchone()[0]
        # ОТБОР ДОЧЕРНИХ ЭЛЕМЕНТОВ (КНОПОК)
        bid = cur.execute(
            """SELECT qid FROM tree WHERE pid IS (?) AND properties LIKE '<button%' """, (qid, )
            ).fetchall()
        ikbs = []
        kbs = []
        for id in bid:
            # СОЗДАНИЕ СПИСКА ИНЛАЙН-КНОПОК
            if prop == '<ikb>':
                ikbs.append(cur.execute(
                    """SELECT text, id FROM data WHERE id IS (?) """, (id)
                    ).fetchone())
            # СОЗДАНИЕ СПИСКА ОБЫЧНЫХ КНОПОК
            elif prop == '<kb>':
                kbs.append(cur.execute(
                    """SELECT text FROM data WHERE id IS (?) """, (id)
                    ).fetchone())
    
    if ikbs:
        buttonsText = [button for button in ikbs] # СОЗДАНИЕ СПИСКА ТИПА [('Text', ID), ('Text', ID), ...]
        # СОЗДАНИЕ КЛАВИАТУРЫ
        kb = InlineKeyboardMarkup(row_width=1
                                  ).add(*[InlineKeyboardButton(text=text, callback_data=qid) for text, qid in buttonsText]) # ДОБАВЛЕНИЕ КНОПОК
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ
        await message.answer(text=text,
                             reply_markup=kb) # ПЕРЕДАЧА КЛАВИТАУРЫ В TELEGRAM

    elif kbs:
        buttonsText = [button[0] for button in kbs] # СОЗДАНИЕ СПИСКА ТИПА ['Text', 'Text', ...]
        # СОЗДАНИЕ КЛАВИАТУРЫ
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=1
                                 ).add(*[KeyboardButton(text=text) for text in buttonsText]).add(back_button) # ДОБАВЛЕНИЕ КНОПОК
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ
        await message.answer(text=text,
                             reply_markup=kb) # ПЕРЕДАЧА КЛАВИТАУРЫ В TELEGRAM
    else:
        # ОТПРАВКА СООБЩЕНИЯ БОТОМ, ЕСЛИ КНОПОК НЕТ
        await message.answer(text=text, reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(cat_button))
    async with state.proxy() as st:
        st['prev'] = qid


@dp.callback_query_handler()
async def definePath(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.finish()
    if int(callback.data) == 2:
        async with state.proxy() as st:
            st['start'] = int(callback.data)
        await InfoStates.dialog.set()
        await callback.message.answer('Пожалуйста, используй кнопки', reply_markup=InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton(text='Хорошо', callback_data='continue')))
    elif int(callback.data) == 17:
        async with state.proxy() as st:
            st['start'] = int(callback.data)
        await ComplainStates.complain.set()
        async with state.proxy() as st:
            st['complain'] = []
        await callback.message.answer('Пожалуйста, следуйте инструкциям', reply_markup=InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton(text='Хорошо', callback_data='continue')))



if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
