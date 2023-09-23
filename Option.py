# General Settings ---------------------------------------------------------------------------------------------------------------------------------------------------

class Telegram:
    TG_BOT_SEND = False                                                 # Включить уведомления в тг или нет                              [True or False]
    TG_TOKEN    = ''     # API токен тг-бота - создать его можно здесь - https://t.me/BotFather
    TG_ID       = 0                                            # id твоего телеграмма можно узнать тут https://t.me/getmyid_bot

shuffle_wallets = True                                                 # Мешать кошельки                                                [True or False]

RPC_ETH        = 'https://rpc.ankr.com/eth'                            #

time_delay_min = 10                                                    # Максимальная и
time_delay_max = 20                                                    # Минимальная задержка между транзакциями

SYSTEM = 0                                                             # 0 - Windows, 1 - aarch64-apple, 2 - x86_64-apple, 3 - Linux

MINT_NFT       = False             # Минт НФТ
TRANSFER_NFT   = False             # Отправка нфт самому себе
SEND_ETH       = False             # Отправка ETH самому себе

number_send_nft_min = 1            # Минимальное и
number_send_nft_max = 2            # Максимальное количество раз отправки нфт самому себе

value_send_eth_min = 0.03          # Минимальное и
value_send_eth_max = 0.031         # Максимальное значение отправки ETH самому себе -> Будет рандомное среднее
                                   # Если сумма больше, чем есть на аккаунте, будет бридж всего баланса

number_send_eth_min = 1            # Минимальное и
number_send_eth_max = 2            # Максимальное количество раз отправки ETH самому себе

WITHDRAWL_ETH   = False            # Вывод денег (Орбитер)

CHAIN_WITHDRAWL = 'Arbitrum'       # В какую сеть выводить : [Arbitrum, Optimism, ZkSync_Era, Polygon, BSC]

value_withdrawl_eth_min = 0.03     # Минимальное и
value_withdrawl_eth_max = 0.031    # Максимальное значение -> Будет рандомное среднее
                                   # Если сумма больше, чем есть на аккаунте, будет вывод всего баланса
