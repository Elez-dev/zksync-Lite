import random

from utils.tg_bot import TgBot
from zksync_sdk import ZkSync, HttpJsonRPCTransport, ZkSyncProviderV01, network, ZkSyncSigner, ZkSyncLibrary,\
    EthereumSignerWeb3, EthereumProvider, Wallet
from fractions import Fraction
from zksync_sdk.types import RatioType
from zksync_sdk.types import ChangePubKeyEcdsa
from decimal import Decimal
from time import sleep
from web3 import Web3
import json as js
import asyncio
import base58
import binascii
import requests
import os


async def get_contracts_address(provider):
    contracts = await provider.get_contract_address()
    return contracts


async def get_committed_eth_balance(wall):
    eth_balance = await wall.get_balance("ETH", "committed")
    return eth_balance


async def tx_send_async(wall, to_address, amount):
    tx = await wall.transfer(to_address, amount=amount, token="ETH")
    await tx.await_committed()
    hash_ = tx.transaction_hash.split(':')
    return hash_[1]


def ipfscidv0_to_byte32(_cid):
    decoded = base58.b58decode(_cid)
    sliced_decoded = decoded[2:]
    return binascii.b2a_hex(sliced_decoded).decode("utf-8")


async def send_nft_tx(wall, acc, random_image):
    tx = await wall.mint_nft(random_image, acc.address, "ETH")
    await tx.await_committed()
    hash_ = tx.transaction_hash.split(':')
    return hash_[1]


async def create_acc_in_zksync(wall):
    if not await wall.is_signing_key_set():
        tx = await wall.set_signing_key("ETH", eth_auth_data=ChangePubKeyEcdsa())
        await tx.await_committed()
        hash_ = tx.transaction_hash.split(':')
        return hash_[1]


def get_fee_to_mint_nft(wall):
    url = 'https://api.zksync.io/api/v0.2/fee/batch'
    json = {
        'tokenLike': 'ETH',
        'transactions': [{
            'address': wall.address(),
            'txType': "MintNFT"
        },
            {
                'address': wall.address(),
                'txType': "Transfer"
            }]
    }
    res = requests.post(url=url, json=json, timeout=120)
    json_data = res.json()
    if json_data['status'] == 'success':
        return int(json_data['result']['totalFee'])
    else:
        return 'error'


def get_fee_to_transfer_nft(wall):
    url = 'https://api.zksync.io/api/v0.2/fee/batch'
    json = {
        'tokenLike': 'ETH',
        'transactions': [{
            'address': wall.address(),
            'txType': "Transfer"
        },
            {
                'address': wall.address(),
                'txType': "Transfer"
            }]
    }
    res = requests.post(url=url, json=json, timeout=120)
    json_data = res.json()
    if json_data['status'] == 'success':
        return int(json_data['result']['totalFee'])
    else:
        return 'error'


def get_fee_to_transfer_eth(wall):
    url = 'https://api.zksync.io/api/v0.2/fee'
    json = {
        'tokenLike': 'ETH',
        'txType': "Transfer",
        'address': wall.address()
    }
    res = requests.post(url=url, json=json, timeout=120)
    json_data = res.json()
    if json_data['status'] == 'success':
        return int(json_data['result']['totalFee'])
    else:
        return 'error'


async def get_acc_state(wall):
    account_state = await wall.get_account_state()
    return account_state


def get_list_nft(wall):
    loop = asyncio.new_event_loop()
    task = loop.create_task(get_acc_state(wall))
    loop.run_until_complete(task)
    account_state = task.result()
    owned_nfts = account_state.verified.minted_nfts
    return owned_nfts


async def transfer_nft(wall, nft):
    tx = await wall.transfer_nft(wall.address(), nft, "ETH")
    await tx[0].await_committed()
    hash_ = tx[0].transaction_hash
    return hash_.split(':')[1]


ORBITER_MARKER = js.load(open('./utils/orbiter_maker.json'))


def check_orbiter_limits(from_chain, to_chain):

    orbiter_ids = {
        'ethereum'      : 1,
        'optimism'      : 7,
        'bsc'           : 15,
        'arbitrum'      : 2,
        'nova'          : 16,
        'polygon'       : 6,
        'polygon_zkevm' : 17,
        'zksync'        : 14,
        'zksync_lite'   : 3,
        'starknet'      : 4,
    }

    from_maker  = orbiter_ids[from_chain]
    to_maker    = orbiter_ids[to_chain]

    marker = f'{from_maker}-{to_maker}'

    min_bridge = Web3.toWei(ORBITER_MARKER[marker]['ETH-ETH']['minPrice'], 'ether')
    max_bridge = Web3.toWei(ORBITER_MARKER[marker]['ETH-ETH']['maxPrice'], 'ether')
    fees = Web3.toWei(ORBITER_MARKER[marker]['ETH-ETH']['tradingFee'], 'ether')

    return min_bridge, max_bridge, fees


