import unittest

import core
from pb_platform.storage import store


class NotificationPolicyTests(unittest.TestCase):
    def setUp(self):
        core._EXTERNAL_EVENT_CACHE.clear()
        store.clear_notification_events()

    def test_new_record_generates_one_received_event(self):
        anterior = {}
        atual = {
            "REQ-1": {
                "label": "Bidu - Tutor",
                "data": "2026-04-01",
                "itens": {
                    "I1": {"nome": "Hemograma", "status": "Recebido"},
                    "I2": {"nome": "ALT", "status": "Recebido"},
                },
            }
        }

        internal, external = core.build_notification_plan("bitlab", "BitLab", anterior, atual)

        self.assertEqual(len(internal), 1)
        self.assertEqual(len(external), 1)
        self.assertEqual(external[0]["kind"], "received")
        self.assertIn("Exame recebido no laboratório", external[0]["message"])

    def test_ready_items_are_grouped_by_record(self):
        anterior = {
            "REQ-1": {
                "label": "Bidu - Tutor",
                "data": "2026-04-01",
                "itens": {
                    "I1": {"nome": "Hemograma", "status": "Recebido"},
                    "I2": {"nome": "ALT", "status": "Em Andamento"},
                    "I3": {"nome": "Ureia", "status": "Analisando"},
                },
            }
        }
        atual = {
            "REQ-1": {
                "label": "Bidu - Tutor",
                "data": "2026-04-01",
                "itens": {
                    "I1": {"nome": "Hemograma", "status": "Pronto"},
                    "I2": {"nome": "ALT", "status": "Pronto"},
                    "I3": {"nome": "Ureia", "status": "Pronto"},
                },
            }
        }

        internal, external = core.build_notification_plan("bitlab", "BitLab", anterior, atual)

        self.assertEqual(len(internal), 3)
        self.assertEqual(len(external), 1)
        self.assertEqual(external[0]["kind"], "completed")
        self.assertIn("Hemograma", external[0]["message"])
        self.assertIn("ALT", external[0]["message"])
        self.assertIn("Ureia", external[0]["message"])

    def test_external_signature_deduplicates_repeated_dispatch(self):
        signature = "abc123"

        self.assertTrue(core._should_send_external_event(signature))
        self.assertFalse(core._should_send_external_event(signature))

    def test_notification_templates_can_be_customized(self):
        anterior = {}
        atual = {
            "REQ-1": {
                "label": "Bidu - Tutor",
                "data": "2026-04-01",
                "itens": {
                    "I1": {"nome": "Hemograma", "status": "Recebido"},
                },
            }
        }
        settings = {
            "events": {
                "received": {
                    "enabled": True,
                    "template": "RX {lab_name} :: {record_id} :: {items_total}",
                },
                "completed": {
                    "enabled": True,
                    "template": "CX {record_id}",
                },
            }
        }

        _, external = core.build_notification_plan("bitlab", "BitLab", anterior, atual, settings)

        self.assertEqual(len(external), 1)
        self.assertEqual(external[0]["message"], "RX BitLab :: REQ-1 :: 1")

    def test_notification_events_can_be_disabled(self):
        anterior = {}
        atual = {
            "REQ-1": {
                "label": "Bidu - Tutor",
                "data": "2026-04-01",
                "itens": {
                    "I1": {"nome": "Hemograma", "status": "Recebido"},
                },
            }
        }
        settings = {
            "events": {
                "received": {
                    "enabled": False,
                    "template": "ignored",
                },
                "completed": {
                    "enabled": True,
                    "template": "CX {record_id}",
                },
            }
        }

        _, external = core.build_notification_plan("bitlab", "BitLab", anterior, atual, settings)

        self.assertEqual(external, [])


    def test_inconsistente_item_fires_completed_notification(self):
        """Items the lab marks Pronto but whose result couldn't be parsed are
        stored as Inconsistente (lab_status=Pronto). A completed notification
        must still be sent so the vet knows the exam is ready at the lab."""
        anterior = {
            "REQ-1": {
                "label": "Polenta - Fabiana",
                "data": "2026-04-13",
                "itens": {
                    "I1": {"nome": "Hemograma", "status": "Em Andamento"},
                },
            }
        }
        atual = {
            "REQ-1": {
                "label": "Polenta - Fabiana",
                "data": "2026-04-13",
                "itens": {
                    "I1": {
                        "nome": "Hemograma",
                        "status": "Inconsistente",
                        "lab_status": "Pronto",
                    },
                },
            }
        }

        internal, external = core.build_notification_plan("bitlab", "BitLab", anterior, atual)

        self.assertEqual(len(external), 1)
        self.assertEqual(external[0]["kind"], "completed")

    def test_inconsistente_item_does_not_refire_on_subsequent_cycles(self):
        """Once an item is already Inconsistente (lab Pronto, no result), the
        next cycle must NOT re-send the completed notification."""
        already_inconsistente = {
            "REQ-1": {
                "label": "Polenta - Fabiana",
                "data": "2026-04-13",
                "itens": {
                    "I1": {
                        "nome": "Hemograma",
                        "status": "Inconsistente",
                        "lab_status": "Pronto",
                    },
                },
            }
        }

        internal, external = core.build_notification_plan(
            "bitlab", "BitLab", already_inconsistente, already_inconsistente
        )

        # s_old == s_new == Inconsistente → no change detected → no events
        self.assertEqual(external, [])

    def test_inconsistente_item_does_not_generate_status_update(self):
        """An Inconsistente item must not generate a status_update event
        (that event is disabled by default and would only create noise)."""
        anterior = {
            "REQ-1": {
                "label": "Polenta - Fabiana",
                "data": "2026-04-13",
                "itens": {
                    "I1": {"nome": "Hemograma", "status": "Em Andamento"},
                },
            }
        }
        atual = {
            "REQ-1": {
                "label": "Polenta - Fabiana",
                "data": "2026-04-13",
                "itens": {
                    "I1": {
                        "nome": "Hemograma",
                        "status": "Inconsistente",
                        "lab_status": "Pronto",
                    },
                },
            }
        }
        settings = {
            "events": {
                "received": {"enabled": True, "template": "RX {record_id}"},
                "completed": {"enabled": True, "template": "CX {record_id}"},
                "status_update": {"enabled": True, "template": "UPD {record_id}"},
            }
        }

        internal, external = core.build_notification_plan("bitlab", "BitLab", anterior, atual, settings)

        kinds = [e["kind"] for e in external]
        self.assertNotIn("status_update", kinds)
        self.assertIn("completed", kinds)


if __name__ == "__main__":
    unittest.main()
