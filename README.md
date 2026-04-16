# KeyNova Telegram Bot

Python-бот для Telegram, який продає цифрові коди: показує каталог, створює замовлення, приймає підтвердження оплати від покупця, а після підтвердження адміном автоматично видає код зі складу.

## Запуск Через VS Code

1. Відкрий цю папку у VS Code:

```text
D:\VS.project
```

2. Один раз встанови бібліотеки.

Натисни `Ctrl+Shift+P`, знайди:

```text
Tasks: Run Task
```

Потім вибери:

```text
Install bot requirements
```

3. Відкрий файл `.env` і заповни його:

```env
BOT_TOKEN=токен_від_BotFather
ADMIN_IDS=твій_telegram_id
PAYMENT_TEXT=Оплата на карту/гаманець: XXXX. Після оплати натисни "Я оплатив".
STORE_NAME=KeyNova
```

4. Натисни `F5` у VS Code.

Вибери конфігурацію:

```text
Run KeyNova Bot
```

5. У Telegram напиши боту:

```text
/start
```

## Як Дізнатись Telegram ID

Після запуску напиши боту:

```text
/id
```

Бот відповість твоїм Telegram ID. Скопіюй це число в `.env`:

```env
ADMIN_IDS=це_число
```

Після зміни `.env` перезапусти бота: зупини через `Ctrl+C` і знову натисни `F5`.

## Команди Покупця

```text
/start
/catalog
/orders
/help
/id
```

## Команди Адміністратора

```text
/admin
/stock
/addproduct id | Назва | опис | ціна | валюта
/addproducts
/addcode product_id | CODE-123
/addcodes product_id
/confirm order_id
/cancel order_id
```

## Приклади

Додати товар:

```text
/addproduct steam-10 | Steam Gift Card $10 | Digital activation code | 10 | USD
```

Додати багато кодів до одного товару:

```text
/addcodes steam-10
STEAM-CODE-001
STEAM-CODE-002
STEAM-CODE-003
```

Додати багато товарів одним повідомленням:

```text
/addproducts
steam-10 | Steam Gift Card $10 | Digital activation code | 10 | USD
nitro-1 | Discord Nitro | 1 month code | 5 | USD
robux-100 | Robux 100 | Roblox code | 2 | USD
```

Кількість товару рахується автоматично за кількістю доступних кодів на складі.

## Як Поділитись Ботом

Можеш передати всю папку проєкту іншій людині.

Перед передачею не забудь:

- видалити `.env`, якщо там є справжній токен;
- не передавати файли бази `data/*.sqlite3`;
- залишити `.env.example`, щоб інша людина могла створити свої налаштування.

У папці `data` зараз є тільки безпечний приклад:

```text
products.example.json
```

## Структура Проєкту

```text
src/bot.py                         запуск бота
src/code_shop_bot/app.py           створення aiogram-бота
src/code_shop_bot/config.py        налаштування з .env
src/code_shop_bot/database.py      SQLite база
src/code_shop_bot/keyboards.py     inline-кнопки
src/code_shop_bot/services.py      логіка магазину
src/code_shop_bot/handlers_user.py команди покупця
src/code_shop_bot/handlers_admin.py команди адміна
```
