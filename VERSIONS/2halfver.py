import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt

class TrollWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # Настройка окна
        self.setWindowTitle("Упс!")
        self.setMinimumSize(400, 150)

        # Создание лейбла с текстом (используем HTML для переноса строки и стилизации)
        label = QLabel(
            "Ля ты крыса :)\n"
            "Думал так просто получить исходники?"
        )
        
        # Выравнивание текста по центру
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Немного увеличим шрифт, чтобы читалось чётко
        font = label.font()
        font.setPointSize(14)
        font.setBold(True)
        label.setFont(font)

        # Слой для центрирования виджета в окне
        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TrollWindow()
    window.show()
    sys.exit(app.exec())
