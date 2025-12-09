import os
import asyncio
import httpx
import json

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, TelegramObject, Update
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from typing import Callable, Dict, Any, Awaitable
from io import BytesIO

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

TRANSLATIONS_FILE = "Studiora.translations.json"
translations_data = {}

def load_translations(filepath):
    global translations_data
    with open(filepath, 'r', encoding='utf-8') as f:
        translations_data = json.load(f)
        
def get_translated_text(key, lang_code="en", **kwargs):
    translation_dict = translations_data.get(key,{})
    text = translation_dict.get(lang_code, translation_dict.get("en", ""))
    return text.format(**kwargs)

def is_button_text_for_key(message_text: str, key: str) -> bool:
    translations_for_key = translations_data.get(key, {})
    for translated_text in translations_for_key.values():
        if translated_text == message_text:
            return True
    return False
    
load_translations(TRANSLATIONS_FILE)

user_languages = {}
user_messages_to_delete = {}

async def delete_old_messages(user_id: int):
    if user_id in user_messages_to_delete:
        for msg_id in user_messages_to_delete[user_id]:
            try:
                await bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception as e:
                pass 
        user_messages_to_delete[user_id] = []

async def add_message_to_delete(user_id: int, message_id: int):
    if user_id not in user_messages_to_delete:
        user_messages_to_delete[user_id] = []
    user_messages_to_delete[user_id].append(message_id)

async def set_user_language_middleware(
    handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
    event: Update,
    data: Dict[str, Any]
) -> Any:
    user = None
    if event.message:
        user = event.message.from_user
    elif event.callback_query:
        user = event.callback_query.from_user

    if user is None:
        return await handler(event, data)
    
    user_id = user.id

    if user_id not in user_languages:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{API_URL}/users/{user_id}")
                response.raise_for_status()
                user_data_from_db = response.json()
                
                lang_code_to_set = user_data_from_db.get("language_code", 'en')

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    initial_telegram_lang_code = user.language_code if user.language_code else 'en'
                    
                    user_to_create = {
                        "telegram_id": user_id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "language_code": initial_telegram_lang_code
                    }
                    
                    create_response = await client.post(f"{API_URL}/users", json=user_to_create)
                    create_response.raise_for_status()
                    lang_code_to_set = initial_telegram_lang_code
                else:
                    raise
            except Exception as e:
                raise
            
            if lang_code_to_set not in ['en', 'ru', 'hy']:
                lang_code_to_set = 'en'
            user_languages[user_id] = lang_code_to_set
            
    data["current_lang"] = user_languages.get(user_id, 'en')
    return await handler(event, data)

async def get_main_keyboard_markup(current_lang: str) -> ReplyKeyboardMarkup:
    button_user_text = get_translated_text("btn_user",current_lang)
    button_history_text = get_translated_text("btn_history", current_lang)
    button_settings_text = get_translated_text("btn_settings", current_lang)
    button_cl_text = get_translated_text("btn_create_lesson", current_lang)

    keyboard_buttons = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_user_text), KeyboardButton(text=button_history_text)],
            [KeyboardButton(text=button_settings_text),KeyboardButton(text=button_cl_text)],
            [KeyboardButton(text="/help")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=False
    )
    return keyboard_buttons

class CreateLessonStates(StatesGroup):
    waiting_for_lesson_details = State()
    waiting_for_confirmation = State()


@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await delete_old_messages(message.from_user.id)
    await state.clear()
    user_id = message.from_user.id
    current_lang = user_languages.get(user_id, 'en') 
    
    start_message_text = get_translated_text("start_message", current_lang)
    
    main_keyboard = await get_main_keyboard_markup(current_lang)
    await message.answer(start_message_text, reply_markup=main_keyboard)

    choose_language_text = get_translated_text("choose_language", current_lang)

    button_en = InlineKeyboardButton(text="English",callback_data="set_lang:en") 
    button_ru = InlineKeyboardButton(text="Русский",callback_data="set_lang:ru")
    button_hy = InlineKeyboardButton(text="Հայերեն",callback_data="set_lang:hy")
    
    choose_language_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                button_en,
                button_ru,
                button_hy
            ]
        ]
    )
    
    msg = await message.answer(choose_language_text, reply_markup=choose_language_markup) 
    await add_message_to_delete(user_id, msg.message_id) 

@dp.message(Command(commands=["help"]))
async def cmd_help(message: types.Message):
    await delete_old_messages(message.from_user.id) 
    await message.answer(get_translated_text("cmd_help_description", user_languages.get(message.from_user.id, 'en')))

