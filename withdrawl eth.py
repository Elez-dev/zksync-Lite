import random, hmac, base64
from web3 import Web3
import requests
import logging
import time

RETRY = 10
sleep_min = 50
sleep_max = 100

# можешь записать любое кол-во аккаунтов, сделал таким образом чтобы постоянно данные от новых акков не вводить, а просто вызывать по имени аккаунта
OKX_KEYS = {
    'account_1' : {
        'api_key'   : 'your_api_key',
        'api_secret': 'your_api_secret',
        'password'  : 'your_api_password',
    },
    'account_2' : {
        'api_key'   : 'your_api_key',
        'api_secret': 'your_api_secret',
        'password'  : 'your_api_password',
    },
}


def value_okx():

    chain       = 'zkSync Lite'
    symbol      = 'ETH'

    amount_from = 0.001
    amount_to   = 0.001

    account = 'account_1'

    FEE         = 0.0002 # комса на вывод
    SUB_ACC     = False # True / False. True если хочешь проверять субаккаунты и сначала делать с них перевод на основной счет

    is_private_key = True # True если в wallets.txt вставил evm приватники. False если адреса (evm / не evm)

    return chain, symbol, amount_from, amount_to, account, FEE, SUB_ACC, is_private_key


logger = logging.getLogger()
console_out = logging.StreamHandler()
basic_format = logging.Formatter('%(asctime)s : %(message)s')
console_out.setFormatter(basic_format)
logger.setLevel(logging.INFO)
logger.addHandler(console_out)


def okx_data(api_key, secret_key, passphras, request_path="/api/v5/account/balance?ccy=USDT", body='', meth="GET"):

    try:
        import datetime
        def signature(
            timestamp: str, method: str, request_path: str, secret_key: str, body: str = ""
        ) -> str:
            if not body:
                body = ""

            message = timestamp + method.upper() + request_path + body
            mac = hmac.new(
                bytes(secret_key, encoding="utf-8"),
                bytes(message, encoding="utf-8"),
                digestmod="sha256",
            )
            d = mac.digest()
            return base64.b64encode(d).decode("utf-8")

        dt_now = datetime.datetime.utcnow()
        ms = str(dt_now.microsecond).zfill(6)[:3]
        timestamp = f"{dt_now:%Y-%m-%dT%H:%M:%S}.{ms}Z"

        base_url = "https://www.okex.com"
        headers = {
            "Content-Type": "application/json",
            "OK-ACCESS-KEY": api_key,
            "OK-ACCESS-SIGN": signature(timestamp, meth, request_path, secret_key, body),
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": passphras,
            'x-simulated-trading': '0'
        }
    except Exception as ex:
        logger.error(ex)
    return base_url, request_path, headers


def evm_wallet(key):

    try:
        web3 = Web3(Web3.HTTPProvider('https://rpc.ankr.com/eth'))
        wallet = web3.eth.account.from_key(key).address
        return wallet
    except:
        return key


