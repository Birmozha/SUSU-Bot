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

bot = Bot(TOKEN, parse_mode='HTML')
dp = Dispatcher(bot, storage=MemoryStorage())

class InfoStates(StatesGroup):
    dialog = State()

class ComplainStates(StatesGroup):
    complain = State()
    wait_text = State()
    wait_photo = State()
    wait_choose = State()    

# ОБРАБОТЧИК КОМАНДЫ /start
@dp.message_handler(commands=['start'], state=['*'])
async def start(message: types.Message, state: FSMContext):
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


@dp.callback_query_handler()
async def definePath(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
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

@dp.message_handler(state=ComplainStates.wait_choose)
async def waitText(message: types.Message, state: FSMContext):
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
     

@dp.message_handler(content_types=['any'], state=ComplainStates.wait_photo)
async def waitPhoto(message: types.Message, state: FSMContext):
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
                    t = st['complain']
                    photo_path = st['photo_path']
                    photo_name = st['photo_name']
                addr_from = MAIL_BOX
                addr_to = MAIL_BOX
                msg = MIMEMultipart()
                msg['From'] = addr_from
                msg['To'] = addr_to
                msg['Subject'] = f'Новая жалоба: {t[0]}'
                body = (f'''--{t[1]}--''')
                msg.attach(MIMEText(body, 'plain'))
                # await asyncio.sleep(1)
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
        
    else:
        await message.reply(text='Пожалуйста, пришлите фото')

@dp.message_handler(state=ComplainStates.wait_text)
async def waitText(message: types.Message, state: FSMContext):
    async with state.proxy() as st:
        pid = st['prev']
        st['complain'].append(message.text)
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        next = cur.execute("""
                        SELECT qid FROM tree WHERE pid is (?)
                        """, (pid, )).fetchall()
        if not next:
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

    if kbs:
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

# ОБРАБОТЧИК ТЕКСТОВОГО СООБЩЕНИЯ
@dp.message_handler(state=InfoStates.dialog)
async def dialog(message: types.Message, state: FSMContext):
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
        ikbs = []
        kbs = []
        for id in bid:
            # СОЗДАНИЕ СПИСКА ИНЛАЙН-КНОПОК
            if prop == '<ikb>':
                ikbs.append(cur.execute(
                    """SELECT text, id FROM data WHERE id IS (?) """, (id, )
                    ).fetchone())
            # СОЗДАНИЕ СПИСКА ОБЫЧНЫХ КНОПОК
            elif prop == '<kb>':
                kbs.append(cur.execute(
                    """SELECT text FROM data WHERE id IS (?) """, (id, )
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


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
