GIGACHAT_API_KEY = '934c718e70f7374e0e2eab4236c612f4'
GIGACHAT_API_URL = 'https://gigachat-api.sbercloud.ru/v1/your-endpoint'


import requests

def generate_recommendations(flake8_output, pylint_output):
    messages = flake8_output + "\n" + pylint_output
    try:
        response = requests.post(
            GIGACHAT_API_URL,
            headers={
                'Authorization': f'Bearer {GIGACHAT_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'messages': [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"Дайте рекомендации по устранению следующих ошибок кода:\n{messages}"}
                ],
                'max_tokens': 500,
                'temperature': 0.7
            }
        )
        response_json = response.json()
        return response_json['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Ошибка при обращении к GigaChat API: {e}"


generate_recommendations()
