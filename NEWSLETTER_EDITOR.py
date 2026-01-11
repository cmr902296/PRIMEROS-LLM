# LIBRERIAS
from dotenv import load_dotenv
from agents import Agent, Runner, trace, function_tool
from openai.types.responses import ResponseTextDeltaEvent
from typing import Dict, List
import sendgrid
import os
from sendgrid.helpers.mail import Mail,Email,To,Content
import asyncio
import re


# CARGAR ENTORNO
load_dotenv(override=True)

# INSTRUCCIONES PARA LOS AGENTES-REDACTORES

instructions_tech = "Eres un redactor de periódico del ámbito teconológico.\
    Los temas principales que tratas son la inteligencia artificial y robótica.\
    Prepara un artículo para una newsletter que sea atractivo y sin complejidad técnica."

instructions_economy = "Eres un redactor de periódico del ámbito económico-financiero.\
    Los temas principales son renta variable, liquidez y criptomonedas como bitcoin y ethereum.\
    Prepara un artículo para una newsletter que sea atractiva y sin complejidad técnica."

instructions_health = "Eres un redactor de periódico del ámbito fitness.\
    Los temas principales que tratas son rutinas para el gimnasio y nutrición.\
    Prepara un artículo para una newsletter que sea atractivo y sin complejidad."

# CONSTRUCCIÓN DE LOS AGENTES REDACTORES
from agents import Agent

# REDACTOR TECH
redactor_tech = Agent (
    name ="Redactor_Tech",
    instructions = instructions_tech,
    model = "gpt-4o-mini"    
)
# CONVERSION A HERRAMIENTA
tool_tech = redactor_tech.as_tool(
    tool_name = "Redactor_tech",
    tool_description = "Redacta noticias tech"
)

# REDACTOR ECONOMY
redactor_economy = Agent(
    name = "Redactor_economy",
    instructions = instructions_economy,
    model = "gpt-4o-mini"
)

# CONVERSION A HERRAMIENTA
tool_economy = redactor_economy.as_tool(
    tool_name = "Redactor_economy",
    tool_description= "Escribe noticias económicas"
)

# REDACTOR HEALTH
redactor_health = Agent(
    name = "Redactor_health",
    instructions = instructions_health,
    model = "gpt-4o-mini"
)

# CONVERSION A HERRAMIENTA
tool_health = redactor_health.as_tool(
    tool_name = "Redactor_health",
    tool_description = "Escribe noticias sobre fitness y nutrición" 
)

# EMPAQUETAR CONJUNTO DE HERRAMIENTAS
tools_redactor = [tool_tech,tool_economy,tool_health]
tools_redactor

# DEFINICION DE HANDOFFS, AGENTES SOBRE LOS QUE SE DELEGAN TAREAS DE OTROS AGENTES
# INSTRUCCIONES
subject_instructions = "Puedes escribir un asunto para un correo electrónico de ventas en frío. \
    Se te proporciona un mensaje y necesitas escribir un asunto para un correo electrónico que probablemente obtenga respuesta."

html_instructions = "Puedes convertir un cuerpo de correo electrónico de texto a un cuerpo de correo electrónico HTML. \
    Se te proporciona un cuerpo de correo electrónico de texto que puede tener algún markdown \
    y necesitas convertirlo a un cuerpo de correo electrónico HTML con un diseño simple, claro y atractivo."

subject_writer = Agent(name="Escritor de asunto de correo electrónico", instructions=subject_instructions, model="gpt-4o-mini")
subject_tool = subject_writer.as_tool(tool_name="subject_writer", 
                                      tool_description="Escribe un asunto para un correo electrónico de ventas en frío")

html_converter = Agent(name="Conversor de cuerpo de correo electrónico HTML", instructions=html_instructions, model="gpt-4o-mini")
html_tool = html_converter.as_tool(tool_name="html_converter",
                                   tool_description="Convierte un cuerpo de correo electrónico de texto a un cuerpo de correo electrónico HTML")

# DEFINICION DE HERRAMIENTAS (SOFTWARE)
# ENVIO CORREOS ELECTRÓNICO MEDIANTE SENDGRID
@function_tool
def send_html_email(subject: str, html_body: str) -> Dict[str, str]:
    """ Envía un correo electrónico con el asunto y el cuerpo HTML a todos los clientes potenciales de ventas """
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        return {"status": "error", "detail": "Falta SENDGRID_API_KEY en el entorno."}

    try:
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        from_email = Email("fmr10@live.com")  # Cambiar a tu remitente verificado
        to_email = To("fmr10@live.com")       # Cambiar a tu receptor
        content = Content("text/html", html_body)
        mail = Mail(from_email, to_email, subject, content).get()
        response = sg.client.mail.send.post(request_body=mail)
        return {"status": "success", "code": str(getattr(response, "status_code", ""))}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# EMPAQUETADO DE HERRAMIENTAS PARA DISEÑO DE NEWSLETTER
tools = [subject_tool, html_tool, send_html_email]

# DEFINIR EMAILER AGENT
instructions ="Eres un formateador y remitente de correos electrónicos. \
    Recibes el cuerpo de un correo electrónico para enviarlo. \
    Primero usas la herramienta subject_writer para escribir un asunto para el correo electrónico, \
    luego usas la herramienta html_converter para convertir el cuerpo a HTML. \
    Finalmente, usas la herramienta send_html_email para enviar el correo electrónico con el asunto y el cuerpo HTML."


emailer_agent = Agent(
    name="Email Manager",
    instructions=instructions,
    tools=tools,
    model="gpt-4o-mini",
    handoff_description="Convierte un email a HTML y lo envía")

handoffs = [emailer_agent]

# DEFINICION AGENTE ORQUESTADOR GERENTE

instruction_manager = "Eres un gerente que trabaja en una agencia de marketing. Utilizas las herramientas que se te proporcionan para elaborar articulos sobre tecnológica, economía y hábitos saludables.\
    Nunca generas redactas artículos; siempre utilizas las herramientas.\
    Seleccionas los artículos que te parecen más interesantes usando tu propio criterio sobre cuál capatará más la atención del público.\
    Después de elegir los mejores artículos, transfieres al agente emailer_agent para formatear y enviar el correo electrónico."

manager = Agent(
    name = "Manager",
    instructions=instruction_manager,
    tools = tools_redactor,
    handoffs = handoffs,
    model = "gpt-4o-mini"
)

message = "Elabora una newsletter sobre las principales novedades en tecnología, economía y hábitos saludables."

async def main():
    with trace("Automated Newsletter"):
        result = await asyncio.wait_for(
            Runner.run(manager, message, max_turns=5),
            timeout=55
        )
    return result

