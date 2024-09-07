import os
import sys
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import pyaudio
import speech_recognition as sr
from translate import Translator
import re

def resource_path(relative_path):
    
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class RealTimeTranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Recognition-Text-Translator")
        self.root.geometry("1000x800") # Default windoww
        self.root.configure(bg='#F5F5DC')

        # Style Scrollbars
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Vertical.TScrollbar", gripcount=0,
                        background="#666", darkcolor="#666", lightcolor="#aaa",
                        troughcolor="#eee", bordercolor="#ccc", arrowcolor="#333")

        # Style LabelFrame
        style.configure("Custom.TLabelframe", background="#F5F5DC")  # Background
        style.configure("Custom.TLabelframe.Label", background="#F5F5DC")  # label

        # Canvas with vertical scrollbar
        self.canvas = tk.Canvas(root, bg='#F5F5DC')
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Vertical scrollbar on the right
        self.scrollbar_y = ttk.Scrollbar(root, orient=tk.VERTICAL, command=self.canvas.yview, style="Vertical.TScrollbar")
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Frame for containing the content
        self.content_frame = tk.Frame(self.canvas, bg='#F5F5DC')
        self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        # Disable horizontal scrolling
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set)

        # Sscrolling behavior to update
        self.content_frame.bind("<Configure>", self.update_scroll_region)
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)

        self.language_label = tk.Label(self.content_frame, text="Select translation", font=('Arial', 18, 'bold'), fg='black', bg='#F5F5DC')
        self.language_label.pack(pady=20)

        self.languages = {
            "Polish -> English": ("pl", "en", "pl.png", "en.png"),
            "Polish -> German": ("pl", "de", "pl.png", "de.png"),
            "Polish -> Spanish": ("pl", "es", "pl.png", "es.png"),
            "English -> Polish": ("en", "pl", "en.png", "pl.png"),
            "German -> Polish": ("de", "pl", "de.png", "pl.png"),
            "Spanish -> Polish": ("es", "pl", "es.png", "pl.png")
        }

        # ImageTk.PhotoImage
        self.image_references = {}

        try:
            for key, (from_lang, to_lang, from_flag, to_flag) in self.languages.items():
                self.image_references[key] = {
                    "from": ImageTk.PhotoImage(Image.open(resource_path(from_flag)).resize((40, 30))),
                    "to": ImageTk.PhotoImage(Image.open(resource_path(to_flag)).resize((40, 30))),
                    "arrow": ImageTk.PhotoImage(Image.open(resource_path("arrow.png")).resize((30, 20)))  # Arrow image
                }
        except Exception as e:
            print(f"Error loading images: {e}")
            return

        self.language_var = tk.StringVar(value=None)
        # Create two main blocks
        self.block1_frame = ttk.LabelFrame(self.content_frame, style="Custom.TLabelframe")
        self.block1_frame.pack(pady=20, padx=20, fill="x")
        # Buttons to select languages (side by side)
        self.radio_buttons = []
        button_frame = tk.Frame(self.block1_frame)
        button_frame.pack(pady=10)

        for i, (text, (from_lang, to_lang, from_flag, to_flag)) in enumerate(self.languages.items()):
            button_frame_inner = tk.Frame(button_frame, bg='#F5F5DC')

            left_flag_label = tk.Label(button_frame_inner, image=self.image_references[text]["from"], bg='#F5F5DC')
            left_flag_label.pack(side=tk.LEFT, padx=5)

            button = tk.Radiobutton(button_frame_inner, text=f"{text}", variable=self.language_var, value=text,
                                    font=('Arial', 12, 'bold'), indicatoron=0, width=25, height=2, bg='#F5F5DC')
            button.pack(side=tk.LEFT)

            self.radio_buttons.append(button)

            right_flag_label = tk.Label(button_frame_inner, image=self.image_references[text]["to"], bg='#F5F5DC')
            right_flag_label.pack(side=tk.LEFT, padx=5)

            button_frame_inner.grid(row=i // 3, column=i % 3, padx=30, pady=10)

        # Disable Start button until language is selected
        self.language_var.trace_add("write", self.check_language_selected)

        # Initially hide the "Selected" label
        self.selected_label = tk.Label(self.content_frame, text="Selected", font=('Arial', 14, 'bold'), fg='black', bg='#F5F5DC')
        self.selected_label.pack(pady=5)
        self.selected_label.pack_forget()  # Initially hidden

        # Section for flags and arrow
        self.flag_frame = tk.Frame(self.content_frame, bg='#F5F5DC')
        self.flag_frame.pack(pady=10)

        self.from_flag_label = tk.Label(self.flag_frame, bg='#F5F5DC')
        self.from_flag_label.pack(side=tk.LEFT, padx=10)

        self.arrow_label = tk.Label(self.flag_frame, bg='#F5F5DC')
        self.arrow_label.pack(side=tk.LEFT, padx=10)

        self.to_flag_label = tk.Label(self.flag_frame, bg='#F5F5DC')
        self.to_flag_label.pack(side=tk.LEFT, padx=10)

        self.update_flags()
        self.language_var.trace_add("write", self.update_flags)

        # Label to instruct the user to start/stop (always visible)
        self.start_instruction_label = tk.Label(self.content_frame, text="Press Start to begin", font=('Arial', 16, 'bold'), fg='black', bg='#F5F5DC')
        self.start_instruction_label.pack(pady=20)

        # Create Start and Stop buttons with status label
        self.status_label = tk.Label(self.content_frame, text="", font=('Arial', 16, 'bold'), fg='red', bg='#F5F5DC')
        self.status_label.pack(pady=10)

        # Frame for buttons
        self.button_frame = tk.Frame(self.content_frame, bg='#F5F5DC')
        self.button_frame.pack(pady=20)

        self.start_button = tk.Button(self.button_frame, text="Start", command=self.start_listening, width=15, height=2, font=('Arial', 14, 'bold'), state='disabled')
        self.start_button.pack(side=tk.LEFT, padx=10)
        
        self.stop_button = tk.Button(self.button_frame, text="Stop", command=self.stop_listening, width=15, height=2, font=('Arial', 14, 'bold'), state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=10)

        # Create text entry fields for displaying recognized text and translations with proper scrollbars
        # Frame for recognized text with scrollbar
        recognized_text_frame = tk.Frame(self.content_frame)
        recognized_text_frame.pack(pady=10)
        
        self.text_scroll = tk.Scrollbar(recognized_text_frame)
        self.text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_display = tk.Text(recognized_text_frame, wrap=tk.WORD, height=6, font=('Arial', 14), yscrollcommand=self.text_scroll.set)
        self.text_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_scroll.config(command=self.text_display.yview)

        # Frame for translation text with scrollbar
        translated_text_frame = tk.Frame(self.content_frame)
        translated_text_frame.pack(pady=10)
        
        self.trans_scroll = tk.Scrollbar(translated_text_frame)
        self.trans_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.translation_display = tk.Text(translated_text_frame, wrap=tk.WORD, height=6, font=('Arial', 14), yscrollcommand=self.trans_scroll.set)
        self.translation_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.trans_scroll.config(command=self.translation_display.yview)
        
        self.listening = False

    def check_language_selected(self, *args):
        if self.language_var.get():
            self.start_button.config(state='normal')
            self.status_label.config(text="")
            self.stop_button.config(state='disabled')

            # Show "Selected" label after selecting translation and make sure it's placed before the flag frame
            self.selected_label.pack_forget()  # Remove it first to ensure reordering
            self.selected_label.pack(before=self.flag_frame, pady=5)  # Pack it before flag frame
        else:
            self.start_button.config(state='disabled')
            self.selected_label.pack_forget()  # Hide "Selected" label when no language is selected

    def update_flags(self, *args):
        selected_lang = self.language_var.get()
        if selected_lang:
            from_flag = self.image_references[selected_lang]["from"]
            to_flag = self.image_references[selected_lang]["to"]
            arrow = self.image_references[selected_lang]["arrow"]
            self.from_flag_label.config(image=from_flag)
            self.to_flag_label.config(image=to_flag)
            self.arrow_label.config(image=arrow)

    def detect_sentences(self, text, language="pl"):
        text = text.strip()
        if language == "pl":
            text = re.sub(r'\b(which|because|that|what)\b', r', \1', text)
        if not text.endswith('.'):
            text += '.'
        sentences = re.split(r'(?<=[.!?]) +', text)
        sentences = [s.capitalize() for s in sentences]
        final_text = ' '.join(sentences)
        return final_text

    def translate_text(self, text, from_lang="pl", to_lang="en"):
        translator = Translator(from_lang=from_lang, to_lang=to_lang)
        translation = translator.translate(text)
        return translation

    def start_listening(self):
        self.listening = True
        self.status_label.config(text="Listening", fg='green')
        self.stop_button.config(state='normal')
        self.start_button.config(state='disabled')
        self.start_instruction_label.config(text="Press Stop to stop")

        for button in self.radio_buttons:
            button.config(state='disabled')

        self.thread = threading.Thread(target=self.recognize_and_translate_live)
        self.thread.start()

    def stop_listening(self):
        self.listening = False
        self.status_label.config(text="Stopped", fg='red')
        self.stop_button.config(state='disabled')
        self.start_button.config(state='normal')
        self.start_instruction_label.config(text="Press Start to begin")

        for button in self.radio_buttons:
            button.config(state='normal')

    def recognize_and_translate_live(self):
        recognizer = sr.Recognizer()
        mic = sr.Microphone()

        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=2)

            while self.listening:
                try:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)

                    # Recognize speech and adjust to current language
                    from_lang, to_lang = self.languages[self.language_var.get()][:2]
                    text = recognizer.recognize_google(audio, language=f"{from_lang}-{from_lang.upper()}")

                    # Process recognized speech into complete sentences
                    text_with_punctuation = self.detect_sentences(text, language=from_lang)

                    # Display recognized speech
                    self.display_text(self.text_display, text_with_punctuation)

                    # Translate the recognized sentence
                    translation = self.translate_text(text_with_punctuation, from_lang=from_lang, to_lang=to_lang)
                    self.display_text(self.translation_display, translation)

                except sr.UnknownValueError:
                    self.display_text(self.text_display, "Speech could not be recognized.\n")
                except sr.RequestError as e:
                    self.display_text(self.text_display, f"Speech recognition service error: {e}\n")

    def display_text(self, widget, text):
        widget.configure(state='normal')
        widget.insert(tk.END, text + "\n")
        widget.configure(state='disabled')
        widget.see(tk.END)

    # Update scroll region when the frame is resized
    def update_scroll_region(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_mouse_wheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

if __name__ == "__main__":
    root = tk.Tk()
    app = RealTimeTranslatorApp(root)
    root.mainloop()