ORBITER_AMOUNT_STR = {
            'ethereum'      : '09001',
            'optimism'      : '09007',
            'arbitrum'      : '09002',
            'zksync'        : '09014',
            'polygon'       : '09006',
            'bsc'           : '09015'
        }


def get_orbiter_value(base_num, chain):
    difference = str(Web3.fromWei(base_num, 'ether') + Decimal(0.00000001).quantize(Decimal('1.00000000')))
    difference = difference[:9] + ORBITER_AMOUNT_STR[chain]
    return Decimal(difference)


class ZkSyncLite(TgBot):

    def __init__(self, private_key, web3, number, log):
        self.private_key = private_key
        self.web3 = web3
        self.log = log
        self.number = number
        self.account = self.web3.eth.account.from_key(private_key)

    def get_balance(self, wall):
        loop = asyncio.new_event_loop()
        task = loop.create_task(get_committed_eth_balance(wall))
        loop.run_until_complete(task)
        return task.result()

    def connect_wallet(self, path, retry=0):
        try:
            path = os.getcwd() + path
            # This ZkSyncLibrary is predefined for Linux system. Use https://github.com/zksync-sdk/zksync-crypto-c/releases to download library for your system
            library = ZkSyncLibrary(path)
            provider = ZkSyncProviderV01(provider=HttpJsonRPCTransport(network=network.mainnet))

            # get all contracts in Zksync network
            loop = asyncio.new_event_loop()
            task = loop.create_task(get_contracts_address(provider))
            loop.run_until_complete(task)
            contracts = task.result()

            # create wallet object
            zksync = ZkSync(account=self.account, web3=self.web3, zksync_contract_address=contracts.main_contract)
            ethereum_provider = EthereumProvider(self.web3, zksync)
            ethereum_signer = EthereumSignerWeb3(account=self.account)
            signer = ZkSyncSigner.from_account(self.account, library, network.mainnet.chain_id)
            wall = Wallet(ethereum_provider=ethereum_provider, zk_signer=signer, eth_signer=ethereum_signer, provider=provider)
            return wall
        except Exception as error:
            self.log.info(error)
            retry += 1
            if retry > 5:
                return 0
            sleep(30)
            self.connect_wallet(retry)

    def send_eth(self, wall, to_address, value, retry=0):
        try:
            amount = Decimal(value).quantize(Decimal('1.0000000000'))

            balance = self.get_balance(wall)
            fee = get_fee_to_transfer_eth(wall)

            if balance - int(fee * 1.01) > 0:

                if Web3.toWei(amount, 'ether') > balance:
                    val = Web3.fromWei(balance - int(fee * 1.01), 'ether')
                    amount = Decimal(val).quantize(Decimal('1.0000000000'))

                self.log.info(f"I gonna send {amount} ETH")
                loop = asyncio.new_event_loop()
                task = loop.create_task(tx_send_async(wall, to_address, amount))
                loop.run_until_complete(task)
                tx_status = task.result()
                self.log.info(f'Successfully send {amount} ETH || https://zkscan.io/explorer/transactions/0x{tx_status}\n')
                if TgBot.TG_BOT_SEND is True:
                    TgBot.send_message_success(self, self.number, f'Successfully send {amount} ETH', self.account.address,
                                               f'https://zkscan.io/explorer/transactions/0x{tx_status}')
            else:
                self.log.info(f'Insufficient funds')
                return 'balance'
        except Exception as error:
            self.log.info(error)
            retry += 1
            if retry > 5:
                return 0
            sleep(30)
            self.send_eth(wall, to_address, value, retry)

    def claim_nft(self, wall, cid, retry=0):
        try:

            balance = self.get_balance(wall)
            fee = get_fee_to_mint_nft(wall)

            if balance - fee > 0:
                self.log.info(f'Claim NFT - {cid}')
                random_image = '0x' + ipfscidv0_to_byte32(cid)
                loop = asyncio.new_event_loop()
                task = loop.create_task(send_nft_tx(wall, self.account, random_image))
                loop.run_until_complete(task)
                tx_status = task.result()
                self.log.info(f'Successfully claim NFT || https://zkscan.io/explorer/transactions/0x{tx_status}\n')
                if TgBot.TG_BOT_SEND is True:
                    TgBot.send_message_success(self, self.number, 'Successfully claim NFT', self.account.address,
                                               f'https://zkscan.io/explorer/transactions/0x{tx_status}')
            else:
                self.log.info(f'Insufficient funds\n')
                return 'balance'
        except Exception as error:
            self.log.info(f'Unsuccessfully claim NFT')
            self.log.info(error)
            retry += 1
            if retry > 5:
                return 0
            sleep(30)
            self.claim_nft(wall, cid, retry)

    def check_create_acc(self, wall, retry=0):
        try:
            loop = asyncio.new_event_loop()
            task = loop.create_task(create_acc_in_zksync(wall))
            loop.run_until_complete(task)
            tx_status = task.result()
            if tx_status is None:
                return
            else:
                self.log.info(f'Your account has not been activated. Activation was successful. || https://zkscan.io/explorer/transactions/0x{tx_status}\n')
                if TgBot.TG_BOT_SEND is True:
                    TgBot.send_message_success(self, self.number, 'Your account has not been activated.\nActivation was successful', self.account.address,
                                               f'https://zkscan.io/explorer/transactions/0x{tx_status}')
                sleep(30)
        except Exception as error:
            self.log.info(error)
            retry += 1
            if retry > 5:
                return 0
            sleep(30)
            self.check_create_acc(wall, retry)

    def bridge_nft(self, wall, retry=0):
        try:

            balance = self.get_balance(wall)
            fee = get_fee_to_transfer_nft(wall)

            if balance - fee > 0:
                self.log.info(f'Transfer NFT')
                list_nft = get_list_nft(wall)
                if len(list_nft) == 0:
                    self.log.info('Not found NFT in wallet\n')
                else:
                    nft = random.choice(list(list_nft.values()))
                    loop = asyncio.new_event_loop()
                    task = loop.create_task(transfer_nft(wall, nft))
                    loop.run_until_complete(task)
                    tx_status = task.result()
                    self.log.info(f'Successfully transfer NFT || https://zkscan.io/explorer/transactions/0x{tx_status}\n')
                    if TgBot.TG_BOT_SEND is True:
                        TgBot.send_message_success(self, self.number, 'Successfully transfer NFT', self.account.address,
                                                   f'https://zkscan.io/explorer/transactions/0x{tx_status}')
            else:
                self.log.info(f'Insufficient funds\n')
                return 'balance'
        except Exception as error:
            self.log.info(error)
            retry += 1
            if retry > 5:
                return 0
            sleep(30)
            self.bridge_nft(wall, retry)

    def withdrawl_eth(self, wall, chain_to, value_eth, retry=0):
        try:
            min_value_bridge, max_value_bridge, fees = check_orbiter_limits("zksync_lite", chain_to)
            value_bridge = Web3.toWei(value_eth, 'ether') + fees
            balance = self.get_balance(wall)
            fee = get_fee_to_transfer_eth(wall)
            comsa = Web3.toWei(0.002, 'ether')
            if balance - comsa < value_bridge:
                value_bridge = int(balance - comsa - int(fee * 0.01))
            if value_bridge < min_value_bridge + fees:
                self.log.info('Insufficient balance')
                return 'balance'
            if value_bridge > max_value_bridge:
                value_bridge = max_value_bridge
            amount = round(Web3.fromWei(value_bridge, 'ether'), 6)
            value_bridge = get_orbiter_value(value_bridge, chain_to)
            self.log.info(f"I gonna send {amount} ETH")
            address = Web3.toChecksumAddress('0x80C67432656d59144cEFf962E8fAF8926599bCF8')
            loop = asyncio.new_event_loop()
            task = loop.create_task(tx_send_async(wall, address, value_bridge))
            loop.run_until_complete(task)
            tx_status = task.result()
            self.log.info(f'Successfully withdrawl {amount} ETH to {chain_to} || https://zkscan.io/explorer/transactions/0x{tx_status}\n')
            if TgBot.TG_BOT_SEND is True:
                TgBot.send_message_success(self, self.number, f'Successfully withdrawl {amount} ETH to {chain_to}',
                                           self.account.address, f'https://zkscan.io/explorer/transactions/0x{tx_status}')
        except Exception as error:
            self.log.info(error)
            retry += 1
            if retry > 5:
                return 0
            sleep(30)
            self.send_eth(wall, chain_to, value_eth, retry)
