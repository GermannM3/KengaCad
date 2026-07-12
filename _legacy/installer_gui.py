"""
Простой установщик для KengaCAD
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk, filedialog


class KengaCADInstaller:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_ui()
        
    def setup_ui(self):
        self.root.title("Установка KengaCAD")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # Заголовок
        title_label = tk.Label(self.root, text="Установка KengaCAD", font=("Arial", 16, "bold"))
        title_label.pack(pady=20)
        
        # Описание
        desc_label = tk.Label(self.root, text="CAD-программа для настройки траекторий роботов", font=("Arial", 10))
        desc_label.pack()
        
        # Путь установки
        install_frame = tk.Frame(self.root)
        install_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(install_frame, text="Папка установки:").pack(anchor=tk.W)
        
        path_frame = tk.Frame(install_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        self.install_path_var = tk.StringVar(value=os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "KengaCAD"))
        self.path_entry = tk.Entry(path_frame, textvariable=self.install_path_var)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_btn = tk.Button(path_frame, text="Обзор...", command=self.browse_folder)
        browse_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Компоненты для установки
        components_frame = tk.LabelFrame(self.root, text="Компоненты для установки")
        components_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.install_main_var = tk.BooleanVar(value=True)
        main_check = tk.Checkbutton(components_frame, text="Основное приложение (обязательно)", 
                                   variable=self.install_main_var, state=tk.DISABLED)
        main_check.pack(anchor=tk.W, padx=10, pady=5)
        
        self.install_docs_var = tk.BooleanVar(value=True)
        docs_check = tk.Checkbutton(components_frame, text="Документация", variable=self.install_docs_var)
        docs_check.pack(anchor=tk.W, padx=10, pady=5)
        
        self.install_examples_var = tk.BooleanVar(value=True)
        examples_check = tk.Checkbutton(components_frame, text="Примеры", variable=self.install_examples_var)
        examples_check.pack(anchor=tk.W, padx=10, pady=5)
        
        # Прогресс бар
        self.progress = ttk.Progressbar(self.root, mode='determinate')
        self.progress.pack(fill=tk.X, padx=20, pady=10)
        
        # Статус
        self.status_var = tk.StringVar(value="Готов к установке")
        self.status_label = tk.Label(self.root, textvariable=self.status_var)
        self.status_label.pack(pady=5)
        
        # Кнопки
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=20, pady=20)
        
        install_btn = tk.Button(button_frame, text="Установить", command=self.install, bg="#4CAF50", fg="white")
        install_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        cancel_btn = tk.Button(button_frame, text="Отмена", command=self.root.destroy)
        cancel_btn.pack(side=tk.RIGHT)
    
    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.install_path_var.get())
        if folder:
            self.install_path_var.set(folder)
    
    def install(self):
        install_path = Path(self.install_path_var.get())
        
        # Проверяем права администратора
        if not self.check_admin_rights():
            messagebox.showerror("Ошибка", "Установка требует прав администратора. Запустите от имени администратора.")
            return
        
        # Создаем директорию установки
        try:
            install_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            messagebox.showerror("Ошибка", f"Нет прав на запись в {install_path}. Выберите другую директорию.")
            return
        
        # Копируем файлы
        self.status_var.set("Копирование файлов...")
        self.root.update()
        
        try:
            # Копируем исполняемый файл
            exe_src = Path("dist") / "KengaCAD.exe"
            if exe_src.exists():
                exe_dst = install_path / "KengaCAD.exe"
                shutil.copy2(exe_src, exe_dst)
                
                # Копируем зависимости
                if Path("dist").exists():
                    for item in Path("dist").iterdir():
                        if item.name != "KengaCAD.exe":  # Не копируем сам exe файл снова
                            dst_item = install_path / item.name
                            if item.is_dir():
                                if dst_item.exists():
                                    shutil.rmtree(dst_item)
                                shutil.copytree(item, dst_item)
                            else:
                                shutil.copy2(item, dst_item)
            
            # Копируем документацию
            if self.install_docs_var.get():
                docs_dir = install_path / "docs"
                docs_dir.mkdir(exist_ok=True)
                for doc_file in ["README.md", "docs/INSTALL.md", "COMMAND_REFERENCE.md", "API_DOCS.md"]:
                    if Path(doc_file).exists():
                        shutil.copy2(doc_file, docs_dir / doc_file)
            
            # Копируем примеры
            if self.install_examples_var.get():
                examples_dir = install_path / "examples"
                examples_dir.mkdir(exist_ok=True)
                if Path("examples").exists():
                    for example_file in Path("examples").iterdir():
                        if example_file.is_file():
                            shutil.copy2(example_file, examples_dir / example_file.name)
            
            # Создаем ярлыки
            self.create_shortcuts(install_path)
            
            # Регистрируем в системе
            self.register_application(install_path)
            
            self.status_var.set("Установка завершена!")
            messagebox.showinfo("Установка завершена", f"KengaCAD успешно установлен в {install_path}")
            
        except Exception as e:
            messagebox.showerror("Ошибка установки", f"Произошла ошибка при установке:\n{str(e)}")
            self.status_var.set("Ошибка установки")
    
    def check_admin_rights(self):
        """Проверка прав администратора"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def create_shortcuts(self, install_path):
        """Создание ярлыков"""
        try:
            import ctypes.wintypes
            
            # Создаем ярлык в меню "Пуск"
            startup_menu = Path(os.environ["ProgramData"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "KengaCAD"
            startup_menu.mkdir(parents=True, exist_ok=True)
            
            # Создаем ярлык на рабочем столе
            desktop_path = Path(os.environ["USERPROFILE"]) / "Desktop"
            self.create_lnk(str(install_path / "KengaCAD.exe"), 
                           str(desktop_path / "KengaCAD.lnk"), 
                           "KengaCAD - CAD-программа для настройки траекторий роботов")
            
        except Exception as e:
            print(f"Ошибка при создании ярлыков: {e}")
    
    def create_lnk(self, target, link_path, description):
        """Создание ярлыка (упрощенная версия)"""
        # В реальном приложении использовался бы winshell или pywin32
        # Для демонстрации просто создадим текстовый файл
        with open(link_path, 'w') as f:
            f.write(f"Target: {target}\nDescription: {description}")
    
    def register_application(self, install_path):
        """Регистрация приложения в системе"""
        try:
            import winreg
            
            # Регистрируем в реестре для деинсталляции
            key_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KengaCAD"
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "KengaCAD")
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, 
                                 f'"{install_path}\\uninstall.exe"')
                winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, 
                                 f"{install_path}\\KengaCAD.exe,0")
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "KengaCAD Team")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
                winreg.SetValueEx(key, "URLInfoAbout", 0, winreg.REG_SZ, 
                                 "https://github.com/GermannM3/KengaCAD")
                
        except Exception as e:
            print(f"Ошибка при регистрации в реестре: {e}")
    
    def run(self):
        self.root.mainloop()


def main():
    installer = KengaCADInstaller()
    installer.run()


if __name__ == "__main__":
    main()