import os
import gspread
import requests
import json
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv('BOT_TOKEN')
ACCESS_TOKEN_MP = os.getenv('ACCESS_TOKEN_MP')
GRUPO_FREE_ID = int(os.getenv('GRUPO_FREE_ID'))
GRUPO_VIP_ID = int(os.getenv('GRUPO_VIP_ID'))

# Estados do cadastro
NOME, IDADE, GENERO, ESTADO, EMAIL, AREA = range(6)

genero_options = [["Masculino", "Feminino", "Outro"]]
estado_options = [
    ["AC", "AL", "AP", "AM", "BA"],
    ["CE", "DF", "ES", "GO", "MA"],
    ["MT", "MS", "MG", "PA", "PB"],
    ["PR", "PE", "PI", "RJ", "RN"],
    ["RS", "RO", "RR", "SC", "SP"],
    ["SE", "TO"]
]
area_options = [
    ["Administração", "Agricultura", "Alimentação"],
    ["Arquitetura", "Construção", "Educação"],
    ["Engenharia Civil", "TI", "Logística"],
    ["Marketing", "Saúde", "Serviços Gerais"],
    ["Turismo", "Outros"]
]

def connect_to_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_info = json.loads(os.getenv('GOOGLE_CREDENTIALS_JSON'))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    return sheet

def save_user_data(user_id, user_data):
    sheet = connect_to_sheet("Cadastros_Grupo_Free")  # Nome da planilha Free
    data = [
        str(user_id),
        user_data["nome"],
        user_data["idade"],
        user_data["genero"],
        user_data["estado"],
        user_data["email"],
        user_data["area"]
    ]
    sheet.append_row(data)

def criar_pagamento(nome_usuario, telegram_id):
    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN_MP}",
        "Content-Type": "application/json"
    }
    payload = {
        "items": [{
            "title": "Assinatura Grupo VIP Licitações",
            "quantity": 1,
            "currency_id": "BRL",
            "unit_price": 49.00
        }],
        "payer": {
            "name": nome_usuario
        },
        "metadata": {
            "telegram_id": str(telegram_id)
        },
        "back_urls": {
            "success": "https://www.google.com",
            "failure": "https://www.google.com",
            "pending": "https://www.google.com"
        },
        "auto_return": "approved",
        "notification_url": "https://SEU_DOMINIO/webhook"  # Substituir pelo seu link do Railway
    }
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        preference = response.json()
        return preference["init_point"]
    else:
        print("Erro ao criar pagamento:", response.text)
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Vamos começar seu cadastro.\nQual o seu nome?")
    return NOME

async def nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nome"] = update.message.text
    await update.message.reply_text("Qual a sua idade?")
    return IDADE

async def idade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["idade"] = update.message.text
    await update.message.reply_text("Qual seu gênero?", reply_markup=ReplyKeyboardMarkup(genero_options, one_time_keyboard=True, resize_keyboard=True))
    return GENERO

async def genero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["genero"] = update.message.text
    await update.message.reply_text("Qual seu estado?", reply_markup=ReplyKeyboardMarkup(estado_options, one_time_keyboard=True, resize_keyboard=True))
    return ESTADO

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["estado"] = update.message.text
    await update.message.reply_text("Qual o seu e-mail?")
    return EMAIL

async def email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text
    await update.message.reply_text("Qual sua área de atuação?", reply_markup=ReplyKeyboardMarkup(area_options, one_time_keyboard=True, resize_keyboard=True))
    return AREA

async def area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["area"] = update.message.text

    user_id = update.effective_user.id
    save_user_data(user_id, context.user_data)

    await update.message.reply_text("Cadastro concluído! ✅ Você será adicionado ao nosso Grupo Free.")
    await context.bot.add_chat_members(GRUPO_FREE_ID, [user_id])
    return ConversationHandler.END

async def assinar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome_usuario = update.effective_user.first_name
    telegram_id = update.effective_user.id
    link_pagamento = criar_pagamento(nome_usuario, telegram_id)

    if link_pagamento:
        keyboard = [[InlineKeyboardButton("💳 Assinar Grupo VIP – R$49", url=link_pagamento)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "💬 Para garantir seu acesso ao nosso Grupo VIP de Licitações, clique no botão abaixo e realize o pagamento de R$49,00.\n\n"
            "Após o pagamento aprovado, seu acesso será liberado automaticamente! 🚀",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("Erro ao gerar link de pagamento. Tente novamente mais tarde.")

app = ApplicationBuilder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, nome)],
        IDADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, idade)],
        GENERO: [MessageHandler(filters.TEXT & ~filters.COMMAND, genero)],
        ESTADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, estado)],
        EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email)],
        AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, area)],
    },
    fallbacks=[]
)

app.add_handler(conv_handler)
app.add_handler(CommandHandler("assinar", assinar))

print("Bot rodando!")
app.run_polling()
