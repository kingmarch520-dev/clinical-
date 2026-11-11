"""Pseudo Clinic - Android app (Kivy), friendly style with an expressive mascot.
Needs clinic_core.py, content.json and the mascot_*.png images packaged with it.
"""

import os
import random
import threading

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import clinic_core as core

Window.softinput_mode = "below_target"  # keep the keyboard from covering the text box
Window.clearcolor = (1, 1, 1, 1)

HERE = os.path.dirname(os.path.abspath(__file__))

FONT = sp(16)
TEXT = (0.17, 0.20, 0.25, 1)
MUTED = (0.46, 0.50, 0.56, 1)

# Button styles: (face colour, edge colour, text colour)
GREEN = ((0.24, 0.75, 0.42, 1), (0.17, 0.59, 0.32, 1), (1, 1, 1, 1))
BLUE = ((0.30, 0.64, 1.00, 1), (0.20, 0.49, 0.85, 1), (1, 1, 1, 1))
YELLOW = ((1.00, 0.79, 0.24, 1), (0.85, 0.62, 0.10, 1), TEXT)
CORAL = ((1.00, 0.42, 0.42, 1), (0.82, 0.29, 0.29, 1), (1, 1, 1, 1))
PURPLE = ((0.70, 0.48, 0.96, 1), (0.55, 0.35, 0.80, 1), (1, 1, 1, 1))
WHITE = ((1, 1, 1, 1), (0.85, 0.87, 0.90, 1), TEXT)

MOODS = ("happy", "wink", "worried", "alarmed", "thinking", "caring", "celebrate")


# ---------- the mascot ----------

