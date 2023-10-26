import random
from web3 import Web3
from requests.adapters import Retry
import requests
import logging
import threading
from utils.lite import ZkSyncLite
from Option import *
from tqdm import tqdm
import time


def sleeping(sleep_from: int, sleep_to: int):
    delay = random.randint(sleep_from, sleep_to)
    with tqdm(
            total=delay,
            desc="💤 Sleep",
            bar_format="{desc}: |{bar:20}| {percentage:.0f}% | {n_fmt}/{total_fmt}",
            colour="green"
    ) as pbar:
        for _ in range(delay):
            time.sleep(1)
            pbar.update(1)


def get_chain(chain):
    if chain == 'Arbitrum':
        chain = 'arbitrum'
    elif chain == 'ZkSync_Era':
        chain = 'zksynk'
    elif chain == 'Optimism':
        chain = 'optimism'
    elif chain == 'Polygon':
        chain = 'polygon'
    elif chain == 'BSC':
        chain = 'bsc'
    else:
        raise ValueError("\nНеверное значение переменной 'chain_from'. Ожидается 'Arbitrum' or 'ZkSync' or 'Optimism'.")
    return chain


def get_path(system):
    if system == 0:
        path = r'\utils\lib\zks-crypto-x86_64-pc-windows-gnu.dll'
    elif system == 1:
        path = r'\utils\lib\zks-crypto-aarch64-apple-darwin.a'
    elif system == 2:
        path = r'\utils\lib\zks-crypto-x86_64-apple-darwin.a'
    elif system == 3:
        path = r'\utils\lib\zks-crypto-x86_64-unknown-linux-gnu.a'
    else:
        raise ValueError('Вы ввели неверное значение переменной "system". Ожидало 0, 1, 2 или 3')
    return path


def shuffle(wallets_list, shuffle_wallets):
    if shuffle_wallets is True:
        numbered_wallets = list(enumerate(wallets_list, start=1))
        random.shuffle(numbered_wallets)
    elif shuffle_wallets is False:
        numbered_wallets = list(enumerate(wallets_list, start=1))
    else:
        raise ValueError("\nНеверное значение переменной 'shuffle_wallets'. Ожидается 'True' or 'False'.")
    return numbered_wallets


class Worker:

    def run(self):

        log = logging.getLogger(threading.current_thread().name)
        console_out = logging.StreamHandler()
        basic_format = logging.Formatter('%(asctime)s : %(message)s')
        console_out.setFormatter(basic_format)
        file_handler = logging.FileHandler(f"LOGS/{threading.current_thread().name}.txt", 'w', 'utf-8')
        file_handler.setFormatter(basic_format)
        log.setLevel(logging.DEBUG)
        log.addHandler(console_out)
        log.addHandler(file_handler)

        path_to_lib = get_path(SYSTEM)

        while keys_list:
            account = keys_list.pop(0)
            number = account[0]
            private_key = account[1]
            retries = Retry(total=100, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
            adapter = requests.adapters.HTTPAdapter(max_retries=retries)
            session = requests.Session()
            session.mount('http://', adapter)
            session.mount('https://', adapter)

            web3 = Web3(Web3.HTTPProvider(RPC_ETH, request_kwargs={'timeout': 120}, session=session))

            address = web3.eth.account.from_key(private_key).address
            log.info('----------------------------------------------------------------------------')
            log.info(f'|   Сейчас работает аккаунт - {address}   |')
            log.info('----------------------------------------------------------------------------\n\n')

            str_number = f'{number} / {all_wallets}'
            lite = ZkSyncLite(private_key, web3, str_number, log)
            wallet = lite.connect_wallet(path_to_lib)
            lite.check_create_acc(wallet)

            if MINT_NFT is True:
                cid = cid_list.pop(0)
                res = lite.claim_nft(wallet, cid)
                if res == 'balance':
                    session.close()
                    continue
                sleeping(time_delay_min, time_delay_max)

            if TRANSFER_NFT is True:
                number_send_nft = random.randint(number_send_nft_min, number_send_nft_max)
                log.info(f'Количесвто раз отправки NFT самому себе - {number_send_nft}\n')
                for i in range(number_send_nft):
                    res = lite.bridge_nft(wallet)
                    if res == 'balance':
                        break
                    sleeping(time_delay_min, time_delay_max)

            if SEND_ETH is True:
                number_send_eth = random.randint(number_send_eth_min, number_send_eth_max)
                log.info(f'Количесвто раз отправки ETH самому себе - {number_send_eth}\n')
                for i in range(number_send_eth):
                    val = random.uniform(value_send_eth_min, value_send_eth_max)
                    res = lite.send_eth(wallet, wallet.address(), val)
                    if res == 'balance':
                        break
                    sleeping(time_delay_min, time_delay_max)

            if WITHDRAWL_ETH is True:
                value = random.uniform(value_withdrawl_eth_min, value_withdrawl_eth_max)
                chain = get_chain(CHAIN_WITHDRAWL)
                res = lite.withdrawl_eth(wallet, chain, value)
                if res == 'balance':
                    session.close()
                    continue
                sleeping(time_delay_min, time_delay_max)

            session.close()
            log.info(f'Аккаунт завершен, сплю перехожу к следующему')
            sleeping(TIME_DELAY_ACC_MIN, TIME_DELAY_ACC_MAX)


if __name__ == '__main__':
    with open("private_key.txt", "r") as f:
        list1 = [row.strip() for row in f if row.strip()]
    keys_list = shuffle(list1, shuffle_wallets)
    all_wallets = len(keys_list)

    if MINT_NFT is True:
        with open("cid_picture.txt", "r") as f:
            cid_list = [row.strip() for row in f if row.strip()]

        random.shuffle(cid_list)
        all_cid = len(cid_list)
        if all_cid < all_wallets:
            raise ValueError('CID ключей меньше чем кошельков!')

    print(f'Number of wallets: {all_wallets}\n')
    worker = Worker()
    worker.run()
