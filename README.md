**Studiora** is an intelligent Telegram bot designed to instantly generate structured lessons and educational materials on any topic specified by the user. By harnessing the power of the advanced **Gemini 2.5 Flash** model, the bot transforms your simple request into a ready-made, comprehensive educational plan.

## ✨ Core Features and Capabilities

* **On-the-Fly Lesson Generation:** Create full-fledged learning materials based on a user's text prompt.
* **Powered by Gemini 2.5 Flash:** Ensures high quality, relevance, and creativity of the educational content, delivering expert-level explanations.
* **Structured Learning:** The bot provides logically organized lessons complete with headings, subsections, and illustrative examples, making complex topics easy to digest.
* **Multilingual Support:** All generated lessons can be instantly translated into **three different languages** (e.g., Spanish, German, French - *list your specific languages here*) to cater to a diverse user base.
* **History Tracking:** User-generated lessons and personal settings are saved for easy access and continuation of studies at any time.

## 🛠️ Technological Stack

The Studiora project is built on reliable and modern asynchronous tools, demonstrating robust and scalable architecture:

* **AI Core:** Google **Gemini 2.5 Flash**
* **Telegram Bot Interface:** **Aiogram** (Asynchronous Python framework)
* **Backend / API:** **FastAPI** (A fast, high-performance Python framework for handling requests and interacting with Gemini and the database)
* **Database:** **MongoDB** (A flexible NoSQL database used for storing user data and lesson history)
* **Language:** **Python**

## ⚙️ Setup and Installation

### Prerequisites

1.  Python installed (3.10+ recommended).
2.  A Google Gemini API Key.
3.  Access to and connection details for a MongoDB instance.
4.  A Telegram Bot Token (obtained from BotFather).

### Steps

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/](https://github.com/)poghdev/studiora.git
    cd studiora
    ```

2.  **Set up the virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate   # Linux/macOS
    # venv\Scripts\activate    # Windows
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a file named `.env` in the root folder and add your credentials:
    ```
    # Telegram Bot
    BOT_TOKEN="<YOUR TELEGRAM BOT TOKEN>"

    # Google AI
    GEMINI_API_KEY="<YOUR GEMINI API KEY>"

    # Database
    MONGO_URI="<YOUR MONGO_DB CONNECTION STRING>"
    MONGO_DB_NAME="studiora_db"
    ```

4.  **Run the bot:**
    ```bash
    python main.py  # Or use the specific command from your documentation
    ```

## 🧑‍💻 How to Use the Bot

1.  Start a chat with the bot on Telegram: **<LINK TO BOT>**
2.  Send the `/start` command.
3.  Enter the topic you wish to study (e.g., "The basics of quantum computing," "The history of the Renaissance," or "How to configure a Raspberry Pi").
4.  Studiora will instantly generate a comprehensive, structured lesson for you!

***

# Studiora 📚🧠 (Русская версия)

**Studiora** — это интеллектуальный Telegram-бот, разработанный для мгновенной генерации структурированных уроков и учебных материалов по любой теме, заданной пользователем. Используя мощность передовой модели **Gemini 2.5 Flash**, бот превращает Ваш простой запрос в готовый, всесторонний учебный план.

## ✨ Основные функции и возможности

* **Генерация уроков на лету:** Создание полноценных учебных материалов на основе текстового запроса пользователя.
* **Работа на базе Gemini 2.5 Flash:** Обеспечивает высокое качество, релевантность и креативность учебного контента, предлагая объяснения экспертного уровня.
* **Структурированное обучение:** Бот создает логично организованные уроки с заголовками, подразделами и наглядными примерами, что упрощает усвоение сложных тем.
* **Многоязыковая поддержка:** Все сгенерированные уроки могут быть мгновенно переведены на **три разных языка** (например, испанский, немецкий, французский — *укажите здесь свои конкретные языки*), что позволяет работать с разнообразной аудиторией.
* **Отслеживание истории:** Сгенерированные уроки и личные настройки пользователя сохраняются для удобного доступа и продолжения обучения в любое время.

## 🛠️ Технологический стек

Проект Studiora построен на надежных и современных асинхронных инструментах, демонстрирующих масштабируемую и надежную архитектуру:

* **Ядро AI:** Google **Gemini 2.5 Flash**
* **Интерфейс Telegram-бота:** **Aiogram** (асинхронный Python-фреймворк)
* **Backend / API:** **FastAPI** (быстрый, высокопроизводительный Python-фреймворк для обработки запросов и взаимодействия с Gemini и базой данных)
* **База данных:** **MongoDB** (гибкая NoSQL база данных, используемая для хранения пользовательских данных и истории уроков)
* **Язык:** **Python**

## ⚙️ Установка и запуск

(См. инструкции на английском выше. Шаги 1-4 полностью совпадают).