class Mascot(Image):
    """The app mascot. Change its face with set_mood, bounce it in with pop."""

    def __init__(self, mood="happy", full=dp(80), **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        super().__init__(size=(full, full), **kwargs)
        self.full = full
        self.mood = "happy"
        self.set_mood(mood, pop=False)

    def set_mood(self, mood, pop=True):
        if mood not in MOODS:
            mood = "happy"
        self.mood = mood
        self.source = os.path.join(HERE, "mascot_" + mood + ".png")
        if pop:
            self.pop()

    def pop(self):
        Animation.cancel_all(self, "size")
        self.size = (self.full * 0.55, self.full * 0.55)
        Animation(size=(self.full, self.full), duration=0.4, t="out_back").start(self)


class TapMascot(ButtonBehavior, Mascot):
    """A mascot you can poke. Each tap changes its face."""

    FACES = ["wink", "thinking", "caring", "happy"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._next = 0
        self.bind(on_release=self.poke)

    def poke(self, *args):
        self.set_mood(self.FACES[self._next % len(self.FACES)])
        self._next += 1


class Confetti(FloatLayout):
    """A see-through layer on top of everything. burst() rains confetti."""

    COLORS = [GREEN[0], BLUE[0], YELLOW[0], CORAL[0], PURPLE[0]]

    def burst(self, count=45):
        for _ in range(count):
            piece = Widget(size_hint=(None, None),
                           size=(dp(random.randint(6, 12)), dp(random.randint(10, 18))))
            with piece.canvas:
                Color(*random.choice(self.COLORS))
                rect = Rectangle(pos=piece.pos, size=piece.size)
            piece.bind(pos=lambda inst, value, r=rect: setattr(r, "pos", value))
            x = random.uniform(0, max(self.width - dp(12), 1))
            piece.pos = (x, self.height + dp(20))
            self.add_widget(piece)
            anim = Animation(x=x + random.uniform(-dp(60), dp(60)), y=-dp(30),
                             duration=random.uniform(1.6, 2.8), t="in_quad")
            anim.bind(on_complete=lambda a, w: self.remove_widget(w))
            Clock.schedule_once(lambda dt, p=piece, a=anim: a.start(p), random.uniform(0, 0.6))


def celebrate():
    App.get_running_app().confetti.burst()


# ---------- friendly building blocks ----------

class ChunkyButton(ButtonBehavior, Label):
    """A rounded button with a thick bottom edge that squashes when pressed."""

    def __init__(self, text="", style=GREEN, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(56))
        super().__init__(text=text, bold=True, font_size=FONT,
                         halign="center", valign="middle", **kwargs)
        self.face, self.edge, text_color = style
        self.color = text_color
        with self.canvas.before:
            self._edge_color = Color(*self.edge)
            self._edge_rect = RoundedRectangle(radius=[dp(16)])
            self._face_color = Color(*self.face)
            self._face_rect = RoundedRectangle(radius=[dp(14)])
        self.bind(pos=self._redraw, size=self._redraw, state=self._redraw)
        self.bind(size=self._fit_text)
        self._redraw()
        self._fit_text()

    def set_style(self, style):
        self.face, self.edge, text_color = style
        self.color = text_color
        self._face_color.rgba = self.face
        self._edge_color.rgba = self.edge

    def _redraw(self, *args):
        drop = dp(2) if self.state == "down" else dp(5)
        inset = dp(2)
        self._edge_rect.pos = self.pos
        self._edge_rect.size = self.size
        self._face_rect.pos = (self.x + inset, self.y + drop)
        self._face_rect.size = (max(self.width - 2 * inset, 0),
                                max(self.height - drop - inset, 0))

    def _fit_text(self, *args):
        self.text_size = (max(self.width - dp(24), 0), self.height)


class ChunkyToggle(ChunkyButton):
    """A yes/no button. White when NO, green when YES."""

    def __init__(self, text, change_callback=None, **kwargs):
        kwargs.setdefault("height", dp(64))
        super().__init__(text=text + ": NO", style=WHITE, **kwargs)
        self.base_text = text
        self.active = False
        self.change_callback = change_callback
        self.bind(on_release=self.flip)

    def flip(self, *args):
        self.active = not self.active
        self.text = self.base_text + (": YES" if self.active else ": NO")
        self.set_style(GREEN if self.active else WHITE)
        if self.change_callback:
            self.change_callback()


def wrapped_label(text, pad=dp(12), **kwargs):
    """A label that wraps its text and grows to fit it."""
    kwargs.setdefault("font_size", FONT)
    kwargs.setdefault("color", TEXT)
    kwargs.setdefault("halign", "left")
    label = Label(text=text, size_hint_y=None, valign="top", **kwargs)
    label.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
    label.bind(texture_size=lambda inst, s: setattr(inst, "height", s[1] + pad))
    return label


def field(**kwargs):
    """A soft, flat text box."""
    kwargs.setdefault("font_size", FONT)
    return TextInput(background_normal="", background_active="",
                     background_color=(0.95, 0.96, 0.98, 1), foreground_color=TEXT,
                     hint_text_color=MUTED, cursor_color=GREEN[0],
                     padding=[dp(14), dp(14), dp(14), dp(14)], **kwargs)


def scroll_box():
    """Returns (scrollview, inner vertical box that grows with its content)."""
    scroll = ScrollView()
    box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(10))
    box.bind(minimum_height=box.setter("height"))
    scroll.add_widget(box)
    return scroll, box


class Bubble(BoxLayout):
    """A rounded chat bubble. Green for you, light gray for the app."""

    def __init__(self, text, mine=False, **kwargs):
        super().__init__(size_hint_y=None, padding=dp(12), **kwargs)
        fill = GREEN[0] if mine else (0.94, 0.95, 0.97, 1)
        with self.canvas.before:
            Color(*fill)
            self._rect = RoundedRectangle(radius=[dp(18)])
        self.bind(pos=self._sync, size=self._sync)
        label = wrapped_label(text, pad=0, color=(1, 1, 1, 1) if mine else TEXT)
        label.bind(height=lambda inst, h: setattr(self, "height", h + dp(24)))
        self.add_widget(label)

    def _sync(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size


def show_popup(title, text, kind="info", mood="happy"):
    urgent = kind == "urgent"
    style = CORAL if urgent else GREEN
    content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
    mascot = Mascot(mood=mood, full=dp(84), pos_hint={"center_x": 0.5})
    content.add_widget(mascot)
    scroll, box = scroll_box()
    box.add_widget(wrapped_label(text))
    content.add_widget(scroll)
    close = ChunkyButton("Close", style=style)
    content.add_widget(close)
    popup = Popup(title=title, content=content, size_hint=(0.92, 0.88),
                  background="", title_size=sp(18), title_color=style[1],
                  separator_color=style[0], overlay_color=(0, 0, 0, 0.5),
                  background_color=(1, 0.94, 0.94, 1) if urgent else (1, 1, 1, 1))
    close.bind(on_release=popup.dismiss)
    popup.bind(on_open=lambda *_: mascot.pop())
    popup.open()


def top_bar(screen, title, mood="happy"):
    bar = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(10))
    back = ChunkyButton("Back", style=WHITE, size_hint_x=None, width=dp(88))
    back.bind(on_release=lambda *_: setattr(screen.manager, "current", "home"))
    bar.add_widget(back)
    bar.add_widget(Label(text=title, bold=True, font_size=sp(18), color=TEXT))
    bar.mascot = Mascot(mood=mood, full=dp(52))
    bar.add_widget(bar.mascot)
    return bar


def engine():
    return App.get_running_app().engine


# ---------- screens ----------

class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="home", **kwargs)
        scroll, box = scroll_box()
        box.padding = dp(16)
        self.mascot = TapMascot(mood="happy", full=dp(140), pos_hint={"center_x": 0.5})
        box.add_widget(self.mascot)
        box.add_widget(Label(text=core.APP_NAME, bold=True, font_size=sp(30),
                             color=GREEN[1], size_hint_y=None, height=dp(44)))
        box.add_widget(wrapped_label(core.TAGLINE, color=MUTED, halign="center"))
        box.add_widget(ChunkyButton("Ask a health question", style=GREEN,
                                    on_release=lambda *_: self.go("chat")))
        box.add_widget(ChunkyButton("Check my symptoms", style=BLUE,
                                    on_release=lambda *_: self.go("symptoms")))
        box.add_widget(ChunkyButton("Free hygiene tips", style=YELLOW,
                                    on_release=lambda *_: self.go("hygiene")))
        box.add_widget(ChunkyButton("I feel better today", style=PURPLE,
                                    on_release=lambda *_: self.better()))
        box.add_widget(ChunkyButton("Tip of the day", style=WHITE,
                                    on_release=lambda *_: self.tip()))
        box.add_widget(ChunkyButton("Update content (needs internet)", style=WHITE,
                                    on_release=lambda *_: self.update()))
        self.version_label = Label(font_size=sp(13), color=MUTED, size_hint_y=None, height=dp(24))
        box.add_widget(self.version_label)
        box.add_widget(wrapped_label(core.DISCLAIMER, font_size=sp(13), color=MUTED,
                                     halign="center"))
        self.add_widget(scroll)

    def on_pre_enter(self, *args):
        self.version_label.text = "Content version " + str(engine().version)
        self.mascot.set_mood("happy")

    def go(self, name):
        self.manager.current = name

    def better(self):
        self.mascot.set_mood("celebrate")
        celebrate()
        show_popup("Good news", core.RECOVERY_MESSAGE, mood="celebrate")

    def tip(self):
        topic, tip = engine().random_tip()
        self.mascot.set_mood("wink")
        show_popup("Tip of the day", topic + "\n\n" + tip, mood="wink")

    def update(self):
        self.version_label.text = "Checking for updates..."
        self.mascot.set_mood("thinking")

        def work():
            _, message = engine().update()
            Clock.schedule_once(lambda dt: self.update_done(message))

        threading.Thread(target=work, daemon=True).start()

    def update_done(self, message):
        self.version_label.text = "Content version " + str(engine().version)
        self.mascot.set_mood("happy")
        show_popup("Update", message)


