import os
import requests
from datetime import datetime

LATITUDE = -3.1019
LONGITUDE = -60.0250
TIMEZONE = "America/Manaus"

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

WEATHER_CODES = {
    0: ("☀️", "céu limpo"),
    1: ("🌤️", "predomínio de sol"),
    2: ("⛅", "parcialmente nublado"),
    3: ("☁️", "nublado"),
    45: ("🌫️", "nevoeiro"),
    48: ("🌫️", "nevoeiro"),
    51: ("🌦️", "garoa leve"),
    53: ("🌦️", "garoa moderada"),
    55: ("🌦️", "garoa forte"),
    61: ("🌧️", "chuva leve"),
    63: ("🌧️", "chuva moderada"),
    65: ("🌧️", "chuva forte"),
    80: ("🌧️", "pancadas de chuva leves"),
    81: ("🌧️", "pancadas de chuva moderadas"),
    82: ("⛈️", "pancadas de chuva fortes"),
    95: ("⛈️", "tempestade"),
    96: ("⛈️", "tempestade com granizo"),
    99: ("⛈️", "tempestade forte com granizo"),
}


def buscar_previsao():
    url = "https://api.open-meteo-QUEBRADO-DE-PROPOSITO.invalid/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "weathercode",
            "sunrise",
            "sunset",
            "uv_index_max",
            "windspeed_10m_max",
        ]),
        "hourly": "precipitation_probability,relative_humidity_2m",
        "timezone": TIMEZONE,
        "forecast_days": 1,
    }
    resposta = requests.get(url, params=params, timeout=30)
    resposta.raise_for_status()
    return resposta.json()


def hora_mais_provavel_de_chuva(dados_horarios):
    probabilidades = dados_horarios["precipitation_probability"]
    horarios = dados_horarios["time"]
    indice_pico = probabilidades.index(max(probabilidades))
    hora_inicio = datetime.fromisoformat(horarios[indice_pico]).hour
    hora_fim = (hora_inicio + 2) % 24
    return hora_inicio, hora_fim


def umidade_media(dados_horarios):
    valores = dados_horarios["relative_humidity_2m"]
    return round(sum(valores) / len(valores))


def formatar_hora(iso_str):
    return datetime.fromisoformat(iso_str).strftime("%Hh%M")


def montar_resumo(temp_min, temp_max, chuva_prob, umidade, vento, uv, condicao_texto):
    frases = []

    if temp_max >= 33:
        frases.append("O calor deve ser intenso à tarde, então procure se hidratar bem e evitar exposição prolongada ao sol.")
    elif temp_max >= 30:
        frases.append("Tarde quente em Manaus, vale manter a hidratação em dia.")
    else:
        frases.append("Temperatura mais amena para os padrões de Manaus.")

    if chuva_prob >= 70:
        frases.append("Alta chance de chuva forte, leve guarda-chuva e evite deixar para sair de última hora.")
    elif chuva_prob >= 40:
        frases.append("Há possibilidade de chuva, vale levar um guarda-chuva por precaução.")

    if umidade >= 85:
        frases.append("A umidade estará bem elevada, o que pode deixar a sensação térmica mais pesada.")

    if uv >= 8:
        frases.append("Índice UV alto, use protetor solar se for ficar exposto ao ar livre.")

    return " ".join(frases)


def montar_mensagem(dados):
    diario = dados["daily"]
    horario = dados["hourly"]

    temp_min = round(diario["temperature_2m_min"][0])
    temp_max = round(diario["temperature_2m_max"][0])
    chuva_prob = diario["precipitation_probability_max"][0]
    vento = round(diario["windspeed_10m_max"][0])
    uv = round(diario["uv_index_max"][0])
    nascer_sol = formatar_hora(diario["sunrise"][0])
    por_sol = formatar_hora(diario["sunset"][0])
    codigo_tempo = diario["weathercode"][0]
    emoji_condicao, texto_condicao = WEATHER_CODES.get(codigo_tempo, ("🌡️", "condição variável"))

    umidade = umidade_media(horario)
    hora_inicio_chuva, hora_fim_chuva = hora_mais_provavel_de_chuva(horario)

    alerta = ""
    if codigo_tempo in (95, 96, 99) or chuva_prob >= 70:
        alerta = "⚠️ Atenção: previsão de chuva forte/tempestade hoje!\n\n"
    elif temp_max >= 35:
        alerta = "⚠️ Atenção: previsão de calor extremo hoje!\n\n"

    resumo = montar_resumo(temp_min, temp_max, chuva_prob, umidade, vento, uv, texto_condicao)

    mensagem = (
        f"{alerta}"
        f"{emoji_condicao} Bom dia! Previsão para hoje em Manaus\n\n"
        f"🌡️ Temperatura: {temp_min}°C – {temp_max}°C\n"
        f"🌥️ Condição: {texto_condicao}\n"
        f"🌧️ Chuva: {chuva_prob:.0f}% (mais provável entre {hora_inicio_chuva}h e {hora_fim_chuva}h)\n"
        f"💧 Umidade: {umidade}%\n"
        f"💨 Vento: {vento} km/h\n"
        f"☀️ UV: {uv}\n"
        f"🌅 Nascer do sol: {nascer_sol}\n"
        f"🌇 Pôr do sol: {por_sol}\n\n"
        f"Resumo: {resumo}"
    )
    return mensagem


def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resposta = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}, timeout=30)
    if not resposta.ok:
        print(f"Erro do Telegram: {resposta.text}")
    resposta.raise_for_status()


def main():
    dados = buscar_previsao()
    mensagem = montar_mensagem(dados)
    enviar_telegram(mensagem)
    print("Mensagem enviada com sucesso:")
    print(mensagem)


if __name__ == "__main__":
    main()
