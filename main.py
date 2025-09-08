import requests
import threading
import time
import json
from datetime import datetime
import sys
import os

class RobloxGroupParser:
    def __init__(self, group_id, threads=1, max_users=None):
        self.group_id = group_id
        self.threads = threads
        self.max_users = max_users
        self.users = set()
        self.lock = threading.Lock()
        self.running = False
        self.processed = 0
        self.current_cursor = None
        self.has_more_pages = True
        self.filename = f"users_{group_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        
    def get_group_users(self, cursor=None):
        url = f"https://groups.roblox.com/v1/groups/{self.group_id}/users"
        params = {
            'sortOrder': 'Asc',
            'limit': 100
        }
        if cursor:
            params['cursor'] = cursor
            
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Ошибка запроса: {e}")
            return None
            
    def parse_single_page(self, cursor=None):
        if not self.running:
            return None
            
        data = self.get_group_users(cursor)
        if not data:
            return None
            
        with self.lock:
            for user in data.get('data', []):
                if 'user' in user and 'username' in user['user']:
                    self.users.add(user['user']['username'])
            self.processed += len(data.get('data', []))
            
        print(f"Обработано участников: {self.processed}", end='\r')

        if self.max_users and len(self.users) >= self.max_users:
            self.running = False
            return None
            
        return data.get('nextPageCursor')
        
    def worker(self):
        while self.running and self.has_more_pages:
            with self.lock:
                current_cursor = self.current_cursor
                if current_cursor is None and not self.has_more_pages:
                    break
                    
            next_cursor = self.parse_single_page(current_cursor)
            
            with self.lock:
                if next_cursor:
                    self.current_cursor = next_cursor
                else:
                    self.has_more_pages = False
                    break
                    
            time.sleep(0.1)
            
    def sequential_parser(self):
        cursor = None
        while self.running and self.has_more_pages:
            next_cursor = self.parse_single_page(cursor)
            
            with self.lock:
                if next_cursor:
                    cursor = next_cursor
                else:
                    self.has_more_pages = False
                    break
                    
            time.sleep(0.1)
            
    def save_results(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            for username in sorted(self.users):
                f.write(f"{username}\n")
        print(f"\nРезультаты сохранены в {self.filename}")
        print(f"Всего найдено уникальных пользователей: {len(self.users)}")
        
    def start(self):
        print(f"Начинаем парсинг группы {self.group_id}")
        print(f"Потоков: {self.threads}")
        if self.max_users:
            print(f"Лимит пользователей: {self.max_users}")
        print(f"Файл для сохранения: {self.filename}")
        print("Для остановки нажмите CTRL+Z")
        
        self.running = True
        self.has_more_pages = True
        self.current_cursor = None
        
        if self.threads > 1:
            threads = []
            for _ in range(self.threads):
                thread = threading.Thread(target=self.worker)
                thread.daemon = True
                thread.start()
                threads.append(thread)

            try:
                while self.running and self.has_more_pages:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\nПрервано пользователем")
                self.running = False
                
            for thread in threads:
                thread.join(timeout=1.0)
        else:
            try:
                self.sequential_parser()
            except KeyboardInterrupt:
                print("\nПрервано пользователем")
                self.running = False
                
        self.save_results()
        
    def stop(self):
        print("\nОстанавливаемся...")
        self.running = False
        self.has_more_pages = False

def main():
    global parser
    
    print("=== RoParse Username ===")
    
    try:
        group_id = input("Введите ID группы: ").strip()
        if not group_id.isdigit():
            print("ID группы должен быть числом!")
            return
        
        max_users = input("Введите количество пользователей для сбора (оставьте пустым для сбора всех): ").strip()
        max_users = int(max_users) if max_users.isdigit() else None

        threads = input("Введите количество потоков (по умолчанию 1): ").strip()
        threads = int(threads) if threads.isdigit() and int(threads) > 0 else 1

        if threads > 1:
            print("Внимание: многопоточность может вызвать проблемы с пагинацией!")
            print("Рекомендуется использовать 1 поток для стабильной работы.")
            time.sleep(2)
        
        parser = RobloxGroupParser(group_id, threads, max_users)
        parser.start()
        
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    parser = None
    main()