@dp.callback_query(lambda c: c.data and c.data.startswith('set_lang:'))
async def set_language_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    new_lang = callback_query.data.split(':')[1]

    user_languages[user_id] = new_lang

    async with httpx.AsyncClient() as client:
        response = await client.patch(f"{API_URL}/users/{user_id}/language", json={"language_code": new_lang})
        response.raise_for_status()

    confirm_message_text = get_translated_text("language_set", new_lang, lang=new_lang.upper())

    updated_main_keyboard = await get_main_keyboard_markup(new_lang)
    
    await delete_old_messages(user_id) 
    await bot.send_message(
        callback_query.message.chat.id,
        confirm_message_text,
        reply_markup=updated_main_keyboard
    )
    await callback_query.answer()

@dp.message(lambda message: is_button_text_for_key(message.text, "btn_user"))
async def handle_user_button(message: types.Message, state: FSMContext):
    await delete_old_messages(message.from_user.id) 
    await state.clear()
    user_id = message.from_user.id
    current_lang = user_languages.get(user_id, 'en') 

    async with httpx.AsyncClient() as client:
        all_user_info_response = await client.get(f"{API_URL}/users/{user_id}")
        all_user_info_response.raise_for_status()
        user_data = all_user_info_response.json()

        username = user_data.get("username")
        first_name = user_data.get("first_name")
        last_name = user_data.get("last_name")
        language_code_db = user_data.get("language_code")
    
        user_text = (
            f"{get_translated_text('user_info_title', current_lang)}\n\n"
            f"{get_translated_text('username', current_lang)}: {username if username else 'none'}\n"
            f"{get_translated_text('first_name', current_lang)}: {first_name if first_name else 'none'}\n"
            f"{get_translated_text('last_name', current_lang)}: {last_name if last_name else 'none'}\n"
            f"{get_translated_text('language', current_lang)}: {language_code_db if language_code_db else 'none'}\n"
        )

        await message.answer(user_text)

@dp.message(lambda message: is_button_text_for_key(message.text, "btn_settings"))
async def settings_button(message: types.Message, state: FSMContext):
    await delete_old_messages(message.from_user.id) 
    await state.clear()
    user_id = message.from_user.id
    current_lang = user_languages.get(user_id, 'en') 

    settings_message = get_translated_text("button_settings", current_lang)
    
    button_en = InlineKeyboardButton(text="English", callback_data="set_lang:en") 
    button_ru = InlineKeyboardButton(text="Русский", callback_data="set_lang:ru")
    button_hy = InlineKeyboardButton(text="Հայերեն", callback_data="set_lang:hy")
    
    choose_language_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                button_en,
                button_ru,
                button_hy
            ]
        ]
    )
    msg = await message.answer(settings_message, reply_markup=choose_language_markup) 
    await add_message_to_delete(user_id, msg.message_id) 

    
@dp.message(lambda message: is_button_text_for_key(message.text, "btn_create_lesson"))
async def start_create_lesson(message:types.Message, state: FSMContext):
    await delete_old_messages(message.from_user.id) 
    user_id = message.from_user.id
    current_lang = user_languages.get(user_id, "en") 
    
    await state.clear()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/users/{user_id}")
            response.raise_for_status()
            user_data = response.json()
            last_request = user_data.get("last_request")
            
            if last_request and last_request.get("topic") and last_request.get("current_level") and last_request.get("target_level"):
                await state.update_data(
                    lesson_topic = last_request["topic"],
                    lesson_current_level = last_request["current_level"],
                    lesson_target_level = last_request["target_level"]
                )

                confirmation_message_text = (
                        f"{get_translated_text('ask_study_topic', current_lang)}: {last_request['topic']}\n"
                        f"{get_translated_text('ask_current_level', current_lang)}: {last_request['current_level']}\n"
                        f"{get_translated_text('ask_target_level', current_lang)}: {last_request['target_level']}\n\n"
                        f"{get_translated_text('confirm_lesson', current_lang)}"
                    )
                
                confirm_button = InlineKeyboardButton(text = get_translated_text("btn_confirm", current_lang), callback_data="confirm_button")
                edit_button = InlineKeyboardButton(text = get_translated_text("btn_edit", current_lang), callback_data="edit_lesson")
                cancel_button = InlineKeyboardButton(text=get_translated_text("btn_cancel", current_lang), callback_data="cancel_lesson")
            
                confirmation_markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [confirm_button, edit_button, cancel_button]
                    ]
                )
                msg = await message.answer(confirmation_message_text, reply_markup=confirmation_markup) 
                await add_message_to_delete(user_id, msg.message_id) 
                await state.set_state(CreateLessonStates.waiting_for_confirmation)
                return

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                pass 
            else:
                raise
        except Exception as e:
            print(f"Error checking last_request: {e}")
            pass 

    full_prompt = (
        f"{get_translated_text('ask_study_topic', current_lang)}\n"
        f"{get_translated_text('ask_current_level', current_lang)}\n"
        f"{get_translated_text('ask_target_level', current_lang)}\n"
        f"{get_translated_text('enter_all_in_one_message', current_lang)}\n"
        f"{get_translated_text('example_input', current_lang)}"
    )
    
    msg = await message.answer(full_prompt) 
    await add_message_to_delete(user_id, msg.message_id) 
    
    await state.set_state(CreateLessonStates.waiting_for_lesson_details)
    
