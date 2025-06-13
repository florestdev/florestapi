import os
try:
  from florestbotfunctions import AsyncFunctionsObject, FunctionsObject
  from flask import Flask, jsonify, request, Response
  from pytubefix import YouTube, Search
  import asyncio, base64, random, os, pathlib, sys
  from flask_limiter import Limiter, RateLimitExceeded
  import logging
  import aiosmtplib
  from email.message import EmailMessage
  import re
  import aiosqlite
  from mcstatus import JavaServer
except ImportError:
  os.system('pip install -r requirements.txt')

app = Flask(__name__)
functions = AsyncFunctionsObject(google_api_key='...', gigachat_id='...', gigachat_key='...', vk_token='...', html_headers={})
fl = FunctionsObject()
path = pathlib.Path(sys.argv[0]).parent.resolve()
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = '/data/database.db'

def get_api_key():
    return request.headers.get('Api-Token')

async def is_ip_banned(ip: str):
    return False

limit = Limiter(get_api_key, app=app, storage_uri='memory://', strategy='fixed-window', default_limits=['5 per second'])

@app.errorhandler(RateLimitExceeded)
def rate_limit_exceeded(e):
    return jsonify({"error":f"Эй, чел! Успокойся! Ты привысил ограничения по использованию данной функции. Попробуй позже!"}), 429
    
@app.errorhandler(405)
async def this_method_not_provided(e):
    if request.method == 'GET':
        return jsonify({"error":f"Функция поддерживает только POST-запросы."}), 405
    elif request.method == 'POST':
        return jsonify({"error":f"Функция поддерживает только GET-запросы."}), 405
    else:
        return jsonify({"error":f"Выбранный вами метод ({request.method}) не поддерживается ни одной функцией в FlorestAPI. Только POST и GET."}), 405
    
@app.before_request
async def before_request():
    logging.info(request.headers)
    logging.info(request.remote_addr)
    print(request.endpoint, request.url)
    f = await is_ip_banned(request.headers.get('X-Forwarded-For', 'undefined'))
    if f == True:
        return jsonify({"error":"Работа FlorestAPI ограничена в Вашем регионе."}), 403
    
    if request.endpoint in ['index', 'generate_docs', 'snake_games', 'games_clicker', 'create_new_api_key']:
        return
    else:
        api_key = request.headers.get('Api-Token')
        if not api_key:
            return jsonify({"error":"Бро, напиши свой API-ключик в заголовок Api-Token, токен можно достать бесплатно с моего бота @postbotflorestbot."}), 401
        else:
            connection = await aiosqlite.connect(DB_PATH)
            check = await connection.execute(f'SELECT * FROM users WHERE token=?', (api_key, ))
            if await check.fetchone() == None:
                return jsonify({"error":"API ключ не найден в датабазе. Попробуйте пересоздать с помощью @postbotflorestbot."}), 401
            else:
                return      

