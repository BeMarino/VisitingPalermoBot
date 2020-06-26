# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 22:31:07 2020

@author: Benny
"""
from collections import OrderedDict
import telepot
import time
import urllib
import json
import xml.etree.ElementTree as ET
from geopy.distance import great_circle
from lxml import etree
import collections
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
TOKEN="1250773791:AAErrLVj1nHKw30evXu90hokjkvYtWKKHnA"

# Creazione albero a partire dal file xml 
tree = ET.parse(urllib.request.urlopen('https://www.comune.palermo.it/xmls/VIS_DATASET_TURISMO03.xml'))
root = tree.getroot()

#Definizione variabili
wait_mess="⌛️Richiesta inoltrata, attendi qualche secondo⏳"
distance_request="A che distanza❓ "
position_request="❌ Non posso aiutarti se non condividi con me la tua posizione 📡"
command_request="🧐Non capisco, usa i comandi 👇🏻 per interagire con me"
welcome="\nIo sono *VisitingPalermoBot*🤖, la tua guida turistica tascabile. Lascia che ti localizzi📡 così da poterti aiutare ad esplorare la città."
no_results="❌ Non sono stati trovati luoghi d'interesse 😕.\nProva a selezionare una distanza maggiore."
distances=["100 metri","500 metri","1000 metri","2000 metri","🔙 Indietro"]

info_bot="Bot non ufficiale sviluppato da *Benedetto Marino*(@Bennym4)\n\n*Foto profilo*: Teatro Massimo di Palermo\n"
link_dati="https://www.comune.palermo.it"


position=[None,None]
bot = telepot.Bot(TOKEN)

places={}
lis={}

# Inserisco nel placesionario places{} le informazioni dei luoghi di interesse
for dataRecord in root:
    b=(float(dataRecord.find("LATITUDE").text.replace(",",".")),float(dataRecord.find("LONGITUDE").text.replace(",",".")))
    
    location=[b[0],b[1]]
    denom=dataRecord.find("DENOMINAZIONE").text
    story=dataRecord.find("CENNI_STORICI").text
    addr=dataRecord.find("INDIRIZZO").text
    desc=dataRecord.find("DESCRIZIONE").text
    places[dataRecord.find("ID").text]=[location,denom,story,addr,desc]

# Metodo che creare le tatiere da pasare a telegram, in base al parametro distance crea una tastiera piuttosto che un'altra
def build_keyboard(distances=None):
    if distances:
        keyboard = [[button] for button in distances]
        reply_markup = {"keyboard":keyboard,"one_time_keyboard":False}
        return json.dumps(reply_markup)
    else:
        keyboard=[[{"text":'Localizzami 📡\n (Attiva prima il gps)',"request_location":True}],[{"text":"🔄 Riavvia bot"}],[{"text":"ℹ️ Info bot"}]]
        reply_markup = {"keyboard":keyboard,"one_time_keyboard":False}
        return json.dumps(reply_markup)

# Creazione delle tastiere
keyboard_d=build_keyboard(distances)
keyboard_home=build_keyboard()

# Metodo che legge i messaggi ricevuti dall'utente
def on_chat_message(msg):
    content_type, _, chat_id = telepot.glance(msg)  # Il metodo glance(msg) restituisce alcune informazioni sul messaggio ricevuto (ad esempio il tipo di messaggio)
    name = msg["from"]["first_name"]    # name contiene il nome dell'utente che usa il bot ed è usata nel messaggio di benvenuto del bot
    lis.clear()     # svuoto il placesionario in modo da non includere i risultati precedenti in caso di query ripetute
    global places  
    global position

    if content_type=='location':    
        position=[msg["location"]["latitude"],msg["location"]["longitude"]] # memorizzo la posizione dell'utente 
        bot.sendMessage(chat_id,distance_request,reply_markup=keyboard_d) # invio all'utente la richiesta di una distanza e una tastiera da cui selezionare
    elif content_type == 'text':
        text = msg['text']
        if text == "/start" or text=="🔄 Riavvia bot":
            bot.sendMessage(chat_id,"Ciao *"+name+"*❗️"+welcome,parse_mode="Markdown",reply_markup=keyboard_home)
        elif text=="ℹ️ Info bot":
            bot.sendMessage(chat_id,info_bot+"\n*Sorgenti dati*:\n"+link_dati,parse_mode="Markdown")
        elif text == "🔙 Indietro":
            bot.sendMessage(chat_id,"Torno al menù...",reply_markup=keyboard_home)
        elif text in distances:
            if position[0]==None:
                bot.sendMessage(chat_id,position_request,reply_markup=keyboard_home)
            else: 
                select_by_distance(chat_id,int(text[:-6])) # Una volta ricevuta la distanza richiamo il metodo select_by_distance. -6 per escludere "metri"
        else :bot.sendMessage(chat_id,command_request) # Operazione eseguita in caso di comando non riconosciuto

# Metodo che, presi in input l'id della chat e la distanza in cui cercare, restituisce una lista con i luoghi entro quella distanza
def select_by_distance(chat_id,distance):
    global places
    global lis
    global position
    i=0
   
    for k in places.keys(): # cerco in places tutti i luoghi entro quella distanza
        b=places[str(k)][0] # places[key][0] contiene la posizione del luogo
        d=great_circle(position,b).meters
        
        if(d<distance):
            lis[k]=d # lis conterrà le distanze che ogni luogo ha dal punto in cui si trova l'utente
    
    od=OrderedDict(sorted(lis.items(), key=lambda item: item[1])) # A partire dalla lista ,creo un dizionario (od) che contiene gli elementi di places ordinati per valore (distanza)
    bot.sendMessage(chat_id,wait_mess)
    time.sleep(1)

    if lis:     # Controllo se la lista contiene delle entries o meno
        bot.sendMessage(chat_id,"✅Ecco qui la lista dei luoghi a meno di "+str(distance)+" m 😊")
    else:
        bot.sendMessage(chat_id,no_results,reply_markup=build_keyboard(distances))  
    
    for k in od.keys(): # Scorro la lista dei luoghi ordinata per mandare poi i risultati all'utente
        time.sleep(0.15)
        key=str(k)
        if i==0: time.sleep(0.6), time.sleep(0.2)
        i=1
        latitude,longitude=places[key][0]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[       # Creazione inline keyboard per ogni posizione inviata
                   [InlineKeyboardButton(text="🔎Vedi descrizione🔍", callback_data=key)],  # La pressione del tasto provocherà una query. key=id del luogo
               ])
        # Invio di ogni risultato con annessa distanza, denominazione, categoria e tastiera inline
        bot.sendVenue(chat_id,latitude,longitude,"📍"+str(int(lis[key]))+"m "+places[key][1],places[key][3],reply_markup=keyboard) 


# metodo per "raccogliere" le query mandate tramite la tastiera inline
def on_callback_query(msg):
    global places
    _, from_id, query_data = telepot.glance(msg, flavor='callback_query') 
    if(str(places[query_data][2])=="0"):    #in alcuni casi la descrizione del luogo è "0", in questo caso mando un output diverso
        bot.sendMessage(from_id,"*"+str(places[query_data][1])+"*\n"+str(places[query_data][4])+"\n",parse_mode="Markdown",reply_to_message_id=msg["message"]["message_id"])
    else:
        bot.sendMessage(from_id,"*"+str(places[query_data][1])+"*\n"+str(places[query_data][4])+"\n"+str(places[query_data][2]),parse_mode="Markdown",reply_to_message_id=msg["message"]["message_id"])
   
 
MessageLoop(bot,{"chat":on_chat_message,"callback_query":on_callback_query}).run_as_thread()

while 1:
    
    time.sleep(10) 
   
