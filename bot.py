import sqlite3
import os


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

bot = Bot(os.environ.get('TOKEN'), parse_mode='HTML')
dp = Dispatcher(bot, storage=MemoryStorage())


# ОБРАБОТЧИК КОМАНДЫ /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        # ОТБОР ID ПЕРВОГО ЭЛЕМЕНТА ИЗ БАЗЫ ДАННЫХ
        qid = cur.execute(
            """SELECT qid FROM tree WHERE pid IS NULL and properties is '<text>' """
            ).fetchone()[0]
        # КОНВЕРТАЦИЯ ID В ТЕКСТ ДЛЯ ОТПРАВКИ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ
        text = cur.execute(
            """SELECT text FROM data WHERE qid IS (?) """, (qid, )
            ).fetchone()[0]
        # ОТБОР ДОЧЕРНИХ ЭЛЕМЕНТОВ (КНОПОК)
        bid = cur.execute(
            """SELECT qid, properties FROM TREE WHERE pid IS (?) AND properties LIKE '<button%' """, (qid, )
            ).fetchall()
        ikbs = []
        kbs = []
        for id, prop in bid:
            # СОЗДАНИЕ СПИСКА ИНЛАЙН-КНОПОК
            if prop == '<button:ikb>':
                ikbs.append(cur.execute(
                    """SELECT text, qid FROM data WHERE qid IS (?) """, (id, )
                    ).fetchone())
            # СОЗДАНИЕ СПИСКА ОБЫЧНЫХ КНОПОК
            else:
                kbs.append(cur.execute(
                    """SELECT text FROM data WHERE qid IS (?) """, (id, )
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


# ОБРАБОТЧИК INLINE-КНОПОК 
@dp.callback_query_handler()
async def dialog(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        # ОТБОР  ИЗ БАЗЫ ДАННЫХ ДОЧЕРНЕГО ID ЭЛЕМЕНТА К ПОЛУЧЕННОМУ ID ОТ CALLBACK-ЗАПРОСА
        qid = cur.execute(
            """SELECT qid FROM tree WHERE pid IS (?) and properties is '<text>' """, (callback.data, )
            ).fetchone()[0]
        # КОНВЕРТАЦИЯ ID В ТЕКСТ ДЛЯ ОТПРАВКИ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ
        text = cur.execute(
            """SELECT text FROM data WHERE qid IS (?) """, (qid, )
            ).fetchone()[0]
        # ОТБОР ДОЧЕРНИХ ЭЛЕМЕНТОВ (КНОПОК)
        bid = cur.execute(
            """SELECT qid, properties FROM TREE WHERE pid IS (?) AND properties LIKE '<button%' """, (qid, )
            ).fetchall()
        print(bid)
        ikbs = []
        kbs = []
        for id, prop in bid:
            # СОЗДАНИЕ СПИСКА ИНЛАЙН-КНОПОК
            if prop == '<button:ikb>':
                ikbs.append(cur.execute(
                    """SELECT text, qid FROM data WHERE qid IS (?) """, (id, )
                    ).fetchone())
                print(ikbs)
            # СОЗДАНИЕ СПИСКА ОБЫЧНЫХ КНОПОК
            else:
                kbs.append(cur.execute(
                    """SELECT text FROM data WHERE qid IS (?) """, (id, )
                    ).fetchone())
    
    
    if ikbs:
        print(ikbs)
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
@dp.message_handler()
async def dialog(message: types.Message, state: FSMContext):
    async with state.proxy() as st:
        print(st['prev'])

    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        # НАХОЖДЕНИЕ ID ПОЛУЧЕННОГО ТЕКСТОВОГО СООБЩЕНИЯ (ВОПРОСА)
        temp = cur.execute(
            """SELECT qid FROM data WHERE text is (?) """, (message.text, )
        ).fetchone()[0]
        # ОТБОР ИЗ БАЗЫ ДАННЫХ ДОЧЕРНЕГО ID ЭЛЕМЕНТА К ID ТЕКСТОВОГО СООБЩЕНИЯ
        qid = cur.execute(
            """SELECT qid FROM tree WHERE pid IS (?) and properties is '<text>' """, (temp, )
            ).fetchone()[0]
        # КОНВЕРТАЦИЯ ID В ТЕКСТ ДЛЯ ОТПРАВКИ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ
        text = cur.execute(
            """SELECT text FROM data WHERE qid IS (?) """, (qid, )
            ).fetchone()[0]
        # ОТБОР ДОЧЕРНИХ ЭЛЕМЕНТОВ (КНОПОК)
        bid = cur.execute(
            """SELECT qid, properties FROM TREE WHERE pid IS (?) AND properties LIKE '<button%' """, (qid, )
            ).fetchall()
        ikbs = []
        kbs = []
        for id, prop in bid:
            # СОЗДАНИЕ СПИСКА ИНЛАЙН-КНОПОК
            if prop == '<button:ikb>':
                ikbs.append(cur.execute(
                    """SELECT text, qid FROM data WHERE qid IS (?) """, (id, )
                    ).fetchone())
            # СОЗДАНИЕ СПИСКА ОБЫЧНЫХ КНОПОК
            else:
                kbs.append(cur.execute(
                    """SELECT text FROM data WHERE qid IS (?) """, (id, )
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


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
