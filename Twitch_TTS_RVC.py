import json
import tkinter as tk
import pandas as pd
import subprocess
import os
import pygame
import requests
import shutil
import time
import asyncio
import threading
import queue
import time

from tkinter import ttk
from twitchio.ext import commands
from datetime import datetime
from threading import Thread
from PIL import Image, ImageTk

#------Globale Variablen-----------------
last_generated_file = None
last_rvc_file = None
show_model_label = False
show_user_label = False
show_img_label = False
model_change_bool = False
AutoPlay_bool = False
running_bool = False
m_count = 0
message_queue = queue.Queue()
queue_df = pd.DataFrame(columns=['Zeit', 'Count', 'Autor', 'Nachricht', 'Reward'])
done_df = pd.DataFrame(columns=['Zeit', 'Count', 'Autor', 'Nachricht', 'Reward'])

#--------Config-Datei laden--------------------
def load_config(file_path):
    try:
        with open(file_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file '{file_path}' not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Malformed JSON in config file '{file_path}'.")
        return {}

#---------Umlaute anpassen------------
def replace_umlaute(input_string):
    # Ersetzen der Umlaute
    input_string = input_string.replace('ä', 'ae')
    input_string = input_string.replace('ö', 'oe')
    input_string = input_string.replace('ü', 'ue')
    input_string = input_string.replace('Ä', 'Ae')
    input_string = input_string.replace('Ö', 'Oe')
    input_string = input_string.replace('Ü', 'Ue')
    return input_string   

#---------Piper TTS----------------------
def piper_generate(prompt):
    #TTS mit Piper    
    global last_generated_file
    
    config = load_config('config.json')
    
    model_name = config.get('TTS', {}).get('model')
    output_file = os.path.join("piper_output", 'TTS_output.wav')  # Ausgabedatei im "Output" Ordner speichern
    
    # Erstelle den "Output" Ordner, falls er nicht existiert
    os.makedirs("piper_output", exist_ok=True)
    
    n_prompt = replace_umlaute(prompt)
    
    # Konstruiere den Befehl
    command = f'echo "{n_prompt}" | .\\piper.exe --model {model_name} --output_file {output_file}'
    
    # Führe den Befehl aus
    subprocess.run(command, shell=True)
    
    # Setze den zuletzt generierten Dateinamen
    last_generated_file = output_file
    
    print("TTS abgeschlossen!")

#---------RVC Model laden--------------
def RVC_config(rvc_model):
    #RVC model festlegen
    #Input ist der .pth Dateiname
    response = requests.post("http://localhost:7897/run/infer_change_voice", json={
        "data": [
            rvc_model,
            0.33,
            0.33,
        ]
    }).json()

    global show_model_label
    if not show_model_label:
        show_model_label = True
        init_model_label(rvc_model)
    else:
        upd_model_label(rvc_model)
    
    #get_image(rvc_model)
    print(f"RVC Model '{rvc_model}' wurde geladen!")

#-------RVC Konvertierung---------------
def RVC_convert():
    #Audio convert mit RVC
    root_dir = os.path.abspath(os.path.dirname(__file__))
    input_wav_file = os.path.join(root_dir, 'piper_output/TTS_output.wav')
    
    response = requests.post("http://localhost:7897/run/infer_convert", json={
        "data": [
            0,
            input_wav_file,
            0,
            None,
            "rmvpe",
            "",
            "",
            0.75,
            3,
            0,
            0.25,
            0.33,
        ]
    }).json()
    
    get_RVC_file()

#----------RVC File aus temporären Daten kopieren------------
def get_RVC_file():
    global last_rvc_file
    
    # Pfad zum temporären Verzeichnis    
    config = load_config('config.json')
    
    temp_dir = config.get('RVC', {}).get('temp_dir')

    # Suchen nach allen .wav-Dateien im temporären Verzeichnis
    wav_files = [f for f in os.listdir(temp_dir) if f.endswith(".wav")]

    # Überprüfen, ob mindestens eine .wav-Datei gefunden wurde
    if wav_files:
        # Neueste .wav-Datei finden, indem das Modifikationsdatum verglichen wird
        latest_wav = max(wav_files, key=lambda x: os.path.getmtime(os.path.join(temp_dir, x)))
        
        # Neuer Name für die Zieldatei im Output-Ordner
        new_filename = os.path.join("RVC_output", "RVC_output.wav")
        
        # Vollständige Pfade für die Quell- und Zieldatei erstellen
        source_file = os.path.join(temp_dir, latest_wav)
        target_file = os.path.join(os.getcwd(), new_filename)

        # Die neueste .wav-Datei in den Output-Ordner kopieren und umbenennen
        shutil.copy(source_file, target_file)
        
        # Setze den zuletzt generierten Dateinamen
        last_rvc_file = new_filename                       
        
        #print(f"Datei wurde kopiert nach:'{target_file}'")
    else:
        print("Keine .wav-Dateien im temporären Verzeichnis gefunden.")

#--------Länge der RVC Audiodatei ermitteln---------------
def get_audio_length(file_path):
    #Audiodateilänge ermitteln    
    if file_path:
        pygame.init()
        pygame.mixer.init()

        # Lade die Audiodatei
        sound = pygame.mixer.Sound(file_path)

        # Ermittle die Länge der Audiodatei in Sekunden
        audio_length = sound.get_length()

        # Beende Pygame
        pygame.mixer.quit()
        pygame.quit()

        return audio_length 

#---------RVC abspielen-------------
def play_last_rvc(file_path):
    #Audiodatei abspielen
    if file_path:
        # Initialisiere Pygame
        pygame.init()
        pygame.mixer.init()
        
        # Lade die Audiodatei
        sound = pygame.mixer.Sound(file_path)
        
        # Ermittle die Länge der Audiodatei
        audio_length = sound.get_length()        
        
        # Spiele die Audiodatei ab
        sound.play()  

#------------TTS/RVC starten mit Test Prompt------------
def init_TTS(): 
    
    global last_rvc_file  
    
    bot_thread = threading.Thread(target=bot_run)
    bot_thread.daemon = True
    bot_thread.start()
    
    test_prompt = "Das Programm rennt jetzt, Hänno."
    
    piper_generate(test_prompt)
    
    RVC_convert()
    
    rvc_length = get_audio_length(last_rvc_file)
    print(f'Audio Length: {rvc_length}')   

#----------Model wechsel dich-------------
def model_change():
    while model_change_bool:
        if model_change_bool:
            time.sleep(20)
        if model_change_bool:
            RVC_config("Olaf_Scholz.pth")
        if model_change_bool:
            time.sleep(20)
        if model_change_bool:
            RVC_config("Stronghold_3.pth")
        if model_change_bool:
            time.sleep(20)        
        if model_change_bool:
            RVC_config("Maxim.pth")
        if model_change_bool:
            time.sleep(20)
        if model_change_bool:
            RVC_config("peter_lustig.pth")

#----------Twitch Bot Steuerung------------
def bot_run():
    
    asyncio.set_event_loop(asyncio.new_event_loop())
    print("Verbindung zu Twitch herstellen")
    bot = Bot()
    bot.run()

##---------Queue Funktionen------------------
# Funktion, um Nachrichten und Absender in die Queue zu schreiben
def enqueue_message(m_time, m_count, m_author, message, m_reward):
    global message_queue
    global queue_df
    message_queue.put((m_time, m_count, m_author, message, m_reward))
    add_queue_content(m_time, m_count, m_author, message, m_reward)

# Die nächste TTS Nachricht in der Queue abspielen
def process_next_message():
    if not message_queue.empty():  # Überprüfe, ob die Queue leer ist
        global running_bool
        running_bool = True
        m_time, m_count, m_author, message, m_reward = message_queue.get()  # Holt Nachricht und Absender aus der Queue
        print(f'[{m_time}] [{m_count}] {m_author}: {message} | Reward Title: {m_reward}') # Gibt Infos in Konsole aus
        
        #PiperTTS durchführen
        piper_generate(message)
        #RVC Convert durchführen
        RVC_convert()
        
        #RVC Audiolänge ermitteln und ausgeben
        global rvc_length
        rvc_length = get_audio_length(last_rvc_file)
        print(f'Audio Length: {rvc_length}')
        
        #Auf der Nutzeroberfläche user_label zeigen
        global show_user_label
        show_user_label = True
        
        #RVC Audio ausgeben
        play_last_rvc(last_rvc_file)
        time.sleep(rvc_length)
        # user_label ausblenden                        
        show_user_label = False
        
        # fill Dataframes
        add_done_content(m_time, m_count, m_author, message, m_reward)
        del_queue_content(m_count)
        
        running_bool = False
        global NextMsg_button
        NextMsg_button.config(state="active")
        message_queue.task_done()  # Markiert die Nachricht als erledigt    

# Funktion um Daten aus der Queue zu holen    
def process_messages():
    while AutoPlay_bool:
        if not message_queue.empty():  # Überprüfe, ob die Queue leer ist            
            m_time, m_count, m_author, message, m_reward = message_queue.get()  # Holt Nachricht und Absender aus der Queue
            print(f'[{m_time}] [{m_count}] {m_author}: {message} | Reward Title: {m_reward}') # Gibt Infos in Konsole aus
            
            #PiperTTS durchführen
            piper_generate(message)
            #RVC Convert durchführen
            RVC_convert()
            
            #RVC Audiolänge ermitteln und ausgeben
            global rvc_length
            rvc_length = get_audio_length(last_rvc_file)
            print(f'Audio Length: {rvc_length}')
            
            #Auf der Nutzeroberfläche user_label zeigen
            global show_user_label
            show_user_label = True
            
            #RVC Audio ausgeben
            play_last_rvc(last_rvc_file)
            time.sleep(rvc_length)
            # user_label ausblenden                        
            show_user_label = False
            
            # fill Dataframes
            add_done_content(m_time, m_count, m_author, message, m_reward)
            del_queue_content(m_count)
            
            message_queue.task_done()  # Markiert die Nachricht als erledigt
        else:
            time.sleep(1)  # Kurze Pause, um die CPU nicht zu überlasten

def add_queue_content(m_time, m_count, m_author, message, m_reward):
    global queue_df
    queue_df = pd.concat([queue_df, pd.DataFrame({'Zeit': [m_time], 'Count': [m_count], 'Autor': [m_author], 'Nachricht': [message], 'Reward': [m_reward]})], ignore_index=True)

def del_queue_content(m_count):
    global queue_df
    queue_df = queue_df.drop(queue_df[queue_df['Count'] == m_count].index)

def add_done_content(m_time, m_count, m_author, message, m_reward):
    global done_df
    done_df = pd.concat([done_df, pd.DataFrame({'Zeit': [m_time], 'Count': [m_count], 'Autor': [m_author], 'Nachricht': [message], 'Reward': [m_reward]})], ignore_index=True)

# Queue Listeninhalt laden
def update_queue_contents():
    global queue_listbox
    global queue_df
    while True:
        # Lösche vorherige Einträge in der ListBox
        queue_listbox.delete(0, tk.END)    
        # Fülle DataFrame mit den aktuellen Nachrichten aus der Queue
        while not queue_df.empty:
            queue_listbox.delete(0, tk.END)        
        # Füge die Nachrichten aus dem DataFrame der ListBox hinzu
            for index, row in queue_df.iterrows():
                queue_listbox.insert(tk.END, f'[{row["Zeit"]}] [{row["Count"]}] {row["Autor"]}: {row["Nachricht"]} | Reward Title: {row["Reward"]}')        
            time.sleep(1)  # Kurze Pause
        time.sleep(1)

# Done Listeninhalt laden
def update_done_contents():
    global done_listbox
    global done_df
    while True:
        # Lösche vorherige Einträge in der ListBox
        done_listbox.delete(0, tk.END)    
        # Fülle DataFrame mit den aktuellen Nachrichten aus der Queue
        while not done_df.empty:
            done_listbox.delete(0, tk.END)        
        # Füge die Nachrichten aus dem DataFrame der ListBox hinzu
            for index, row in done_df.iterrows():
                done_listbox.insert(tk.END, f'[{row["Zeit"]}] [{row["Count"]}] {row["Autor"]}: {row["Nachricht"]} | Reward Title: {row["Reward"]}')        
            time.sleep(1)  # Kurze Pause
        time.sleep(1)    
    
#---------Nutzeroberfläche--------------------------------------------
def init_window(window):

    window.title("Twitch TTS RVC")
    window.geometry("600x300")  # Set initial window size to 400x200 pixels
    
    tab_control = ttk.Notebook(window)
    
#----# Seite 1 erstellen
    global page1
    page1 = create_page(tab_control, "TTS/RVC Control")
    
    # Auswahlfeld für RVC-Modelle
    model_label = tk.Label(page1, text="Choose RVC Model:")
    model_label.place(relx=0.15, rely=0.1, anchor="center")
    
    # Liste der .pth-Dateien im Unterverzeichnis RVC/assets/weights abrufen
    rvc_models = [f for f in os.listdir(os.path.join("RVC", "assets", "weights")) if f.endswith(".pth")]

    # Variable für die Auswahl des RVC-Modells
    selected_model = tk.StringVar(page1)
    selected_model.set(rvc_models[0])  # Standardmäßig das erste Modell auswählen

    # Dropdown-Menü für die Auswahl des RVC-Modells
    model_dropdown = tk.OptionMenu(page1, selected_model, *rvc_models)
    model_dropdown.place(relx=0.5, rely=0.1, anchor="center")
    
    # Button "Model laden"
    load_model_button = tk.Button(page1, text="Load Model", command=lambda: load_model_action(selected_model.get()))
    load_model_button.place(relx=0.8, rely=0.1, anchor="center")
    
    # Model-Chance Button
    global model_change_button
    model_change_button = tk.Button(page1, text="Start Model rotation", command=lambda: model_change_action())
    model_change_button.place(relx=0.15, rely=0.3, anchor="center")
    
    # AutoPlay Button
    global AutoPlay_button
    AutoPlay_button = tk.Button(page1, text="Start Auto-Play", command=lambda: AutoPlay_action())
    AutoPlay_button.place(relx=0.5, rely=0.3, anchor="center")
    
    # Next Message Button
    global NextMsg_button
    NextMsg_button = tk.Button(page1, text="Next TTS", command=lambda: NextMsg_action())
    NextMsg_button.place(relx=0.8, rely=0.3, anchor="center")
    
    # Start-Button
    global start_button
    start_button = tk.Button(page1, text="Start Twitch Bot", command=lambda: start_action(page1))
    start_button.place(relx=0.5, rely=0.8, anchor="center") 
    
#----# Seite 2 erstellen
    page2 = create_page(tab_control, "TTS Queue")
    # Liste zur Anzeige der Nachrichten und Absender
    global queue_listbox
    queue_listbox = tk.Listbox(page2, width=150, height=10)
    queue_listbox.pack(padx=10, pady=20)
    
    queue_display_thread = threading.Thread(target=update_queue_contents)
    queue_display_thread.daemon = True
    queue_display_thread.start()


#----# Seite 3 erstellen
    page3 = create_page(tab_control, "TTS Done")
    # Liste zur Anzeige der Nachrichten und Absender
    global done_listbox
    done_listbox = tk.Listbox(page3, width=150, height=10)
    done_listbox.pack(padx=10, pady=20)
    
    done_display_thread = threading.Thread(target=update_done_contents)
    done_display_thread.daemon = True
    done_display_thread.start()  
    
    # Tab-Steuerung platzieren
    tab_control.pack(expand=1, fill="both")


def create_page(tab_control, title):
    page = ttk.Frame(tab_control)
    tab_control.add(page, text=title)
    return page

def load_model_action(selected_model):
    RVC_config(selected_model)

def model_change_action():
    global model_change_bool
    global model_change_button
    if not model_change_bool:
        model_change_bool = True
        print('Model Rotation started!')
        model_change_button.config(text="Stop Model Rotation")
        model_thread = threading.Thread(target=model_change)
        model_thread.start()
    else:
        model_change_bool = False
        print('Model Rotation stopped!')
        model_change_button.config(text="Start Model Rotation")

def init_model_label(model_name):
    global page1
    global model_label
    model_label = tk.Label(page1, text= f"RVC Model: {model_name}", font=("Arial", 18), fg="red")
    model_label.place(relx=0.5, rely=0.55, anchor="center")  # Place text label in the center of the window

def upd_model_label(model_name):
    global model_label
    model_label.config(text = f"RVC Model: {model_name}")

def bot_live(window):
    global text_label
    text_label = tk.Label(window, text="Connection to Chat enabled! Close Shell to stop! ", font=("Arial", 10), fg="red")
    text_label.place(relx=0.5, rely=0.7, anchor="center")  # Place text label in the center of the window
    global start_button
    start_button.destroy()    

def start_action(window):
    start_button.config(state="disabled", text="Warte auf Twitch...")  # Disable start button once clicked
    init_TTS()

def init_user_label():
    global root
    global user_label
    global show_user_label
    global m_count
    global m_author
    global rvc_length
    while True:
        if show_user_label:
            user_label = tk.Label(root, text=f"Nachricht {m_count} von {m_author}", font=("Arial", 20), fg="black")
            user_label.place(relx=0.5, rely=0.85, anchor="center")  # Place text label in the center of the window
            time.sleep(rvc_length+1)
            user_label.destroy()

def NextMsg_action():
    global NextMsg_button  
    
    next_thread = threading.Thread(target=process_next_message)
    next_thread.start()    
   
    if running_bool:
        NextMsg_button.config(state="disabled")
    else:
        NextMsg_button.config(state="active")   
    
def AutoPlay_action():
    global AutoPlay_bool, AutoPlay_button, NextMsg_button
    if not AutoPlay_bool:
        AutoPlay_bool = True
        AutoPlay_button.config(text="Stop Auto-Play")
        NextMsg_button.config(state="disabled")
        
        queue_thread = threading.Thread(target=process_messages)
        queue_thread.daemon = True
        queue_thread.start()
        
    else:
        AutoPlay_bool = False
        AutoPlay_button.config(text="Start Auto-Play")
        NextMsg_button.config(state="active")

def get_image(rvc_model):
    global root
    #print(rvc_model)
    if rvc_model == "Maxim.pth":
        img_path = os.path.join(os.getcwd(),"img", "maxim.png")
        show_image(img_path)
    elif rvc_model == "Olaf_Scholz.pth":
        img_path = os.path.join(os.getcwd(),"img", "olaf.png")
        show_image(img_path)
    elif rvc_model == "Stronghold_3.pth":
        img_path = os.path.join(os.getcwd(),"img", "stronghold.png")
        show_image(img_path)
    elif rvc_model == "peter_lustig.pth":
        img_path = os.path.join(os.getcwd(),"img", "peter.png")
        show_image(img_path)

def show_image(img_path):        
    # Bild laden
    img = Image.open(img_path)
        
    # Bild auf 100x100 skalieren
    img.thumbnail((100, 100))
    
    # ImageTk verwenden, um das Bild in Tkinter zu laden
    img = ImageTk.PhotoImage(img)
        
    # Label erstellen und Bild zuweisen
    global show_img_label
    global img_label
    if not show_img_label:
        show_img_label = True
        img_label = tk.Label(root, image=img)
        img_label.image = img  # Bildreferenz behalten, um das Bild vor dem Garbage Collector zu bewahren
        img_label.place(relx=0.5, rely=0.9, anchor="center")
        img_label.pack()
    else:
        img_label.destroy()
        img_label = tk.Label(root, image=img)
        img_label.image = img  # Bildreferenz behalten, um das Bild vor dem Garbage Collector zu bewahren
        img_label.place(relx=0.5, rely=0.9, anchor="center")
        img_label.pack()
    
#-----Der Twitch Bot---------
class Bot(commands.Bot):

    def __init__(self):
        # Initialize our Bot with our access token, prefix and a list of channels to join on boot...
        # prefix can be a callable, which returns a list of strings or a string...
        # initial_channels can also be a callable which returns a list of strings...
        # Pfad zum temporären Verzeichnis    
        config = load_config('config.json')
    
        token_key = config.get('twitchio', {}).get('token')
        channel = config.get('twitchio', {}).get('channel')
        
        super().__init__(token=token_key, prefix='?', initial_channels=[channel])

    async def event_ready(self):
        # Notify us when everything is ready!
        # We are logged in and ready to chat and use commands...
        print(f'Logged in as | {self.nick}')
        #print(f'User id is | {self.user_id}')
        global page1
        bot_live(page1)
        play_last_rvc(last_rvc_file)
        user_label_thread = threading.Thread(target=init_user_label)
        user_label_thread.start()
    
    async def stop(self):
        self._ws.teardown()
    
    async def event_raw_pubsub(self, data):
        # Überprüfen, ob es sich um eine PubSub-Nachricht für Channel Points handelt
        if data['type'] == 'reward-redeemed':
            # Erstellen Sie ein PubSubChannelPointsMessage-Objekt aus den Daten
            message = PubSubChannelPointsMessage(client=self, topic=data['topic'], data=data['message'])

            # Extrahieren Sie die relevanten Informationen aus der Nachricht
            channel_id = message.channel_id
            user_id = message.user.id
            user_name = message.user.name
            reward_id = message.reward.id
            reward_title = message.reward.title
            user_input = message.input

            # Handle the PointMessage as per your requirements
            # Zum Beispiel könnten Sie die erhaltenen Informationen verwenden, um auf die Channel-Points-Aktion zu reagieren
            print(f"PointMessage received - User: {user_name}, Reward: {reward_title}")

#----------Event Empfang einer Nachricht---------------------------
    async def event_message(self, message):
        global last_rvc_file        
        
        #Alle Infos sammeln
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        reward_title = message.tags.get('msg-id')
        
        global m_count
        m_count = m_count + 1   
        
        global m_author
        m_author = message.author.name
        
        # Infos in die Queue
        enqueue_message(timestamp,m_count,message.author.name,message.content,reward_title)
        
        await self.handle_commands(message)

#------Programm Main Loop--------------
def main():
    global root
    root = tk.Tk()
    init_window(root)
    
    root.mainloop()

if __name__ == "__main__":
    main()