@dp.message(CreateLessonStates.waiting_for_lesson_details)
async def proces_lesson_details(message:types.Message, state:FSMContext):
    user_id = message.from_user.id
    current_lang = user_languages.get(user_id, 'en') 
    
    user_input = message.text.strip()
    parts = [p.strip() for p in user_input.replace("\n",",").split(",") if p.strip()]
    
    if len(parts) == 3:
        topic = parts[0]
        current_level = parts[1]
        target_level = parts[2]

        await state.update_data(
            lesson_topic = topic,
            lesson_current_level = current_level,
            lesson_target_level = target_level
        )

        confirmation_message_text = (
                f"{get_translated_text('ask_study_topic', current_lang)}: {topic}\n"
                f"{get_translated_text('ask_current_level', current_lang)}: {current_level}\n"
                f"{get_translated_text('ask_target_level', current_lang)}: {target_level}\n\n"
                f"{get_translated_text('confirm_lesson', current_lang)}"
            )
        
        user_data = await state.get_data()
        lesson_details_for_api = {
            "topic": user_data.get("lesson_topic"),
            "current_level": user_data.get("lesson_current_level"),
            "target_level": user_data.get("lesson_target_level")
        }

        async with httpx.AsyncClient() as client:
            response_post = await client.post(f"{API_URL}/users/{user_id}/last_request", json=lesson_details_for_api)
            response_post.raise_for_status()

        await asyncio.sleep(0.5)

        confirm_button = InlineKeyboardButton(text = get_translated_text("btn_confirm", current_lang), callback_data="confirm_button")
        edit_button = InlineKeyboardButton(text = get_translated_text("btn_edit", current_lang), callback_data="edit_lesson")
        cancel_button = InlineKeyboardButton(text=get_translated_text("btn_cancel", current_lang), callback_data="cancel_lesson")
    
        confirmation_markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [confirm_button, edit_button, cancel_button]
            ]
        )
        await delete_old_messages(user_id) 
        msg = await message.answer(confirmation_message_text, reply_markup=confirmation_markup) 
        await add_message_to_delete(user_id, msg.message_id) 
        await state.set_state(CreateLessonStates.waiting_for_confirmation)

    else:
        msg = await message.answer(get_translated_text("expecting_lesson_details_format", current_lang)) 
        await add_message_to_delete(user_id, msg.message_id) 
        
@dp.callback_query(F.data == "cancel_lesson", CreateLessonStates.waiting_for_confirmation)
async def delete_lesson(callback_query:types.CallbackQuery, state: FSMContext):
        await delete_old_messages(callback_query.from_user.id) 
        current_lang = user_languages.get(callback_query.from_user.id, "en")
        
        user_id = callback_query.from_user.id
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{API_URL}/users/{user_id}/last_request", json={})
                response.raise_for_status()
            except Exception as e:
                print(f"Error clearing last_request on cancel: {e}")

        await callback_query.message.answer(get_translated_text("lesson_cancelled", current_lang))
        
        await state.clear()
        await callback_query.answer()
        
