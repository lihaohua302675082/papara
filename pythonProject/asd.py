from quart import Quart, request, jsonify, render_template, redirect, url_for
import aiosqlite
import aiohttp
import asyncio
import warnings

warnings.filterwarnings("ignore")

app = Quart(__name__)

# 设置每个用户的acsTransID累积数量阈值，可以根据需要调整
ACS_TRANSID_THRESHOLD = {}

async def init_db():
    async with aiosqlite.connect('acstransid.db') as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS ids (
                acsTransID TEXT,
                used INTEGER DEFAULT 0,
                user TEXT,
                UNIQUE(acsTransID, user)
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS device (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                user TEXT,
                UNIQUE(device_id, user)
            )
        ''')
        await conn.commit()

async def add_acsTransID(acsTransID, user):
    async with aiosqlite.connect('acstransid.db') as conn:
        try:
            await conn.execute('INSERT INTO ids (acsTransID, user) VALUES (?, ?)', (acsTransID, user))
            await conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False
async def delete_device_by_id(user, index):
    async with aiosqlite.connect('acstransid.db') as conn:
        # 获取该用户的设备列表
        async with conn.execute('SELECT id FROM device WHERE user = ?', (user,)) as cursor:
            device_ids = await cursor.fetchall()

        if index < 1 or index > len(device_ids):
            return "Invalid index. Please provide a valid number."

        # 获取要删除的设备 ID
        device_id_to_delete = device_ids[index - 1][0]

        # 删除设备 ID
        await conn.execute('DELETE FROM device WHERE id = ?', (device_id_to_delete,))
        await conn.commit()
        return f"Device ID at position {index} deleted successfully."


async def add_device_id(device_id, user):
    async with aiosqlite.connect('acstransid.db') as conn:
        cursor = await conn.execute('SELECT COUNT(*) FROM device WHERE device_id = ? AND user = ?', (device_id, user))
        if (await cursor.fetchone())[0] == 0:
            cursor = await conn.execute('SELECT COUNT(*) FROM device WHERE user = ?', (user,))
            count = (await cursor.fetchone())[0]
            if count < 5:
                await conn.execute('INSERT INTO device (device_id, user) VALUES (?, ?)', (device_id, user))
            else:
                cursor = await conn.execute('SELECT id FROM device WHERE user = ? ORDER BY id LIMIT 1', (user,))
                oldest_id = (await cursor.fetchone())[0]
                await conn.execute('UPDATE device SET device_id = ? WHERE id = ?', (device_id, oldest_id))
            await conn.commit()

async def delete_device_id(device_id, user):
    async with aiosqlite.connect('acstransid.db') as conn:
        await conn.execute('DELETE FROM device WHERE device_id = ? AND user = ?', (device_id, user))
        await conn.commit()

async def get_device_ids(user):
    async with aiosqlite.connect('acstransid.db') as conn:
        cursor = await conn.execute('SELECT device_id FROM device WHERE user = ?', (user,))
        results = await cursor.fetchall()
        return [row[0] for row in results]

async def mark_acsTransID_as_used(acsTransID, user):
    async with aiosqlite.connect('acstransid.db') as conn:
        await conn.execute('UPDATE ids SET used = 1 WHERE acsTransID = ? AND user = ?', (acsTransID, user))
        await conn.commit()

async def send_post_request(acsTransID, device_id, user):
    if user == 'lhh':
        # 使用您提供的iOS请求头部
        headers = {
            'Host': 'api.papara.com',
            'X-Papara-App-Platform': 'iOS',
            'User-Agent': 'Papara/iOS/3.14.0',
            'p': '1',
            'X-Papara-App-Device-Manufacturer': 'Apple',
            'X-Papara-App-Build': '757',
            'X-IsVoiceOverRunning': 'false',
            'X-Papara-App-Device-System-Version': '16.6.1',
            'X-Papara-App-Version': '3.14.0',
            'X-Papara-App-Device-Identifier': device_id,
            'X-Papara-App-Device-Model': 'iPhone',
            'Connection': 'keep-alive',
            'X-IsNfcSupported': 'true',
            'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
            'X-Papara-App-Device-Description': 'iPhone 12 mini',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Resource-Language': 'en-US',
            'X-Papara-App-Dark-Mode-Enabled': 'false',
            'Content-Type': 'application/json; charset=UTF-8',
        }
    else:
        # 默认使用Android请求头部
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
            'p': '2',
            'X-Papara-App-Version': '3.13.0',
            'X-Papara-App-Build': '395',
            'X-Papara-App-Platform': 'Android',
            'X-Papara-App-Device-Manufacturer': 'VIVO',
            'X-Papara-App-Device-Description': 'LYA-AL111',
            'X-Papara-App-Device-Identifier': device_id,
            'X-Resource-Language': 'en-US',
            'X-Papara-App-Dark-Mode-Enabled': 'false',
            'X-Papara-App-Device-System-Version': '18',
            'X-IsNfcSupported': 'false',
            'X-IsVoiceOverRunning': 'false',
            'User-Agent': 'Papara/Android/3.13.0',
            'Host': 'api.papara.com',
            'Connection': 'Keep-Alive',
        }

    json_data = {
        'AcsTransID': acsTransID,
        'IsApproved': True,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.papara.com/acs/challengeresult',
                headers=headers,
                json=json_data,
                ssl=False
            ) as response:
                if response.status == 200:
                    message = f"成功发送POST请求，AcsTransID: {acsTransID}，Device ID: {device_id}，User: {user}"
                    print(message)
                    return {"status": "success", "message": message}
                else:
                    # 如果不是 200 状态码，返回空消息
                    return {"status": "error", "message": None}
    except Exception as e:
        # 如果发生异常，返回空消息
        print(f"发送POST请求时出错: {e}")
        return {"status": "error", "message": None}
async def process_unprocessed_acsTransIDs(user, force=False):
    device_ids = await get_device_ids(user)
    messages = []  # 用来存储每次请求的结果（包括成功、失败和无可用设备ID的消息）
    if not device_ids:
        no_device_message = f"没有可用的设备ID for user {user}"
        print(no_device_message)
        messages.append(no_device_message)  # 返回无可用设备ID的消息
        return messages
    async with aiosqlite.connect('acstransid.db') as conn:
        cursor = await conn.execute('SELECT acsTransID FROM ids WHERE used = 0 AND user = ?', (user,))
        acsTransIDs = await cursor.fetchall()
        threshold = ACS_TRANSID_THRESHOLD.get(user, 1)

        if force or len(acsTransIDs) >= threshold:
            tasks = []
            for acsTransID_tuple in acsTransIDs:
                acsTransID = acsTransID_tuple[0]
                for device_id in device_ids:
                    result = await send_post_request(acsTransID, device_id, user)
                    messages.append(result["message"])  # 保存所有的消息（成功或失败）
                await mark_acsTransID_as_used(acsTransID, user)
            if tasks:
                await asyncio.gather(*tasks)

    return messages  # 返回所有请求的消息

@app.route('/<user>/get_device_ids', methods=['GET'])
async def get_device_ids_route(user):
    device_ids = await get_device_ids(user)
    return jsonify({"device_ids": device_ids}), 200

@app.route('/<user>/get_status', methods=['GET'])
async def get_status(user):
    async with aiosqlite.connect('acstransid.db') as conn:
        # 获取用户的所有 device_id
        cursor = await conn.execute('SELECT device_id FROM device WHERE user = ?', (user,))
        device_rows = await cursor.fetchall()
        device_ids = [row[0] for row in device_rows] if device_rows else ['Not available']

        # 获取用户的所有未使用的 acsTransID
        cursor = await conn.execute('SELECT acsTransID FROM ids WHERE user = ? AND used = 0', (user,))
        acs_trans_rows = await cursor.fetchall()
        acs_trans_ids = [row[0] for row in acs_trans_rows] if acs_trans_rows else ['Not available']

    return jsonify({
        "device_ids": device_ids,
        "acs_trans_ids": acs_trans_ids
    })

@app.route('/<user>/receive', methods=['POST'])
@app.route('/<user>/receive/<string:acsTransID>', methods=['GET'])
async def receive(user, acsTransID=None):
    if request.method == 'POST':
        data = await request.get_json()
        acsTransID = data.get('acsTransID')
        force = data.get('force', False)
    else:
        force = False

    if acsTransID:
        if await add_acsTransID(acsTransID, user):
            # 检查是否立即处理
            await process_unprocessed_acsTransIDs(user, force=force)
            return jsonify({"status": f"收到 acsTransID for user {user}"}), 200
        else:
            return jsonify({"status": f"重复的 acsTransID 已忽略 for user {user}"}), 200
    return jsonify({"error": "请求中没有 acsTransID"}), 400

@app.route('/<user>/receive_device', methods=['POST'])
@app.route('/<user>/receive_device/<string:device_id>', methods=['GET'])
async def receive_device(user, device_id=None):
    if request.method == 'POST':
        data = await request.get_json()
        device_id = data.get('device_id')
    if device_id:
        await add_device_id(device_id, user)
        # 不立即处理 acsTransID，而是等达到阈值或手动触发
        return jsonify({"status": f"device_id 已更新 for user {user}"}), 200
    return jsonify({"error": "请求中没有 device_id"}), 400

@app.route('/<user>/delete_device/<string:device_id>', methods=['DELETE'])
async def delete_device(user, device_id):
    await delete_device_id(device_id, user)
    return jsonify({"status": f"device_id {device_id} 已删除 for user {user}"}), 200

@app.route('/<user>/set_threshold/<int:threshold>', methods=['GET'])
async def set_threshold(user, threshold):
    ACS_TRANSID_THRESHOLD[user] = threshold
    return jsonify({"status": f"用户 {user} 的阈值已设置为 {threshold}"}), 200

@app.route('/<user>/process_now', methods=['GET'])
async def process_now(user):
    await process_unprocessed_acsTransIDs(user, force=True)
    return jsonify({"status": f"已立即处理用户 {user} 的未处理 acsTransID"}), 200

@app.route('/<user>/delete_device_by_id/<int:index>', methods=['DELETE'])
async def delete_device_id(user, index):
    result = await delete_device_by_id(user, index)
    return jsonify({'status': result})

@app.before_serving
async def startup():
    await init_db()

# 首页，提供输入用户的表单
@app.route('/')
async def index():
    return await render_template('index.html')

# 跳转并显示 user_page.html 页面，处理查询参数
@app.route('/user_page', methods=['GET'])
async def user_page():
    username = request.args.get('username')

    if not username:
        return redirect(url_for('index'))

    # 查询数据库，获取用户的所有 device_id 和 acsTransID
    async with aiosqlite.connect('acstransid.db') as conn:
        # 获取用户的所有 device_id
        cursor = await conn.execute('SELECT device_id FROM device WHERE user = ?', (username,))
        device_rows = await cursor.fetchall()
        device_ids = [row[0] for row in device_rows] if device_rows else ['Not available']

        # 获取用户的所有未使用的 acsTransID
        cursor = await conn.execute('SELECT acsTransID FROM ids WHERE user = ? AND used = 0', (username,))
        acs_trans_rows = await cursor.fetchall()
        acs_trans_ids = [row[0] for row in acs_trans_rows] if acs_trans_rows else ['Not available']

    # 渲染 user_page.html 并传递用户的所有 device_id 和 acsTransID
    return await render_template('user_page.html', username=username, device_ids=device_ids, acsTransIDs=acs_trans_ids)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)

