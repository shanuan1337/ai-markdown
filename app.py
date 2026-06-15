import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

API_URL = os.getenv("MARKDOWN_API_URL", "API_URL")
API_TOKEN = os.getenv("MARKDOWN_API_TOKEN", "API_TOKEN")
MODEL_NAME = os.getenv("MARKDOWN_MODEL", "MODEL_NAME")

SYSTEM_PROMPT = """Ты — эксперт по преобразованию произвольного текста в хорошо структурированный Markdown. Твоя задача — получить текст пользователя и вернуть **только** Markdown-разметку, без лишних пояснений.

Правила:
- Определи заголовки, списки, абзацы, таблицы, блоки кода.
- Если видишь данные, похожие на таблицу (строки с разделителями, табуляцией, колонками), **обязательно** оформляй их как Markdown-таблицу с выравниванием столбцов (используй `:---` для левого, `:---:` для центра, `---:` для правого).
- Код оборачивай в тройные обратные апострофы с указанием языка, если он понятен из контекста (например `bash`, `python`, `yaml`).
- Сохраняй смысл и информацию полностью, только улучшай читаемость.
- Используй корректный синтаксис Markdown (заголовки через `#`, списки через `-` или `*` и т.п.).
- Результат должен быть готов к немедленному использованию.
- Никаких вводных фраз, только Markdown.
"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico', mimetype='image/x-icon')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/convert', methods=['POST'])
def convert():
    data = request.json
    user_text = data.get('text', '')
    if not user_text.strip():
        return jsonify({'error': 'Пустой текст'}), 400

    logging.info(f"Получен запрос на конвертацию. Длина текста: {len(user_text)} символов")

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
        "stream": False
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_TOKEN}"
    }

    try:
        logging.info("Отправка запроса к llama.cpp...")
        resp = requests.post(API_URL, json=payload, headers=headers, timeout=300)
        resp.raise_for_status()
        result = resp.json()

        msg = result['choices'][0]['message']
        markdown_text = msg.get('content') or msg.get('reasoning_content', '')

        if not markdown_text.strip():
            logging.warning("Модель вернула пустой ответ.")
            return jsonify({'error': 'Модель вернула пустой ответ'}), 500

        logging.info(f"Конвертация успешна. Длина ответа: {len(markdown_text)} символов")
        return jsonify({'markdown': markdown_text})
    except requests.exceptions.Timeout:
        logging.error("Таймаут ожидания ответа от модели (300 с)")
        return jsonify({'error': 'Таймаут ожидания ответа от модели (300 с)'}), 500
    except Exception as e:
        logging.error(f"Ошибка API: {str(e)}")
        return jsonify({'error': f'Ошибка API: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1337, debug=False)
