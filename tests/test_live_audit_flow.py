#!/usr/bin/env python
"""
Canlı akış testi: EventStreams + ORES + MDM pipeline'ı çalıştırır,
en az 1 paket veya N olay görülene kadar bekler (timeout 45s).
Kullanım: cd repo_kökü && python tests/test_live_audit_flow.py
"""
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_get_live_module():
    """Dashboard'ın kullandığı import: tools.live_wiki_audit veya dosyadan."""
    import importlib.util
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from tools import live_wiki_audit
        return live_wiki_audit
    except ImportError:
        pass
    path = ROOT / "tools" / "live_wiki_audit.py"
    assert path.exists(), f"Yok: {path}"
    spec = importlib.util.spec_from_file_location(
        "live_wiki_audit", path, submodule_search_locations=[str(ROOT)]
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["live_wiki_audit"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_run_live_loop_receives_data():
    """run_live_loop başlar, EventStreams'e bağlanır ve en az 1 paket veya olay gelir."""
    mod = test_get_live_module()
    LIVE_PACKETS = mod.LIVE_PACKETS
    LIVE_STATUS = mod.LIVE_STATUS
    run_live_loop = mod.run_live_loop

    stop_ev = threading.Event()
    received = []
    LIVE_PACKETS.clear()

    th = threading.Thread(
        target=run_live_loop,
        args=(received.append, stop_ev),
        kwargs={"sample_every_n": 3},
        daemon=True,
    )
    th.start()

    timeout = 45.0
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(1.0)
        events_seen = LIVE_STATUS.get("events_seen", 0)
        packets_sent = LIVE_STATUS.get("packets_sent", 0)
        err = LIVE_STATUS.get("error")
        connected = LIVE_STATUS.get("connected", False)

        if err:
            stop_ev.set()
            th.join(timeout=2)
            raise AssertionError(f"LIVE_STATUS error: {err}")
        if len(received) >= 1:
            stop_ev.set()
            th.join(timeout=2)
            print(f"OK: {len(received)} paket alındı, events_seen={events_seen}, packets_sent={packets_sent}")
            assert received[0].get("schema_version") in (None, "1.1", "1.2", "1.3", "2.0")
            assert "run_id" in received[0]
            assert "mdm" in received[0]
            return
        if connected and events_seen >= 5 and packets_sent == 0:
            # ORES atlanıyor veya henüz N'e ulaşılmadı; akış çalışıyor sayılır
            stop_ev.set()
            th.join(timeout=2)
            print(f"OK (akış çalışıyor): events_seen={events_seen}, connected={connected}")
            return

    stop_ev.set()
    th.join(timeout=2)
    msg = (
        f"Timeout {timeout}s: connected={LIVE_STATUS.get('connected')}, "
        f"events_seen={LIVE_STATUS.get('events_seen')}, packets_sent={LIVE_STATUS.get('packets_sent')}, "
        f"error={LIVE_STATUS.get('error')}, received={len(received)}"
    )
    raise AssertionError(msg)


if __name__ == "__main__":
    print("Test: Modül yükleme...")
    mod = test_get_live_module()
    print(f"  Modül: {mod.__name__}, LIVE_PACKETS={type(mod.LIVE_PACKETS)}, run_live_loop={hasattr(mod, 'run_live_loop')}")

    print("Test: Canlı akış (EventStreams + ORES + MDM), en fazla 45s...")
    test_run_live_loop_receives_data()
    print("Tüm testler geçti.")
