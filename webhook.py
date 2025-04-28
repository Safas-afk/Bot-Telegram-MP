import os
import json
import gspread
import requests
from flask import Flask, request
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot

app = Flask(__name__)

# Configurações
BOT_TOKEN = os.getenv('BOT_TOKEN')
GRUPO_VIP_ID = int(os.getenv('GRUPO_VIP_ID'))
ACCESS_TOKEN_MP = os.getenv('ACCESS_TOKEN_MP')
bot = Bot(token=BOT_TOKEN)


def connect_to_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_info = json.loads(os.getenv('GOOGLE_CREDENTIALS_JSON'))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    return sheet


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if data and data.get("type") == "payment":
        resource_id = data["data"]["id"]

        # Buscar dados do pagamento no Mercado Pago
        telegram_id = consultar_pagamento(resource_id)

        if telegram_id:
            mover_usuario_para_vip(telegram_id)
            enviar_mensagem_vip(telegram_id)

    return "ok", 200


def consultar_pagamento(payment_id):
    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN_MP}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        payment_data = response.json()
        # Pega o telegram_id salvo no metadata na criação do pagamento
        return payment_data.get("metadata", {}).get("telegram_id")
    else:
        print("Erro ao consultar pagamento:", response.text)
        return None


def mover_usuario_para_vip(user_id):
    sheet_free = connect_to_sheet("Cadastros_Grupo_Free")
    sheet_vip = connect_to_sheet("Cadastros_Grupo_VIP")

    users = sheet_free.get_all_records()

    for idx, user in enumerate(users, start=2):
        if str(user.get("user_id")) == str(user_id):
            values = list(user.values())
            values[-1] = "Grupo VIP"  # Atualiza o status na linha
            sheet_vip.append_row(values)
            sheet_free.delete_row(idx)
            break


def enviar_mensagem_vip(telegram_id):
    try:
        # Criar link de convite exclusivo para o Grupo VIP
        new_invite = bot.create_chat_invite_link(
            chat_id=GRUPO_VIP_ID,
            member_limit=1  # Limita para 1 uso
        )

        mensagem = (
            "🎉 Parabéns! Seu pagamento foi aprovado!\n\n"
            "✅ Agora você é oficialmente membro do nosso Grupo VIP de Licitações!\n\n"
            f"Clique no link abaixo para entrar:\n\n🔗 {new_invite.invite_link}"
        )
        bot.send_message(chat_id=telegram_id, text=mensagem)
    except Exception as e:
        print(f"Erro ao enviar mensagem para o usuário: {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
