import os
import subprocess
import sys

def main():
    print("========================================")
    print("🚀 AMEVA-WoL Auto-Runner (run.py)")
    print("========================================")
    
    script_name = "start_bot.sh"
    
    # 1. 파일 실행 권한 부여
    print(f"[*] 권한 부여 중... (chmod +x {script_name})")
    os.system(f"chmod +x {script_name}")
    
    # 2. 쉘 스크립트 실행
    print(f"[*] {script_name} 실행 중...\n")
    try:
        # Popen을 사용하여 쉘 스크립트로 제어권을 완전히 넘깁니다.
        sys.exit(subprocess.call(["./" + script_name]))
    except KeyboardInterrupt:
        print("\n[INFO] 사용자가 종료했습니다. (Ctrl+C) 안전하게 종료됩니다. 👋")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] 실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
