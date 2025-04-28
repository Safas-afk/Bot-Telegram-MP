import os
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request
from telegram import Bot

BOT_TOKEN = os.getenv('BOT_TOKEN')
GRUPO_VIP_ID = int(os.getenv('GRUPO_VIP_ID'))

bot = Bot(BOT_TOKEN)
app = Flask(__name__)

def connect_to_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_info = json.loads(os.getenv('GOOGLE_CREDENTIALS_JSON'))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    return sheet

def move_user_to_vip(telegram_id):
    free_sheet = connect_to_sheet("Cadastros_Grupo_Free")
    vip_sheet = connect_to_sheet("Cadastros_Grupo_VIP")

    records = free_sheet.get_all_records()
    for idx, record in enumerate(records, start=2):
        if str(record["Telegram ID"]) == str(telegram_id):
            vip_sheet.append_row([
                record["Telegram ID"],
                record["Nome"],
                record["Idade"],
                record["Gênero"],
                record["Estado"],
                record["E-mail"],
                record["Área de Atuação"]
            ])
            free_sheet.delete_rows(idx)
            break

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    if data.get('type') == 'payment':
        payment_data = data['data']

        if payment_data:
            try:
                telegram_id = payment_data['metadata']['telegram_id']

                move_user_to_vip(telegram_id)

                try:
                    bot.add_chat_members(GRUPO_VIP_ID, [int(telegram_id)])
                    bot.send_message(int(telegram_id), "🎉 Parabéns! Seu pagamento foi aprovado e agora você faz parte do Grupo VIP!")
                except Exception as e:
                    print(f"Erro ao adicionar usuário ao grupo VIP: {e}")

            except Exception as e:
                print(f"Erro ao processar webhook: {e}")

    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)
