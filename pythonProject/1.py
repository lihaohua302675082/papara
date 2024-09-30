import requests

import requests

def main():
    acsTransID = 'ca275af8-f919-4d71-847a-ab96e03ce0d4'  # 替换为提取到的 acsTransID
    proxies = {
        "http": "http://127.0.0.1:7890",  # 根据你的 Clash 配置修改
        "https": "http://127.0.0.1:7890",

    }
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'p': '2',
        'X-Papara-App-Version': '3.10.32',
        'X-Papara-App-Build': '348',
        'X-Papara-App-Platform': 'Android',
        'X-Papara-App-Device-Manufacturer': 'samsung',
        'X-Papara-App-Device-Description': 'LIO-AN00',
        'X-Papara-App-Device-Identifier': '459a0118f6d80057',
        'X-Resource-Language': 'en-US',
        'X-Papara-App-Dark-Mode-Enabled': 'false',
        'X-Papara-App-Device-System-Version': '28',
        'X-IsNfcSupported': 'false',
        'X-IsVoiceOverRunning': 'false',
        'User-Agent': 'Papara/Android/3.10.32',
        'Host': 'api.papara.com',
        'Connection': 'Keep-Alive',
    }

    try:
        result = requests.post(
            'https://api.papara.com/acs/challengeresult',
            json={
  "acsTransID": "9d19191d-7884-416c-83f5-237ac1d6e751",
  "refNo": "19PJLEL3"
},
            headers=headers,
            proxies=proxies
        )

        if result.status_code == 200:
            print("成功发送 3DS 验证:", result.text)
        else:
            print("发送失败，状态码:", result.status_code)

    except requests.exceptions.RequestException as e:
        print("请求异常:", e)

if __name__ == "__main__":
    main()