@dp.callback_query(F.data == "edit_lesson", CreateLessonStates.waiting_for_confirmation)
async def edit_lesson(callback_query:types.CallbackQuery, state: FSMContext):
        await delete_old_messages(callback_query.from_user.id) 
        current_lang = user_languages.get(callback_query.from_user.id, "en")
        
        await state.clear()
        
        user_id = callback_query.from_user.id
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{API_URL}/users/{user_id}/last_request", json={})
                response.raise_for_status()
            except Exception as e:
                print(f"Error clearing last_request on edit: {e}")

        full_prompt = (
            f"{get_translated_text('ask_study_topic', current_lang)}\n"
            f"{get_translated_text('ask_current_level', current_lang)}\n"
            f"{get_translated_text('ask_target_level', current_lang)}\n"
            f"{get_translated_text('enter_all_in_one_message', current_lang)}\n"
            f"{get_translated_text('example_input', current_lang)}"
        )
        
        msg = await callback_query.message.answer(full_prompt) 
        await add_message_to_delete(callback_query.from_user.id, msg.message_id) 
        await state.set_state(CreateLessonStates.waiting_for_lesson_details)
        await callback_query.answer()

@dp.callback_query(F.data == "confirm_button", CreateLessonStates.waiting_for_confirmation)
async def send_lesson_details(callback_query:types.CallbackQuery, state: FSMContext):
        await delete_old_messages(callback_query.from_user.id) 
        user_id = callback_query.from_user.id
        current_lang = user_languages.get(user_id, "en")
        
        user_data = await state.get_data()

        await callback_query.message.answer(get_translated_text("generating_lesson_pdf", current_lang))
        await callback_query.answer()

        async with httpx.AsyncClient(timeout=120.0) as client:
            response_get_pdf = await client.get(f"{API_URL}/users/{user_id}/lesson_details")
            response_get_pdf.raise_for_status()

            pdf_data = BytesIO(response_get_pdf.content)
            pdf_data.name = f"{user_data.get('lesson_topic')}_lesson.pdf"

            await bot.send_document(chat_id=user_id, document=types.BufferedInputFile(pdf_data.getvalue(), filename=f"{user_data.get("lesson_topic")}_lesson.pdf"))
            await callback_query.message.answer(get_translated_text("lesson_sent_successfully", current_lang))

        await state.clear()
    

@dp.message(lambda message: is_button_text_for_key(message.text, "btn_history"))
async def handle_history_button(message: types.Message, state: FSMContext):
    await delete_old_messages(message.from_user.id) 
    await state.clear()
    await send_history_with_pagination(message.chat.id, skip=0)

@dp.callback_query(F.data.startswith("history_page:"))
async def handle_history_pagination(callback_query: types.CallbackQuery):
    await delete_old_messages(callback_query.from_user.id) 
    skip = int(callback_query.data.split(":")[1])
    user_id = callback_query.from_user.id

    await send_history_with_pagination(user_id=user_id, skip=skip)
    await callback_query.answer()

async def send_history_with_pagination(user_id: int, skip: int = 0):
    current_lang = user_languages.get(user_id, 'ru')
    limit = 5

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_URL}/users/{user_id}/history?skip={skip}&limit={limit}")
        resp.raise_for_status()
        data = resp.json()

        pdf_files = data.get("pdf_files", [])
        total = data.get("total_count", 0)

        if not pdf_files:
            text = get_translated_text("no_pdfs_found", current_lang)
            msg = await bot.send_message(user_id, text)
            await add_message_to_delete(user_id, msg.message_id) 
            return

        API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "api"))
        DB_DIR = os.path.join(API_DIR, "db")

        for filename in pdf_files:
            file_path = os.path.join(DB_DIR, str(user_id), filename)
            if not os.path.exists(file_path):
                continue
            with open(file_path, "rb") as f:
                msg = await bot.send_document(chat_id=user_id, document=types.BufferedInputFile(f.read(), filename=filename), caption=f"📄 {filename}")
                await add_message_to_delete(user_id, msg.message_id) 
        
        buttons = []
        if skip > 0:
            buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"history_page:{skip - limit}"))
        if skip + limit < total:
            buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"history_page:{skip + limit}"))
        
        current_page = (skip // limit) + 1
        total_pages = (total + limit - 1) // limit
        page_info_text = get_translated_text("page_info", current_lang, current_page=current_page, total_pages=total_pages)
        
        markup = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None

        nav_msg = await bot.send_message(
            chat_id=user_id,
            text=page_info_text,
            reply_markup=markup
        )
        await add_message_to_delete(user_id, nav_msg.message_id) 


async def main():
    dp.update.outer_middleware.register(set_user_language_middleware)
    await dp.start_polling(bot)

if __name__ == '__main__': 
    asyncio.run(main())
