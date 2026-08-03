#!/usr/bin/env python3
"""
Мосбиржа Сигналы — Android приложение
Собирает данные по открытому интересу юрлиц и показывает уведомления
"""

import requests
import json
import os
import time
from datetime import datetime, time as dt_time, timedelta
import pytz
from threading import Thread, Event

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.logger import Logger

# === НАСТРОЙКИ ===
JWT_TOKEN = "eyJhbG...NNwQ"

TICKERS = ["NG", "BR", "SV", "GD", "YD", "GZ", "SR", "PD", "CE"]
TICKER_NAMES = {
    "NG": "NG", "BR": "BR", "SV": "SV", "GD": "GD",
    "YD": "YD", "GZ": "GZ", "SR": "SR", "PD": "PD", "CE": "CE"
}

MOSCOW_TZ = pytz.timezone("Europe/Moscow")
BASELINE_FILE = "baseline.json"
STATE_FILE = "state.json"


class MoexEngine:
    """Движок — получает данные с Мосбиржи, ищет сигналы"""

    def __init__(self):
        self.baseline = {}
        self.state = {"date": None, "signals": {}}
        self.stop_event = Event()
        self.on_signal = None  # callback: func(ticker, direction, info)

    # ─── работа с файлами ───

    def _read(self, path, default):
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ERR] read {path}: {e}")
        return default

    def _write(self, path, data):
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[ERR] write {path}: {e}")

    # ─── загрузка / сохранение ───

    def load(self):
        self.baseline = self._read(BASELINE_FILE, {})
        self.state = self._read(STATE_FILE, {"date": None, "signals": {}})
        self._reset_state_if_needed()

    def save_state(self):
        self._write(STATE_FILE, self.state)

    # ─── API Мосбиржи ───

    def get_positions(self, ticker):
        try:
            now = datetime.now(MOSCOW_TZ)
            week_ago = now - timedelta(days=7)
            url = f"https://apim.moex.com/iss/analyticalproducts/futoi/securities/{ticker}.json"
            params = {"from": week_ago.strftime("%Y-%m-%d"), "till": now.strftime("%Y-%m-%d"), "latest": "1"}
            headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
            r = requests.get(url, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            if "futoi" not in data or "data" not in data["futoi"]:
                return None
            cols = data["futoi"]["columns"]
            for row in data["futoi"]["data"]:
                d = dict(zip(cols, row))
                if d.get("clgroup") == "YUR":
                    return {
                        "long": d.get("pos_long", 0),
                        "short": abs(d.get("pos_short", 0)),
                        "date": d.get("tradedate"),
                        "time": d.get("tradetime"),
                    }
        except Exception as e:
            print(f"[ERR] {ticker}: {e}")
        return None

    # ─── baseline ───

    def create_baseline(self):
        print("[BASELINE] создаю…")
        bl = {}
        for t in TICKERS:
            p = self.get_positions(t)
            if p:
                bl[t] = {"long": p["long"], "short": p["short"], "date": p["date"], "time": p["time"]}
        if bl:
            self.baseline = bl
            self._write(BASELINE_FILE, bl)
            print(f"[BASELINE] сохранён для {len(bl)} тикеров")
        else:
            print("[BASELINE] пусто — данные не получены")
        return bl

    def clear_baseline(self):
        self.baseline = {}
        if os.path.exists(BASELINE_FILE):
            os.remove(BASELINE_FILE)
        print("[BASELINE] очищен")

    # ─── состояние ───

    def _reset_state_if_needed(self):
        today = datetime.now(MOSCOW_TZ).strftime("%Y-%m-%d")
        if self.state.get("date") != today:
            self.state = {"date": today, "signals": {}}
            self.save_state()
            print("[STATE] сброшен на новый день")

    # ─── сигналы ───

    def check(self):
        if not self.baseline:
            print("[CHECK] нет baseline — пропускаю")
            return
        self._reset_state_if_needed()
        changed = False
        for t in TICKERS:
            if t not in self.baseline:
                continue
            cur = self.get_positions(t)
            if not cur:
                continue
            sig = self._detect(t, cur)
            if not sig:
                continue
            direction, info = sig
            last = self.state["signals"].get(t)
            if last is None or last.get("direction") != direction:
                print(f"[SIGNAL] {t} {direction}")
                if self.on_signal:
                    self.on_signal(t, direction, info)
                self.state["signals"][t] = {"direction": direction}
                changed = True
        if changed:
            self.save_state()

    def _detect(self, ticker, cur):
        bl = self.baseline.get(ticker)
        if not bl:
            return None
        bl_l, bl_s = bl["long"], bl["short"]
        if bl_l <= 0 or bl_s <= 0:
            return None
        l_ch = (cur["long"] - bl_l) / bl_l * 100
        s_ch = (cur["short"] - bl_s) / bl_s * 100
        if l_ch >= 10 and s_ch <= -5:
            return "LONG", f"LONG: {l_ch:.1f}% / SHORT: {s_ch:.1f}%"
        if s_ch >= 10 and l_ch <= -5:
            return "SHORT", f"SHORT: {s_ch:.1f}% / LONG: {l_ch:.1f}%"
        return None

    # ─── фоновый цикл ───

    def start_loop(self):
        self.stop_event.clear()
        Thread(target=self._loop, daemon=True).start()

    def stop_loop(self):
        self.stop_event.set()

    def _loop(self):
        last_midnight = None
        while not self.stop_event.is_set():
            try:
                now = datetime.now(MOSCOW_TZ)
                today = now.strftime("%Y-%m-%d")
                t = now.time()

                # полночь
                if last_midnight != today and t >= dt_time(0, 0):
                    self.clear_baseline()
                    self._reset_state_if_needed()
                    last_midnight = today

                # 07:00 — baseline
                if t.hour == 7 and t.minute == 0:
                    self.create_baseline()
                    time.sleep(61)
                    continue

                # 09:00–23:59 — проверка каждые 5 мин
                if dt_time(9, 0) <= t <= dt_time(23, 59) and now.minute % 5 == 0 and now.second < 5:
                    self.check()
                    time.sleep(10)
                    continue

                time.sleep(1)
            except Exception as e:
                print(f"[LOOP ERR] {e}")
                time.sleep(5)


class MainLayout(BoxLayout):
    def __init__(self, engine, **kwargs):
        super().__init__(orientation="vertical", padding=12, spacing=10, **kwargs)
        self.engine = engine
        self.engine.on_signal = self._on_signal

        # заголовок
        self.add_widget(Label(text="📊 Мосбиржа Сигналы", font_size="22sp", size_hint=(1, None), height=50))

        # статус
        self.status = Label(text="Статус: остановлен", size_hint=(1, None), height=36)
        self.add_widget(self.status)

        # переключатель
        sw_row = BoxLayout(size_hint=(1, None), height=50, spacing=10)
        sw_row.add_widget(Label(text="Мониторинг:", size_hint=(0.5, 1)))
        self.switch = Switch(active=False)
        self.switch.bind(active=self._toggle)
        sw_row.add_widget(self.switch)
        self.add_widget(sw_row)

        # кнопки
        btn_row = BoxLayout(size_hint=(1, None), height=50, spacing=10)
        b1 = Button(text="Обновить сейчас", on_press=lambda _: self._force())
        b2 = Button(text="Очистить baseline", on_press=lambda _: self._clear())
        btn_row.add_widget(b1)
        btn_row.add_widget(b2)
        self.add_widget(btn_row)

        # лог
        self.add_widget(Label(text="📋 Лог:", size_hint=(1, None), height=30))
        scroll = ScrollView(size_hint=(1, 1))
        self.log_grid = GridLayout(cols=1, size_hint_y=None, spacing=3)
        self.log_grid.bind(minimum_height=self.log_grid.setter("height"))
        scroll.add_widget(self.log_grid)
        self.add_widget(scroll)

        # загружаем данные
        self.engine.load()
        self.log("✅ Приложение загружено")
        self.log(f"📈 Тикеры: {', '.join(TICKERS)}")

    def log(self, text):
        Clock.schedule_once(lambda _: self._add_log(text))

    def _add_log(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        lbl = Label(
            text=f"[{ts}] {text}",
            size_hint_y=None, height=26,
            halign="left", valign="middle",
            text_size=(self.width - 20, None),
        )
        self.log_grid.add_widget(lbl)
        if len(self.log_grid.children) > 80:
            self.log_grid.remove_widget(self.log_grid.children[-1])

    def _toggle(self, _, active):
        if active:
            self.engine.start_loop()
            self.status.text = "Статус: 🟢 работает"
            self.log("▶️ Мониторинг запущен")
            # если baseline пуст — создаём
            if not self.engine.baseline:
                Clock.schedule_once(lambda _: self._create_baseline(), 1)
        else:
            self.engine.stop_loop()
            self.status.text = "Статус: ⏹ остановлен"
            self.log("⏹ Мониторинг остановлен")

    def _create_baseline(self):
        self.log("📥 Создаю baseline…")
        self.engine.create_baseline()
        self.log(f"✅ Baseline: {len(self.engine.baseline)} тикеров")

    def _force(self):
        self.log("🔄 Принудительная проверка…")
        self.engine.check()
        self.log("✅ Проверка завершена")

    def _clear(self):
        self.engine.clear_baseline()
        self.log("🗑️ Baseline очищен")

    def _on_signal(self, ticker, direction, info):
        msg = f"📡 {ticker} — {direction}: {info}"
        self.log(msg)
        # уведомление
        try:
            from plyer import notification
            notification.notify(title=f"{ticker} {direction}", message=info, timeout=10)
        except Exception:
            pass


class MoexApp(App):
    def build(self):
        self.engine = MoexEngine()
        return MainLayout(self.engine)

    def on_stop(self):
        self.engine.stop_loop()


if __name__ == "__main__":
    MoexApp().run()