docs_data = {
    "title": "FlorestAPI",
    "description": "Ну, наверное, мощный инструмент в разработке приложений.",
    "endpoints": {
        "/utilits/vk_get_songs": {
            "method": "GET",
            "params": {
                "query": "Поисковый запрос для музыки (строка)",
                "count": "Количество треков (число)"
            },
            "description": "Поиск музыки во ВКонтакте."
        },
        "/youtube/search_videos": {
            "method": "GET",
            "params": {
                "query": "Поисковый запрос для видео (строка)",
                "count": "Количество видео (число)",
                "resolution":"Качество, в котором нужно качать видео. Либо `min`, либо `max`. По умолчанию `min`."
            },
            "description": "Поиск видео на YouTube с полной инфой и ссылкой для скачивания."
        },
        "/utilits/parse_google": {
            "method": "GET",
            "params": {
                "query": "Поисковый запрос для картинок (строка)",
                "resolution":""
            },
            "description": "Парсинг картинок из Google."
        },
        "/youtube/download_video": {
            "method": "GET",
            "params": {
                "url": "URL видео на YouTube (строка)",
                'resolution':"Качество, в котором нужно качать видео. Либо `min`, либо `max`, а также можно указать самому качество (пример: 1080p). По умолчанию, `min`."
            },
            "description": "Получение прямой ссылки и инфы о видео."
        },
        "/utilits/get_vk_last_post": {
            "method": "GET",
            "params": {
                "query": "ID или домен VK-группы (строка)"
            },
            "description": "Получение последнего поста из группы ВКонтакте."
        },
        "/ai/text_gen": {
            "method": "GET",
            "params": {
                "prompt": "Текст запроса для AI (строка)",
                "is_voice": "Вернуть аудио-ответ (true/false, по умолчанию false)"
            },
            "description": "Генерация текста через AI (с опцией голосового ответа)."
        },
        "/ai/img_gen": {
            "method": "GET",
            "params": {
                "prompt": "Описание изображения (строка)"
            },
            "description": "Генерация изображения через AI."
        },
        "/utilits/bmi_check": {
            "method": "GET",
            "params": {
                "weight": "Вес в кг (число)",
                "height": "Рост в метрах (число)"
            },
            "description": "Расчёт индекса массы тела (ИМТ)."
        },
        "/utilits/weather_check": {
            "method": "GET",
            "params": {
                "city": "Название города (строка)"
            },
            "description": "Проверка погоды в городе."
        },
        "/utilits/fake_data": {
            "method": "GET",
            "params": {},
            "description": "Генерация фейковых данных гражданина РФ."
        },
        "/utilits/get_crypto_price": {
            "method": "GET",
            "params": {
                "crypto": "Криптовалюта (bitkoin, tether, dogecoin, hamster)",
                "currency": "Валюта для конверсии (опционально, строка)"
            },
            "description": "Получение цены криптовалюты."
        },
        "/deanon/deanon_ip": {
            "method": "GET",
            "params": {
                "ip": "IP-адрес (строка)"
            },
            "description": "Деанонимизация по IP."
        },
        "/deanon/info_about_photo": {
            "method": "POST",
            "params": {
                "photo": "Фото в files. Пример: requests.post('url', files={'photo':open('...', 'rb')})"
            },
            "description": "Извлечение геоданных из фото."
        },
        "/utilits/make_qr": {
            "method": "GET",
            "params": {
                "content": "Текст или URL для QR-кода (строка)"
            },
            "description": "Создание QR-кода."
        },
        "/utilits/get_charts": {
            "method": "GET",
            "params": {},
            "description": "Получение чартов Яндекс Музыки."
        },
        "/utilits/create_password": {
            "method": "GET",
            "params": {},
            "description": "Генерация случайного пароля."
        },
        "/utilits/password_check": {
            "method": "GET",
            "params": {
                "nickname": "Никнейм для проверки (строка)"
            },
            "description": "Проверка утечек паролей по никнейму."
        },
        "/youtube/get_info_about_channel": {
            "method": "GET",
            "params": {
                "url": "URL YouTube-канала (строка)"
            },
            "description": "Получение информации о YouTube-канале."
        },
        "/ai/text_to_speech": {
            "method": "GET",
            "params": {
                "content": "Текст для озвучки (строка)",
                "lang": "Язык (опционально, строка, по умолчанию ru)"
            },
            "description": "Преобразование текста в речь."
        },
        "/utilits/get_photo_black": {
            "method": "POST",
            "params": {
                "photo": "Фото в files. Пример: requests.post('url', files={'photo':open('...', 'rb')})"
            },
            "description": "Преобразование фото в чёрно-белое."
        },
        '/utilits/py_to_exe': {
            'method':"POST",
            'params': {
                'py_file':"Python File в files. Пример: requests.post('url', files={'py_file':open('...', 'rb')})"
            },
            'description':"Удобный онлайн-конвертер из .py в .exe! Возвращает exe в base64."
        },
        '/utilits/censor_faces':{
            'method':'POST',
            'params':{
                "photo":"Фото в files. Пример: requests.post('url', files={'photo':open('...', 'rb')})"
            },
            'description':"Цензура лиц на фотографии. Возвращает фотографию (с цензурой) в base64."
        },
        '/games/snake': {
            'method':"GET",
            'params':{},
            'description':"Просто игра в змейку, для забавы. (ДЛЯ ПК)"
        },
        '/games/clicker': {
            'method':'GET',
            'params':{},
            'description':"Личный кликер от Флореста!"
        },
        '/utilits/send_mail': {
            'method':"POST",
            'params':{
                "title":"Заголовок письма (строка)",
                'description':"Описание письма (строка)",
                'receiver':"Получатель письма (строка)"
            },
            'description':"Отправка письма с помощью SMTP-сервера. В headers укажите Service (к примеру, smtp.mail.ru), Port (к примеру, 465), User (чаще всего является вашей электронной почтой) и Password (пароль от вашего SMTP-сервера)."
        },
        '/utilits/get_minecraft_server_info': {
            'method':"GET",
            'params':{
                'ip':"IP сервера (строка)",
                'port':"Порт сервера (опционально)"
            },
            'description':"Данная функция нужна, чтобы узнать фулл информацию о майнкрафт сервере."
        },
        '/utilits/cpp_to_exe':{
            'method':"POST",
            'params':{
                'app':".cpp в files. requests.post('url', files={'app':open('...', 'rb')})"
            },
            'description':'Из C++ в exe.'
        }
    }
}

