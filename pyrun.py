"""더블클릭(또는 .py 파일 연결 프로그램)으로 실행되는 범용 파이썬 런처.

대상 .py 파일 경로를 argv[1] 로 받아 실행한다. 대상 스크립트는 절대 수정하지 않는다.
PyInstaller로 PyRun.exe 빌드해서 배포 (build_exe.bat 참고).
"""
import os
import re
import shlex
import subprocess
import sys

if sys.platform == "win32":
    # exe로 직접 실행될 때(파일 연결 등)는 .cmd 래퍼의 chcp/PYTHONIOENCODING 설정이 없으므로
    # 콘솔 코드페이지를 직접 UTF-8로 맞춰준다. 안 해주면 한글 출력이 시스템 로캘에 따라 깨짐.
    import ctypes
    try:
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# ponytail: import 이름과 pip 패키지 이름이 다른 흔한 경우만 커버. 새 사례 나오면 여기 추가.
PIP_NAME_ALIASES = {
    "cv2": "opencv-python",
    "PIL": "pillow",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
    "dotenv": "python-dotenv",
    "win32com": "pywin32",
    "win32api": "pywin32",
    "serial": "pyserial",
}

MODULE_NOT_FOUND_RE = re.compile(r"No module named '([\w.\-]+)'")

# ponytail: pkg_resources 버전충돌 예외("Requirement.parse('numpy>=2.0')")와
# pip resolver 경고("X requires numpy<3.0,>=2.0, but you have...") 두 형태만 커버.
# 순수 런타임 AttributeError 같은 버전 이슈는 패턴이 제각각이라 범위 밖.
VERSION_CONFLICT_RE = re.compile(
    r"(?:Requirement\.parse\(['\"]|requires\s+)"
    r"([A-Za-z][\w.\-]*)\s*"
    r"([<>=!~]=?\s*[\w.\-]+(?:\s*,\s*[<>=!~]=?\s*[\w.\-]+)*)"
)

# 자식 파이썬 프로세스의 stdout/stderr 인코딩을 시스템 로캘(cp949 등)과 무관하게 고정.
CHILD_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def find_python():
    for cmd in (["py", "-3"], ["python"], ["python3"]):
        try:
            subprocess.run(cmd + ["--version"], capture_output=True, check=True)
            return cmd
        except Exception:
            continue
    return None


def pip_install(python_cmd, packages):
    if not packages:
        return
    subprocess.run(python_cmd + ["-m", "pip", "install", "--quiet",
                                  "--disable-pip-version-check", *packages], env=CHILD_ENV)


def resolve_missing_module(stderr_text):
    """stderr 에서 누락 모듈 이름 찾아 pip 패키지명으로 변환. 없으면 None."""
    m = MODULE_NOT_FOUND_RE.search(stderr_text or "")
    if not m:
        return None
    mod = m.group(1).split(".")[0]
    return PIP_NAME_ALIASES.get(mod, mod), m.group(1)


def resolve_version_conflict(stderr_text):
    """stderr 에서 버전 충돌(pkg_resources/pip resolver) 찾아 (패키지, 버전조건) 반환. 없으면 None."""
    m = VERSION_CONFLICT_RE.search(stderr_text or "")
    if not m:
        return None
    pkg = m.group(1)
    spec = re.sub(r"\s+", "", m.group(2))
    return pkg, spec


def get_help_text(python_cmd, script):
    try:
        r = subprocess.run(python_cmd + [script, "--help"], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=10,
                            env=CHILD_ENV)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
    except Exception:
        pass
    return None


def run_script(python_cmd, script, args):
    proc = subprocess.Popen(python_cmd + [script, *args], stderr=subprocess.PIPE,
                             stdout=None, text=True, encoding="utf-8", errors="replace",
                             bufsize=1, env=CHILD_ENV)
    stderr_lines = []
    for line in proc.stderr:
        print(line, end="")
        stderr_lines.append(line)
    proc.wait()
    return proc.returncode, "".join(stderr_lines)


def main():
    if len(sys.argv) < 2:
        print("사용법: 실행할 .py 파일을 이 창(또는 PyRun.cmd 아이콘)에 드래그하세요.")
        input("종료하려면 Enter...")
        return

    script = os.path.abspath(sys.argv[1])
    if not os.path.isfile(script):
        print(f"파일을 찾을 수 없습니다: {script}")
        input("종료하려면 Enter...")
        return

    workdir = os.path.dirname(script)
    os.chdir(workdir)

    python_cmd = find_python()
    if not python_cmd:
        print("파이썬이 설치되어 있지 않습니다. https://python.org 에서 설치 후 다시 실행하세요.")
        input("종료하려면 Enter...")
        return

    print(f"[준비] {os.path.basename(script)} 실행 준비 중...\n")

    req = os.path.join(workdir, "requirements.txt")
    if os.path.isfile(req):
        print("[준비] requirements.txt 설치 중...")
        subprocess.run(python_cmd + ["-m", "pip", "install", "--quiet",
                                      "--disable-pip-version-check", "-r", req], env=CHILD_ENV)

    help_text = get_help_text(python_cmd, script)
    if help_text:
        print("\n--- 사용 가능한 옵션 ---")
        print(help_text.rstrip())
        print("------------------------\n")

    try:
        user_input = input("실행 옵션 입력 (그냥 Enter = 기본 실행): ").strip()
    except EOFError:
        user_input = ""
    args = shlex.split(user_input) if user_input else []

    tried = set()
    code = 1
    for _ in range(8):
        print()
        code, err = run_script(python_cmd, script, args)
        if code == 0:
            print("\n[완료] 정상 종료.")
            break
        resolved = resolve_missing_module(err)
        if resolved and resolved[1] not in tried:
            pip_name, raw_name = resolved
            tried.add(raw_name)
            print(f"\n[자동설치] 모듈 '{raw_name}' 없음 → '{pip_name}' 설치 시도...")
            pip_install(python_cmd, [pip_name])
            continue
        conflict = resolve_version_conflict(err)
        if conflict and conflict not in tried:
            pkg, spec = conflict
            tried.add(conflict)
            print(f"\n[버전조정] '{pkg}' 버전 충돌 감지 → '{pkg}{spec}' 로 재설치...")
            pip_install(python_cmd, [f"{pkg}{spec}"])
            continue
        print("\n[오류] 아래 내용을 복사해서 물어보세요:")
        print("=" * 60)
        print(err.strip() or f"(종료 코드 {code})")
        print("=" * 60)
        break
    else:
        print("[오류] 자동 설치를 반복했지만 실패했습니다. 위 오류를 복사해 문의하세요.")

    try:
        input("\n창을 닫으려면 Enter...")
    except EOFError:
        pass


def _selftest():
    assert resolve_missing_module("No module named 'cv2'") == ("opencv-python", "cv2")
    assert resolve_missing_module("No module named 'requests'") == ("requests", "requests")
    assert resolve_missing_module("Traceback...\nValueError: x") is None
    assert resolve_version_conflict(
        "rembg 2.0.81 requires numpy<3.0.0,>=2.3.0, but you have numpy 1.26.4 which is incompatible."
    ) == ("numpy", "<3.0.0,>=2.3.0")
    assert resolve_version_conflict(
        "pkg_resources.ContextualVersionConflict: (numpy 1.26.4 (...), "
        "Requirement.parse('numpy>=2.3.0'), {'rembg'})"
    ) == ("numpy", ">=2.3.0")
    assert resolve_version_conflict("Traceback...\nValueError: x") is None
    print("selftest OK")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    else:
        main()
