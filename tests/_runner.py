import io
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

SUITES = [
    "test_theme",
    "test_preview",
    "test_dashboard",
    "test_first_launch",
    "test_core",
    "test_appshell",
]

out = []
for name in SUITES:
    buf = io.StringIO()
    try:
        mod = __import__(name)
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.main()
            ok = True
        except SystemExit as e:
            ok = e.code in (None, 0)
        except Exception:  # noqa: BLE001
            traceback.print_exc(file=buf)
            ok = False
        finally:
            sys.stdout = old
    except Exception:  # noqa: BLE001
        traceback.print_exc(file=buf)
        ok = False
    out.append(f"=== {name} === {'PASS' if ok else 'FAIL'}")
    out.append(buf.getvalue())

(ROOT / "_results.txt").write_text("\n".join(out), encoding="utf-8")