@app.route('/docs', methods=['GET'])
@limit.exempt
async def generate_docs():
    """Генерация документации API."""
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:   
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{docs_data['title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #1a1a1a; color: #ffffff; }}
                h1 {{ color: #00ff88; }}
                h2 {{ color: #ff4444; }}
                pre {{ background-color: #333; padding: 15px; border-radius: 5px; overflow-x: auto; }}
                a {{ color: #00ff88; text-decoration: none; }}
                .endpoint {{ margin-bottom: 20px; }}
                .yuni {{ font-size: 18px; margin-top: 20px; color: #ff88cc; }}
            </style>
        </head>
        <body>
            <img src="https://cdn.discordapp.com/attachments/1315625070361710605/1378628948912508958/image0.jpg?ex=683d4bc3&is=683bfa43&hm=bf8679469edca8df81dfc05f687adff7b029138de633ffafd6a6879420d63e11&" alt="Герб Российской Федерации"></img>
            <h1>{docs_data['title']}</h1>
            <p>{docs_data['description']}</p>
            <h2>Эндпоинты:</h2>
            {"".join(
                f"<div class='endpoint'><strong>{endpoint}</strong><br>"
                f"Метод: {data['method']}<br>"
                f"Параметры: {', '.join([f'{k}: {v}' for k, v in data['params'].items()]) or 'Нет'}<br>"
                f"Описание: {data['description']}</div>"
                for endpoint, data in docs_data['endpoints'].items()
            )}
            <div class='yuni'>Благодарю за чтение документации.</div>
            <div class='api-key'>Требуется API ключ из @postbotflorestbot.</div>
            <footer>FlorestAPI, since 2025.</footer>
        </body>
        </html>
        """
        return Response(html, mimetype='text/html')
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403

@app.route('/', methods=['GET'])
@limit.exempt
async def index():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:    
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{docs_data['title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #1a1a1a; color: #ffffff; }}
                h1 {{ color: #00ff88; }}
                h2 {{ color: #ff4444; }}
                pre {{ background-color: #333; padding: 15px; border-radius: 5px; overflow-x: auto; }}
                a {{ color: #00ff88; text-decoration: none; }}
                .endpoint {{ margin-bottom: 20px; }}
                .yuni {{ font-size: 18px; margin-top: 20px; color: #ff88cc; }}
            </style>
        </head>
        <body>
        <img src="https://cdn.discordapp.com/attachments/1315625070361710605/1378628948912508958/image0.jpg?ex=683d4bc3&is=683bfa43&hm=bf8679469edca8df81dfc05f687adff7b029138de633ffafd6a6879420d63e11&" alt="Герб Российской Федерации"></img>
            <h1>{docs_data['title']}</h1>
            <p>{docs_data['description']}</p>
            <h2>Эндпоинты:</h2>
            {"".join(
                f"<div class='endpoint'><strong>{endpoint}</strong><br>"
                f"Метод: {data['method']}<br>"
                f"Параметры: {', '.join([f'{k}: {v}' for k, v in data['params'].items()]) or 'Нет'}<br>"
                f"Описание: {data['description']}</div>"
                for endpoint, data in docs_data['endpoints'].items()
            )}
            <div class='yuni'>Благодарю за чтение документации.</div>
            <div class='api-key'>Требуется API ключ из @postbotflorestbot.</div>
            <footer>FlorestAPI, since 2025.</footer>
        </body>
        </html>
        """
        return Response(html, mimetype='text/html')
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403

@app.errorhandler(500)
async def error_server(e):
    return jsonify({'error':'API неисправен! Произошла серверная ошибка.'}), 500

@app.errorhandler(404)
async def page_not_founded(e):
    return jsonify({'error':'Данной страницы не существует.'}), 404

@app.route('/utilits/vk_get_songs', methods=['GET'])
async def vk_get_songs():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        query = request.args.get('query')
        count = request.args.get('count')
        if all([query, count]):
            result = await functions.searching_musics_vk(query, int(count))
            return jsonify(result)
        else:
            return jsonify({"error":"Параметры query и count обязательны!"}), 400
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
    
@app.route('/youtube/search_videos', methods=['GET'])
async def search_videos():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        query = request.args.get('query')
        count = request.args.get('count')
        resolution = request.args.get('resolution', 'min')
        if all([query, count]):
            result = []
            search = Search(query, proxies={})
            if resolution == 'min':
                for r in search.videos[:int(count)]:
                    captions = []
                    resolutions = []
                    for c in r.captions:
                        captions.append({"lang_code":c.code, 'json_caption':c.json_captions})
                    for res in r.streams.all():
                        resolutions.append(res.resolution)
                    try:
                        await asyncio.to_thread(result.append, {'author':r.author, 'title':r.title, 'url':r.watch_url, 'desc':r.description, 'metadata':r.metadata.raw_metadata, 'keywords':r.keywords, 'resolutions':resolutions, 'url_for_download':r.streams.get_lowest_resolution().url, 'likes':r.likes, 'views':r.views, 'thumbnail_url':r.thumbnail_url, 'publish_date':r.publish_date.strftime('%m/%d/%Y, %H:%M:%S'), 'captions':captions})
                    except:
                        pass
            elif resolution == 'max':
                for r in search.videos[:int(count)]:
                    captions = []
                    resolutions = []
                    for c in r.captions:
                        captions.append({"lang_code":c.code, 'json_caption':c.json_captions})
                    for res in r.streams.all():
                        resolutions.append(res.resolution)
                    try:
                        await asyncio.to_thread(result.append, {'author':r.author, 'title':r.title, 'url':r.watch_url, 'desc':r.description, 'metadata':r.metadata.raw_metadata, 'keywords':r.keywords, 'resolutions':resolutions, 'url_for_download':r.streams.get_highest_resolution().url, 'likes':r.likes, 'views':r.views, 'thumbnail_url':r.thumbnail_url, 'publish_date':r.publish_date.strftime('%m/%d/%Y, %H:%M:%S'), 'captions':captions})
                    except:
                        pass
            else:
                return jsonify({"error":"Поддерживаются только `min` и `max`."}), 400
            
            return jsonify(result)
        else:
            return jsonify({"error":"Параметры query и count обязательны!"}), 400
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/utilits/parse_google', methods=['GET'])
async def parse_google():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        query = request.args.get('query')
        if all([query]):
            res = await functions.google_photo_parsing(query)
            return jsonify(res)
        else:
            return jsonify({'error':'query обязателен!'}), 400
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/youtube/download_video', methods=['GET'])
async def download_video():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        url = request.args.get('url')
        resolution = request.args.get('resolution', 'min')
        if not url:
            return jsonify({'error':'url обязателен.'}), 400
        else:
            r = YouTube(url, proxies={})
            if r.age_restricted:
                return {'error':'На видео есть возрастные ограничения.'}
            
            if resolution == 'min':
                try:
                    captions = []
                    resolutions = []
                    for c in r.captions:
                        captions.append({"lang_code":c.code, 'json_caption':c.json_captions})
                    for res in r.streams.all():
                        resolutions.append(res.resolution)
                    result = {'author':r.author, 'title':r.title, 'url':r.watch_url, 'desc':r.description, 'metadata':r.metadata.raw_metadata, 'keywords':r.keywords, 'resolutions':resolutions, 'url_for_download':r.streams.get_lowest_resolution().url, 'likes':r.likes, 'views':r.views, 'thumbnail_url':r.thumbnail_url, 'publish_date':r.publish_date.strftime('%m/%d/%Y, %H:%M:%S'), 'captions':captions}
                    return jsonify(result)
                except:
                    return jsonify({"error":"Ошибка случилась, мда."}), 500
            elif resolution == 'max':
                try:
                    captions = []
                    resolutions = []
                    for c in r.captions:
                        captions.append({"lang_code":c.code, 'json_caption':c.json_captions})
                    for res in r.streams.all():
                        resolutions.append(res.resolution)
                    result = {'author':r.author, 'title':r.title, 'url':r.watch_url, 'desc':r.description, 'metadata':r.metadata.raw_metadata, 'keywords':r.keywords, 'resolutions':resolutions, 'url_for_download':r.streams.get_highest_resolution().url, 'likes':r.likes, 'views':r.views, 'thumbnail_url':r.thumbnail_url, 'publish_date':r.publish_date.strftime('%m/%d/%Y, %H:%M:%S'), 'captions':captions}
                    return jsonify(result)
                except:
                    return jsonify({"error":"Ошибка случилась, мда."}), 500
            else:
                stream = r.streams.get_by_resolution(resolution)
                resolutions = []
                for res in r.streams.all():
                    resolutions.append(res.resolution)
                if stream:
                    try:
                        captions = []
                        for c in r.captions:
                            captions.append({"lang_code":c.code, 'json_caption':c.json_captions})
                        result = {'author':r.author, 'title':r.title, 'url':r.watch_url, 'desc':r.description, 'metadata':r.metadata.raw_metadata, 'keywords':r.keywords, 'resolutions': resolutions, 'url_for_download':stream.url, 'likes':r.likes, 'views':r.views, 'thumbnail_url':r.thumbnail_url, 'publish_date':r.publish_date.strftime('%m/%d/%Y, %H:%M:%S'), 'captions':captions}
                        return jsonify(result)
                    except:
                        return jsonify({"error":"Ошибка случилась, мда."}), 500
                else:
                    try:
                        result = {'author':r.author, 'title':r.title, 'url':r.watch_url, 'desc':r.description, 'metadata':r.metadata.raw_metadata, 'keywords':r.keywords, 'resolutions':resolutions, 'url_for_download':'Ссылка на это разрешение для этого ролика не найдена.', 'likes':r.likes, 'views':r.views, 'thumbnail_url':r.thumbnail_url, 'publish_date':r.publish_date.strftime('%m/%d/%Y, %H:%M:%S')}
                        return jsonify(result)
                    except:
                        return jsonify({"error":"Ошибка случилась, мда."}), 500
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/utilits/get_vk_last_post', methods=['GET'])
async def get_vk_last_post():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        query = request.args.get('query')
        if not query:
            return jsonify({"error":"query обязателен!"}), 400
        else:
            r = await functions.get_last_post(query)
            return jsonify(r), 200
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/ai/text_gen', methods=['GET'])
async def ai_text_gen():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        prompt = request.args.get('prompt')
        is_voice = request.args.get('is_voice') == 'false'
        if not prompt:
            return jsonify({'error':'prompt обязателен!'}), 500
        else:
            r = await functions.ai(prompt, is_voice)
            return jsonify(r)
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/ai/img_gen', methods=['GET'])
async def ai_img_gen():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        prompt = request.args.get('prompt')
        if not prompt:
            return jsonify({'error':'prompt обязателен!'}), 400
        else:
            r = await functions.generate_image(prompt)
            return jsonify({"image_base64":base64.b64encode(r).decode(errors='ignore')})
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/utilits/bmi_check', methods=['GET'])
async def bmi_check():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        weight = request.args.get('weight')
        height = request.args.get('height')
        
        if not all([weight, height]):
            return jsonify({"error":"weight и height обязательны!"}), 400
        else:
            r = await functions.bmi(float(weight), float(height))
            return jsonify(r)
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/utilits/weather_check', methods=['GET'])
async def weather_check():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        city = request.args.get('city')
        if not city:
            return jsonify({'error':'city обязателен!'}), 400
        else:
            r = await functions.check_weather(city)
            return jsonify(r)
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/utilits/fake_data', methods=['GET'])
async def fake_data():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        i = await functions.fake_human()
        return jsonify(i)
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/utilits/get_crypto_price', methods=['GET'])
async def get_crypto_price():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        crypto = request.args.get('crypto')
        currency = request.args.get('currency')
        if not crypto:
            return jsonify({"error":"crypto обязателен. `bitkoin`, `tether`, `dogecoin`, `hamster`."}), 400
        else:
            if not currency:
                r = await functions.crypto_price(crypto)
            else:
                r = await functions.crypto_price(crypto, currency)
            return jsonify({'crypto_price':r})
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/deanon/deanon_ip', methods=['GET'])
async def deanon_deanon_ip():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        ip = request.args.get('ip')
        if not ip:
            return jsonify({'error':'ip обязателен.'}), 400
        else:
            r = await functions.deanon(ip)
            return jsonify(r)
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/deanon/info_about_photo', methods=['POST'])
async def deanon_info_about_photo():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        if 'photo' not in request.files:
            return jsonify({'error':'Файл фото обязателен в multipart/form-data!'}), 400
        
        photo_file = request.files.get('photo')
        if not photo_file.filename:
            return jsonify({'error':'photo не найден в запросе'}), 400
            
        try:
            photo_data = photo_file.stream.read()
            r = await functions.real_info_of_photo(photo_data)
            return jsonify({'photo_info': r})
        except Exception as e:
            return jsonify({'error': f'Ошибка обработки: {str(e)}'}), 500
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403

@app.route('/utilits/get_photo_black', methods=['POST'])
async def get_photo_black():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        if not request.files:
            return jsonify({"error":"Файл фото обязателен в multipart/form-data!"}), 400
            
        photo_file = request.files.get('photo')
        if not photo_file:
            return jsonify({'error':'photo не найден в запросе.'}), 400
            
        try:
            photo_data = photo_file.stream.read()
            r = await functions.photo_make_black(photo_data)
            return jsonify({"result": base64.b64encode(r).decode()})
        except Exception as e:
            return jsonify({'error': f'Ошибка обработки: {str(e)}'}), 500
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403

@app.route('/utilits/censor_faces', methods=['POST'])
async def censor_faces_():
    if not request.files:
        return jsonify({"error":"Файл изображения обязателен в multipart/form-data!"}), 400
        
    image_file = request.files.get('photo')
    if not image_file.filename:
        return jsonify({'error':'photo не найден в запросе.'}), 400
        
    try:
        image_data = image_file.stream.read()
        _ = await asyncio.to_thread(fl.censor_faces_image, image_data, 'tiny')
        return jsonify({"image_with_censor": base64.b64encode(_).decode()}), 200
    except Exception as e:
        return jsonify({'error': f'Ошибка обработки: {str(e)}'}), 500
@app.route('/utilits/make_qr', methods=['GET'])
async def make_qr():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        content = request.args.get('content')
        if not content:
            return jsonify({"error":'content необязателен!'}), 400
        else:
            r = await functions.create_qr(content)
            return jsonify({'qr':base64.b64encode(r).decode()})
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/utilits/get_charts', methods=['GET'])
async def get_charts():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        r = await functions.get_charts()
        return jsonify(r.splitlines())
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/utilits/create_password', methods=['GET'])
async def create_password():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        r = await functions.generate_password()
        return jsonify({"password":r})
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/utilits/password_check', methods=['GET'])
async def password_check():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        nickname = request.args.get('nickname')
        if not nickname:
            return jsonify({"error":"nickname обязателен!"}), 400
        else:
            r = await functions.password_check(nickname)
            return jsonify({"count":r})
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/youtube/get_info_about_channel', methods=['GET'])
async def get_info_about_channel():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        url = request.args.get('url')
        if not url:
            return jsonify({"error":"url обязателен!"}), 400
        else:
            data = await functions.information_about_yt_channel(url)
            return jsonify(data)
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403
@app.route('/ai/text_to_speech', methods=['GET'])
async def ai_text_to_speech():
    is_b = await is_ip_banned(request.headers.get('X-Forwarded-For', '127.0.0.1'))
    if not is_b:
        content = request.args.get('content')
        lang = request.args.get('lang', 'ru')
        
        if not content:
            return jsonify({"error":"content обязателен!"}), 500
        else:
            if lang:
                r = await functions.text_to_speech(content, lang)
            else:
                r = await functions.text_to_speech(content)
            return jsonify({"result":base64.b64encode(r).decode()})
    else:
        return jsonify({"error":"This country has banned by FlorestAPI."}), 403

@app.route('/utilits/py_to_exe', methods=['POST'])
async def py_to_exe():
    py_file = request.files.get('py_file')
    if not py_file:
        return jsonify({"error":"py_file обязателен в files."}), 400
    else:
        r = random.random()
        f = open(f'{r}.py', 'wb')
        f.write(py_file.stream.read())
        f.close()
        i = os.system(f'pyinstaller --distpath {path} --onefile {r}.py')
        if i == 1:
            os.remove(path / f'{r}.py')
            return jsonify({"error":"Непревиденная ошибка. Обратите внимание на свой код для правильной компиляции."}), 500
        else:
            r_ = base64.b64encode(open(path / f'{r}.exe', 'rb').read()).decode()
            os.remove(path / f'{r}.py')
            os.remove(path / f'{r}.exe')
            return jsonify({"ready_application":r_}), 200
        
@app.route('/games/snake', methods=['GET'])
@limit.exempt
async def snake_games():
    if request.headers.get('Sec-Ch-Ua-Mobile', '?0') == '?0':
        code = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Змейка - FlorestAPI</title>
            <style>
                body {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    font-family: Arial, sans-serif;
                    background-color: #f0f0f0;
                }
                canvas {
                    border: 3px solid #333;
                    margin-top: 20px;
                    background-color: #000;
                }
                .info {
                    margin-top: 20px;
                    font-size: 20px;
                    text-align: center;
                }
                h1 {
                    color: #2e8b57;
                }
            </style>
        </head>
        <body>
            <h1>Змейка от Флореста!</h1>
            <div class="info">
                <p>Счёт: <span id="score" style="font-weight:bold">0</span></p>
                <p>Управление: стрелки клавиатуры</p>
            </div>
            <canvas id="gameCanvas" width="400" height="400"></canvas>

            <script>
                const canvas = document.getElementById('gameCanvas');
                const ctx = canvas.getContext('2d');
                const scoreElement = document.getElementById('score');

                // Настройки игры
                const gridSize = 20;
                const tileCount = canvas.width / gridSize;
                let score = 0;
                let gameSpeed = 120; // Скорость игры (меньше = быстрее)
                let gameRunning = true;

                // Змейка
                let snake = [
                    {x: 10, y: 10}
                ];
                let velocityX = 0;
                let velocityY = 0;

                // Еда
                let food = {
                    x: Math.floor(Math.random() * tileCount),
                    y: Math.floor(Math.random() * tileCount)
                };

                // Рисование с закругленными углами
                function roundRect(x, y, width, height, radius, color) {
                    ctx.beginPath();
                    ctx.moveTo(x + radius, y);
                    ctx.lineTo(x + width - radius, y);
                    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
                    ctx.lineTo(x + width, y + height - radius);
                    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
                    ctx.lineTo(x + radius, y + height);
                    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
                    ctx.lineTo(x, y + radius);
                    ctx.quadraticCurveTo(x, y, x + radius, y);
                    ctx.closePath();
                    ctx.fillStyle = color;
                    ctx.fill();
                }

                // Игровой цикл
                function gameLoop() {
                    if (!gameRunning) return;

                    // Очистка поля
                    ctx.fillStyle = 'black';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);

                    // Рисуем змейку
                    for (let i = 0; i < snake.length; i++) {
                        const color = i === 0 ? '#4CAF50' : '#2E8B57';
                        roundRect(
                            snake[i].x * gridSize + 1, 
                            snake[i].y * gridSize + 1, 
                            gridSize - 2, 
                            gridSize - 2, 
                            3, 
                            color
                        );
                    }

                    // Рисуем еду
                    roundRect(
                        food.x * gridSize + 1, 
                        food.y * gridSize + 1, 
                        gridSize - 2, 
                        gridSize - 2, 
                        10, 
                        '#FF5252'
                    );

                    // Двигаем змейку
                    const head = {
                        x: snake[0].x + velocityX,
                        y: snake[0].y + velocityY
                    };
                    snake.unshift(head);

                    // Проверка на съедание еды
                    if (head.x === food.x && head.y === food.y) {
                        score++;
                        scoreElement.textContent = score;
                        // Увеличиваем сложность
                        if (score % 5 === 0 && gameSpeed > 60) {
                            gameSpeed -= 5;
                        }
                        // Новая еда
                        food = {
                            x: Math.floor(Math.random() * tileCount),
                            y: Math.floor(Math.random() * tileCount)
                        };
                    } else {
                        // Удаляем хвост, если не съели еду
                        snake.pop();
                    }

                    // Проверка на столкновение с границами
                    if (
                        head.x < 0 || 
                        head.y < 0 || 
                        head.x >= tileCount || 
                        head.y >= tileCount
                    ) {
                        gameOver();
                        return;
                    }

                    // Проверка на столкновение с собой
                    for (let i = 1; i < snake.length; i++) {
                        if (head.x === snake[i].x && head.y === snake[i].y) {
                            gameOver();
                            return;
                        }
                    }

                    setTimeout(gameLoop, gameSpeed);
                }

                function gameOver() {
                    gameRunning = false;
                    alert(`Игра окончена! Ваш счёт: ${score}\nНажмите OK для перезапуска`);
                    resetGame();
                }

                function resetGame() {
                    score = 0;
                    scoreElement.textContent = score;
                    snake = [{x: 10, y: 10}];
                    velocityX = 0;
                    velocityY = 0;
                    gameSpeed = 120;
                    food = {
                        x: Math.floor(Math.random() * tileCount),
                        y: Math.floor(Math.random() * tileCount)
                    };
                    gameRunning = true;
                    setTimeout(gameLoop, gameSpeed);
                }

                // Управление
                document.addEventListener('keydown', (e) => {
                    // Блокируем другие клавиши и предотвращаем скроллинг страницы
                    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                        e.preventDefault();
                    }

                    // Избегаем разворота на 180 градусов
                    const key = e.key;
                    if (key === 'ArrowUp' && velocityY !== 1) {
                        velocityX = 0;
                        velocityY = -1;
                    } else if (key === 'ArrowDown' && velocityY !== -1) {
                        velocityX = 0;
                        velocityY = 1;
                    } else if (key === 'ArrowLeft' && velocityX !== 1) {
                        velocityX = -1;
                        velocityY = 0;
                    } else if (key === 'ArrowRight' && velocityX !== -1) {
                        velocityX = 1;
                        velocityY = 0;
                    }
                });

                // Запускаем игру
                resetGame();
            </script>
        </body>
        </html>
            
        """
        return Response(code, mimetype='text/html'), 200
    else:
        code = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Змейка - FlorestAPI</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    font-family: Arial, sans-serif;
                    background-color: #f0f0f0;
                    touch-action: none; /* Prevent default touch behaviors like scrolling */
                    margin: 0;
                    padding: 10px;
                    box-sizing: border-box;
                }
                canvas {
                    border: 3px solid #333;
                    margin-top: 10px;
                    background-color: #000;
                    max-width: 100%;
                }
                .info {
                    margin-top: 10px;
                    font-size: clamp(14px, 4vw, 16px);
                    text-align: center;
                }
                h1 {
                    color: #2e8b57;
                    font-size: clamp(20px, 6vw, 24px);
                    margin: 10px 0;
                }
                .controls {
                    margin-top: 10px;
                    display: grid;
                    grid-template-areas: 
                        ". up ."
                        "left down right";
                    gap: 8px;
                    justify-content: center;
                }
                .control-btn {
                    width: clamp(40px, 12vw, 50px);
                    height: clamp(40px, 12vw, 50px);
                    font-size: clamp(16px, 5vw, 20px);
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    touch-action: manipulation;
                }
                .control-btn:active {
                    background-color: #2E8B57;
                }
                #up-btn { grid-area: up; }
                #left-btn { grid-area: left; }
                #down-btn { grid-area: down; }
                #right-btn { grid-area: right; }
            </style>
        </head>
        <body>
            <h1>Змейка от Флореста!</h1>
            <div class="info">
                <p>Счёт: <span id="score" style="font-weight:bold">0</span></p>
                <p>Управление: стрелки клавиатуры или кнопки ниже</p>
            </div>
            <canvas id="gameCanvas"></canvas>
            <div class="controls">
                <button id="up-btn" class="control-btn">↑</button>
                <button id="left-btn" class="control-btn">←</button>
                <button id="down-btn" class="control-btn">↓</button>
                <button id="right-btn" class="control-btn">→</button>
            </div>

            <script>
                const canvas = document.getElementById('gameCanvas');
                const ctx = canvas.getContext('2d');
                const scoreElement = document.getElementById('score');

                // Responsive canvas size
                const size = Math.min(window.innerWidth, window.innerHeight) * 0.9;
                canvas.width = Math.floor(size / 20) * 20; // Ensure divisibility by gridSize
                canvas.height = canvas.width;

                // Настройки игры
                const gridSize = canvas.width / 20;
                const tileCount = 20;
                let score = 0;
                let gameSpeed = 120;
                let gameRunning = true;

                // Змейка
                let snake = [{x: 10, y: 10}];
                let velocityX = 0;
                let velocityY = 0;

                // Еда
                let food = {
                    x: Math.floor(Math.random() * tileCount),
                    y: Math.floor(Math.random() * tileCount)
                };

                // Рисование с закругленными углами
                function roundRect(x, y, width, height, radius, color) {
                    ctx.beginPath();
                    ctx.moveTo(x + radius, y);
                    ctx.lineTo(x + width - radius, y);
                    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
                    ctx.lineTo(x + width, y + height - radius);
                    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
                    ctx.lineTo(x + radius, y + height);
                    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
                    ctx.lineTo(x, y + radius);
                    ctx.quadraticCurveTo(x, y, x + radius, y);
                    ctx.closePath();
                    ctx.fillStyle = color;
                    ctx.fill();
                }

                // Игровой цикл
                function gameLoop() {
                    if (!gameRunning) return;

                    // Очистка поля
                    ctx.fillStyle = 'black';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);

                    // Рисуем змейку
                    for (let i = 0; i < snake.length; i++) {
                        const color = i === 0 ? '#4CAF50' : '#2E8B57';
                        roundRect(
                            snake[i].x * gridSize + 1, 
                            snake[i].y * gridSize + 1, 
                            gridSize - 2, 
                            gridSize - 2, 
                            gridSize * 0.15, // Scaled radius
                            color
                        );
                    }

                    // Рисуем еду
                    roundRect(
                        food.x * gridSize + 1, 
                        food.y * gridSize + 1, 
                        gridSize - 2, 
                        gridSize - 2, 
                        gridSize * 0.5, // Scaled radius
                        '#FF5252'
                    );

                    // Двигаем змейку
                    const head = {
                        x: snake[0].x + velocityX,
                        y: snake[0].y + velocityY
                    };
                    snake.unshift(head);

                    // Проверка на съедание еды
                    if (head.x === food.x && head.y === food.y) {
                        score++;
                        scoreElement.textContent = score;
                        if (score % 5 === 0 && gameSpeed > 60) {
                            gameSpeed -= 5;
                        }
                        food = {
                            x: Math.floor(Math.random() * tileCount),
                            y: Math.floor(Math.random() * tileCount)
                        };
                    } else {
                        snake.pop();
                    }

                    // Проверка на столкновение с границами
                    if (
                        head.x < 0 || 
                        head.y < 0 || 
                        head.x >= tileCount || 
                        head.y >= tileCount
                    ) {
                        gameOver();
                        return;
                    }

                    // Проверка на столкновение с собой
                    for (let i = 1; i < snake.length; i++) {
                        if (head.x === snake[i].x && head.y === snake[i].y) {
                            gameOver();
                            return;
                        }
                    }

                    setTimeout(gameLoop, gameSpeed);
                }

                function gameOver() {
                    gameRunning = false;
                    alert(`Игра окончена! Ваш счёт: ${score}\nНажмите OK для перезапуска`);
                    resetGame();
                }

                function resetGame() {
                    score = 0;
                    scoreElement.textContent = score;
                    snake = [{x: 10, y: 10}];
                    velocityX = 0;
                    velocityY = 0;
                    gameSpeed = 120;
                    food = {
                        x: Math.floor(Math.random() * tileCount),
                        y: Math.floor(Math.random() * tileCount)
                    };
                    gameRunning = true;
                    setTimeout(gameLoop, gameSpeed);
                }

                // Управление клавиатурой
                document.addEventListener('keydown', (e) => {
                    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                        e.preventDefault();
                    }

                    const key = e.key;
                    if (key === 'ArrowUp' && velocityY !== 1) {
                        velocityX = 0;
                        velocityY = -1;
                    } else if (key === 'ArrowDown' && velocityY !== -1) {
                        velocityX = 0;
                        velocityY = 1;
                    } else if (key === 'ArrowLeft' && velocityX !== 1) {
                        velocityX = -1;
                        velocityY = 0;
                    } else if (key === 'ArrowRight' && velocityX !== -1) {
                        velocityX = 1;
                        velocityY = 0;
                    }
                });

                // Управление кнопками
                document.getElementById('up-btn').addEventListener('click', () => {
                    if (velocityY !== 1) {
                        velocityX = 0;
                        velocityY = -1;
                    }
                });
                document.getElementById('left-btn').addEventListener('click', () => {
                    if (velocityX !== 1) {
                        velocityX = -1;
                        velocityY = 0;
                    }
                });
                document.getElementById('down-btn').addEventListener('click', () => {
                    if (velocityY !== -1) {
                        velocityX = 0;
                        velocityY = 1;
                    }
                });
                document.getElementById('right-btn').addEventListener('click', () => {
                    if (velocityX !== -1) {
                        velocityX = 1;
                        velocityY = 0;
                    }
                });

                // Handle window resize
                window.addEventListener('resize', () => {
                    const newSize = Math.min(window.innerWidth, window.innerHeight) * 0.9;
                    canvas.width = Math.floor(newSize / 20) * 20;
                    canvas.height = canvas.width;
                    // Update gridSize for rendering
                    window.gridSize = canvas.width / 20;
                });

                // Запускаем игру
                resetGame();
            </script>
        </body>
        </html>
        """
        return Response(code, mimetype='text/html')
    
@app.route('/games/clicker', methods=['GET'])
@limit.exempt
async def games_clicker():
    code = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Кликер | FlorestDev.</title>
        <style>
            body {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                background-color: #f0f0f0;
                color: #333;
                font-family: Arial, sans-serif;
            }
            h1 {
                margin-bottom: 20px;
                font-size: 2em;
            }
            #clickButton {
                padding: 20px;
                font-size: 1.5em;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                transition: background-color 0.3s;
            }
            #clickButton:hover {
                background-color: #218838;
            }
            #score {
                font-size: 3em;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <h1>Кликер Флореста</h1>
        <p id="greeting"></p>
        <p id="recomendations">Желаю удачи в тапании кнопке ниже.<br>Надеюсь, Вам понравился данный кликер и вы подпишитесь на <a href="https://taplink.cc/florestone4185">мои социальные сети</a></p>
        <p id="score">Очки: 0</p>
        <img src="https://yt3.ggpht.com/a/AGF-l78TQy2bDo_WgEkZGYDSfi7AX6JZn1LN5hL_-w=s88-c-k-c0xffffffff-no-rj-mo" alt="Кнопка, на которую нужно нажимать." id="clickButton">

        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <script>
            // Получаем информацию о пользователе
            const user = window.Telegram.WebApp.initDataUnsafe.user;
            const greetingElement = document.getElementById('greeting');
            const scoreElement = document.getElementById('score');
            const clickButton = document.getElementById('clickButton');
            const recomendations = document.getElementById('recomendations');
            
            // Приветствие пользователя
            if (user && user.first_name) {
                window.Telegram.WebApp.expand();
                alert(`Добро пожаловать! В этой игре-тапалке - ты ген. директор FlorestDev.\nЗдесь, ты жестко тапаешь кнопочку внизу экрана.\nЭто самый обычный кликер, без заработков в час и т.д. Красивый дизайн и простота.\nУдачи тебе, ${user.first_name}`);
                greetingElement.textContent = `${user.first_name} (Ген. директор)`;
            } 
            else {
                greetingElement.textContent = 'Неизвестный (Ген. Директор)';
                recomendations.textContent = 'Внимание! Так как ты не вошёл через WebApp Telegram - твоего имени здесь нет. А так, удачи в тапании!';
            }

            // Инициализация счётчика очков
            let score = 0;

            // Обработчик клика по кнопке
            clickButton.addEventListener('click', function() {
                score++;
                scoreElement.textContent = `Очки: ${score}`;
            });
        </script>
    </body>
    </html>
    """
    return Response(code, mimetype='text/html')

@app.route('/utilits/send_mail', methods=['POST'])
async def utilits_send_mail():
    # Получаем заголовки
    service = request.headers.get('Service')
    port = request.headers.get('Port')
    username = request.headers.get('User')
    password = request.headers.get('Password')
    
    # Проверяем, что все заголовки на месте
    if not all([service, port, username, password]):
        return jsonify({"error": "Нужно указать Service, Port, User и Password в заголовках."}), 400
    
    # Проверяем, что порт — это число и в разумных пределах
    if not port.isdigit() or not (0 < int(port) <= 65535):
        return jsonify({"error": "Port должен быть числом от 1 до 65535."}), 400
    
    # Проверяем валидность email-адреса отправителя и получателя
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    
    # Получаем параметры запроса
    title = request.args.get('title')
    description = request.args.get('description')
    receiver = request.args.get('receiver')
    
    # Проверяем, что все параметры переданы
    if not all([title, description, receiver]):
        return jsonify({"error": "Введите title, description и receiver в параметрах запроса."}), 400
    
    # Проверяем валидность email получателя
    if not re.match(email_regex, receiver):
        return jsonify({"error": "Некорректный email в receiver."}), 400
    
    try:
        # Создаём письмо
        msg = EmailMessage()
        msg['Subject'] = title
        msg['From'] = username
        msg['To'] = receiver
        msg.set_content(description)  # Используем set_content вместо add_alternative для простоты
        
        use_tls = port == "587"  # STARTTLS для порта 587
        use_ssl = port == "465"  # SSL для порта 465
        
        # Подключаемся к SMTP-серверу
        async with aiosmtplib.SMTP(hostname=service, port=int(port), use_tls=use_ssl, start_tls=use_tls, timeout=5) as server:
            if use_tls:
                await server.starttls()  # Включаем TLS
            await server.login(username, password)  # Логинимся
            await server.send_message(msg)  # Отправляем письмо
            
        return jsonify({"success": f"Письмо успешно отправлено на {receiver}."}), 200
    
    except aiosmtplib.SMTPException as e:
        return jsonify({"error": f"Ошибка отправки письма: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Что-то пошло не так: {str(e)}"}), 500
    
@app.route('/admin/create_new_api_key', methods=['GET'])
@limit.exempt
async def create_new_api_key():
    user_agent = request.headers.get('User-Agent')
    if user_agent != 'your-useragent':
        return jsonify({"error":"Доступ запрещен!"}), 401
    key = request.headers.get('Key')
    if key != 'your-key':
        return jsonify({"error":"Доступ запрещен!"}), 401
    else:
        id = int(request.args.get('id'))
        connection = await aiosqlite.connect(DB_PATH)
        check = await connection.execute(f'SELECT * FROM users WHERE id=?', (id, ))
        if await check.fetchone() != None:
            return jsonify({"error":"API ключ уже зарегистрирован!"}), 400
        else:
            key = await functions.generate_password(20)
            await connection.execute('INSERT INTO users VALUES (?, ?)', (id, key, ))
            await connection.commit()
            return jsonify({"api_key":key})
        
@app.route('/utilits/get_minecraft_server_info', methods=['GET']) 
async def utilits_get_minecraft_server_info():
    ip = request.args.get('ip')
    port = request.args.get('port')
    
    if not ip:
        return jsonify({"error":"Необходим IP и порт сервера (опционально)."}), 404
    else:
        try:
            if not port:
                server = JavaServer(ip)
            else:
                server = JavaServer(ip, port)
            latency = await asyncio.to_thread(server.ping)
            query = await asyncio.to_thread(server.query)
            status = await asyncio.to_thread(server.status)
            return jsonify({"latency":latency, 'query':{"query_motd":query.motd.to_ansi(), 'query_map':query.map, 'query_players_count':query.players.online, 'query_players_max':query.players.max}, 'status':{"query_motd":status.motd.to_ansi(), 'description':status.description, 'icon_of_server_base64':status.icon, 'query_players_count':query.players.online, 'query_players_max':query.players.max, 'version':status.version.name}})
        except Exception as e:
            return jsonify({"error":f"Произошла ошибка: {e}. Скорее всего, данные о сервере были неправильны."})
        
@app.route('/utilits/cpp_to_exe', methods=['POST'])
async def auto_cpp_to_exe():
    files = request.files
    
    if not files:
        return jsonify({"error":"Не были найдены файлы в files."}), 400
    else:
        application = request.files.get('app')
        if not application:
            return jsonify({"error":"Не были найдены файлы в files."}), 400
        else:
            r = random.random()
            _ = application.stream.read()
            f = open(path / f'{r}.cpp', 'wb')
            f.write(_)
            f.close()
            operation = await asyncio.to_thread(os.system, f'g++ {r}.cpp -o {r}')
            if operation == 1:
                await asyncio.to_thread(os.remove, path / f'{r}.cpp')
                try:
                    await asyncio.to_thread(os.remove, path / f'{r}.exe')
                except:
                    pass
                return jsonify({"error":"Ошибка компиляции кода."}), 500
            else:
                a = open(path / f'{r}.exe', 'rb').read()
                await asyncio.to_thread(os.remove, path / f'{r}.cpp')
                try:
                    await asyncio.to_thread(os.remove, path / f'{r}.exe')
                except:
                    pass
                return jsonify({"exe_in_base64":base64.b64encode(a).decode()})

if __name__ == '__main__':
    app.run('0.0.0.0', 80)