class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="chat", **kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
        self.bar = top_bar(self, "Ask a health question", mood="happy")
        root.add_widget(self.bar)
        self.scroll, self.box = scroll_box()
        root.add_widget(self.scroll)
        row = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8))
        self.input = field(hint_text="Type your question", multiline=False)
        self.input.bind(on_text_validate=lambda *_: self.send())
        send = ChunkyButton("Send", style=GREEN, size_hint_x=None, width=dp(88))
        send.bind(on_release=lambda *_: self.send())
        row.add_widget(self.input)
        row.add_widget(send)
        root.add_widget(row)
        self.add_widget(root)
        self.say("Hi, I am Pseudo Clinic. Ask me about a symptom or a hygiene question. "
                 "I only answer from checked content stored on this phone, and I cannot "
                 "diagnose you.")

    def on_pre_enter(self, *args):
        self.bar.mascot.set_mood("happy")

    def say(self, text, mine=False, mood="happy"):
        bubble = Bubble(text, mine=mine)
        bubble.size_hint_x = 0.85
        row = BoxLayout(size_hint_y=None, spacing=dp(6))
        row.height = max(bubble.height, dp(48))
        bubble.bind(height=lambda inst, h: setattr(row, "height", max(h, dp(48))))
        if mine:
            row.add_widget(Widget(size_hint_x=0.15))
            row.add_widget(bubble)
        else:
            holder = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(44))
            avatar = Mascot(mood=mood, full=dp(40))
            holder.add_widget(avatar)
            holder.add_widget(Widget())
            row.add_widget(holder)
            row.add_widget(bubble)
            row.add_widget(Widget(size_hint_x=0.15))
            avatar.pop()
        self.box.add_widget(row)
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.15)

    def send(self):
        text = self.input.text.strip()
        if not text:
            return
        self.input.text = ""
        self.say(text, mine=True)
        reply, mood = engine().respond(text)
        self.say(reply, mood=mood)
        self.bar.mascot.set_mood(mood)
        if mood == "celebrate":
            celebrate()


class SymptomsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="symptoms", **kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
        self.bar = top_bar(self, "Check my symptoms", mood="thinking")
        root.add_widget(self.bar)
        scroll, box = scroll_box()
        self.desc = field(hint_text="Describe what you feel", size_hint_y=None, height=dp(110))
        self.days = field(hint_text="How many days? (0 if just started)", multiline=False,
                          input_filter="int", size_hint_y=None, height=dp(52))
        self.fever = ChunkyToggle("Fever or feeling very hot", self.refresh_mood)
        self.worse = ChunkyToggle("Getting worse", self.refresh_mood)
        self.risk = ChunkyToggle("For a child under 5, pregnant woman, or over 60",
                                 self.refresh_mood)
        for widget in (self.desc, self.days, self.fever, self.worse, self.risk):
            box.add_widget(widget)
        box.add_widget(ChunkyButton("Check", style=GREEN, on_release=lambda *_: self.check()))
        root.add_widget(scroll)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.refresh_mood()

    def refresh_mood(self):
        concerned = self.fever.active or self.worse.active
        self.bar.mascot.set_mood("worried" if concerned else "thinking")

    def check(self):
        text = self.desc.text.strip()
        if not text:
            show_popup("Symptom check", "Please describe what you feel first.", mood="thinking")
            return
        try:
            days = max(0, int(self.days.text or 0))
        except ValueError:
            days = 0
        urgent, reasons = engine().assess(
            text, days, self.fever.active, self.worse.active, self.risk.active)
        if urgent:
            caring = urgent == core.SELF_HARM_MESSAGE
            mood = "caring" if caring else "alarmed"
            self.bar.mascot.set_mood(mood)
            show_popup("Urgent", urgent, kind="info" if caring else "urgent", mood=mood)
            return
        mood = "worried" if reasons else "happy"
        self.bar.mascot.set_mood(mood)
        topic, tip = engine().random_tip()
        show_popup("Symptom check",
                   core.format_assessment(reasons) + "\n\nFree hygiene tip (" + topic + "): " + tip,
                   mood=mood)


class HygieneScreen(Screen):
    STYLES = [GREEN, BLUE, YELLOW]

    def __init__(self, **kwargs):
        super().__init__(name="hygiene", **kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
        self.bar = top_bar(self, "Free hygiene tips", mood="wink")
        root.add_widget(self.bar)
        self.scroll, self.box = scroll_box()
        root.add_widget(self.scroll)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.bar.mascot.set_mood("wink")
        self.box.clear_widgets()  # rebuilt each time so updated content shows up
        for i, topic in enumerate(engine().topics()):
            button = ChunkyButton(topic, style=self.STYLES[i % len(self.STYLES)])
            button.bind(on_release=lambda *_, t=topic: self.open_topic(t))
            self.box.add_widget(button)

    def open_topic(self, topic):
        show_popup(topic, core.format_tips(topic, engine().tips(topic)), mood="happy")


# ---------- app ----------

class PseudoClinicApp(App):
    title = core.APP_NAME
    icon = os.path.join(HERE, "mascot.png")

    def build(self):
        self.engine = core.Engine(os.path.join(HERE, "content.json"),
                                  self.user_data_dir, core.CONTENT_URL)
        self.sm = ScreenManager()
        for screen in (HomeScreen(), ChatScreen(), SymptomsScreen(), HygieneScreen()):
            self.sm.add_widget(screen)
        self.confetti = Confetti()
        root = FloatLayout()
        root.add_widget(self.sm)
        root.add_widget(self.confetti)  # on top, so confetti falls over every screen
        Window.bind(on_keyboard=self.on_key)
        if core.CONTENT_URL:  # quiet update check in the background
            threading.Thread(target=self.engine.update, daemon=True).start()
        return root

    def on_key(self, window, key, *args):
        if key == 27 and self.sm.current != "home":  # Android back button
            self.sm.current = "home"
            return True
        return False


if __name__ == "__main__":
    PseudoClinicApp().run()
