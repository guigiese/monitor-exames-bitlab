import json
from pathlib import Path
from datetime import datetime

CONFIG_FILE = Path(__file__).parent.parent / "config.json"


class AppState:
    def __init__(self):
        self.snapshots:   dict[str, dict] = {}
        self.last_check:  dict[str, str]  = {}
        self.last_error:  dict[str, str]  = {}
        self.is_checking: dict[str, bool] = {}
        self.notifications: list[dict]    = []
        self._config: dict | None         = None

    @property
    def config(self) -> dict:
        if self._config is None:
            self._config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return self._config

    def save_config(self):
        CONFIG_FILE.write_text(
            json.dumps(self._config, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def toggle_lab(self, lab_id: str):
        for lab in self.config["labs"]:
            if lab["id"] == lab_id:
                lab["enabled"] = not lab.get("enabled", True)
                break
        self.save_config()

    def toggle_notifier(self, notifier_id: str):
        for n in self.config["notifiers"]:
            if n["id"] == notifier_id:
                n["enabled"] = not n.get("enabled", True)
                break
        self.save_config()

    def set_interval(self, minutes: int):
        self.config["interval_minutes"] = minutes
        self.save_config()

    def add_notification(self, lab_name: str, msg: str):
        self.notifications.insert(0, {
            "time": datetime.now().strftime("%H:%M:%S"),
            "lab":  lab_name,
            "msg":  msg,
        })
        self.notifications = self.notifications[:50]

    def get_exames(self, lab_filter: str = "", status_filter: str = "") -> list[dict]:
        rows = []
        for lab_id, snapshot in self.snapshots.items():
            lab_cfg = next((l for l in self.config["labs"] if l["id"] == lab_id), {})
            lab_name = lab_cfg.get("name", lab_id)
            if lab_filter and lab_id != lab_filter:
                continue
            for record_id, record in snapshot.items():
                for item_id, item in record["itens"].items():
                    if status_filter and item["status"] != status_filter:
                        continue
                    rows.append({
                        "lab_id":    lab_id,
                        "lab":       lab_name,
                        "record_id": record_id,
                        "paciente":  record["label"],
                        "data":      record["data"],
                        "exame":     item["nome"],
                        "status":    item["status"],
                    })
        return sorted(rows, key=lambda x: x["data"], reverse=True)

    def get_lab_counts(self) -> dict:
        STATUS_PRONTO = {"Pronto", "Entrega"}
        STATUS_ANDAMENTO = {"Em Andamento", "Recebido", "Analisando"}
        result = {}
        for lab_cfg in self.config["labs"]:
            lid   = lab_cfg["id"]
            snap  = self.snapshots.get(lid, {})
            itens = [item for rec in snap.values() for item in rec["itens"].values()]
            result[lid] = {
                "name":      lab_cfg["name"],
                "enabled":   lab_cfg.get("enabled", True),
                "pronto":    sum(1 for i in itens if i["status"] in STATUS_PRONTO),
                "andamento": sum(1 for i in itens if i["status"] in STATUS_ANDAMENTO),
                "total":     len(itens),
                "last_check": self.last_check.get(lid, "—"),
                "error":      self.last_error.get(lid, ""),
                "checking":   self.is_checking.get(lid, False),
            }
        return result


state = AppState()
