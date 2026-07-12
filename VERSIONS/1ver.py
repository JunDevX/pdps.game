import sys
import os
import random
import requests
import zipfile

# --- ФИКС ИКОНКИ НА ПАНЕЛИ ЗАДАЧ WINDOWS ---
if sys.platform == "win32":
    import ctypes
    myappid = "zapl.pixeldash.launcher.1.0"  # Уникальный ID приложения
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
# ------------------------------------------

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QUrl
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QStackedWidget, 
                             QProgressBar, QGraphicsDropShadowEffect, QTextBrowser)
from PyQt6.QtGui import QDesktopServices, QColor, QFont, QIcon

# Настройки приложения
CURRENT_VERSION = "1.0.0"
REPO_RELEASES_URL = "https://api.github.com/repos/JunDevX/pdps.game/releases/latest"
CHANGELOG_BASE_URL = "https://raw.githubusercontent.com/JunDevX/pdps.game/main/CHANGELOG/"
DROPBOX_ZIP_URL = "https://www.dropbox.com/scl/fi/vx0uiefw1xqh7ygiv18fj/Pixel-Dash.zip?rlkey=x5f66q9ng01kfgugq2bx251up&st=g5b7mheb&dl=1"
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), "Pixel Dash")

class LoadingWorker(QObject):
    finished = pyqtSignal(dict)
    phrase_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.phrases = [
            "Привет! Давай поиграем?",
            "Готов к строительству?",
            "Как дела?",
            "Сверяем контрольные суммы...",
            "Проверяем наличие обновлений...",
            "Подключаемся к репозиторию...",
            "Инициализация Pixel Dash...",
            "Проверка файлов игры..."
        ]

    def run(self):
        result = {
            "update_type": "none", 
            "version": CURRENT_VERSION, 
            "changelog": "История изменений пуста.",
            "game_installed": False
        }
        
        # Имитация загрузки (~4.5 секунды)
        used_phrases = random.sample(self.phrases, min(6, len(self.phrases)))
        for phrase in used_phrases:
            self.phrase_changed.emit(phrase)
            QThread.msleep(750)

        # 1. Проверяем наличие установленных файлов игры (ищем конкретный exe)
        game_exe_path = os.path.join(APPDATA_DIR, "Pixel Dash", "GeometryDash.exe")
        if os.path.exists(game_exe_path):
            result["game_installed"] = True

        # 2. Проверка обновлений через GitHub API
        try:
            response = requests.get(REPO_RELEASES_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", CURRENT_VERSION).replace("v", "").replace("V", "")
                
                if latest_version != CURRENT_VERSION:
                    curr_parts = list(map(int, CURRENT_VERSION.split('.')))
                    late_parts = list(map(int, latest_version.split('.')))
                    
                    if late_parts[0] > curr_parts[0] or late_parts[1] > curr_parts[1]:
                        result["update_type"] = "critical"
                    elif late_parts[2] > curr_parts[2]:
                        result["update_type"] = "fix"
                    
                    result["version"] = latest_version
                    result["html_url"] = data.get("html_url", "https://github.com/JunDevX/pdps.game/releases")
        except Exception:
            pass

        # 3. Получение Changelog с гитхаба (ищет .md файлы для Markdown)
        try:
            ver_to_fetch = result["version"]
            changelog_url = f"{CHANGELOG_BASE_URL}v{ver_to_fetch}.md"
            ch_res = requests.get(changelog_url, timeout=5)
            if ch_res.status_code == 200:
                result["changelog"] = ch_res.text
            else:
                changelog_url = f"{CHANGELOG_BASE_URL}{ver_to_fetch}.md"
                ch_res = requests.get(changelog_url, timeout=5)
                if ch_res.status_code == 200:
                    result["changelog"] = ch_res.text
                else:
                    result["changelog"] = f"### Обновление v{ver_to_fetch}\nИнформации об изменениях пока нет."
        except Exception:
            result["changelog"] = "Не удалось загрузить список изменений (проверьте сеть)."

        self.finished.emit(result)


class DownloaderWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def run(self):
        try:
            if not os.path.exists(APPDATA_DIR):
                os.makedirs(APPDATA_DIR)

            zip_path = os.path.join(APPDATA_DIR, "update.zip")
            
            response = requests.get(DROPBOX_ZIP_URL, stream=True, timeout=15)
            total_length = response.headers.get('content-length')

            if total_length is None:
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                with open(zip_path, 'wb') as f:
                    for data in response.iter_content(chunk_size=4096):
                        dl += len(data)
                        f.write(data)
                        done = int(70 * dl / total_length)
                        self.progress.emit(done)

            self.progress.emit(80)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(APPDATA_DIR)
            
            os.remove(zip_path)
            self.progress.emit(100)
            self.finished.emit(True, "Установка успешно завершена!")
        except Exception as e:
            self.finished.emit(False, f"**Ошибка при установке:**\n{str(e)}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Прямоугольная горизонтальная форма
        self.resize(750, 420)
        
        # Установка иконки для окна приложения
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))

        self.old_pos = None
        self.app_data_status = {}

        # Жирные красивые шрифты и CSS стили
        self.main_style = """
            QWidget#MainContainer {
                background-color: rgba(22, 22, 26, 0.55);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 14px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: bold;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 900;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            
            /* Стили для текстового поля с поддержкой Markdown */
            QTextBrowser {
                background-color: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.85);
                font-size: 13px;
                font-weight: 600;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            /* Красивый скроллбар для списка изменений */
            QScrollBar:vertical {
                border: none;
                background: rgba(255, 255, 255, 0.05);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """

        self.init_ui()
        self.start_loading_thread()

    def init_ui(self):
        self.container = QWidget()
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet(self.main_style)
        self.setCentralWidget(self.container)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 0)
        self.container.setGraphicsEffect(shadow)

        self.root_layout = QVBoxLayout(self.container)
        self.root_layout.setContentsMargins(20, 15, 20, 20)

        # Шапка
        header_layout = QHBoxLayout()
        self.version_label = QLabel("Версия 1.0.0")
        self.version_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 13px; font-weight: 800;")
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton { background: transparent; color: rgba(255,255,255,0.6); font-size: 14px; border-radius: 15px; padding: 0; }
            QPushButton:hover { background: rgba(239, 83, 80, 0.8); color: white; }
        """)
        close_btn.clicked.connect(self.close)
        
        header_layout.addWidget(self.version_label)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        self.root_layout.addLayout(header_layout)

        self.stacked_widget = QStackedWidget()
        self.root_layout.addWidget(self.stacked_widget)

        # 1. ЭКРАН ЗАГРУЗКИ
        self.loading_page = QWidget()
        loading_layout = QVBoxLayout(self.loading_page)
        loading_layout.addStretch()
        
        self.spinner_label = QLabel("PIXEL DASH")
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner_label.setStyleSheet("font-size: 38px; font-weight: 900; letter-spacing: 4px; color: #ffffff;")
        loading_layout.addWidget(self.spinner_label)

        self.phrase_label = QLabel("Загрузка...")
        self.phrase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.phrase_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 16px; font-weight: 700; margin-top: 12px;")
        loading_layout.addWidget(self.phrase_label)
        loading_layout.addStretch()
        
        self.stacked_widget.addWidget(self.loading_page)

        # 2. ГЛАВНЫЙ ЭКРАН
        self.main_page = QWidget()
        main_layout = QHBoxLayout(self.main_page)
        main_layout.setContentsMargins(0, 5, 0, 0)
        main_layout.setSpacing(20)

        left_block = QWidget()
        left_layout = QVBoxLayout(left_block)
        left_layout.setContentsMargins(0,0,0,0)
        
        gdps_title = QLabel("Pixel Dash GDPS")
        gdps_title.setStyleSheet("font-size: 26px; font-weight: 900; color: #ffffff;")
        
        gdps_desc = QLabel("Добро пожаловать в приватный сервер Geometry Dash! Оцени кастомные уровни, соревнуйся с другими игроками в топе и создавай свои шедевры без ограничений.")
        gdps_desc.setWordWrap(True)
        gdps_desc.setStyleSheet("color: rgba(255,255,255,0.75); font-size: 14px; font-weight: 600; line-height: 20px;")
        
        self.install_btn = QPushButton("Установить")
        self.install_btn.setFixedHeight(45)
        self.install_btn.clicked.connect(self.start_installation)

        self.p_bar = QProgressBar()
        self.p_bar.setStyleSheet("""
            QProgressBar { border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; text-align: center; color: white; background: rgba(0,0,0,0.4); font-weight: bold; }
            QProgressBar::chunk { background-color: #2196F3; border-radius: 5px; }
        """)
        self.p_bar.setVisible(False)

        left_layout.addWidget(gdps_title)
        left_layout.addSpacing(10)
        left_layout.addWidget(gdps_desc)
        left_layout.addStretch()
        left_layout.addWidget(self.p_bar)
        left_layout.addWidget(self.install_btn)
        
        right_block = QWidget()
        right_block.setStyleSheet("background: rgba(0,0,0,0.25); border-radius: 10px; border: 1px solid rgba(255,255,255,0.06);")
        right_layout = QVBoxLayout(right_block)
        right_layout.setContentsMargins(15, 15, 5, 15)
        
        ch_title = QLabel("ЧТО НОВОГО:")
        ch_title.setStyleSheet("font-weight: 900; font-size: 14px; color: #2196F3; letter-spacing: 1px;")
        
        # Используем QTextBrowser для поддержки Markdown
        self.ch_text = QTextBrowser()
        self.ch_text.setOpenExternalLinks(True)
        self.ch_text.setMarkdown("Синхронизация патчноутов...")
        
        right_layout.addWidget(ch_title)
        right_layout.addSpacing(8)
        right_layout.addWidget(self.ch_text, 1)

        main_layout.addWidget(left_block, 4)
        main_layout.addWidget(right_block, 3)
        self.stacked_widget.addWidget(self.main_page)

        # 3. ЭКРАН С ПОДПИСКОЙ
        self.social_page = QWidget()
        social_layout = QVBoxLayout(self.social_page)
        social_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        thanks_lbl = QLabel("Спасибо что выбрали нас!")
        thanks_lbl.setStyleSheet("font-size: 26px; font-weight: 900; color: #4CAF50;")
        thanks_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        sub_lbl = QLabel("Подпишитесь, чтобы узнавать об обновлениях")
        sub_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: rgba(255,255,255,0.8); margin-bottom: 20px;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        discord_btn = QPushButton("  Присоединиться к Discord")
        discord_btn.setFixedSize(260, 48)
        discord_btn.setStyleSheet("""
            QPushButton { background-color: #5865F2; font-size: 15px; font-weight: 800; border-radius: 8px; }
            QPushButton:hover { background-color: #4752C4; }
        """)
        discord_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://discord.gg/Fuqm8RmWHz")))

        skip_btn = QPushButton("Пропустить")
        skip_btn.setFixedSize(110, 32)
        skip_btn.setStyleSheet("""
            QPushButton { background: transparent; color: rgba(255,255,255,0.5); font-size: 13px; font-weight: 700; border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; }
            QPushButton:hover { background: rgba(255,255,255,0.1); color: white; }
        """)
        skip_btn.clicked.connect(self.go_to_play_state)

        social_layout.addWidget(thanks_lbl)
        social_layout.addWidget(sub_lbl)
        social_layout.addWidget(discord_btn, 0, Qt.AlignmentFlag.AlignCenter)
        social_layout.addSpacing(25)
        social_layout.addWidget(skip_btn, 0, Qt.AlignmentFlag.AlignCenter)
        self.stacked_widget.addWidget(self.social_page)

    def start_loading_thread(self):
        self.loading_thread = QThread()
        self.worker = LoadingWorker()
        self.worker.moveToThread(self.loading_thread)
        
        self.loading_thread.started.connect(self.worker.run)
        self.worker.phrase_changed.connect(self.update_loading_phrase)
        self.worker.finished.connect(self.on_loading_finished)
        
        self.loading_thread.start()

    def update_loading_phrase(self, text):
        self.phrase_label.setText(text)

    def on_loading_finished(self, data):
        self.loading_thread.quit()
        self.ch_text.setMarkdown(data["changelog"])
        self.app_data_status = data
        
        self.stacked_widget.setCurrentWidget(self.main_page)

        if data["update_type"] == "critical":
            self.install_btn.setText("Найдено критическое обновление!")
            self.install_btn.setStyleSheet("background-color: #E53935; font-weight: 900;")
            try: self.install_btn.clicked.disconnect()
            except TypeError: pass
            self.install_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(data["html_url"])))
        elif data["update_type"] == "fix":
            self.install_btn.setText("Обновить")
            self.install_btn.setStyleSheet("background-color: #FF9800; font-weight: 900;")
        else:
            if data["game_installed"]:
                self.set_btn_to_play()
            else:
                self.install_btn.setText("Установить")
                self.install_btn.setStyleSheet("background-color: #2196F3; font-weight: 900;")

    def start_installation(self):
        if self.install_btn.text() == "Играть":
            self.launch_game_process()
            return

        self.install_btn.setEnabled(False)
        self.p_bar.setVisible(True)
        self.p_bar.setValue(0)

        self.download_thread = QThread()
        self.downloader = DownloaderWorker()
        self.downloader.moveToThread(self.download_thread)

        self.download_thread.started.connect(self.downloader.run)
        self.downloader.progress.connect(self.p_bar.setValue)
        self.downloader.finished.connect(self.on_installation_finished)

        self.download_thread.start()

    def on_installation_finished(self, success, message):
        self.download_thread.quit()
        self.p_bar.setVisible(False)
        self.install_btn.setEnabled(True)
        
        if success:
            self.stacked_widget.setCurrentWidget(self.social_page)
        else:
            self.ch_text.setMarkdown(message)

    def go_to_play_state(self):
        self.set_btn_to_play()
        self.stacked_widget.setCurrentWidget(self.main_page)

    def set_btn_to_play(self):
        self.install_btn.setText("Играть")
        self.install_btn.setStyleSheet("background-color: #4CAF50; font-weight: 900; color: white;")
        try: self.install_btn.clicked.disconnect()
        except TypeError: pass
        self.install_btn.clicked.connect(self.start_installation)

    def launch_game_process(self):
        # Точный путь к GeometryDash.exe внутри структуры папок
        game_exe_path = os.path.join(APPDATA_DIR, "Pixel Dash", "GeometryDash.exe")
        
        if os.path.exists(game_exe_path):
            # Переключаем рабочую папку лаунчера на папку с игрой, чтобы подхватились DLL и ресурсы
            working_dir = os.path.dirname(game_exe_path)
            os.chdir(working_dir)
            
            # Запуск игры
            os.startfile(game_exe_path)
        else:
            # Запасной вариант: если exe не найден, просто открываем корневую папку AppData
            if os.path.exists(APPDATA_DIR):
                os.startfile(APPDATA_DIR)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
