"""Tests sin red del paso (a): parseo de progreso gogdl, lang, builds, carpetas.

NOTA: las líneas de progreso son SINTÉTICAS (derivadas de los format
strings de gogdl/dl/progressbar.py, NO capturadas de una descarga real).
En la prueba real con Hank se capturan líneas verdaderas y se agregan
como fixtures. written_raw/total_raw son contadores SIN unidad confirmada.

Uso: python3 tests/test_gog_install.py (stdlib, sin pytest ni red).
"""
import importlib.machinery
import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "heroic-store"


def load():
    # El plugin no tiene extensión .py: SourceFileLoader explícito.
    loader = importlib.machinery.SourceFileLoader("heroic_store", str(SCRIPT))
    spec = importlib.util.spec_from_loader("heroic_store", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class ProgressLines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_v2_progress_con_eta(self):
        ev = self.m._parse_progress_line(
            "[PROGRESS] INFO: = Progress: 42.50 123456/789012, "
            "Running for: 00:01:23, ETA: 00:05:00")
        self.assertEqual(ev["percent"], 42.5)
        self.assertEqual((ev["written_raw"], ev["total_raw"]), (123456, 789012))
        self.assertEqual(ev["eta_s"], 300)

    def test_v2_progress_sin_eta(self):
        ev = self.m._parse_progress_line("= Progress: 0.00 0/789012")
        self.assertEqual(ev["percent"], 0.0)
        self.assertIsNone(ev["eta_s"])

    def test_v2_speed_sola(self):
        ev = self.m._parse_progress_line(
            "[PROGRESS] INFO:  + Download\t- 8.20 MiB/s (raw) / 1.50 MiB/s (decompressed)")
        self.assertIsNone(ev["percent"])
        self.assertEqual(ev["speed_mibs"], 8.2)

    def test_porcentaje_generico_legendary(self):
        ev = self.m._parse_progress_line("Downloaded 1.2 GB (45%)")
        self.assertEqual((ev["stage"], ev["percent"]), ("downloading", 45.0))

    def test_ruido_no_es_progreso(self):
        self.assertIsNone(self.m._parse_progress_line(
            "[API] INFO: Getting Dependencies repository"))
        self.assertIsNone(self.m._parse_progress_line(""))
        self.assertIsNone(self.m._parse_progress_line(
            "[PROGRESS] INFO: = Downloaded: 12.34 MiB, Written: 45.67 MiB"))


class LangPick(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_en_us_si_esta(self):
        self.assertEqual(
            self.m._gog_pick_lang({"languages": ["de-DE", "en-US"]}, ""), "en-US")

    def test_primero_si_no_esta(self):
        self.assertEqual(
            self.m._gog_pick_lang({"languages": ["fr-FR"]}, ""), "fr-FR")

    def test_override_manual(self):
        self.assertEqual(
            self.m._gog_pick_lang({"languages": ["fr-FR"]}, "de-DE"), "de-DE")

    def test_sin_lista_vacio(self):
        self.assertEqual(self.m._gog_pick_lang({}, ""), "")


class LinuxBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_solo_windows(self):
        info = {"builds": {"items": [{"os": "windows"}]}}
        self.assertFalse(self.m._gog_has_linux_build(info))

    def test_con_linux(self):
        info = {"builds": {"items": [{"os": "windows"}, {"os": "linux"}]}}
        self.assertTrue(self.m._gog_has_linux_build(info))

    def test_info_vacio(self):
        self.assertFalse(self.m._gog_has_linux_build({}))


class SanitizeFolder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_nombre_real(self):
        self.assertEqual(
            self.m._sanitize_folder("Hank Straightjacket", "1831618557"),
            "Hank Straightjacket")

    def test_fallback(self):
        self.assertEqual(self.m._sanitize_folder("...   ", "1831618557"), "1831618557")
        self.assertEqual(self.m._sanitize_folder("", "1831618557"), "1831618557")



class GogRailPools(unittest.TestCase):
    """Constantes de pool y filtro Free (sin red)."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_pools_parejos_30(self):
        q = self.m.GOG_RAIL_QUERIES
        for rail in ("sale", "new", "free"):
            _q, limit, top = q[rail]
            self.assertEqual((limit, top), (30, 30), rail)

    def test_free_filtra_pagado_dlc_placeholder(self):
        items = [
            {"title": "Knytt Classic", "free": True, "ptype": "game"},
            {"title": "Algo Pago", "free": False, "ptype": "game"},
            {"title": "DLC Extra", "free": True, "ptype": "dlc"},
            {"title": "TEST TEST TEST", "free": True, "ptype": "game"},
            {"title": "The Witcher 3 REDkit", "free": True, "ptype": "game"},
        ]
        out = self.m._gog_rail_filter_free(items, 30)
        titles = [x["title"] for x in out]
        self.assertEqual(titles, ["Knytt Classic", "The Witcher 3 REDkit"])

    def test_free_respeta_top(self):
        items = [{"title": f"Juego {i}", "free": True, "ptype": "game"}
                 for i in range(5)]
        self.assertEqual(len(self.m._gog_rail_filter_free(items, 3)), 3)


class GogModalCover(unittest.TestCase):
    """Cadena vertical → bg con ext → público → .jpg → vacío."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_vertical_gana(self):
        self.assertEqual(
            self.m._gog_modal_cover("https://x/v.jpg", "https://x/a.jpg", "https://x/b.jpg"),
            "https://x/v.jpg")

    def test_gamedetails_con_extension(self):
        self.assertEqual(
            self.m._gog_modal_cover("", "https://x/a.jpg", "https://x/b.jpg"),
            "https://x/a.jpg")

    def test_publico_sobre_hash_pelado(self):
        self.assertEqual(
            self.m._gog_modal_cover("", "https://x/abc", "https://x/bg.jpg"),
            "https://x/bg.jpg")

    def test_jpg_sobre_hash_sin_publico(self):
        self.assertEqual(
            self.m._gog_modal_cover("", "https://x/abc", ""),
            "https://x/abc.jpg")

    def test_vacio_sin_nada(self):
        self.assertEqual(self.m._gog_modal_cover("", "", ""), "")


class GogMergeEntry(unittest.TestCase):
    """Guardado único: solo datos nuevos, nunca fallos."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_guarda_desc_nueva(self):
        out = self.m._gog_merge_entry({}, "Hola", "gog", "")
        self.assertEqual((out["description"], out["source"]), ("Hola", "gog"))

    def test_no_reescribe_igual(self):
        saved = {"description": "Hola", "source": "gog", "cover": "v"}
        self.assertIsNone(self.m._gog_merge_entry(saved, "Hola", "gog", ""))

    def test_no_guarda_fallos(self):
        self.assertIsNone(self.m._gog_merge_entry({}, "", "", ""))
        self.assertIsNone(self.m._gog_merge_entry({"description": "X"}, "", "", ""))

    def test_agrega_cover_sin_pisar_desc(self):
        saved = {"description": "Hola", "source": "gog"}
        out = self.m._gog_merge_entry(saved, "Hola", "gog", "https://x/v.jpg")
        self.assertEqual((out["description"], out["cover"]), ("Hola", "https://x/v.jpg"))


class GogDescKeys(unittest.TestCase):
    """Wipe total (refresh) vs poda de ausentes (cargas)."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_wipe_borra_solo_gog(self):
        data = {"gog:1": {"description": "x"}, "epic:Abc": {"description": "y"},
                "otro": 1}
        out = self.m._gog_desc_wipe(data)
        self.assertEqual(out, {"epic:Abc": {"description": "y"}, "otro": 1})

    def test_prune_solo_ausentes(self):
        data = {"gog:1": {}, "gog:2": {}, "epic:Abc": {}}
        out = self.m._gog_desc_prune(data, {"gog:1"})
        self.assertEqual(out, {"gog:1": {}, "epic:Abc": {}})


class GogV2Game(unittest.TestCase):
    """Un solo fetch v2: boxArt+desc, sin boxArt, red, JSON, 404."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _resp(self, payload, exc=None):
        from unittest import mock
        if exc is not None:
            m = mock.MagicMock()
            m.__enter__.side_effect = exc
            return mock.patch("urllib.request.urlopen", return_value=m)
        m = mock.MagicMock()
        m.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        return mock.patch("urllib.request.urlopen", return_value=m)

    def test_boxart_y_desc(self):
        payload = {"_links": {"boxArtImage": {"href": "https://x/v.jpg"}},
                   "description": "<p>Hola &amp; chau</p>"}
        with self._resp(payload):
            self.assertEqual(self.m._gog_v2_game("1"),
                             ("https://x/v.jpg", "Hola & chau"))

    def test_sin_boxart_solo_desc(self):
        payload = {"_links": {}, "description": "Solo texto"}
        with self._resp(payload):
            self.assertEqual(self.m._gog_v2_game("1"), ("", "Solo texto"))

    def test_fallo_red_vacio(self):
        with self._resp(None, exc=Exception("boom")):
            self.assertEqual(self.m._gog_v2_game("1"), ("", ""))

    def test_json_invalido_vacio(self):
        from unittest import mock
        m = mock.MagicMock()
        m.__enter__.return_value.read.return_value = b"no-json{"
        with mock.patch("urllib.request.urlopen", return_value=m):
            self.assertEqual(self.m._gog_v2_game("1"), ("", ""))

    def test_404_no_se_guarda(self):
        import urllib.error
        with self._resp(None, exc=urllib.error.HTTPError(
                "https://x", 404, "NF", {}, None)):
            self.assertEqual(self.m._gog_v2_game("1"), ("", ""))


class GogMergeCoverSrc(unittest.TestCase):
    """cover_src v2-box y migración de entradas legacy."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_src_se_guarda_con_vertical(self):
        out = self.m._gog_merge_entry({}, "", "", "https://x/v.jpg", "v2-box")
        self.assertEqual((out["cover"], out["cover_src"]),
                         ("https://x/v.jpg", "v2-box"))

    def test_migracion_reemplaza_bg_legacy(self):
        saved = {"description": "D", "source": "gog", "cover": "https://x/bg.jpg"}
        out = self.m._gog_merge_entry(saved, "D", "gog", "https://x/v.jpg", "v2-box")
        self.assertEqual((out["cover"], out["cover_src"]),
                         ("https://x/v.jpg", "v2-box"))
        self.assertEqual(out["description"], "D")


class EpicDealsMoney(unittest.TestCase):
    """Badge desde el dinero: promo 80 + 799/999 → 20."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _el(self, disc, orig, promo=80, start="2026-09-25T15:00:00.000Z",
            end="2026-10-09T15:00:00.000Z", fmt=None):
        total = {"discountPrice": disc, "originalPrice": orig,
                 "currencyCode": "USD"}
        if fmt is not None:
            total["fmtPrice"] = {"discountPrice": fmt[0], "originalPrice": fmt[1]}
        return {"title": "T", "price": {"totalPrice": total},
                "promotions": {"promotionalOffers": [{"promotionalOffers": [{
                    "startDate": start, "endDate": end,
                    "discountSetting": {"discountPercentage": promo}}]}]}}

    def test_mismatch_cozy(self):
        self.assertEqual(self.m._epic_money_pct(self._el(799, 999)), 20)

    def test_fmtprice_ignorado_para_badge(self):
        # fmtPrice es solo display: sin números no hay badge.
        el = self._el(0, 0, fmt=("$3.19", "$3.99"))
        self.assertEqual(self.m._epic_money_pct(el), 0)

    def test_decimals_cero(self):
        el = {"price": {"totalPrice": {
            "discountPrice": 799, "originalPrice": 999,
            "currencyCode": "JPY",
            "currencyInfo": {"decimals": 0}}}}
        self.assertEqual(self.m._epic_money_pct(el), 20)

    def test_gratis_100(self):
        self.assertEqual(self.m._epic_money_pct(self._el(0, 1999, promo=100)), 100)

    def test_plano_con_promo_se_descarta(self):
        self.assertEqual(self.m._epic_money_pct(self._el(999, 999, promo=50)), 0)

    def test_ends_formato_local(self):
        import datetime
        tz = datetime.timezone(datetime.timedelta(hours=-5))
        self.assertEqual(
            self.m._epic_fmt_end("2026-10-09T15:00:00.000Z", tz), "Oct 9")

    def test_ends_frontera_utc(self):
        # 02:00 UTC del 9 = 21:00 del 8 en -05: la zona decide el día.
        import datetime
        tz = datetime.timezone(datetime.timedelta(hours=-5))
        self.assertEqual(
            self.m._epic_fmt_end("2026-10-09T02:00:00.000Z", tz), "Oct 8")

    def test_ends_invalido_vacio(self):
        self.assertEqual(self.m._epic_fmt_end("no-fecha"), "")

    def test_orden_por_dinero(self):
        a = {"title": "A80", "discount": 80}  # orden viejo (promo)
        b = {"title": "B70", "discount": 70}
        money = {"A80": 20, "B70": 30}  # orden nuevo (dinero)
        nuevo = sorted([a, b], key=lambda x: -(money[x["title"]] or 0))
        self.assertEqual([x["title"] for x in nuevo], ["B70", "A80"])


class EpicCountry(unittest.TestCase):
    """País Epic: --country > $LANG > US."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _args(self, country=""):
        import types
        return types.SimpleNamespace(country=country)

    def _with_lang(self, lang):
        import os
        from unittest import mock
        env = {"LANG": lang, "LC_ALL": ""}
        return mock.patch.dict(os.environ, env, clear=False)

    def test_lang_ec(self):
        with self._with_lang("es_EC.UTF-8"):
            self.assertEqual(self.m._epic_country(self._args()), "EC")

    def test_lang_c(self):
        with self._with_lang("C"):
            self.assertEqual(self.m._epic_country(self._args()), "US")

    def test_lang_vacio(self):
        with self._with_lang(""):
            self.assertEqual(self.m._epic_country(self._args()), "US")

    def test_flag_minusculas(self):
        with self._with_lang("es_EC.UTF-8"):
            self.assertEqual(self.m._epic_country(self._args("ec")), "EC")

    def test_flag_manda_sobre_lang(self):
        with self._with_lang("es_EC.UTF-8"):
            self.assertEqual(self.m._epic_country(self._args("US")), "US")

    def test_invalido_avisa_y_sigue(self):
        import io
        from contextlib import redirect_stderr
        with self._with_lang("es_EC.UTF-8"):
            buf = io.StringIO()
            with redirect_stderr(buf):
                pais = self.m._epic_country(self._args("USA"))
            self.assertEqual(pais, "EC")
            self.assertIn("--country", buf.getvalue())

    def test_basura_cae_a_lang(self):
        with self._with_lang("es_EC.UTF-8"):
            for bad in ("USA", "E", "1A", ""):
                if bad == "":
                    continue
                self.assertEqual(self.m._epic_country(self._args(bad)), "EC")
        with self._with_lang("C"):
            self.assertEqual(self.m._epic_country(self._args("USA")), "US")


class EpicFreePromosE2E(unittest.TestCase):
    """cmd_free_promos punta a punta con red simulada (el NameError
    anterior pasaba con tests en verde porque nada lo ejecutaba)."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _feed(self, offers):
        return {"data": {"Catalog": {"searchStore": {"elements": [{
            "title": "Gratis Ahora", "description": "d",
            "keyImages": [{"type": "OfferImageTall", "url": "https://x/c.jpg"}],
            "promotions": {"promotionalOffers": [{"promotionalOffers": offers}]},
        }]}}}}

    def _urlopen(self, payload):
        from unittest import mock
        m = mock.MagicMock()
        m.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        return mock.patch("urllib.request.urlopen", return_value=m)

    def test_promos_gratis_ok(self):
        import types
        off = [{"startDate": "2020-01-01T00:00:00.000Z",
                "endDate": "2030-01-01T00:00:00.000Z",
                "discountSetting": {"discountPercentage": 0}}]
        events = []
        from unittest import mock
        with self._urlopen(self._feed(off)), \
                mock.patch.object(self.m, "emit", events.append):
            self.m.cmd_free_promos(types.SimpleNamespace(country="EC"))
        done = [e for e in events if e.get("type") == "done"]
        self.assertEqual(len(done), 1)
        self.assertEqual(len(done[0]["free_now"]), 1)
        self.assertEqual(done[0]["free_now"][0]["title"], "Gratis Ahora")

    def test_promos_sin_url_country(self):
        # Sin NameError aunque country venga vacío (usa LANG/US).
        import types
        from unittest import mock
        seen = {}

        def fake_open(req, timeout=None):
            seen["url"] = req.full_url
            m = mock.MagicMock()
            m.__enter__.return_value.read.return_value = json.dumps(
                self._feed([])).encode()
            return m

        with mock.patch("urllib.request.urlopen", side_effect=fake_open), \
                mock.patch.object(self.m, "emit", lambda e: None):
            self.m.cmd_free_promos(types.SimpleNamespace(country=""))
        self.assertIn("freeGamesPromotions", seen["url"])


class EpicDealsE2E(unittest.TestCase):
    """cmd_epic_deals punta a punta: feed + página GraphQL simulados."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_deals_mezcla_feed_y_sale(self):
        import types
        from unittest import mock
        feed = {"data": {"Catalog": {"searchStore": {"elements": []}}}}
        sale = {"data": {"Catalog": {"searchStore": {
            "paging": {"total": 1},
            "elements": [{
                "title": "Barato", "description": "d",
                "urlSlug": "barato", "productSlug": "barato",
                "catalogNs": {"mappings": []},
                "keyImages": [{"type": "OfferImageTall",
                               "url": "https://x/b.jpg"}],
                "price": {"totalPrice": {"discountPrice": 799,
                                         "originalPrice": 999,
                                         "currencyCode": "USD"}},
                "promotions": {"promotionalOffers": [{"promotionalOffers": [{
                    "startDate": "2020-01-01T00:00:00.000Z",
                    "endDate": "2030-01-01T00:00:00.000Z",
                    "discountSetting": {"discountPercentage": 80}}]}]},
            }]}}}}

        def fake_open(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else ""
            body = feed if "freeGamesPromotions" in url else sale
            m = mock.MagicMock()
            m.__enter__.return_value.read.return_value = json.dumps(body).encode()
            return m

        events = []
        args = types.SimpleNamespace(start=1, count=10, country="US")
        with mock.patch("urllib.request.urlopen", side_effect=fake_open), \
                mock.patch.object(self.m, "emit", events.append):
            self.m.cmd_epic_deals(args)
        done = [e for e in events if e.get("type") == "done"]
        self.assertEqual(len(done), 1)
        deal = done[0]["deals"][0]
        self.assertEqual((deal["title"], deal["discount"], deal["price"]),
                         ("Barato", 20, "$7.99"))


class GogProbeExe(unittest.TestCase):
    """isPrimary > filetask > mayor .exe, todo con exclusiones."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _tasks(self):
        return [
            {"type": "FileTask", "isPrimary": False,
             "path": "Bloody Hell/UnityCrashHandler64.exe"},
            {"type": "FileTask", "isPrimary": True,
             "path": "Bloody Hell.exe"},
        ]

    def test_isprimary_manda(self):
        self.assertEqual(
            self.m._gog_pick_task(self._tasks()), "Bloody Hell.exe")

    def test_crashhandler_excluido_aunque_primero(self):
        tasks = [{"type": "FileTask", "path": "UnityCrashHandler64.exe"},
                 {"type": "FileTask", "path": "Juego.exe"}]
        self.assertEqual(self.m._gog_pick_task(tasks), "Juego.exe")

    def test_sin_candidatos_vacio(self):
        self.assertEqual(self.m._gog_pick_task(
            [{"type": "FileTask", "path": "setup.exe"}]), "")

    def test_walk_ignora_crashhandler_grande(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "Juego.exe").write_bytes(b"x" * 100)
            (d / "UnityCrashHandler64.exe").write_bytes(b"x" * 9999)
            with mock.patch.object(self.m, "GOGDL_BIN", "/nonexistent/gogdl"):
                ipath, exe, plat = self.m._gog_probe(d, "1")
            self.assertEqual((exe, plat), ("Juego.exe", "Windows"))
            self.assertEqual(ipath, str(d))

    def test_find_dir_desciende_un_nivel_legacy(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inner = base / "Juego" / "Juego"
            inner.mkdir(parents=True)
            (inner / "goggame-1.info").write_text("{}")
            self.assertEqual(
                self.m._gog_find_game_dir(base, "Juego"), inner)

    def test_find_dir_sin_doble_nesting(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "Juego").mkdir()
            (base / "Juego" / "goggame-1.info").write_text("{}")
            self.assertEqual(
                self.m._gog_find_game_dir(base, "Juego"), base / "Juego")
            self.assertEqual(
                self.m._gog_find_game_dir(base, "Otro"), base)


class GogInstallE2E(unittest.TestCase):
    """Flujo install GOG con red simulada: --path = base, sin nesting."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _args(self, path):
        import types
        return types.SimpleNamespace(store="gog", app_id="99", path=path,
                                     lang="", platform="windows", ppid=0)

    def test_path_base_sin_doble_carpeta(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "Heroic"
            base.mkdir()
            (base / "Juego").mkdir()
            (base / "Juego" / "goggame-99.info").write_text("{}")
            seen = {}
            real_info = {"folder_name": "Juego", "languages": ["en-US"],
                         "builds": {"items": [{"os": "windows"}]}}

            def fake_stream(cmd, store, ppid=0):
                seen["cmd"] = list(cmd)
                return True

            events = []
            with patch.object(self.m, "CONFIG_DIR", Path(tmp)), \
                    patch.object(self.m, "INSTALLS_JSON", Path(tmp) / "installs.json"), \
                    patch.object(self.m, "_gog_info_raw", return_value=(real_info, "")), \
                    patch.object(self.m, "_run_streaming", side_effect=fake_stream), \
                    patch.object(self.m, "emit", events.append):
                self.m.cmd_install(self._args(str(base)))
            idx = seen["cmd"].index("--path")
            self.assertEqual(seen["cmd"][idx + 1], str(base))
            self.assertFalse((base / "Juego" / "Juego").exists())
            rec = [e for e in events if e.get("type") == "done"][0]
            self.assertEqual(rec["install_path"], str(base / "Juego"))


class GogReprobe(unittest.TestCase):
    """reprobe: dry-run no escribe, --write solo toca exe (+ .bak)."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _env(self, tmp):
        import json
        from pathlib import Path
        from unittest.mock import patch
        (Path(tmp) / "installs.json").write_text(json.dumps(
            {"gog:9": {"path": str(Path(tmp) / "J"), "exe": "Viejo.exe",
                       "status": "partial"}}))
        (Path(tmp) / "J").mkdir(exist_ok=True)
        return (patch.object(self.m, "CONFIG_DIR", Path(tmp)),
                patch.object(self.m, "INSTALLS_JSON", Path(tmp) / "installs.json"))

    def _ns(self, write=False, fix_path=False):
        import types
        return types.SimpleNamespace(store="gog", app_id="9", write=write,
                                     fix_path=fix_path)

    def test_dryrun_no_escribe(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            p1, p2 = self._env(tmp)
            events = []
            with p1, p2, mock.patch.object(
                    self.m, "_gog_probe",
                    return_value=(tmp + "/J", "Nuevo.exe", "Windows")), \
                    mock.patch.object(self.m, "emit", events.append):
                self.m.cmd_reprobe(self._ns(write=False))
            done = [e for e in events if e.get("type") == "done"][0]
            self.assertEqual((done["old_exe"], done["new_exe"], done["wrote"]),
                             ("Viejo.exe", "Nuevo.exe", False))
            import json
            from pathlib import Path
            rec = json.loads((Path(tmp) / "installs.json").read_text())["gog:9"]
            self.assertEqual(rec["exe"], "Viejo.exe")
            self.assertEqual(list(Path(tmp).glob("installs.json.bak-*")), [])

    def test_write_solo_exe_mas_bak(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            p1, p2 = self._env(tmp)
            events = []
            with p1, p2, mock.patch.object(
                    self.m, "_gog_probe",
                    return_value=(tmp + "/J", "Nuevo.exe", "Windows")), \
                    mock.patch.object(self.m, "emit", events.append):
                self.m.cmd_reprobe(self._ns(write=True))
            rec = json.loads((Path(tmp) / "installs.json").read_text())["gog:9"]
            self.assertEqual(rec["exe"], "Nuevo.exe")
            self.assertEqual(rec["status"], "partial")
            self.assertEqual(len(list(Path(tmp).glob("installs.json.bak-*"))), 1)

    def test_exe_relativo_al_path_registrado(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp) / "J"
            (outer / "J").mkdir(parents=True)
            (outer / "J" / "goggame-1.info").write_text("{}")
            import json
            (Path(tmp) / "installs.json").write_text(json.dumps(
                {"gog:9": {"path": str(outer), "exe": "Viejo.exe"}}))
            p1 = mock.patch.object(self.m, "CONFIG_DIR", Path(tmp))
            p2 = mock.patch.object(self.m, "INSTALLS_JSON", Path(tmp) / "installs.json")
            events = []
            with p1, p2, mock.patch.object(
                    self.m, "_gog_probe",
                    return_value=(str(outer / "J"), "Juego.exe", "Windows")), \
                    mock.patch.object(self.m, "emit", events.append):
                self.m.cmd_reprobe(self._ns(write=False))
            done = [e for e in events if e.get("type") == "done"][0]
            self.assertEqual(done["new_exe"], "J/Juego.exe")

    def test_sin_exe_error_sin_escribir(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            p1, p2 = self._env(tmp)
            with p1, p2, mock.patch.object(
                    self.m, "_gog_probe", return_value=(tmp + "/J", "", "Linux")):
                with self.assertRaises(SystemExit):
                    self.m.cmd_reprobe(self._ns(write=True))

    def test_fixpath_propone_subcarpeta(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            inner = Path(tmp) / "J"
            inner.mkdir()
            (inner / "Juego.exe").write_bytes(b"x")
            (Path(tmp) / "installs.json").write_text(json.dumps(
                {"gog:9": {"path": str(Path(tmp)), "exe": "J/Juego.exe"}}))
            p1 = mock.patch.object(self.m, "CONFIG_DIR", Path(tmp))
            p2 = mock.patch.object(self.m, "INSTALLS_JSON",
                                   Path(tmp) / "installs.json")
            events = []
            with p1, p2, mock.patch.object(self.m, "_gog_probe",
                    return_value=(str(inner), "Juego.exe", "Windows")), \
                    mock.patch.object(self.m, "emit", events.append):
                self.m.cmd_reprobe(self._ns(write=False, fix_path=True))
            done = [e for e in events if e.get("type") == "done"][0]
            self.assertEqual(done["new_path"], str(inner))
            self.assertEqual(done["new_exe"], "Juego.exe")
            self.assertFalse(done["wrote"])
            rec = json.loads((Path(tmp) / "installs.json").read_text())["gog:9"]
            self.assertEqual(rec["path"], str(Path(tmp)))

    def test_fixpath_destino_inexistente_no_escribe(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "installs.json").write_text(json.dumps(
                {"gog:9": {"path": str(Path(tmp)), "exe": "Nope/Juego.exe"}}))
            p1 = mock.patch.object(self.m, "CONFIG_DIR", Path(tmp))
            p2 = mock.patch.object(self.m, "INSTALLS_JSON",
                                   Path(tmp) / "installs.json")
            with p1, p2, mock.patch.object(self.m, "_gog_probe",
                    return_value=(str(Path(tmp)), "Nope/Juego.exe", "Windows")):
                with self.assertRaises(SystemExit):
                    self.m.cmd_reprobe(self._ns(write=True, fix_path=True))
            rec = json.loads((Path(tmp) / "installs.json").read_text())["gog:9"]
            self.assertEqual(rec["path"], str(Path(tmp)))
            self.assertEqual(list(Path(tmp).glob("installs.json.bak-*")), [])

    def test_sin_registro_error(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p1, p2 = self._env(tmp)
            import types
            with p1, p2:
                with self.assertRaises(SystemExit):
                    self.m.cmd_reprobe(types.SimpleNamespace(
                        store="gog", app_id="nope", write=False))


class GogInstallGate(unittest.TestCase):
    """Puerta post-download + repair ante manifest, sin red ni disco real."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _base_env(self, tmp):
        import json
        from pathlib import Path
        from unittest.mock import patch
        base = Path(tmp) / "Heroic"
        base.mkdir(exist_ok=True)
        (Path(tmp) / "installs.json").write_text("{}")
        info = {"folder_name": "Juego", "languages": ["en-US"],
                "builds": {"items": [{"os": "windows"}]}}
        return base, info, [
            patch.object(self.m, "CONFIG_DIR", Path(tmp)),
            patch.object(self.m, "INSTALLS_JSON", Path(tmp) / "installs.json"),
            patch.object(self.m, "_gog_info_raw", return_value=(info, "")),
        ]

    def _ns(self, path):
        import types
        return types.SimpleNamespace(store="gog", app_id="99", path=path,
                                     lang="", platform="windows", ppid=0)

    def _run_ok(self, cmd, store, ppid=0):
        return True

    def test_exito_vacio_muere_sin_escribir(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            base, info, patches = self._base_env(tmp)
            events = []
            with patches[0], patches[1], patches[2], \
                    mock.patch.object(self.m, "_run_streaming",
                                      side_effect=self._run_ok), \
                    mock.patch.object(self.m, "emit", events.append):
                with self.assertRaises(SystemExit) as cm:
                    self.m.cmd_install(self._ns(str(base)))
                self.assertEqual(cm.exception.code, 3)
                self.assertFalse([e for e in events if e.get("type") == "done"])
            import json
            from pathlib import Path
            rec = json.loads((Path(tmp) / "installs.json").read_text())
            self.assertEqual(rec["gog:99"]["status"], "partial")

    def test_manifest_presente_elige_repair(self):
        # Dir borrado + manifest guardado (tu caso): repair verifica disco.
        import shutil
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            base, info, patches = self._base_env(tmp)
            (base / "Juego").mkdir()
            (base / "Juego" / "goggame-99.info").write_text("{}")
            shutil.rmtree(base / "Juego")
            seen = {}
            events = []

            def fake_stream(cmd, store, ppid=0):
                seen["verb"] = cmd[3]
                return True

            with patches[0], patches[1], patches[2], \
                    mock.patch.object(self.m, "_gog_manifest_source",
                                      return_value="old"), \
                    mock.patch.object(self.m, "_run_streaming",
                                      side_effect=fake_stream), \
                    mock.patch.object(self.m, "_gog_probe",
                                      return_value=(str(base / "Juego"),
                                                    "Juego.exe", "Windows")), \
                    mock.patch.object(self.m, "emit", events.append):
                # La puerta muere (nada escrito: el dir sigue vacío), pero
                # el verbo ya quedó decidido antes.
                with self.assertRaises(SystemExit):
                    self.m.cmd_install(self._ns(str(base)))
            self.assertEqual(seen["verb"], "repair")

    def test_manifest_viejo_repair_coherente(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            new = Path(tmp) / "new" / "manifests"
            old = Path(tmp) / "old" / "heroic_gogdl" / "manifests"
            old.mkdir(parents=True)
            (old / "99").write_text("{}")
            with mock.patch.object(self.m, "_gogdl_manifests_dir",
                                   return_value=new), \
                    mock.patch.object(self.m, "_gog_old_manifests_dir",
                                      return_value=old):
                self.assertEqual(self.m._gog_manifest_source("99"), "old")
                self.assertEqual(self.m._gog_manifest_source("otro"), "")

    def test_sin_manifest_download_normal(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            base, info, patches = self._base_env(tmp)
            (base / "Juego").mkdir()
            (base / "Juego" / "Juego.exe").write_bytes(b"x")
            seen = {}

            def fake_stream(cmd, store, ppid=0):
                seen["verb"] = cmd[3]
                return True

            with patches[0], patches[1], patches[2], \
                    mock.patch.object(self.m, "_gog_manifest_source",
                                      return_value=""), \
                    mock.patch.object(self.m, "_run_streaming",
                                      side_effect=fake_stream), \
                    mock.patch.object(self.m, "emit", lambda e: None):
                self.m.cmd_install(self._ns(str(base)))
            self.assertEqual(seen["verb"], "download")


class GogReinstallRobusto(unittest.TestCase):
    """Reinstall tras borrado: nada de éxito vacío ni bloqueos rancios."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_mark_pisa_registro_rancio(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            ip = Path(tmp) / "installs.json"
            ip.write_text('{"gog:9": {"path": "%s", "exe": ""}}' % base)
            with mock.patch.object(self.m, "CONFIG_DIR", Path(tmp)), \
                    mock.patch.object(self.m, "INSTALLS_JSON", ip):
                self.m._mark_partial("gog", "9", str(base / "Juego"))
                import json
                rec = json.loads(ip.read_text())["gog:9"]
                self.assertEqual(rec["status"], "partial")

    def test_mark_bloquea_instal_real(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / "Juego"
            game.mkdir()
            (game / "Juego.exe").write_bytes(b"x")
            ip = Path(tmp) / "installs.json"
            ip.write_text('{"gog:9": {"path": "%s", "exe": "Juego.exe"}}' % game)
            with mock.patch.object(self.m, "CONFIG_DIR", Path(tmp)), \
                    mock.patch.object(self.m, "INSTALLS_JSON", ip):
                with self.assertRaises(SystemExit) as cm:
                    self.m._mark_partial("gog", "9", str(game))
                self.assertEqual(cm.exception.code, 4)

    def test_uninstall_niega_base(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "Heroic"
            base.mkdir()
            regs = {"gog:9": {"path": str(base), "exe": ""}}
            self.assertFalse(self.m._gog_uninstall_safe(str(base), regs, "gog:9"))

    def test_uninstall_permite_juego_solo(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / "Juego"
            game.mkdir()
            (game / "goggame-1.info").write_text("{}")
            regs = {"gog:9": {"path": str(game), "exe": "Juego.exe"}}
            self.assertTrue(self.m._gog_uninstall_safe(str(game), regs, "gog:9"))

    def test_uninstall_niega_hermano_dentro(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp) / "Base"
            inner = outer / "Otro"
            inner.mkdir(parents=True)
            (inner / "goggame-2.info").write_text("{}")
            regs = {"gog:1": {"path": str(outer), "exe": ""},
                    "gog:2": {"path": str(inner), "exe": "J.exe"}}
            self.assertFalse(self.m._gog_uninstall_safe(str(outer), regs, "gog:1"))


class GogRepairPath(unittest.TestCase):
    """Cada verbo con su --path; base con exe sueltos también muere."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _env(self, tmp):
        import json
        from pathlib import Path
        from unittest.mock import patch
        base = Path(tmp) / "Heroic"
        base.mkdir(exist_ok=True)
        (Path(tmp) / "installs.json").write_text("{}")
        info = {"folder_name": "Juego", "languages": ["en-US"],
                "builds": {"items": [{"os": "windows"}]}}
        return base, [
            patch.object(self.m, "CONFIG_DIR", Path(tmp)),
            patch.object(self.m, "INSTALLS_JSON", Path(tmp) / "installs.json"),
            patch.object(self.m, "_gog_info_raw", return_value=(info, "")),
        ]

    def _ns(self, path):
        import types
        return types.SimpleNamespace(store="gog", app_id="99", path=path,
                                     lang="", platform="windows", ppid=0)

    def _stream_ok(self, seen):
        def fake(cmd, store, ppid=0):
            seen["cmd"] = list(cmd)
            return True
        return fake

    def test_repair_path_es_carpeta(self):
        # Dir borrado + manifest: repair IN-PLACE (dir esperado), la
        # puerta muere después porque nada escribió (simulado).
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            base, patches = self._env(tmp)
            seen = {}
            with patches[0], patches[1], patches[2], \
                    mock.patch.object(self.m, "_gog_manifest_source",
                                      return_value="old"), \
                    mock.patch.object(self.m, "_run_streaming",
                                      side_effect=self._stream_ok(seen)), \
                    mock.patch.object(self.m, "emit", lambda e: None):
                with self.assertRaises(SystemExit):
                    self.m.cmd_install(self._ns(str(base)))
            idx = seen["cmd"].index("--path")
            self.assertEqual(seen["cmd"][idx + 1], str(base / "Juego"))

    def test_download_path_es_base(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            base, patches = self._env(tmp)
            (base / "Juego").mkdir()
            (base / "Juego" / "goggame-99.info").write_text("{}")
            seen = {}
            with patches[0], patches[1], patches[2], \
                    mock.patch.object(self.m, "_gog_manifest_source",
                                      return_value=""), \
                    mock.patch.object(self.m, "_run_streaming",
                                      side_effect=self._stream_ok(seen)), \
                    mock.patch.object(self.m, "_gog_probe",
                                      return_value=(str(base / "Juego"),
                                                    "Juego.exe", "Windows")), \
                    mock.patch.object(self.m, "emit", lambda e: None):
                self.m.cmd_install(self._ns(str(base)))
            idx = seen["cmd"].index("--path")
            self.assertEqual(seen["cmd"][idx + 1], str(base))

    def test_base_con_exe_sueltos_muere(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            base, patches = self._env(tmp)
            (base / "Suelto.exe").write_bytes(b"x")
            with patches[0], patches[1], patches[2], \
                    mock.patch.object(self.m, "_gog_manifest_source",
                                      return_value=""), \
                    mock.patch.object(self.m, "_run_streaming",
                                      side_effect=self._stream_ok({})), \
                    mock.patch.object(self.m, "emit", lambda e: None):
                with self.assertRaises(SystemExit) as cm:
                    self.m.cmd_install(self._ns(str(base)))
                self.assertEqual(cm.exception.code, 3)


class StatusCacheInvalidate(unittest.TestCase):
    """Invalidación pura del caché de status tras install/uninstall."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_invalida_existente(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / ".status_cache.json"
            cache.write_text('{"ts": 1, "payload": {}}')
            with mock.patch.object(self.m, "STATUS_CACHE", cache):
                self.assertTrue(self.m._status_cache_invalidate())
                self.assertFalse(cache.exists())

    def test_ausente_ok(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / ".status_cache.json"
            with mock.patch.object(self.m, "STATUS_CACHE", cache):
                self.assertTrue(self.m._status_cache_invalidate())


class GogInstallPath(unittest.TestCase):
    """Sin --path: error. Con --path: ese valor exacto."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _ns(self, path):
        import types
        return types.SimpleNamespace(store="gog", app_id="99", path=path,
                                     lang="", platform="windows", ppid=0)

    def test_sin_path_muere(self):
        for bad in ("", "   "):
            with self.assertRaises(SystemExit) as cm:
                self.m.cmd_install(self._ns(bad))
            self.assertEqual(cm.exception.code, 2)

    def test_con_path_usa_valor(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "Base"
            base.mkdir()
            (base / "Juego").mkdir()
            (base / "Juego" / "goggame-99.info").write_text("{}")
            info = {"folder_name": "Juego", "languages": ["en-US"],
                    "builds": {"items": [{"os": "windows"}]}}
            seen = {}
            events = []

            def fake_stream(cmd, store, ppid=0):
                seen["cmd"] = list(cmd)
                return True

            with mock.patch.object(self.m, "CONFIG_DIR", Path(tmp)), \
                    mock.patch.object(self.m, "INSTALLS_JSON",
                                      Path(tmp) / "installs.json"), \
                    mock.patch.object(self.m, "_gog_info_raw",
                                      return_value=(info, "")), \
                    mock.patch.object(self.m, "_run_streaming",
                                      side_effect=fake_stream), \
                    mock.patch.object(self.m, "_gog_probe",
                                      return_value=(str(base / "Juego"),
                                                    "Juego.exe", "Windows")), \
                    mock.patch.object(self.m, "emit", events.append):
                self.m.cmd_install(self._ns(str(base)))
            idx = seen["cmd"].index("--path")
            # download (sin manifest en tmp): --path es la base tal cual.
            self.assertEqual(seen["cmd"][idx + 1], str(base))
            done = [e for e in events if e.get("type") == "done"][0]
            self.assertEqual(done["install_path"], str(base / "Juego"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