def okx_withdraw(privatekey, retry=0):

    CHAIN, SYMBOL, amount_from, amount_to, account, FEE, SUB_ACC, is_private_key = value_okx()

    AMOUNT = round(random.uniform(amount_from, amount_to), 7)

    api_key         = OKX_KEYS[account]['api_key']
    secret_key      = OKX_KEYS[account]['api_secret']
    passphras       = OKX_KEYS[account]['password']

    if is_private_key == True:
        wallet = evm_wallet(privatekey)
    else:
        wallet = privatekey

    try:

        if SUB_ACC is True:

            try:

                _, _, headers = okx_data(api_key, secret_key, passphras, request_path=f"/api/v5/users/subaccount/list", meth="GET")
                list_sub = requests.get("https://www.okx.cab/api/v5/users/subaccount/list", timeout=10, headers=headers)
                list_sub = list_sub.json()

                for sub_data in list_sub['data']:

                    name_sub = sub_data['subAcct']

                    _, _, headers = okx_data(api_key, secret_key, passphras, request_path=f"/api/v5/asset/subaccount/balances?subAcct={name_sub}&ccy={SYMBOL}", meth="GET")
                    sub_balance = requests.get(f"https://www.okx.cab/api/v5/asset/subaccount/balances?subAcct={name_sub}&ccy={SYMBOL}", timeout=10, headers=headers)
                    sub_balance = sub_balance.json()
                    sub_balance = sub_balance['data'][0]['bal']

                    logger.info(f'{name_sub} | sub_balance : {sub_balance} {SYMBOL}')

                    body = {"ccy": f"{SYMBOL}", "amt": str(sub_balance), "from": 6, "to": 6, "type": "2", "subAcct": name_sub}
                    _, _, headers = okx_data(api_key, secret_key, passphras, request_path=f"/api/v5/asset/transfer", body=str(body), meth="POST")
                    a = requests.post("https://www.okx.cab/api/v5/asset/transfer", data=str(body), timeout=10, headers=headers)
                    a.json()
                    time.sleep(1)

            except Exception as error:
                logger.error(f'{error}. list_sub : {list_sub}')

        try:
            _, _, headers = okx_data(api_key, secret_key, passphras, request_path=f"/api/v5/account/balance?ccy={SYMBOL}")
            balance = requests.get(f'https://www.okx.cab/api/v5/account/balance?ccy={SYMBOL}', timeout=10, headers=headers)
            balance = balance.json()
            balance = balance["data"][0]["details"][0]["cashBal"]
            # print(balance)

            if balance != 0:
                body = {"ccy": f"{SYMBOL}", "amt": float(balance), "from": 18, "to": 6, "type": "0", "subAcct": "", "clientId": "", "loanTrans": "", "omitPosRisk": ""}
                _, _, headers = okx_data(api_key, secret_key, passphras, request_path=f"/api/v5/asset/transfer", body=str(body), meth="POST")
                requests.post("https://www.okx.cab/api/v5/asset/transfer", data=str(body), timeout=10, headers=headers)
        except Exception as ex:
            pass

        body = {"ccy" :SYMBOL, "amt" :AMOUNT, "fee" :FEE, "dest" :"4", "chain" :f"{SYMBOL}-{CHAIN}", "toAddr" :wallet}
        _, _, headers = okx_data(api_key, secret_key, passphras, request_path=f"/api/v5/asset/withdrawal", meth="POST", body=str(body))
        a = requests.post("https://www.okx.cab/api/v5/asset/withdrawal", data=str(body), timeout=10, headers=headers)
        result = a.json()
        # cprint(result, 'blue')

        if result['code'] == '0':
            logger.info(f"withdraw success => {wallet} | {AMOUNT} {SYMBOL}")
            return "success"
        else:
            error = result['msg']
            logger.error(f"withdraw unsuccess => {wallet} | error : {error}")
            if retry < RETRY:
                logger.info(f"try again in 10 sec. => {wallet}")
                time.sleep(10)
                okx_withdraw(privatekey, retry+1)

    except Exception as error:
        logger.error(f"withdraw unsuccess => {wallet} | error : {error}")
        if retry < RETRY:
            logger.info(f"try again in 10 sec. => {wallet}")
            time.sleep(10)
            okx_withdraw(privatekey, retry+1)


if __name__ == '__main__':
    print('  _  __         _               _                                           _ _         ')
    print(' | |/ /___   __| | ___ _ __ ___| | ____ _ _   _  __ _        _____   ____ _| | | ____ _ ')
    print(" | ' // _ \ / _` |/ _ \ '__/ __| |/ / _` | | | |/ _` |      / __\ \ / / _` | | |/ / _` |")
    print(r' | . \ (_) | (_| |  __/ |  \__ \   < (_| | |_| | (_| |      \__ \\ V / (_| | |   < (_| |')
    print(' |_|\_\___/ \__,_|\___|_|  |___/_|\_\__,_|\__, |\__,_|      |___/ \_/ \__,_|_|_|\_\__,_|')
    print('                                          |___/                                    ', '\n')
    print('https://t.me/developercode1')
    print('https://t.me/developercode1')
    print('https://t.me/developercode1\n\n')

    with open("private_key.txt", "r") as f:
        keys_list = [row.strip() for row in f]

    for key in keys_list:
        okx_withdraw(key)
        time.sleep(random.randint(sleep_min, sleep_max))

