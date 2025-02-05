import customtkinter as ctk
import subprocess
import ctypes
import sys
import threading
from datetime import datetime
import os
from tkinter import messagebox
import webbrowser

chat_data = {}  
current_chat_name = None  
selected_model = None  
chat_lock = threading.Lock()
is_processing = False  

def open_linkedin():
    
    linkedin_url = "https://www.linkedin.com/in/isllantoso/"
   
    webbrowser.open(linkedin_url)

def run_as_admin():
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)

def check_ollama_installed():
    try:
        subprocess.check_call(["ollama", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        show_error("Ollama não está instalado ou não está no PATH.")
        sys.exit(1)

def get_available_models():
    try:
        output = subprocess.check_output(
            ["powershell", "-Command", "ollama list"],
            text=True,
            encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if not output.strip():
            raise ValueError("Nenhum modelo encontrado.")
        
        lines = output.strip().split("\n")[1:]

        models = [line.split()[0] for line in lines if line]
        
        if not models:
            raise ValueError("Nenhum modelo válido encontrado.")
        
        return models
    except subprocess.CalledProcessError as e:
        show_error(f"Erro ao executar o comando 'ollama list': {e}")
        return []
    except Exception as e:
        show_error(f"Erro inesperado ao obter modelos: {e}")
        return []

def show_message(message, is_error=False):
    if is_error:
        show_error(message)
    else:
        error_label.configure(text=message)

def show_warning(message):
    warning_window = ctk.CTkToplevel(root)
    warning_window.title("Aviso")
    warning_window.geometry("300x150")
    
    warning_label = ctk.CTkLabel(warning_window, text=message, font=ctk.CTkFont(size=14), text_color="red")
    warning_label.pack(pady=30)
    
    close_button = ctk.CTkButton(warning_window, text="Fechar", command=warning_window.destroy, font=ctk.CTkFont(size=12))
    close_button.pack()

def interact_with_ollama(user_input, callback):
    global chat_data, current_chat_name, selected_model

    if not selected_model:
        show_warning("Erro: Nenhum modelo foi selecionado.") 
        return

    chat_history = chat_data.get(current_chat_name, [])
    compacted_history = compact_history(chat_history, 2000)

    prompt = f"Contexto:\n{compacted_history}\n\nUsuário: {user_input}\n"

    model_safe = selected_model.replace("'", "''")  
    command = ["powershell", "-Command", f"ollama run '{model_safe}' '{prompt}'"]
    
    try:
        response = subprocess.check_output(
            command,
            text=True,
            encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        callback(response.strip())
    except subprocess.CalledProcessError as e:
        callback(f"Erro: Não foi possível executar o comando PowerShell.\nDetalhes: {str(e)}")
    except Exception as e:
        callback(f"Erro inesperado: {str(e)}")

def compact_history(history, max_length):
    compacted = ""
    for message in reversed(history):
        if len(compacted) + len(message) > max_length:
            break
        compacted = message + "\n" + compacted
    return compacted

def send_message(event=None):
    global current_chat_name, is_processing  
    
    if is_processing:  
        show_error("A IA está processando, aguarde a resposta.")
        return

    user_message = entry.get("1.0", ctk.END).strip()
    
    if not user_message:
        show_error("Por favor, digite uma mensagem antes de enviar.")
        return    
    if not selected_model:
        show_error("Por favor, selecione um modelo antes de enviar a mensagem.")
        return  

    if user_message != "":
        if len(user_message) > 2000:
            user_message = user_message[:2000]
            show_error("Mensagem muito longa! Foi limitada até 2000 caracteres.")

        timestamp = get_current_time()
        chat_box.configure(state=ctk.NORMAL)
        chat_box.insert(ctk.END, f"{timestamp} Você: {user_message}\n\n", 'user')
        entry.delete("1.0", ctk.END)
        chat_box.configure(state=ctk.DISABLED)
        log_conversation(f"{timestamp} Você: {user_message}")

        if current_chat_name not in chat_data:
            chat_data[current_chat_name] = []
        chat_data[current_chat_name].append(f"{timestamp} Você: {user_message}")

        is_processing = True
        threading.Thread(target=interact_with_ollama, args=(user_message, update_chat), daemon=True).start()

def show_error(message):
    messagebox.showerror("Erro", message)

def update_chat(response):
    global is_processing  
    root.after(0, update_chat_ui, response)
    
    is_processing = False

def update_chat_ui(response):
    global chat_data, current_chat_name
    timestamp = get_current_time()

    with chat_lock:
        chat_data[current_chat_name].append(f"{timestamp} Llama ({selected_model}): {response}")
        chat_box.configure(state=ctk.NORMAL)
        chat_box.insert(ctk.END, f"{timestamp} Llama ({selected_model}): {response}\n\n", 'bot')
        chat_box.yview(ctk.END)
        chat_box.configure(state=ctk.DISABLED)

def get_current_time():
    return datetime.now().strftime("%H:%M")

def log_conversation(message):
    if current_chat_name:
        log_filename = f"{current_chat_name}.txt"
        threading.Thread(target=write_log, args=(log_filename, message), daemon=True).start()

def write_log(log_filename, message):
    try:
        with open(log_filename, "a", encoding="utf-8") as log_file:
            log_file.write(message + "\n")
    except Exception as e:
        show_error(f"Erro ao escrever no log: {e}")

def create_chat(chat_name):
    button = ctk.CTkButton(sidebar_frame, text=chat_name, font=font, command=lambda: open_chat(chat_name))
    button.grid(row=len(sidebar_frame.winfo_children()), pady=5, sticky="w")

def open_chat(chat_name):
    global current_chat_name, is_processing
    if is_processing:  
        show_error("A IA está processando, aguarde a resposta antes de trocar de chat.")
        return

    if current_chat_name == chat_name:  
        return  

    current_chat_name = chat_name
    chat_box.configure(state=ctk.NORMAL)
    chat_box.delete("1.0", ctk.END)  
    timestamp = datetime.now().strftime("%H:%M")
    chat_box.insert(ctk.END, f"{timestamp} {chat_name} aberto.\n\n")
    chat_box.configure(state=ctk.DISABLED)

    if chat_name in chat_data:
        for msg in chat_data[chat_name]:
            chat_box.configure(state=ctk.NORMAL)
            chat_box.insert(ctk.END, msg + "\n\n")
        chat_box.configure(state=ctk.DISABLED)
 
def update_model_selection(model):
    global selected_model
    selected_model = model
    chat_box.configure(state=ctk.NORMAL)
    chat_box.insert(ctk.END, f"Modelo selecionado: {selected_model}\n\n")
    chat_box.configure(state=ctk.DISABLED)
    open_chat("Chat 1")

def clear_chat():
    global current_chat_name
    if current_chat_name:
        confirm = messagebox.askyesno("Confirmar", "Você tem certeza que deseja limpar o chat?")
        
        if not confirm:
            return

        chat_box.configure(state=ctk.NORMAL)
        chat_box.delete("1.0", ctk.END)
        chat_box.configure(state=ctk.DISABLED)

        if current_chat_name in chat_data:
            chat_data[current_chat_name] = []

        timestamp = get_current_time()
        log_conversation(f"{timestamp} {current_chat_name} foi limpo.")

root = ctk.CTk()
root.title("Llama Educacional")
root.geometry("1280x720")

font = ctk.CTkFont(family="Helvetica", size=14)

root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=10)
root.grid_rowconfigure(2, weight=2)
root.grid_rowconfigure(3, weight=1)
root.grid_rowconfigure(4, weight=1)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=3)

sidebar_frame = ctk.CTkFrame(root)
sidebar_frame.grid(row=0, column=0, rowspan=5, padx=5, pady=10, sticky="ns")
root.grid_columnconfigure(0, weight=0) 

chat_frame = ctk.CTkFrame(root)
chat_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")
chat_frame.grid_rowconfigure(0, weight=1)
chat_frame.grid_columnconfigure(0, weight=1)

chat_box = ctk.CTkTextbox(chat_frame, wrap=ctk.WORD, state=ctk.DISABLED, font=font)
chat_box.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

entry = ctk.CTkTextbox(root, height=100, font=font, wrap=ctk.WORD)
entry.grid(row=3, column=1, padx=10, pady=(10, 0), sticky="ew")

send_button = ctk.CTkButton(root, text="Enviar", command=send_message, font=font, text_color="white", corner_radius=8)
send_button.grid(row=4, column=1, pady=(10, 20), sticky="n")

sobre_button = ctk.CTkButton(root, text="Desenvolvido por Isllan Toso", font=font, text_color="white", corner_radius=8, command=open_linkedin)
sobre_button.grid(row=4, column=1, padx=10, pady=10, sticky="se")

error_label = ctk.CTkLabel(root, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color="red")
error_label.grid(row=1, column=1, padx=10, pady=5, sticky="s")

models = get_available_models()
model_dropdown = ctk.CTkOptionMenu(root, values=models, command=update_model_selection, font=font)
model_dropdown.grid(row=2, column=1, padx=10, pady=10, sticky="n")
model_dropdown.set("Selecione um modelo")

clear_button = ctk.CTkButton(root, text="Limpar Chat", font=font, command=clear_chat)
clear_button.grid(row=4, column=0, padx=10, pady=20, sticky="n")

entry.bind('<Return>', send_message)

run_as_admin()

create_chat("Chat 1")
create_chat("Chat 2")
create_chat("Chat 3")
create_chat("Chat 4")
create_chat("Chat 5")

root.mainloop()
